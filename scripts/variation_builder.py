#!/usr/bin/env python3
"""Inspect and scaffold Woo Creator style variations for bundle themes."""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path

from _bundle_paths import resolve_bundle_dir, resolve_theme_source_dir, slugify


SCHEMA_URL = "https://schemas.wp.org/trunk/theme.json"
DEFAULT_VERSION = 3
COLOR_INDEX_RE = re.compile(r"^(?P<index>\d+)-")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_target(raw: str) -> tuple[Path, Path]:
    candidate = resolve_bundle_dir(raw)
    if (candidate / "style.css").is_file():
        return candidate.parent, candidate
    return candidate, resolve_theme_source_dir(candidate)


def styles_root(theme_dir: Path) -> Path:
    return theme_dir / "styles"


def read_brief_path(bundle_dir: Path) -> Path | None:
    readme = bundle_dir / "README.md"
    if readme.is_file():
        return readme
    return None


def classify_variation_path(theme_dir: Path, path: Path) -> tuple[str, str | None]:
    relative = path.relative_to(styles_root(theme_dir))
    parts = relative.parts
    if len(parts) == 1:
        return "styles", None
    bucket = parts[0]
    group = parts[1] if len(parts) > 2 else None
    return bucket, group


def infer_axes(payload: object) -> list[str]:
    axes: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"palette", "duotone", "gradients", "color"}:
                    axes.add("color")
                if key in {"typography", "fontFamilies", "fontSizes"}:
                    axes.add("typography")
                if key == "variations":
                    axes.add("sections")
                if key == "border":
                    axes.add("border")
                if key == "spacing":
                    axes.add("spacing")
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return sorted(axes)


def summarize_theme(theme_dir: Path) -> dict:
    theme_json = load_json(theme_dir / "theme.json")
    settings = theme_json.get("settings", {})
    styles = theme_json.get("styles", {})
    palette = settings.get("color", {}).get("palette", [])
    fonts = settings.get("typography", {}).get("fontFamilies", [])
    section_variations = sorted(styles.get("variations", {}).keys())
    return {
        "palette_count": len(palette),
        "palette_slugs": [item.get("slug") for item in palette if item.get("slug")],
        "font_family_slugs": [item.get("slug") for item in fonts if item.get("slug")],
        "section_variations": section_variations,
        "axes": infer_axes(theme_json),
    }


def summarize_variation(theme_dir: Path, path: Path) -> dict:
    payload = load_json(path)
    bucket, group = classify_variation_path(theme_dir, path)
    match = COLOR_INDEX_RE.match(path.stem)
    return {
        "path": path.relative_to(theme_dir).as_posix(),
        "title": payload.get("title"),
        "bucket": bucket,
        "group": group,
        "category": payload.get("category"),
        "personality": payload.get("personality", []),
        "keywords": payload.get("keywords", []),
        "axes": infer_axes(payload),
        "color_index": int(match.group("index")) if match else None,
    }


def collect_variations(theme_dir: Path) -> list[dict]:
    root = styles_root(theme_dir)
    if not root.is_dir():
        return []
    return [summarize_variation(theme_dir, path) for path in sorted(root.rglob("*.json"))]


def group_summary(variations: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str | None], list[dict]] = {}
    for item in variations:
        key = (item["bucket"], item["group"])
        grouped.setdefault(key, []).append(item)

    summary: list[dict] = []
    for (bucket, group), items in sorted(grouped.items(), key=lambda entry: (entry[0][0], entry[0][1] or "")):
        summary.append(
            {
                "bucket": bucket,
                "group": group,
                "count": len(items),
                "titles": [item["title"] for item in items[:5] if item.get("title")],
            }
        )
    return summary


def inspect(target: str) -> dict:
    bundle_dir, theme_dir = resolve_target(target)
    brief_path = read_brief_path(bundle_dir)
    variations = collect_variations(theme_dir)
    return {
        "bundle_dir": str(bundle_dir),
        "theme_dir": str(theme_dir),
        "brief_path": str(brief_path) if brief_path else None,
        "base_theme": summarize_theme(theme_dir),
        "variation_count": len(variations),
        "variation_groups": group_summary(variations),
        "variations": variations,
    }


def print_inspect_text(summary: dict) -> None:
    base = summary["base_theme"]
    print(f"Bundle: {summary['bundle_dir']}")
    print(f"Theme:  {summary['theme_dir']}")
    print(f"Brief:  {summary['brief_path'] or 'none'}")
    print(
        "Base:   "
        f"{base['palette_count']} palette colors, "
        f"{len(base['font_family_slugs'])} font families, "
        f"axes={', '.join(base['axes']) or 'none'}"
    )
    if base["section_variations"]:
        print(f"Sections: {', '.join(base['section_variations'])}")
    print(f"Variations: {summary['variation_count']}")
    for group in summary["variation_groups"]:
        label = group["bucket"]
        if group["group"]:
            label = f"{label}/{group['group']}"
        titles = ", ".join(group["titles"]) if group["titles"] else "no titles"
        print(f"- {label}: {group['count']} ({titles})")


def resolve_source_path(theme_dir: Path, raw: str | None) -> Path:
    if not raw:
        return theme_dir / "theme.json"

    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        theme_relative = (theme_dir / candidate).resolve()
        if theme_relative.exists():
            resolved = theme_relative
        else:
            resolved = (Path.cwd() / candidate).resolve()

    if not resolved.is_file():
        raise SystemExit(f"Variation source not found: {resolved}")
    return resolved


