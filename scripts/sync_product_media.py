#!/usr/bin/env python3
"""Attach bundle-local product images to imported WooCommerce products.

This repairs a gap in the initial CSV import flow:

- `products.csv` is the source of truth for product rows
- bundle `assets/` are copied into site uploads by `apply_content.py`
- this script reads the CSV image filenames, creates attachment posts from
  the copied upload files, and assigns featured/gallery images by SKU

The script is idempotent:
- products are looked up by SKU
- attachments are reused by `_woo_creator_asset_filename`
- re-running will re-assert the expected image/gallery IDs without
  duplicating media entries
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from _bundle_paths import resolve_bundle_dir


RUNTIME_EVAL_PATH = "/wordpress/.woo-creator-sync-product-media.php"


def run(command: list[str]) -> None:
    proc = subprocess.run(command, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.stderr:
            print(proc.stderr.strip(), file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, command, output=proc.stdout, stderr=proc.stderr)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle_dir",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument("site_path", help="Studio site path.")
    return parser.parse_args()


def image_filenames(cell: str) -> list[str]:
    filenames: list[str] = []
    seen: set[str] = set()
    for raw in cell.split(","):
        value = raw.strip()
        if not value:
            continue
        if value.startswith("woo-assets://"):
            filename = value.removeprefix("woo-assets://").strip()
        else:
            filename = Path(urlparse(value).path).name.strip()
        if not filename or filename in seen:
            continue
        seen.add(filename)
        filenames.append(filename)
    return filenames


def build_mapping(bundle_dir: Path, site_path: Path) -> list[dict[str, object]]:
    csv_path = bundle_dir / "products.csv"
    uploads_dir = site_path / "wp-content" / "uploads" / "woo-creator-assets"
    if not csv_path.is_file() or not uploads_dir.is_dir():
        return []

    rows: list[dict[str, object]] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_type = (row.get("Type") or "").strip().lower()
            if row_type == "variation":
                continue
            sku = (row.get("SKU") or "").strip()
            if not sku:
                continue
            filenames = [
                name
                for name in image_filenames(row.get("Images") or "")
                if (uploads_dir / name).is_file()
            ]
            if not filenames:
                continue
            rows.append({"sku": sku, "images": filenames})
    return rows


def build_eval_script(mapping: list[dict[str, object]]) -> str:
    payload = json.dumps(mapping, separators=(",", ":"))
    return f"""<?php
if ( ! defined( 'ABSPATH' ) ) {{
\texit;
}}

if ( ! class_exists( 'WooCommerce' ) ) {{
\techo 'WooCommerce not active; skipped product media sync';
\treturn;
}}

require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/media.php';

$mapping = json_decode( <<<'JSON'
{payload}
JSON, true );

$asset_dir      = WP_CONTENT_DIR . '/uploads/woo-creator-assets';
$asset_url_base = trailingslashit( content_url( 'uploads/woo-creator-assets' ) );
$products       = 0;
$created        = 0;
$missing        = 0;

foreach ( $mapping as $item ) {{
\t$sku = isset( $item['sku'] ) ? (string) $item['sku'] : '';
\tif ( '' === $sku ) {{
\t\tcontinue;
\t}}

\t$product_id = wc_get_product_id_by_sku( $sku );
\tif ( ! $product_id ) {{
\t\tcontinue;
\t}}

\t$attachment_ids = array();
\tforeach ( (array) ( $item['images'] ?? array() ) as $filename ) {{
\t\t$relative = ltrim( str_replace( '\\\\', '/', (string) $filename ), '/' );
\t\t$relative = preg_replace( '#(^|/)\.\.(?:/|$)#', '/', $relative );
\t\t$relative = trim( $relative, '/' );
\t\tif ( '' === $relative ) {{
\t\t\tcontinue;
\t\t}}
\t\t$basename = wp_basename( $relative );

\t\t$file = trailingslashit( $asset_dir ) . $relative;
\t\tif ( ! file_exists( $file ) ) {{
\t\t\t$missing++;
\t\t\tcontinue;
\t\t}}

\t\t$existing = get_posts(
\t\t\tarray(
\t\t\t\t'post_type'      => 'attachment',
\t\t\t\t'posts_per_page' => 1,
\t\t\t\t'fields'         => 'ids',
\t\t\t\t'meta_key'       => '_woo_creator_asset_filename',
\t\t\t\t'meta_value'     => $relative,
\t\t\t\t'no_found_rows'  => true,
\t\t\t)
\t\t);
\t\tif ( ! empty( $existing ) ) {{
\t\t\t$attachment_ids[] = (int) $existing[0];
\t\t\tcontinue;
\t\t}}

\t\t$filetype   = wp_check_filetype( $basename, null );
\t\t$asset_url  = $asset_url_base . implode( '/', array_map( 'rawurlencode', explode( '/', $relative ) ) );
\t\t$attachment = array(
\t\t\t'post_mime_type' => $filetype['type'] ?: 'image/jpeg',
\t\t\t'post_title'     => preg_replace( '/\\.[^.]+$/', '', $basename ),
\t\t\t'post_content'   => '',
\t\t\t'post_status'    => 'inherit',
\t\t\t'guid'           => $asset_url,
\t\t);
\t\t$attachment_id = wp_insert_attachment( $attachment, $file, $product_id );
\t\tif ( is_wp_error( $attachment_id ) || ! $attachment_id ) {{
\t\t\t$missing++;
\t\t\tcontinue;
\t\t}}

\t\t$metadata = wp_generate_attachment_metadata( (int) $attachment_id, $file );
\t\tif ( ! is_wp_error( $metadata ) && ! empty( $metadata ) ) {{
\t\t\twp_update_attachment_metadata( (int) $attachment_id, $metadata );
\t\t}}
\t\tupdate_post_meta( (int) $attachment_id, '_woo_creator_asset_filename', $relative );
\t\tupdate_post_meta( (int) $attachment_id, '_wo_source_url', $asset_url );
\t\t$attachment_ids[] = (int) $attachment_id;
\t\t$created++;
\t}}

\tif ( empty( $attachment_ids ) ) {{
\t\tcontinue;
\t}}

\t$product = wc_get_product( $product_id );
\tif ( ! $product ) {{
\t\tcontinue;
\t}}

\t$attachment_ids = array_values( array_unique( array_map( 'intval', $attachment_ids ) ) );
\t$product->set_image_id( (int) $attachment_ids[0] );
\t$product->set_gallery_image_ids( array_slice( $attachment_ids, 1 ) );
\t$product->save();
\t$products++;
}}

echo wp_json_encode(
\tarray(
\t\t'products' => $products,
\t\t'created'  => $created,
\t\t'missing'  => $missing,
\t)
);
"""


def main() -> int:
    args = parse_args()
    bundle_dir = resolve_bundle_dir(args.bundle_dir)
    site_path = Path(args.site_path).expanduser().resolve()

    mapping = build_mapping(bundle_dir, site_path)
    if not mapping:
        print("Skipped product media sync; no mappable product images found.")
        return 0

    eval_path = site_path / ".woo-creator-sync-product-media.php"
    eval_path.write_text(build_eval_script(mapping), encoding="utf-8")
    try:
        run(
            [
                "studio",
                "wp",
                "eval-file",
                RUNTIME_EVAL_PATH,
                "--path",
                str(site_path),
            ]
        )
    finally:
        eval_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
