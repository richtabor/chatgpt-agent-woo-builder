# Interval Blueprint

Interval is a WordPress Playground-ready WooCommerce concept for urban run-club gear and race-day systems.

Included here:

- `blueprint.json`: bundled Playground blueprint
- `interval/`: block theme source
- `products.csv`: starter catalog
- `DESIGN.md`: canonical design spec used for implementation
- `PRODUCT.md`: supporting assortment direction
- `import-products.php`: CSV import script used by the blueprint

Notes:

- The blueprint installs WooCommerce from the WordPress plugin directory.
- The theme and catalog are bundled in this directory so the artifact can be zipped and run as a Blueprint bundle.
- Product images are attempted from remote URLs during import; if a remote fetch fails, the products still import.
