#!/usr/bin/env python3
"""Shared path helpers for repo-level Woo Creator blueprint bundles."""

from __future__ import annotations

import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPO_BLUEPRINTS_ROOT = REPO_ROOT / "blueprints"
BLUEPRINT_SUFFIX = "-blueprint"
LEGACY_THEME_DIR_NAME = "theme"


def default_bundle_dir_name(name: str) -> str:
    """Return the default repo directory name for a blueprint slug."""

    return name if name.endswith(BLUEPRINT_SUFFIX) else f"{name}{BLUEPRINT_SUFFIX}"


def bundle_stem_name(bundle_dir: str | Path) -> str:
    """Return the blueprint slug without the `-blueprint` suffix."""

    name = Path(bundle_dir).name
    if name.endswith(BLUEPRINT_SUFFIX):
        return name[: -len(BLUEPRINT_SUFFIX)]
    return name


def _resolve_bare_bundle_name(name: str) -> Path:
    """Resolve a bare blueprint slug, preferring the new `-blueprint` convention."""

    preferred = (REPO_BLUEPRINTS_ROOT / default_bundle_dir_name(name)).resolve()
    legacy = (REPO_BLUEPRINTS_ROOT / name).resolve()

    if preferred.exists():
        return preferred
    if legacy.exists():
        return legacy
    return preferred


def resolve_bundle_dir(raw: str | Path) -> Path:
    """Resolve a bundle arg into the repo-level `blueprints/` tree.

    Conventions:
    - absolute paths stay absolute
    - bare slugs like `fieldnote` resolve to `<repo>/blueprints/fieldnote-blueprint`
    - other relative paths resolve from the repo root, not the caller's cwd
    """

    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if len(candidate.parts) == 1:
        return _resolve_bare_bundle_name(candidate.name)
    return (REPO_ROOT / candidate).resolve()


def list_theme_source_dirs(bundle_dir: str | Path) -> list[Path]:
    """List top-level theme source directories inside a bundle.

    New bundles should use the actual theme name as the top-level directory name.
    A valid theme source directory contains `style.css` at its root. Older
    bundle shapes may still be detected for compatibility.
    """

    root = Path(bundle_dir)
    candidates: list[Path] = []
    legacy = root / LEGACY_THEME_DIR_NAME
    if legacy.is_dir():
        candidates.append(legacy)

    if not root.is_dir():
        return candidates

    for child in sorted(root.iterdir()):
        if child in candidates:
            continue
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        if (child / "style.css").is_file():
            candidates.append(child)

    return candidates


def resolve_theme_source_dir(bundle_dir: str | Path) -> Path:
    """Resolve the editable theme source directory inside a bundle."""

    candidates = list_theme_source_dirs(bundle_dir)
    if not candidates:
        root = Path(bundle_dir)
        raise ValueError(
            "Missing required theme source directory in "
            f"{root}. Expected a top-level theme-name directory containing `style.css`."
        )
    if len(candidates) > 1:
        raise ValueError(
            "Multiple possible theme source directories found in "
            f"{Path(bundle_dir)}: {', '.join(path.name for path in candidates)}"
        )
    return candidates[0]


def slugify(value: str) -> str:
    """Normalize arbitrary text into a WordPress-style slug."""

    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug


def infer_theme_slug(theme_dir: str | Path) -> str:
    """Infer the installed theme slug from `style.css` or the directory name."""

    root = Path(theme_dir)
    style_css = root / "style.css"
    if style_css.is_file():
        text = style_css.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"^\s*Text\s+Domain:\s*(.+?)\s*$", text, re.MULTILINE)
        if match:
            slug = slugify(match.group(1))
            if slug:
                return slug
    return slugify(root.name) or "woo-theme"
