#!/usr/bin/env python3
"""Import WooCommerce products from a bundle-local `products.csv`.

This bridges the gap between the simplified blueprint bundle and the original
Playground importer model:

- `content.xml` carries pages, posts, attachments, and taxonomy content
- `products.csv` carries WooCommerce product rows

The importer reuses the vendored `resources/importers/wo-import.php`
implementation, but serves the bundle-local `products.csv` and `assets/`
through a temporary HTTP server so the import runs against editable source
files.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import functools
import http.server
import io
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from _bundle_paths import resolve_bundle_dir


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
IMPORTER_SCRIPT = REPO_ROOT / "resources" / "importers" / "wo-import.php"
UPSTREAM_IMAGE_PREFIX = "https://raw.githubusercontent.com/RegionallyFamous/fifty/main/obel/playground/images/"
BUNDLE_ASSET_PREFIX = "woo-assets://"
RUNTIME_EVAL_PATH = "/wordpress/.woo-creator-import.php"


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


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def strip_product_image_columns(csv_text: str) -> str:
    source = io.StringIO(csv_text)
    reader = csv.DictReader(source)
    if not reader.fieldnames or "Images" not in reader.fieldnames:
        return csv_text

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        row["Images"] = ""
        writer.writerow(row)
    return output.getvalue()


@contextlib.contextmanager
def bundle_server(bundle_dir: Path, products_csv: Path, assets_dir: Path, *, product_images: bool):
    with tempfile.TemporaryDirectory(prefix="woo-creator-products-") as temp_root:
        root = Path(temp_root)
        (root / "content").mkdir(parents=True, exist_ok=True)

        local_base_url = "http://127.0.0.1:0/"
        rewritten_csv = products_csv.read_text(encoding="utf-8")
        if not product_images:
            rewritten_csv = strip_product_image_columns(rewritten_csv)
        rewritten_csv = rewritten_csv.replace(
            UPSTREAM_IMAGE_PREFIX,
            local_base_url + "images/",
        )
        rewritten_csv = rewritten_csv.replace(
            BUNDLE_ASSET_PREFIX,
            local_base_url + "images/",
        )

        csv_path = root / "content" / "products.csv"
        csv_path.write_text(rewritten_csv, encoding="utf-8")

        linked_assets = root / "images"
        if linked_assets.exists():
            if linked_assets.is_symlink() or linked_assets.is_file():
                linked_assets.unlink()
            else:
                shutil.rmtree(linked_assets)
        os.symlink(assets_dir, linked_assets)

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
        with ReusableTCPServer(("127.0.0.1", 0), handler) as httpd:
            port = httpd.server_address[1]
            actual_base_url = f"http://127.0.0.1:{port}/"
            csv_path.write_text(
                rewritten_csv.replace(local_base_url, actual_base_url),
                encoding="utf-8",
            )

            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                yield actual_base_url
            finally:
                httpd.shutdown()
                thread.join(timeout=2)


def write_eval_file(site_path: Path, base_url: str) -> Path:
    importer_body = IMPORTER_SCRIPT.read_text(encoding="utf-8")
    stripped = importer_body.lstrip()
    if stripped.startswith("<?php"):
        stripped = stripped[5:].lstrip("\n")

    escaped_base_url = base_url.replace("\\", "\\\\").replace("'", "\\'")
    eval_path = site_path / ".woo-creator-import.php"
    eval_path.write_text(
        "<?php\n"
        f"define( 'WO_CONTENT_BASE_URL', '{escaped_base_url}' );\n"
        + stripped,
        encoding="utf-8",
    )
    return eval_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle_dir",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument("site_path", help="Studio site path.")
    parser.add_argument(
        "--product-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Import images from the products.csv Images column. Use --no-product-images for faster local test imports.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = resolve_bundle_dir(args.bundle_dir)
    site_path = Path(args.site_path).expanduser().resolve()
    products_csv = bundle_dir / "products.csv"
    assets_dir = bundle_dir / "assets"

    if not products_csv.is_file():
        print(f"Skipped product import; no products.csv at {products_csv}")
        return 0
    if not assets_dir.is_dir():
        print(f"Skipped product import; no assets directory at {assets_dir}")
        return 0
    if not IMPORTER_SCRIPT.is_file():
        raise SystemExit(f"Importer script not found: {IMPORTER_SCRIPT}")

    with bundle_server(bundle_dir, products_csv, assets_dir, product_images=args.product_images) as base_url:
        eval_file = write_eval_file(site_path, base_url)
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
            eval_file.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
