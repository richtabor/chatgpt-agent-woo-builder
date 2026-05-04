#!/usr/bin/env python3
"""Copy the starter blueprint seed into a target blueprint bundle and rewrite its identifiers.

Reads the starter bundle at `blueprints/assembler-blueprint/`, copies its
editable theme, content, catalog, and media sources into `<target>/<slug>/`,
and rewrites `assembler` / `Assembler` to the bundle slug and title.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from _bundle_paths import bundle_stem_name, list_theme_source_dirs, resolve_bundle_dir


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_THEME_SLUG = "assembler"
SOURCE_THEME_TITLE = "Assembler"
EDITABLE_SUFFIXES = {".php", ".json", ".html", ".md", ".txt", ".css"}
BASE_BLUEPRINT = REPO_ROOT / "blueprints" / "assembler-blueprint"
BASE_THEME = BASE_BLUEPRINT / SOURCE_THEME_SLUG
BASE_BLUEPRINT_JSON = BASE_BLUEPRINT / "blueprint.json"
BASE_CONTENT_XML = BASE_BLUEPRINT / "content.xml"
BASE_PRODUCTS_CSV = BASE_BLUEPRINT / "products.csv"
BASE_ASSETS_DIR = BASE_BLUEPRINT / "assets"
UPSTREAM_IMAGE_PREFIX = "https://raw.githubusercontent.com/RegionallyFamous/fifty/main/obel/playground/images/"
BUNDLE_ASSET_PREFIX = "woo-assets://"
CATALOG_TEMPLATE_FILES = (
    "templates/archive-product.html",
    "templates/product-search-results.html",
    "templates/taxonomy-product_attribute.html",
)


def normalize_slug(raw: str) -> str:
    slug = raw.strip().lower()
    if not slug:
        raise ValueError("Theme slug must contain at least one letter or digit.")
    if not re.fullmatch(r"[a-z0-9]+", slug):
        raise ValueError(
            "Theme slug must be one word using only letters and digits, for example `fieldnote`."
        )
    return slug


def title_case(slug: str) -> str:
    return slug[:1].upper() + slug[1:]


def php_prefix(slug: str) -> str:
    return slug.replace("-", "_")


def format_bullets(items: list[str] | None, *, empty: str) -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item.strip()}" for item in items if item.strip())


def catalog_grid_columns(catalog_size: str | None) -> int | None:
    if not catalog_size:
        return None

    normalized = catalog_size.strip().lower()
    if not normalized:
        return None

    if "one product" in normalized or normalized in {"single", "single product"}:
        return 1
    if "small" in normalized:
        return 2
    if "medium" in normalized:
        return 3
    if "large" in normalized:
        return 4
    return None


def format_shop_template_notes(catalog_size: str | None) -> list[str]:
    columns = catalog_grid_columns(catalog_size)
    if columns is None:
        return [
            "- Catalog archive grids: default to 4 columns until the brief says otherwise.",
            "- Applies to `templates/archive-product.html`, `templates/product-search-results.html`, and `templates/taxonomy-product_attribute.html`.",
            "- The actual source of truth is the block setting inside those template files; this README records the intent.",
        ]

    column_label = "1 column" if columns == 1 else f"{columns} columns"
    scope_label = catalog_size.strip()
    return [
        f"- Catalog archive grids: {column_label} on desktop.",
        "- Applies to `templates/archive-product.html`, `templates/product-search-results.html`, and `templates/taxonomy-product_attribute.html`.",
        f"- Basis: starter catalog scope `{scope_label}`.",
        "- The actual source of truth is the block setting inside those template files; this README records the intent.",
    ]


def apply_catalog_template_defaults(theme_dir: Path, catalog_size: str | None) -> int:
    columns = catalog_grid_columns(catalog_size)
    if columns is None:
        return 0

    updated_files = 0
    pattern = re.compile(r'("displayLayout"\s*:\s*\{[^{}]*"columns"\s*:\s*)(\d+)')

    for relative_path in CATALOG_TEMPLATE_FILES:
        path = theme_dir / relative_path
        if not path.is_file():
            continue

        text = path.read_text(encoding="utf-8")
        normalized = text.replace(',"className":"wc-adaptive-catalog-grid"', "")
        normalized = normalized.replace(' wc-adaptive-catalog-grid', "")
        updated_text, replacements = pattern.subn(rf"\g<1>{columns}", normalized, count=1)
        if replacements == 0 or updated_text == text:
            if normalized != text:
                path.write_text(normalized, encoding="utf-8")
                updated_files += 1
            continue

        path.write_text(updated_text, encoding="utf-8")
        updated_files += 1

    return updated_files


def write_bundle_readme(
    target: Path,
    *,
    slug: str,
    title: str,
    store_description: str | None,
    catalog_size: str | None,
    vibe: str | None,
    must_haves: list[str] | None,
    must_avoids: list[str] | None,
) -> Path:
    readme_path = target / "README.md"
    if readme_path.exists():
        return readme_path

    store_text = store_description.strip() if store_description else "Not captured during scaffold."
    catalog_text = catalog_size.strip() if catalog_size else "Not captured during scaffold."
    vibe_text = vibe.strip() if vibe else "Not captured during scaffold. Add the intended store vibe here."
    must_haves_text = format_bullets(
        must_haves,
        empty="Add any fixed brand cues, must-have layout ideas, or merchandising constraints.",
    )
    must_avoids_text = format_bullets(
        must_avoids,
        empty="Add any visual directions or patterns this store should avoid.",
    )
    shop_templates_text = format_shop_template_notes(catalog_size)

    lines = [
        f"# {title} Blueprint",
        "",
        "This file is the durable brief for the blueprint. Keep the store concept and visual direction here so future agents and humans can recover intent without re-reading chat history.",
        "",
        "## Summary",
        "",
        f"- Slug: `{slug}`",
        f"- Store: {store_text}",
        f"- Catalog scope: {catalog_text}",
        "",
        "## Vibe",
        "",
        vibe_text,
        "",
        "## Must Keep",
        "",
        *must_haves_text.splitlines(),
        "",
        "## Must Avoid",
        "",
        *must_avoids_text.splitlines(),
        "",
        "## Shop Templates",
        "",
        *shop_templates_text,
        "",
        "## Source Of Truth",
        "",
        f"- `{slug}/`: theme design source",
        "- `content.xml`: editorial and site content source",
        "- `products.csv`: catalog source",
        "- `assets/`: bundle-local media source",
        "- `blueprint.json`: Studio and Playground setup recipe",
        "- `theme.zip`: optional Playground/export artifact, not local Studio apply input",
    ]
    readme = "\n".join(lines) + "\n"
    readme_path.write_text(readme, encoding="utf-8")
    return readme_path


def replace_in_file(
    path: Path,
    *,
    old_lower: str,
    new_lower: str,
    old_title: str,
    new_title: str,
    new_php_prefix: str,
) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    new_text = text.replace(old_title, new_title)
    if path.suffix.lower() == ".php":
        new_text = new_text.replace(f"{old_lower}_", f"{new_php_prefix}_")
    new_text = new_text.replace(old_lower, new_lower)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def seed_content(target: Path) -> list[Path]:
    created: list[Path] = []

    content_xml = target / "content.xml"
    products_csv = target / "products.csv"
    assets_dir = target / "assets"

    if BASE_CONTENT_XML.is_file():
        shutil.copy2(BASE_CONTENT_XML, content_xml)
        content_xml.write_text(
            content_xml.read_text(encoding="utf-8").replace(
                UPSTREAM_IMAGE_PREFIX,
                BUNDLE_ASSET_PREFIX,
            ),
            encoding="utf-8",
        )
        created.append(content_xml)

    if BASE_PRODUCTS_CSV.is_file():
        shutil.copy2(BASE_PRODUCTS_CSV, products_csv)
        products_csv.write_text(
            products_csv.read_text(encoding="utf-8").replace(
                UPSTREAM_IMAGE_PREFIX,
                BUNDLE_ASSET_PREFIX,
            ),
            encoding="utf-8",
        )
        created.append(products_csv)

    if BASE_ASSETS_DIR.is_dir():
        shutil.copytree(
            BASE_ASSETS_DIR,
            assets_dir,
            ignore=shutil.ignore_patterns(".DS_Store"),
        )
        created.append(assets_dir)

    return created


def seed_blueprint_json(
    target: Path,
    *,
    title: str,
    store_description: str | None,
) -> Path | None:
    if not BASE_BLUEPRINT_JSON.is_file():
        return None

    blueprint_path = target / "blueprint.json"
    payload = json.loads(BASE_BLUEPRINT_JSON.read_text(encoding="utf-8"))
    meta = payload.setdefault("meta", {})
    if isinstance(meta, dict):
        meta["title"] = title
        if store_description and store_description.strip():
            meta["description"] = store_description.strip()
        elif (
            not isinstance(meta.get("description"), str)
            or not meta["description"].strip()
        ):
            meta["description"] = f"{title} WooCommerce storefront blueprint."

    blueprint_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return blueprint_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument(
        "theme_slug",
        nargs="?",
        help="Deprecated explicit theme slug. Omit it; new blueprints use the bundle slug as the theme slug.",
    )
    parser.add_argument(
        "--store-description",
        default=None,
        help="Short description of what the store sells. Used to seed the bundle README.",
    )
    parser.add_argument(
        "--catalog-size",
        default=None,
        help="Short catalog scope note such as `small catalog (2-10)` or `medium catalog (11-100)`.",
    )
    parser.add_argument(
        "--vibe",
        default=None,
        help="Short visual brief or vibe summary. Used to seed the bundle README.",
    )
    parser.add_argument(
        "--must-have",
        action="append",
        dest="must_haves",
        default=None,
        help="Repeatable note for fixed brand cues or must-have directions in the bundle README.",
    )
    parser.add_argument(
        "--must-avoid",
        action="append",
        dest="must_avoids",
        default=None,
        help="Repeatable note for must-avoid directions in the bundle README.",
    )
    args = parser.parse_args()

    target = resolve_bundle_dir(args.target)
    inferred_slug = bundle_stem_name(target)
    try:
        slug = normalize_slug(inferred_slug)
    except ValueError as exc:
        raise SystemExit(str(exc))
    if args.theme_slug is not None:
        explicit_slug = normalize_slug(args.theme_slug)
        if explicit_slug != slug:
            raise SystemExit(
                f"Theme slug must match the bundle slug for new blueprints: expected `{slug}`, got `{explicit_slug}`."
            )
    theme_dir = target / slug
    title = title_case(slug)
    symbol_prefix = php_prefix(slug)

    if not BASE_THEME.is_dir():
        raise SystemExit(f"Base theme not found: {BASE_THEME}")
    if not BASE_CONTENT_XML.is_file():
        raise SystemExit(f"Base content.xml not found: {BASE_CONTENT_XML}")
    if not BASE_PRODUCTS_CSV.is_file():
        raise SystemExit(f"Base products.csv not found: {BASE_PRODUCTS_CSV}")
    if not BASE_ASSETS_DIR.is_dir():
        raise SystemExit(f"Base assets directory not found: {BASE_ASSETS_DIR}")

    existing_theme_dirs = list_theme_source_dirs(target)
    source_names = ("README.md", "content.xml", "products.csv", "assets", "blueprint.json")
    conflicts = [target / name for name in source_names if (target / name).exists()]
    if theme_dir.exists():
        conflicts.append(theme_dir)
    for existing_theme_dir in existing_theme_dirs:
        if existing_theme_dir not in conflicts:
            conflicts.append(existing_theme_dir)
    if conflicts:
        raise SystemExit(
            f"Target bundle already has source files. Refusing to overwrite: {target}"
        )

    theme_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        BASE_THEME,
        theme_dir,
        ignore=shutil.ignore_patterns(".DS_Store", "languages"),
    )
    created = seed_content(target)
    blueprint_path = seed_blueprint_json(
        target,
        title=title,
        store_description=args.store_description,
    )
    if blueprint_path is not None:
        created.append(blueprint_path)
    catalog_template_updates = apply_catalog_template_defaults(theme_dir, args.catalog_size)
    readme_path = write_bundle_readme(
        target,
        slug=slug,
        title=title,
        store_description=args.store_description,
        catalog_size=args.catalog_size,
        vibe=args.vibe,
        must_haves=args.must_haves,
        must_avoids=args.must_avoids,
    )
    created.append(readme_path)

    changed = 0
    for path in theme_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in EDITABLE_SUFFIXES:
            if replace_in_file(
                path,
                old_lower=SOURCE_THEME_SLUG,
                new_lower=slug,
                old_title=SOURCE_THEME_TITLE,
                new_title=title,
                new_php_prefix=symbol_prefix,
            ):
                changed += 1

    print(f"Created {theme_dir}")
    for path in created:
        print(f"Seeded {path}")
    if catalog_template_updates:
        print(
            f"Seeded shop template block settings from catalog size in {catalog_template_updates} template files"
        )
    print(f"Rewrote identifiers to slug={slug} title={title}")
    print(f"Updated {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
