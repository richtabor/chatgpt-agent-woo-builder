<?php
/**
 * Title: New Arrivals Product Grid with Buttons
 * Slug: assembler/product-grid-new-arrivals-cta
 * Categories: products
 * Description: Three-column dynamic product grid with a centered heading and product purchase buttons.
 *
 * @package Assembler
 */
declare( strict_types = 1 );
?>

<!-- wp:group {"metadata":{"name":"New Arrivals Product Grid with Buttons","categories":["products"],"patternName":"assembler/product-grid-new-arrivals-cta"},"align":"full","className":"is-style-default","style":{"spacing":{"blockGap":"var:preset|spacing|30","margin":{"top":"0","bottom":"0"},"padding":{"top":"var:preset|spacing|40","bottom":"var:preset|spacing|40"}}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group alignfull is-style-default" style="margin-top:0;margin-bottom:0;padding-top:var(--wp--preset--spacing--40);padding-bottom:var(--wp--preset--spacing--40)"><!-- wp:heading {"textAlign":"center","align":"wide","className":"slot-heading"} -->
<h2 class="wp-block-heading alignwide has-text-align-center slot-heading">New arrivals</h2>
<!-- /wp:heading -->

<!-- wp:woocommerce/product-collection {"queryId":0,"query":{"perPage":6,"pages":1,"offset":0,"postType":"product","order":"desc","orderBy":"date","search":"","exclude":[],"inherit":false,"taxQuery":{},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock","outofstock","onbackorder"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[],"timeFrame":{"operator":"in","value":"-30 days"},"filterable":false,"relatedBy":{"categories":true,"tags":true}},"tagName":"div","displayLayout":{"type":"flex","columns":3,"shrinkColumns":true},"dimensions":{"widthType":"fill"},"collection":"woocommerce/product-collection/new-arrivals","hideControls":["inherit","order","filterable"],"queryContextIncludes":["collection"],"__privatePreviewState":{"isPreview":false,"previewMessage":"Actual products will vary depending on the page being viewed."},"align":"wide"} -->
<div class="wp-block-woocommerce-product-collection alignwide"><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"showSaleBadge":false,"imageSizing":"thumbnail","isDescendentOfQueryLoop":true,"style":{"dimensions":{"aspectRatio":"3/4"},"spacing":{"margin":{"bottom":"var:preset|spacing|20"}}}} -->
<!-- wp:woocommerce/product-sale-badge {"align":"right"} /-->
<!-- /wp:woocommerce/product-image -->

<!-- wp:group {"style":{"spacing":{"blockGap":"var:preset|spacing|20"}},"layout":{"type":"flex","orientation":"vertical","justifyContent":"center","flexWrap":"nowrap"}} -->
<div class="wp-block-group"><!-- wp:post-title {"textAlign":"left","level":3,"isLink":true,"style":{"layout":{"selfStretch":"fill","flexSize":null}},"__woocommerceNamespace":"woocommerce/product-collection/product-title"} /-->

<!-- wp:woocommerce/product-price {"isDescendentOfQueryLoop":true,"textAlign":"left"} /--></div>
<!-- /wp:group -->

<!-- wp:woocommerce/product-button {"width":50,"isDescendentOfQueryLoop":true,"style":{"spacing":{"margin":{"bottom":"var:preset|spacing|30"}}}} /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection --></div>
<!-- /wp:group -->
