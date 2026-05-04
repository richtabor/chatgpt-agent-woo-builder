# AGENTS.md

Purpose

- This repo is a bundle-first WooCommerce storefront generator, not just a single theme.
- The main working unit is a blueprint bundle in `blueprints/<slug>-blueprint/`.
- Skills live in `.codex/skills/`, Python scripts in `scripts/`, and shared importer resources in `resources/importers/`.
- The neutral starter bundle is `blueprints/assembler-blueprint/`.

Facts observed in this checkout

- The default scaffold seed is `blueprints/assembler-blueprint/`.
- The importer script lives at `resources/importers/wo-import.php`.
- The main scripts are:
  - `scripts/scaffold_theme.py`
  - `scripts/variation_builder.py`
  - `scripts/write_blueprint.py`
  - `scripts/apply_content.py`
  - `scripts/import_products.py`
  - `scripts/configure_site.py`
  - `scripts/sync_product_media.py`
  - `scripts/prepare_block_validation.py`
  - `scripts/validate_block_manifest.py`
- The scripts expect the `wordpress-studio` MCP server (exposed by `studio mcp`) to be configured in the host agent.

Canonical file roles

- Top-level theme source directory named after the one-word blueprint slug: storefront design source of truth.
- `README.md`: durable store brief and vibe summary for future humans and agents.
- `content.xml`: pages, posts, attachments, and editorial content source of truth.
- `products.csv`: WooCommerce product source of truth.
- `assets/`: bundle-local media source of truth.
- `blueprint.json`: Studio/Playground setup recipe.
- `theme.zip`: optional Playground/export artifact generated from the theme source directory; do not hand-edit or require it for local Studio apply.
- `.block-validation/`: derived validation targets and manifest; not source of truth.
- `.studio-site/` or any local WordPress database state: applied state, not source of truth.
- `.studio-site/wp-content/themes/<slug>` may be a local symlink back to the bundle theme source for live iteration; it is not a second source tree.

Path conventions

- Working bundles belong under `blueprints/<slug>-blueprint/`.
- Bare blueprint slugs like `fieldnote` resolve to `blueprints/fieldnote-blueprint/`.
- For new blueprints, the bundle slug, theme directory name, and theme slug are the same one-word identifier.
- Generated store display names should also be one word unless the user explicitly requests a multi-word brand.

Expected workflow

1. Create or update a bundle under `blueprints/<slug>-blueprint/`.
2. Scaffold from the `assembler-blueprint` seed bundle:
   `python3 scripts/scaffold_theme.py <slug>`
3. Write or update `blueprint.json`:
   `python3 scripts/write_blueprint.py <slug>`
4. Apply the bundle to a local Studio site:
   `python3 scripts/apply_content.py <slug>`
5. Iterate by editing bundle source files, then re-run apply/build steps.
6. Generate `theme.zip` only for portable Playground/share flows:
   `python3 scripts/write_blueprint.py <slug> --theme-zip`

Important script behavior

- `write_blueprint.py` writes `blueprint.json` without `theme.zip` by default; pass `--theme-zip` to generate the portable theme install artifact and include `installTheme`.
- `apply_content.py` preserves an existing hand-edited `blueprint.json` by default and only rewrites it when `--refresh-blueprint` is passed.
- `write_blueprint.py` infers the installed theme slug from the `Text Domain` in `<slug>/style.css` when possible.
- `scaffold_theme.py` derives the theme slug from the blueprint slug for new blueprints.
- `scaffold_theme.py` copies the starter theme, content, catalog, and media from `blueprints/assembler-blueprint/`.
- `scaffold_theme.py` also creates a top-level bundle `README.md` and can seed it from the current store brief.
- `configure_site.py` applies site title, tagline, permalinks, and disables WooCommerce coming-soon/store-only gating after the site boots.
- `apply_content.py` copies bundle `assets/` into the local Studio uploads directory and rewrites imported page content away from temporary asset URLs.
- `apply_content.py` removes Blueprint theme install steps from the local runtime blueprint, links `.studio-site/wp-content/themes/<slug>` back to the bundle theme source after site creation, and activates that symlinked theme after Studio starts.
- `apply_content.py` also writes nested `.studio-site/AGENTS.md` guardrails so agents treat Studio paths as runtime state, not canonical source.
- `apply_content.py` can prepare `.block-validation/manifest.json` automatically after apply, and can optionally fail the apply when Studio block validation reports invalid content.
- `prepare_block_validation.py` materializes validation targets for templates, parts, patterns, and `content.xml` bodies.
- `validate_block_manifest.py` batch-runs Studio `validate_blocks` against the prepared manifest and exits nonzero on invalid blocks.
- `sync_product_media.py` attaches copied bundle images to imported WooCommerce products by SKU.

Editing rules

- Change design in the top-level theme source directory.
- Change durable brief/context in `README.md`.
- Change editorial/site content in `content.xml`.
- Change catalog rows in `products.csv`.
- Change media in `assets/`.
- Change environment/setup behavior in `blueprint.json` or the apply/build scripts.
- Fix block-validation failures in the authored source files, not in `.block-validation/` or `.studio-site/`.
- Use `woo-assets://<filename>` for bundle-local image references in `content.xml` and `products.csv`.
- Keep blueprint slugs distinctive and one word. `scaffold_theme.py` currently accepts lowercase letters and digits only.
- Do not treat `.studio-site/wp-content/themes/<slug>` as a separate authored copy of the theme, even when it exists locally.
- Prefer extending the existing scripts and references over introducing a parallel workflow.
- If you change file-role conventions or workflow steps, update:
  - `.codex/skills/woo-creator/SKILL.md`
  - `.codex/skills/woo-creator/references/blueprint-layout.md`
  - `.codex/agents/*.toml`
  - `.codex/config.toml`
  - `.codex/hooks.json`

Known prerequisites and uncertainty

- Fact: the scripts expect the `studio` CLI to be installed.
- Fact: `scaffold_theme.py` reads its seed from `blueprints/assembler-blueprint/`.
- Fact: `import_products.py` runs the vendored importer at `resources/importers/wo-import.php`.
- I did not find an automated test suite in this checkout. Validation appears to be script execution plus inspection of the generated bundle and local Studio site.
