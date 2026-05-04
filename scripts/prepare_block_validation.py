#!/usr/bin/env python3
"""Materialize Woo Creator block-validation targets for Studio MCP validation.

This script does not run Studio validation itself. Instead, it creates a
derived manifest plus any extracted/rendered block-content files that the
`validate_blocks` MCP tool can consume directly:

- theme `templates/*.html` and `parts/*.html` are referenced directly
- theme `patterns/*.php` are rendered through a small PHP stub into `.html`
- `content.xml` page/post bodies are extracted into `.html`
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from _bundle_paths import resolve_bundle_dir, resolve_theme_source_dir, slugify


SCRIPT_DIR = Path(__file__).resolve().parent
PHP_STUB = SCRIPT_DIR / "_block_validation_php_stub.php"
DEFAULT_OUTPUT_DIRNAME = ".block-validation"
WXR_NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "wp": "http://wordpress.org/export/1.2/",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "blueprint_dir",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument(
        "--site-path",
        default=None,
        help="Optional Studio site path to include in the manifest for later MCP calls.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for derived validation targets. Defaults to <bundle>/.block-validation/.",
    )
    return parser.parse_args()


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def render_pattern(pattern_path: Path) -> str:
    proc = subprocess.run(
        ["php", str(PHP_STUB), str(pattern_path)],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or f"php exited {proc.returncode}"
        raise RuntimeError(f"{pattern_path}: {stderr}")
    return proc.stdout


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.strip()
    path.write_text((normalized + "\n") if normalized else "", encoding="utf-8")


def theme_file_targets(theme_dir: Path) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for surface in ("templates", "parts"):
        root = theme_dir / surface
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.html")):
            rel = path.relative_to(theme_dir).as_posix()
            targets.append(
                {
                    "kind": "theme-file",
                    "surface": surface[:-1],
                    "source_path": str(path),
                    "validate_file": str(path),
                    "label": rel,
                }
            )
    return targets


def pattern_targets(theme_dir: Path, output_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    targets: list[dict[str, str]] = []
    warnings: list[str] = []
    patterns_dir = theme_dir / "patterns"
    if not patterns_dir.is_dir():
        return targets, warnings

    rendered_root = output_dir / "patterns"
    for path in sorted(patterns_dir.rglob("*.php")):
        try:
            rendered = render_pattern(path)
        except RuntimeError as exc:
            warnings.append(str(exc))
            continue
        if "<!-- wp:" not in rendered:
            continue
        rel = path.relative_to(theme_dir).with_suffix(".html")
        validate_path = rendered_root / rel
        write_text(validate_path, rendered)
        targets.append(
            {
                "kind": "rendered-pattern",
                "surface": "pattern",
                "source_path": str(path),
                "validate_file": str(validate_path),
                "label": path.relative_to(theme_dir).as_posix(),
            }
        )
    return targets, warnings


def content_xml_targets(bundle_dir: Path, output_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    targets: list[dict[str, str]] = []
    warnings: list[str] = []
    content_xml = bundle_dir / "content.xml"
    if not content_xml.is_file():
        return targets, warnings

    try:
        root = ET.parse(content_xml).getroot()
    except ET.ParseError as exc:
        warnings.append(f"{content_xml}: XML parse failed: {exc}")
        return targets, warnings

    extracted_root = output_dir / "content"
    channel = root.find("./channel")
    if channel is None:
        warnings.append(f"{content_xml}: missing <channel>")
        return targets, warnings

    for index, item in enumerate(channel.findall("./item"), start=1):
        body = item.findtext("content:encoded", namespaces=WXR_NAMESPACES) or ""
        if "<!-- wp:" not in body:
            continue

        title = (item.findtext("title") or "").strip()
        post_type = (item.findtext("wp:post_type", namespaces=WXR_NAMESPACES) or "item").strip() or "item"
        post_name = (item.findtext("wp:post_name", namespaces=WXR_NAMESPACES) or "").strip()
        slug = slugify(post_name or title) or f"item-{index}"
        validate_path = extracted_root / f"{post_type}-{slug}.html"
        write_text(validate_path, body)

        targets.append(
            {
                "kind": "wxr-item",
                "surface": post_type,
                "source_path": str(content_xml),
                "validate_file": str(validate_path),
                "label": f"{post_type}:{slug}",
                "title": title,
                "post_type": post_type,
                "post_name": post_name,
            }
        )

    return targets, warnings


def build_manifest(bundle_dir: Path, output_dir: Path, site_path: str | None) -> tuple[dict[str, object], list[str]]:
    theme_dir = resolve_theme_source_dir(bundle_dir)
    ensure_clean_dir(output_dir)

    targets = theme_file_targets(theme_dir)
    warnings: list[str] = []

    pattern_results, pattern_warnings = pattern_targets(theme_dir, output_dir)
    targets.extend(pattern_results)
    warnings.extend(pattern_warnings)

    content_results, content_warnings = content_xml_targets(bundle_dir, output_dir)
    targets.extend(content_results)
    warnings.extend(content_warnings)

    counts: dict[str, int] = {}
    for target in targets:
        kind = str(target["kind"])
        counts[kind] = counts.get(kind, 0) + 1

    manifest: dict[str, object] = {
        "bundle_dir": str(bundle_dir),
        "theme_dir": str(theme_dir),
        "site_path": site_path,
        "output_dir": str(output_dir),
        "counts": counts,
        "targets": targets,
    }
    if warnings:
        manifest["warnings"] = warnings
    return manifest, warnings


def main() -> int:
    args = parse_args()
    bundle_dir = resolve_bundle_dir(args.blueprint_dir)
    if not bundle_dir.is_dir():
        raise SystemExit(f"Blueprint bundle directory not found: {bundle_dir}")

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else (bundle_dir / DEFAULT_OUTPUT_DIRNAME).resolve()
    )

    manifest, warnings = build_manifest(bundle_dir, output_dir, args.site_path)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    total_targets = len(manifest["targets"])  # type: ignore[index]
    print(f"Wrote {manifest_path}")
    print(f"Prepared {total_targets} block-validation target(s)")
    for kind, count in sorted((manifest["counts"] or {}).items()):  # type: ignore[union-attr]
        print(f"- {kind}: {count}")

    if warnings:
        print("Warnings:", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
