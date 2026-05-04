#!/usr/bin/env python3
"""Create or recreate a local Studio site from a storefront blueprint bundle.

Local Studio applies use the live bundle theme source via symlink instead of
installing a generated theme zip.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

from _bundle_paths import infer_theme_slug, resolve_bundle_dir, resolve_theme_source_dir


SCRIPT_DIR = Path(__file__).resolve().parent
WRITE_BLUEPRINT_SCRIPT = SCRIPT_DIR / "write_blueprint.py"
CONFIGURE_SITE_SCRIPT = SCRIPT_DIR / "configure_site.py"
IMPORT_PRODUCTS_SCRIPT = SCRIPT_DIR / "import_products.py"
SYNC_PRODUCT_MEDIA_SCRIPT = SCRIPT_DIR / "sync_product_media.py"
PREPARE_BLOCK_VALIDATION_SCRIPT = SCRIPT_DIR / "prepare_block_validation.py"
VALIDATE_BLOCK_MANIFEST_SCRIPT = SCRIPT_DIR / "validate_block_manifest.py"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "password"
DEFAULT_ADMIN_EMAIL = "admin@localhost.com"
UPSTREAM_IMAGE_PREFIX = "https://raw.githubusercontent.com/RegionallyFamous/fifty/main/obel/playground/images/"
BUNDLE_ASSET_PREFIX = "woo-assets://"
RUNTIME_CONTENT_NAME = "content.runtime.xml"
RUNTIME_BLUEPRINT_NAME = "blueprint.runtime.json"
RUNTIME_PRODUCT_IMPORT_PATH = "/wordpress/woo-creator-import.php"


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(command, check=False, text=True, capture_output=True)
    if check and proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.stderr:
            print(proc.stderr.strip(), file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, command, output=proc.stdout, stderr=proc.stderr)
    return proc


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def ensure_blueprint(bundle_dir: Path, refresh: bool) -> Path:
    blueprint_path = bundle_dir / "blueprint.json"
    if blueprint_path.exists() and not refresh:
        return blueprint_path

    cmd = [sys.executable, str(WRITE_BLUEPRINT_SCRIPT), str(bundle_dir), "--no-theme-zip"]
    proc = run(cmd)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)
    return blueprint_path


def load_site_configuration(blueprint_path: Path) -> dict[str, str]:
    try:
        payload = json.loads(blueprint_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return {}

    config: dict[str, str] = {}
    title = meta.get("title")
    if isinstance(title, str) and title.strip():
        config["blogname"] = title.strip()

    description = meta.get("description")
    if isinstance(description, str):
        config["blogdescription"] = description.strip()

    return config


def load_site_status(site_path: Path) -> dict[str, object]:
    proc = run(
        ["studio", "site", "status", "--path", str(site_path), "--format", "json"],
        check=False,
    )
    if not proc.stdout:
        return {}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def php_single_quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@contextlib.contextmanager
def serve_bundle_assets(bundle_dir: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(bundle_dir))
    with ReusableTCPServer(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        base_url = f"http://127.0.0.1:{port}/"
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield base_url
        finally:
            httpd.shutdown()
            thread.join(timeout=2)


def build_runtime_blueprint(bundle_dir: Path, source_blueprint_path: Path, asset_base_url: str) -> Path:
    source_content = bundle_dir / "content.xml"
    assets_dir = bundle_dir / "assets"

    runtime_content = bundle_dir / RUNTIME_CONTENT_NAME
    runtime_blueprint = bundle_dir / RUNTIME_BLUEPRINT_NAME

    payload = json.loads(source_blueprint_path.read_text(encoding="utf-8"))
    steps = payload.get("steps")
    if isinstance(steps, list):
        def is_local_runtime_excluded_step(step: object) -> bool:
            if not isinstance(step, dict):
                return False
            if step.get("step") in {"installTheme", "activateTheme"}:
                return True
            if step.get("step") == "writeFile" and step.get("path") == RUNTIME_PRODUCT_IMPORT_PATH:
                return True
            if (
                step.get("step") == "wp-cli"
                and step.get("command") == f"wp eval-file {RUNTIME_PRODUCT_IMPORT_PATH}"
            ):
                return True
            return False

        payload["steps"] = [
            step
            for step in steps
            if not is_local_runtime_excluded_step(step)
        ]
        for step in payload["steps"]:
            if not isinstance(step, dict):
                continue
            if step.get("step") != "importWxr":
                continue
            file_block = step.get("file")
            if not isinstance(file_block, dict):
                continue
            resource = file_block.get("resource")
            if resource not in {"bundled", "url"}:
                continue
            if resource == "bundled" and file_block.get("path") != "/content.xml":
                continue
            if not source_content.is_file() or not assets_dir.is_dir():
                continue
            rewritten_content = source_content.read_text(encoding="utf-8").replace(
                UPSTREAM_IMAGE_PREFIX,
                asset_base_url + "assets/",
            )
            rewritten_content = rewritten_content.replace(
                BUNDLE_ASSET_PREFIX,
                asset_base_url + "assets/",
            )
            runtime_content.write_text(rewritten_content, encoding="utf-8")
            file_block["resource"] = "bundled"
            file_block.pop("url", None)
            file_block["path"] = f"/{RUNTIME_CONTENT_NAME}"
            step["file"] = file_block

    runtime_blueprint.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return runtime_blueprint


def studio_site_exists(site_path: Path) -> bool:
    proc = run(
        ["studio", "site", "status", "--path", str(site_path), "--format", "json"],
        check=False,
    )
    return proc.returncode == 0


def sync_bundle_assets(bundle_dir: Path, site_path: Path, site_url: str) -> str | None:
    assets_dir = bundle_dir / "assets"
    if not assets_dir.is_dir():
        return None

    target_dir = site_path / "wp-content" / "uploads" / "woo-creator-assets"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(assets_dir, target_dir, ignore=shutil.ignore_patterns(".DS_Store"))
    return site_url.rstrip("/") + "/wp-content/uploads/woo-creator-assets/"


def write_studio_guardrails(bundle_dir: Path, site_path: Path, theme_dir: Path, theme_slug: str) -> None:
    """Write nested AGENTS instructions into `.studio-site/` runtime paths."""

    studio_agents = site_path / "AGENTS.md"
    themes_agents = site_path / "wp-content" / "themes" / "AGENTS.md"

    studio_agents.parent.mkdir(parents=True, exist_ok=True)
    themes_agents.parent.mkdir(parents=True, exist_ok=True)

    studio_agents.write_text(
        "\n".join(
            [
                "# AGENTS.md",
                "",
                "This `.studio-site/` tree is local applied state for a Woo Creator bundle.",
                "",
                "Rules:",
                f"- Theme source of truth: `{theme_dir}`",
                f"- Content source of truth: `{bundle_dir / 'content.xml'}`",
                f"- Product source of truth: `{bundle_dir / 'products.csv'}`",
                f"- Asset source of truth: `{bundle_dir / 'assets'}`",
                "- Do not treat files in `.studio-site/` as the canonical source of truth.",
                f"- If `.studio-site/wp-content/themes/{theme_slug}` exists, it is local runtime theme state for `{theme_dir}`.",
                "- Make source edits in the bundle unless the task explicitly targets local Studio runtime state or WordPress database state.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    themes_agents.write_text(
        "\n".join(
            [
                "# AGENTS.md",
                "",
                "This directory contains local Studio theme runtime state.",
                "",
                "Rules:",
                f"- Canonical theme source: `{theme_dir}`",
                f"- Do not treat `.studio-site/wp-content/themes/{theme_slug}` as a second source tree.",
                f"- If `{theme_slug}` is symlinked here, edits through this path still affect `{theme_dir}`.",
                f"- Prefer opening and editing `{theme_dir}` directly so the source-of-truth path stays explicit.",
                "- Only work under `.studio-site/wp-content/themes/` when a task explicitly targets local Studio runtime debugging.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def link_bundle_theme(bundle_dir: Path, site_path: Path) -> str:
    """Expose the bundle theme source inside the local Studio site via symlink."""

    theme_dir = resolve_theme_source_dir(bundle_dir)
    theme_slug = infer_theme_slug(theme_dir)
    themes_root = site_path / "wp-content" / "themes"
    linked_theme = themes_root / theme_slug

    themes_root.mkdir(parents=True, exist_ok=True)
    write_studio_guardrails(bundle_dir, site_path, theme_dir, theme_slug)
    if linked_theme.is_symlink():
        try:
            if linked_theme.resolve() == theme_dir.resolve():
                return theme_slug
        except FileNotFoundError:
            pass
        linked_theme.unlink()
    elif linked_theme.exists():
        if linked_theme.is_file():
            linked_theme.unlink()
        else:
            shutil.rmtree(linked_theme)

    linked_theme.symlink_to(theme_dir, target_is_directory=True)
    return theme_slug


def activate_theme(site_path: Path, theme_slug: str) -> None:
    proc = run(
        [
            "studio",
            "wp",
            "theme",
            "activate",
            theme_slug,
            "--path",
            str(site_path),
        ]
    )
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)


def rewrite_content_asset_urls(site_path: Path, old_base_url: str, new_base_url: str | None) -> None:
    if not old_base_url or not new_base_url:
        return

    old_value = php_single_quoted(old_base_url)
    new_value = php_single_quoted(new_base_url)
    proc = run(
        [
            "studio",
            "wp",
            "eval",
            (
                f"$old = '{old_value}'; "
                f"$new = '{new_value}'; "
                "global $wpdb; "
                "$needle = '%' . $wpdb->esc_like($old) . '%'; "
                "$posts = $wpdb->get_results($wpdb->prepare("
                "\"SELECT ID, post_content, post_excerpt FROM {$wpdb->posts} "
                "WHERE post_content LIKE %s OR post_excerpt LIKE %s\", "
                "$needle, $needle)); "
                "$count = 0; "
                "foreach ($posts as $post) { "
                "$content = str_replace($old, $new, $post->post_content); "
                "$excerpt = str_replace($old, $new, $post->post_excerpt); "
                "if ($content === $post->post_content && $excerpt === $post->post_excerpt) { continue; } "
                "$wpdb->update($wpdb->posts, "
                "['post_content' => $content, 'post_excerpt' => $excerpt], "
                "['ID' => $post->ID]); "
                "clean_post_cache($post->ID); "
                "$count++; "
                "} "
                "echo 'Rewrote asset URLs in ' . $count . ' posts';"
            ),
            "--path",
            str(site_path),
        ]
    )
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)


def delete_site(site_path: Path) -> None:
    if studio_site_exists(site_path):
        proc = run(
            ["studio", "site", "delete", "--path", str(site_path), "--files"],
            check=False,
        )
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.stderr:
            print(proc.stderr.strip(), file=sys.stderr)
    if site_path.exists():
        shutil.rmtree(site_path, ignore_errors=True)


def delete_default_fallback_sites(site_path: Path) -> None:
    """Remove timestamped fallback Studio sites for the default `.studio-site` path."""

    if site_path.name != ".studio-site":
        return

    for fallback_site_path in sorted(site_path.parent.glob(".studio-site-*")):
        if fallback_site_path == site_path:
            continue
        delete_site(fallback_site_path)


def create_site(
    site_path: Path,
    *,
    blueprint_path: Path,
    wp_version: str,
    php_version: str,
    name: str | None,
    domain: str | None,
    admin_username: str,
    admin_password: str,
    admin_email: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        "studio",
        "site",
        "create",
        "--path",
        str(site_path),
        "--blueprint",
        str(blueprint_path),
        "--wp",
        wp_version,
        "--php",
        php_version,
        "--admin-username",
        admin_username,
        "--admin-password",
        admin_password,
        "--admin-email",
        admin_email,
        "--skip-browser",
        "--skip-log-details",
        "--no-start",
    ]

    if name:
        command.extend(["--name", name])
    if domain:
        command.extend(["--domain", domain, "--https"])
    return run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "blueprint_dir",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument(
        "--site-path",
        default=None,
        help="Studio site path. Defaults to <blueprint_dir>/.studio-site.",
    )
    parser.add_argument("--name", default=None, help="Studio site display name.")
    parser.add_argument("--wp", default="latest", help="WordPress version.")
    parser.add_argument("--php", default="8.3", help="PHP version.")
    parser.add_argument("--domain", default=None, help="Custom local domain.")
    parser.add_argument(
        "--admin-username",
        default=DEFAULT_ADMIN_USERNAME,
        help="Studio admin username. Defaults to admin.",
    )
    parser.add_argument(
        "--admin-password",
        default=DEFAULT_ADMIN_PASSWORD,
        help="Studio admin password. Defaults to password for local review sites.",
    )
    parser.add_argument(
        "--admin-email",
        default=DEFAULT_ADMIN_EMAIL,
        help="Studio admin email. Defaults to admin@localhost.com.",
    )
    parser.add_argument("--blogname", default=None, help="Override site title after creation.")
    parser.add_argument("--blogdescription", default=None, help="Override site tagline after creation.")
    parser.add_argument(
        "--permalink-structure",
        default="/%postname%/",
        help="Permalink structure to apply after the site is created.",
    )
    parser.add_argument(
        "--recreate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Delete and recreate the Studio site when it already exists.",
    )
    parser.add_argument(
        "--refresh-blueprint",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Rewrite blueprint.json before applying the site. Off by default so manual blueprint edits remain the source of truth.",
    )
    parser.add_argument(
        "--start",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Start the site after creation.",
    )
    parser.add_argument(
        "--prepare-block-validation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Regenerate the derived .block-validation manifest after apply.",
    )
    parser.add_argument(
        "--validate-blocks",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run Studio block validation against the derived manifest after apply.",
    )
    parser.add_argument(
        "--product-images",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Import and sync product images. Interactive runs ask when this is omitted; "
            "non-interactive runs keep the historical default and include images."
        ),
    )
    return parser.parse_args()


def should_import_product_images(choice: bool | None) -> bool:
    if choice is not None:
        return choice
    if not sys.stdin.isatty():
        return True

    answer = input("Import product images too? This is slower. [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def main() -> int:
    args = parse_args()
    bundle_dir = resolve_bundle_dir(args.blueprint_dir)
    if not bundle_dir.is_dir():
        raise SystemExit(f"Blueprint bundle directory not found: {bundle_dir}")
    product_images = should_import_product_images(args.product_images)

    site_path = (
        Path(args.site_path).expanduser().resolve()
        if args.site_path
        else bundle_dir / ".studio-site"
    )
    blueprint_path = ensure_blueprint(bundle_dir, refresh=args.refresh_blueprint)
    site_config = load_site_configuration(blueprint_path)

    if args.blogname is not None:
        site_config["blogname"] = args.blogname
    if args.blogdescription is not None:
        site_config["blogdescription"] = args.blogdescription

    if args.recreate:
        delete_site(site_path)
        delete_default_fallback_sites(site_path)
    elif studio_site_exists(site_path):
        print(f"Site already exists at {site_path}")
        return 0

    actual_site_path = site_path
    runtime_blueprint_path = blueprint_path
    runtime_content_path = bundle_dir / RUNTIME_CONTENT_NAME
    derived_blueprint_path = bundle_dir / RUNTIME_BLUEPRINT_NAME
    imported_asset_base_url = ""
    with serve_bundle_assets(bundle_dir) as asset_base_url:
        imported_asset_base_url = asset_base_url + "assets/"
        runtime_blueprint_path = build_runtime_blueprint(bundle_dir, blueprint_path, asset_base_url)
        try:
            proc = create_site(
                actual_site_path,
                blueprint_path=runtime_blueprint_path,
                wp_version=args.wp,
                php_version=args.php,
                name=args.name,
                domain=args.domain,
                admin_username=args.admin_username,
                admin_password=args.admin_password,
                admin_email=args.admin_email,
            )
        except subprocess.CalledProcessError:
            if not args.recreate:
                raise
            fallback_site_path = site_path.with_name(f"{site_path.name}-{int(time.time())}")
            print(
                "Studio path reuse failed; retrying with a fresh site path:",
                fallback_site_path,
                file=sys.stderr,
            )
            proc = create_site(
                fallback_site_path,
                blueprint_path=runtime_blueprint_path,
                wp_version=args.wp,
                php_version=args.php,
                name=args.name,
                domain=args.domain,
                admin_username=args.admin_username,
                admin_password=args.admin_password,
                admin_email=args.admin_email,
            )
            actual_site_path = fallback_site_path

    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)

    linked_theme_slug = link_bundle_theme(bundle_dir, actual_site_path)
    print(
        "Linked Studio theme:",
        actual_site_path / "wp-content" / "themes" / linked_theme_slug,
        "->",
        resolve_theme_source_dir(bundle_dir),
    )

    if args.start:
        started = run(
            [
                "studio",
                "site",
                "start",
                "--path",
                str(actual_site_path),
                "--skip-browser",
                "--skip-log-details",
            ]
        )
        if started.stdout:
            print(started.stdout.strip())
        if started.stderr:
            print(started.stderr.strip(), file=sys.stderr)

        activate_theme(actual_site_path, linked_theme_slug)

        imported = run(
            [
                sys.executable,
                str(IMPORT_PRODUCTS_SCRIPT),
                str(bundle_dir),
                str(actual_site_path),
                "--product-images" if product_images else "--no-product-images",
            ]
        )
        if imported.stdout:
            print(imported.stdout.strip())
        if imported.stderr:
            print(imported.stderr.strip(), file=sys.stderr)

        configure_command = [sys.executable, str(CONFIGURE_SITE_SCRIPT), str(actual_site_path)]
        if "blogname" in site_config:
            configure_command.extend(["--blogname", site_config["blogname"]])
        if "blogdescription" in site_config:
            configure_command.extend(["--blogdescription", site_config["blogdescription"]])
        configure_command.extend(["--permalink-structure", args.permalink_structure])

        configured = run(configure_command)
        if configured.stdout:
            print(configured.stdout.strip())
        if configured.stderr:
            print(configured.stderr.strip(), file=sys.stderr)

        site_status = load_site_status(actual_site_path)
        site_url = site_status.get("siteUrl")
        if isinstance(site_url, str) and site_url:
            local_assets_url = sync_bundle_assets(bundle_dir, actual_site_path, site_url)
            rewrite_content_asset_urls(
                actual_site_path,
                imported_asset_base_url,
                local_assets_url,
            )
            if product_images:
                synced_media = run(
                    [
                        sys.executable,
                        str(SYNC_PRODUCT_MEDIA_SCRIPT),
                        str(bundle_dir),
                        str(actual_site_path),
                    ]
                )
                if synced_media.stdout:
                    print(synced_media.stdout.strip())
                if synced_media.stderr:
                    print(synced_media.stderr.strip(), file=sys.stderr)
            else:
                print("Skipped product media sync because product images were disabled.")
    else:
        print("Skipped theme activation and configure_site.py because --no-start was set.")

    final_status = load_site_status(actual_site_path)
    if final_status:
        try:
            print(json.dumps(final_status, indent=2))
        except TypeError:
            pass

    if args.prepare_block_validation:
        prepared = run(
            [
                sys.executable,
                str(PREPARE_BLOCK_VALIDATION_SCRIPT),
                str(bundle_dir),
                "--site-path",
                str(actual_site_path),
            ],
            check=False,
        )
        if prepared.stdout:
            print(prepared.stdout.strip())
        if prepared.stderr:
            print(prepared.stderr.strip(), file=sys.stderr)

    if args.validate_blocks:
        if not args.start:
            print("Skipped block validation because --no-start was set.", file=sys.stderr)
        else:
            validated = run(
                [
                    sys.executable,
                    str(VALIDATE_BLOCK_MANIFEST_SCRIPT),
                    str(bundle_dir),
                    "--site-path",
                    str(actual_site_path),
                ],
                check=False,
            )
            if validated.stdout:
                print(validated.stdout.strip())
            if validated.stderr:
                print(validated.stderr.strip(), file=sys.stderr)
            if validated.returncode != 0:
                return validated.returncode

    if runtime_blueprint_path == derived_blueprint_path:
        derived_blueprint_path.unlink(missing_ok=True)
    runtime_content_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
