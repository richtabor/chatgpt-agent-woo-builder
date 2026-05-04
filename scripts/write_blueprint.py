#!/usr/bin/env python3
"""Write or update a minimal `blueprint.json` for a storefront bundle.

The bundle layout for v1 is:

    <bundle>/
      blueprint.json
      content.xml         # optional
      assets/             # optional
      <theme-slug>/       # required, editable source
      theme.zip           # optional generated Playground install artifact
      screenshot.jpg      # optional

This script keeps the bundle simple:
- the top-level theme source directory stays editable
- `theme.zip` can be regenerated from that theme source directory for portable Playground exports
- `content.xml` is imported via `importWxr` when present
- generated blueprints land on `/` and, when canonical Home/Journal pages exist,
  wire the static front page and posts page immediately after import
- site title, tagline, and permalinks are still applied later by
  `configure_site.py` after Studio boots the site
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import quote

from _bundle_paths import (
    REPO_ROOT,
    bundle_stem_name,
    infer_theme_slug,
    resolve_bundle_dir,
    resolve_theme_source_dir,
)


SCHEMA_URL = "https://playground.wordpress.net/blueprint-schema.json"
IMPORTER_SCRIPT = (
    Path(__file__).resolve().parent.parent / "resources" / "importers" / "wo-import.php"
)


def build_theme_zip(bundle_dir: Path) -> tuple[Path, str, Path]:
    theme_dir = resolve_theme_source_dir(bundle_dir)

    theme_slug = infer_theme_slug(theme_dir)
    zip_path = bundle_dir / "theme.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(theme_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name == ".DS_Store":
                continue
            relative_path = path.relative_to(theme_dir)
            archive_path = Path(theme_slug) / relative_path
            archive.write(path, archive_path.as_posix())

    return zip_path, theme_slug, theme_dir


def front_page_bootstrap_code() -> str:
    return (
        "<?php require_once '/wordpress/wp-load.php'; "
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
        "echo 'Front page configured'; "
        "} else { "
        "echo 'Front page skipped'; "
        "}"
    )


def php_file_without_open_tag(path: Path) -> str:
    body = path.read_text(encoding="utf-8")
    stripped = body.lstrip()
    if stripped.startswith("<?php"):
        return stripped[5:].lstrip("\n")
    return body


def product_import_steps(bundle_dir: Path, github_repo_url: str, github_ref: str) -> list[dict]:
    products_csv = bundle_dir / "products.csv"
    if not products_csv.is_file():
        return []
    if not IMPORTER_SCRIPT.is_file():
        raise FileNotFoundError(f"Product importer script not found: {IMPORTER_SCRIPT}")

    base_url = github_raw_url(
        github_repo_url,
        github_ref,
        bundle_dir.relative_to(REPO_ROOT).as_posix(),
    ).rstrip("/") + "/"
    base_php = base_url.replace("\\", "\\\\").replace("'", "\\'")
    importer_body = php_file_without_open_tag(IMPORTER_SCRIPT)

    return [
        {
            "step": "writeFile",
            "path": "/wordpress/woo-creator-import.php",
            "data": (
                "<?php\n"
                f"define( 'WO_CONTENT_BASE_URL', '{base_php}' );\n"
                + importer_body
            ),
        },
        {
            "step": "wp-cli",
            "command": "wp eval-file /wordpress/woo-creator-import.php",
        },
    ]


def build_blueprint_payload(
    bundle_dir: Path,
    *,
    theme_zip_name: str | None,
    github_repo_url: str | None,
    github_ref: str,
    title: str,
    description: str,
    author: str,
    categories: list[str],
    login: bool,
    permalink_structure: str,
) -> dict:
    content_xml = bundle_dir / "content.xml"

    steps: list[dict] = [
        {
            "step": "defineWpConfigConsts",
            "consts": {
                "WP_DEVELOPMENT_MODE": "theme",
            },
        },
        {"step": "resetData"},
        {
            "step": "installPlugin",
            "pluginData": {
                "resource": "wordpress.org/plugins",
                "slug": "woocommerce",
            },
            "options": {
                "activate": True,
            },
        },
    ]

    if github_repo_url is not None:
        theme_dir = resolve_theme_source_dir(bundle_dir)
        theme_slug = infer_theme_slug(theme_dir)
        steps.append(
            {
                "step": "installTheme",
                "themeData": {
                    "resource": "git:directory",
                    "url": github_repo_url,
                    "ref": github_ref,
                    "refType": "branch",
                    "path": theme_dir.relative_to(REPO_ROOT).as_posix(),
                },
                "options": {
                    "activate": True,
                    "targetFolderName": theme_slug,
                },
            }
        )
    elif theme_zip_name is not None:
        steps.append(
            {
                "step": "installTheme",
                "themeData": {
                    "resource": "bundled",
                    "path": f"/{theme_zip_name}",
                },
                "options": {
                    "activate": True,
                },
            }
        )

    if github_repo_url is not None:
        steps.extend(product_import_steps(bundle_dir, github_repo_url, github_ref))

    if content_xml.is_file():
        content_resource = {
            "resource": "bundled",
            "path": "/content.xml",
        }
        if github_repo_url is not None:
            content_resource = {
                "resource": "url",
                "url": github_raw_url(
                    github_repo_url,
                    github_ref,
                    content_xml.relative_to(REPO_ROOT).as_posix(),
                ),
            }
        steps.append(
            {
                "step": "importWxr",
                "file": content_resource,
            }
        )
        steps.append(
            {
                "step": "runPHP",
                "code": front_page_bootstrap_code(),
            }
        )

    payload = {
        "$schema": SCHEMA_URL,
        "meta": {
            "title": title,
            "description": description,
            "author": author,
            "categories": categories,
        },
        "landingPage": "/",
        "login": login,
        "steps": steps,
    }

    if github_repo_url is not None:
        payload["preferredVersions"] = {"php": "8.3", "wp": "latest"}
        payload["features"] = {"networking": True}
        if product_import_steps(bundle_dir, github_repo_url, github_ref):
            payload["extraLibraries"] = ["wp-cli"]

    return payload


def normalize_github_repo_url(raw: str) -> str:
    repo = raw.strip()
    if repo.endswith(".git"):
        repo = repo[:-4]
    if repo.startswith("git@github.com:"):
        repo = "https://github.com/" + repo.removeprefix("git@github.com:")
    if repo.startswith("https://github.com/"):
        return repo.rstrip("/")
    raise ValueError(
        "--github-repo-url must be a GitHub repository URL like "
        "https://github.com/owner/repo"
    )


def discover_github_repo_url() -> str | None:
    env_value = os.environ.get("WOO_CREATOR_GITHUB_REPO_URL")
    if env_value:
        return normalize_github_repo_url(env_value)

    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "config", "--get", "remote.origin.url"],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return normalize_github_repo_url(proc.stdout.strip())
    return None


def github_raw_url(repo_url: str, ref: str, repo_relative_path: str) -> str:
    normalized = normalize_github_repo_url(repo_url)
    owner_repo = normalized.removeprefix("https://github.com/")
    encoded_path = "/".join(quote(part) for part in repo_relative_path.split("/"))
    return f"https://raw.githubusercontent.com/{owner_repo}/{quote(ref)}/{encoded_path}"


def default_title(bundle_dir: Path) -> str:
    return bundle_stem_name(bundle_dir).replace("-", " ").replace("_", " ").strip().title() or "Woo Store"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "blueprint_dir",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument("--title", default=None, help="Blueprint title and site name.")
    parser.add_argument("--description", default="A WooCommerce storefront built with Woo Creator.")
    parser.add_argument("--author", default="Woo Creator")
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        default=None,
        help="Blueprint category. Repeat to add more than one.",
    )
    parser.add_argument(
        "--permalink-structure",
        default="/%postname%/",
        help="WordPress permalink structure to apply after import.",
    )
    parser.add_argument(
        "--login",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether the blueprint should auto-login.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for blueprint.json. Defaults to <blueprint_dir>/blueprint.json.",
    )
    parser.add_argument(
        "--artifacts-only",
        action="store_true",
        help="Only regenerate derived install artifacts such as theme.zip.",
    )
    parser.add_argument(
        "--theme-zip",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Generate theme.zip and include installTheme for portable Playground/export flows.",
    )
    parser.add_argument(
        "--hosted-github",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Write a portable Playground blueprint that installs the theme from "
            "a GitHub repository directory and imports content.xml from raw GitHub."
        ),
    )
    parser.add_argument(
        "--github-repo-url",
        default=None,
        help=(
            "GitHub repository URL for --hosted-github, e.g. "
            "https://github.com/owner/repo. Defaults to WOO_CREATOR_GITHUB_REPO_URL "
            "or git remote origin when available."
        ),
    )
    parser.add_argument(
        "--github-ref",
        default=os.environ.get("WOO_CREATOR_GITHUB_REF", "main"),
        help="Git branch/ref for --hosted-github. Defaults to WOO_CREATOR_GITHUB_REF or main.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = resolve_bundle_dir(args.blueprint_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    title = args.title or default_title(bundle_dir)
    categories = args.categories or ["Website", "WooCommerce"]
    output_path = Path(args.output).expanduser().resolve() if args.output else bundle_dir / "blueprint.json"

    theme_dir = resolve_theme_source_dir(bundle_dir)
    theme_slug = infer_theme_slug(theme_dir)
    theme_zip = None
    github_repo_url = None
    if args.hosted_github:
        github_repo_url = (
            normalize_github_repo_url(args.github_repo_url)
            if args.github_repo_url
            else discover_github_repo_url()
        )
        if github_repo_url is None:
            raise SystemExit(
                "--hosted-github requires --github-repo-url, WOO_CREATOR_GITHUB_REPO_URL, "
                "or a git remote origin."
            )

    if args.theme_zip or args.artifacts_only:
        theme_zip, theme_slug, theme_dir = build_theme_zip(bundle_dir)

    if args.artifacts_only:
        if theme_zip is None:
            print("Skipped theme.zip")
        else:
            print(f"Wrote {theme_zip}")
        print(f"Theme slug: {theme_slug}")
        print(f"Theme source: ./{theme_dir.name}")
        return 0

    payload = build_blueprint_payload(
        bundle_dir,
        theme_zip_name=theme_zip.name if theme_zip is not None else None,
        github_repo_url=github_repo_url,
        github_ref=args.github_ref,
        title=title,
        description=args.description,
        author=args.author,
        categories=categories,
        login=args.login,
        permalink_structure=args.permalink_structure,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {output_path}")
    if theme_zip is None:
        print("Skipped theme.zip")
    else:
        print(f"Wrote {theme_zip}")
    print(f"Title: {title}")
    print(f"Theme source: ./{theme_dir.name}")
    if github_repo_url is not None:
        print(
            "Theme install source:",
            f"{github_repo_url}@{args.github_ref}:{theme_dir.relative_to(REPO_ROOT).as_posix()}",
        )
        print(
            "Playground URL:",
            "https://playground.wordpress.net/?blueprint-url="
            + github_raw_url(
                github_repo_url,
                args.github_ref,
                output_path.relative_to(REPO_ROOT).as_posix(),
            ),
        )
    else:
        print(
            "Theme install artifact:",
            f"./{theme_zip.name}" if theme_zip is not None else "none",
        )
    print(f"Content import: {'yes' if (bundle_dir / 'content.xml').is_file() else 'no'}")
    print("Landing: baked into blueprint.json when canonical Home/Journal pages exist")
    print("Site options: title, tagline, and permalinks applied later via configure_site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
