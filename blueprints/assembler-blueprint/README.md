# Assembler Blueprint

This bundle is the neutral Woo Creator seed blueprint. New storefront bundles are scaffolded from this shape, then renamed and constrained by the incoming store brief.

## Summary

- Slug: `assembler`
- Store: neutral starter WooCommerce storefront content for testing theme, catalog, and media import flows.
- Catalog scope: broad demo catalog with simple, variable, grouped, external, virtual, and downloadable products.

## Vibe

Neutral Assembler baseline. Keep this bundle portable: the theme should remain useful as a starter storefront, and the catalog/media should prove import behavior without becoming the default brand direction for generated stores.

## Must Keep

- One-word theme slug and theme directory: `assembler`.
- Bundle-local media in `assets/` referenced with `woo-assets://<filename>`.
- Block-native pages and templates suitable for Studio block validation.
- Enough content and products to exercise WooCommerce import, media sync, static front-page setup, and product archive rendering.

## Must Avoid

- Store-specific brand opinions that would leak into generated blueprints.
- Runtime state such as `.studio-site/` or `.block-validation/`.
- Treating `theme.zip` as source or as required for local Studio apply.

## Shop Templates

- Catalog archive grids: default starter layout from the Assembler theme.
- Applies to `templates/archive-product.html`, `templates/product-search-results.html`, and `templates/taxonomy-product_attribute.html`.
- Generated storefronts may override the column count during scaffold from the requested catalog size.

## Source Of Truth

- `assembler/`: theme design source
- `content.xml`: editorial and site content source
- `products.csv`: catalog source
- `assets/`: bundle-local media source
- `blueprint.json`: Studio and Playground setup recipe
- `theme.zip`: optional Playground/export artifact, not local Studio apply input