def select_source_payload(source: dict) -> dict:
    payload = {
        "$schema": source.get("$schema", SCHEMA_URL),
        "version": source.get("version", DEFAULT_VERSION),
    }

    if any(key in source for key in ("customTemplates", "templateParts", "patterns")):
        settings = source.get("settings", {})
        styles = source.get("styles", {})
        selected_settings = {}
        for key in ("color", "typography", "custom"):
            if key in settings:
                selected_settings[key] = deepcopy(settings[key])
        if selected_settings:
            payload["settings"] = selected_settings

        selected_styles = {}
        for key in ("color", "blocks", "elements", "typography", "variations"):
            if key in styles:
                selected_styles[key] = deepcopy(styles[key])
        if selected_styles:
            payload["styles"] = selected_styles
    else:
        for key, value in source.items():
            if key in {"$schema", "version", "title", "category", "personality", "keywords"}:
                continue
            payload[key] = deepcopy(value)

    return payload


def next_color_filename(theme_dir: Path, slug: str) -> str:
    root = styles_root(theme_dir) / "colors"
    highest = 0
    if root.is_dir():
        for path in root.glob("*.json"):
            match = COLOR_INDEX_RE.match(path.stem)
            if match:
                highest = max(highest, int(match.group("index")))
    return f"{highest + 1:02d}-{slug}.json"


def destination_path(theme_dir: Path, *, kind: str, slug: str, group: str | None) -> Path:
    root = styles_root(theme_dir)
    if kind == "style":
        return root / f"{slug}.json"
    if kind == "color":
        return root / "colors" / next_color_filename(theme_dir, slug)
    if kind == "typography":
        if group:
            return root / "typography" / slugify(group) / f"{slug}.json"
        return root / "typography" / f"{slug}.json"
    if kind == "block":
        if group:
            return root / "block" / slugify(group) / f"{slug}.json"
        return root / "block" / f"{slug}.json"
    raise ValueError(f"Unsupported kind: {kind}")


def build_payload(
    source_path: Path,
    *,
    title: str,
    category: str | None,
    personality: list[str] | None,
    keywords: list[str] | None,
) -> dict:
    source = load_json(source_path)
    selected = select_source_payload(source)
    payload = {
        "$schema": selected.pop("$schema", SCHEMA_URL),
        "version": selected.pop("version", DEFAULT_VERSION),
        "title": title,
    }

    inherited_category = source.get("category")
    inherited_personality = source.get("personality")
    inherited_keywords = source.get("keywords")

    if category or inherited_category:
        payload["category"] = category or inherited_category
    if personality or inherited_personality:
        payload["personality"] = personality or inherited_personality
    if keywords or inherited_keywords:
        payload["keywords"] = keywords or inherited_keywords

    payload.update(selected)
    return payload


def scaffold(
    target: str,
    *,
    title: str,
    slug: str | None,
    kind: str,
    group: str | None,
    source: str | None,
    category: str | None,
    personality: list[str] | None,
    keywords: list[str] | None,
    force: bool,
    dry_run: bool,
) -> tuple[Path, dict]:
    _, theme_dir = resolve_target(target)
    source_path = resolve_source_path(theme_dir, source)
    variation_slug = slugify(slug or title)
    if not variation_slug:
        raise SystemExit("Variation slug cannot be empty.")

    output_path = destination_path(theme_dir, kind=kind, slug=variation_slug, group=group)
    if output_path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing variation: {output_path}")

    payload = build_payload(
        source_path,
        title=title,
        category=category,
        personality=personality,
        keywords=keywords,
    )

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return output_path, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Summarize the current variation inventory.")
    inspect_parser.add_argument("target", help="Bundle slug, bundle directory, or theme directory.")
    inspect_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )

    scaffold_parser = subparsers.add_parser("scaffold", help="Create a starter variation JSON file.")
    scaffold_parser.add_argument("target", help="Bundle slug, bundle directory, or theme directory.")
    scaffold_parser.add_argument("--title", required=True, help="Human-readable variation title.")
    scaffold_parser.add_argument("--slug", default=None, help="Override the variation file slug.")
    scaffold_parser.add_argument(
        "--kind",
        choices=("style", "color", "typography", "block"),
        default="style",
        help="Destination variation bucket.",
    )
    scaffold_parser.add_argument("--group", default=None, help="Optional subgroup for typography or block variations.")
    scaffold_parser.add_argument(
        "--from",
        dest="source",
        default=None,
        help="Optional source JSON file. Defaults to theme.json.",
    )
    scaffold_parser.add_argument("--category", default=None, help="Optional variation category metadata.")
    scaffold_parser.add_argument(
        "--personality",
        action="append",
        default=None,
        help="Optional variation personality metadata. Repeat for more than one value.",
    )
    scaffold_parser.add_argument(
        "--keyword",
        dest="keywords",
        action="append",
        default=None,
        help="Optional variation keyword metadata. Repeat for more than one value.",
    )
    scaffold_parser.add_argument("--force", action="store_true", help="Overwrite an existing file.")
    scaffold_parser.add_argument("--dry-run", action="store_true", help="Do not write a file.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "inspect":
        summary = inspect(args.target)
        if args.format == "json":
            print(json.dumps(summary, indent=2))
        else:
            print_inspect_text(summary)
        return 0

    output_path, payload = scaffold(
        args.target,
        title=args.title,
        slug=args.slug,
        kind=args.kind,
        group=args.group,
        source=args.source,
        category=args.category,
        personality=args.personality,
        keywords=args.keywords,
        force=args.force,
        dry_run=args.dry_run,
    )
    action = "Would write" if args.dry_run else "Wrote"
    print(f"{action} {output_path}")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
