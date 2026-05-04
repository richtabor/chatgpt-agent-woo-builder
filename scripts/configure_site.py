#!/usr/bin/env python3
"""Apply a small set of site options to a Studio-managed local site.

Permalinks are configured via `WP_Rewrite::set_permalink_structure()` inside
`wp eval` instead of `wp rewrite structure`, matching the original Fifty
Playground flow. That path is more reliable in this environment.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    proc = subprocess.run(command, check=True, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)


def php_single_quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_path", help="Studio site path.")
    parser.add_argument("--blogname", default=None, help="Site title.")
    parser.add_argument("--blogdescription", default=None, help="Site tagline.")
    parser.add_argument(
        "--permalink-structure",
        default="/%postname%/",
        help="Permalink structure to set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    site_path = str(Path(args.site_path).expanduser().resolve())

    if args.blogname:
        run(["studio", "wp", "option", "update", "blogname", args.blogname, "--path", site_path])
    if args.blogdescription is not None:
        run(
            [
                "studio",
                "wp",
                "option",
                "update",
                "blogdescription",
                args.blogdescription,
                "--path",
                site_path,
            ]
        )

    permalink = php_single_quoted(args.permalink_structure)
    run(
        [
            "studio",
            "wp",
            "eval",
            (
                "global $wp_rewrite; "
                f"$wp_rewrite->set_permalink_structure('{permalink}'); "
                "$wp_rewrite->set_category_base(''); "
                "$wp_rewrite->set_tag_base(''); "
                "$wp_rewrite->flush_rules(true); "
                "delete_option('rewrite_rules'); "
                "echo 'Permalinks configured';"
            ),
            "--path",
            site_path,
        ]
    )

    # If the imported content includes canonical Home/Journal pages, use them
    # as the static front page and posts index, and force the Home page onto
    # the front-page template, so local Studio applies match the generated
    # blueprint contract even when an older blueprint is used.
    run(
        [
            "studio",
            "wp",
            "eval",
            (
                "$home = get_page_by_path('home'); "
                "$journal = get_page_by_path('journal'); "
                "if ( $home ) { "
                "update_post_meta((int) $home->ID, '_wp_page_template', 'front-page'); "
                "update_option('show_on_front', 'page'); "
                "update_option('page_on_front', (int) $home->ID); "
                "} "
                "if ( $journal ) { "
                "update_option('page_for_posts', (int) $journal->ID); "
                "} "
                "if ( $home ) { "
                "echo 'Reading settings configured'; "
                "} else { "
                "echo 'Reading settings skipped'; "
                "}"
            ),
            "--path",
            site_path,
        ]
    )

    # WooCommerce defaults new stores into "coming soon / store only" mode,
    # which replaces the product archive with the launch block. Local blueprint
    # previews are meant to render the actual storefront, so disable that
    # visibility gate when WooCommerce is active.
    run(
        [
            "studio",
            "wp",
            "eval",
            (
                "if ( class_exists('WooCommerce') ) { "
                "update_option('woocommerce_coming_soon', 'no'); "
                "update_option('woocommerce_store_pages_only', 'no'); "
                "update_option('woocommerce_feature_site_visibility_badge_enabled', 'no'); "
                "echo 'WooCommerce storefront opened'; "
                "} else { "
                "echo 'WooCommerce not active; skipped store visibility settings'; "
                "}"
            ),
            "--path",
            site_path,
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
