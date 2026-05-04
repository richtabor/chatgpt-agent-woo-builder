<?php
/**
 * Title: Offset Product Category Tiles
 * Slug: assembler/product-category-tiles-offset
 * Categories: featured, products
 * Description: Staggered three-column product category grid with oversized intro text and bold shop CTAs.
 *
 * @package Assembler
 */
declare( strict_types = 1 );
?>

<!-- wp:group {"metadata":{"name":"Product Categories","categories":["featured","products"],"patternName":"assembler/product-category-tiles-offset"},"align":"full","style":{"spacing":{"margin":{"top":"0","bottom":"0"},"padding":{"top":"var:preset|spacing|40","bottom":"var:preset|spacing|40","left":"var:preset|spacing|40","right":"var:preset|spacing|40"},"blockGap":"var:preset|spacing|40"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group alignfull" style="margin-top:0;margin-bottom:0;padding-top:var(--wp--preset--spacing--40);padding-right:var(--wp--preset--spacing--40);padding-bottom:var(--wp--preset--spacing--40);padding-left:var(--wp--preset--spacing--40)"><!-- wp:group {"align":"wide","style":{"spacing":{"blockGap":"var:preset|spacing|30"}},"layout":{"type":"flex","flexWrap":"nowrap","justifyContent":"space-between","verticalAlignment":"bottom"}} -->
<div class="wp-block-group alignwide"><!-- wp:heading {"className":"slot-heading","style":{"spacing":{"margin":{"top":"0","bottom":"0"}},"typography":{"textTransform":"uppercase"}},"fontSize":"xxx-large"} -->
<h2 class="wp-block-heading slot-heading has-xxx-large-font-size" style="margin-top:0;margin-bottom:0;text-transform:uppercase">Shop the lineup</h2>
<!-- /wp:heading -->

<!-- wp:heading {"textAlign":"right","level":3,"className":"slot-note","style":{"typography":{"textTransform":"uppercase"}},"fontSize":"large"} -->
<h3 class="wp-block-heading has-text-align-right slot-note has-large-font-size" style="text-transform:uppercase">Choose your main character</h3>
<!-- /wp:heading --></div>
<!-- /wp:group -->

<!-- wp:columns {"verticalAlignment":"top","align":"wide"} -->
<div class="wp-block-columns alignwide are-vertically-aligned-top"><!-- wp:column {"verticalAlignment":"top","style":{"spacing":{"margin":{"top":"var:preset|spacing|40"}}}} -->
<div class="wp-block-column is-vertically-aligned-top" style="margin-top:var(--wp--preset--spacing--40)"><!-- wp:cover {"alt":"Category campaign image one","dimRatio":0,"isUserOverlayColor":true,"contentPosition":"bottom center","isDark":false,"sizeSlug":"full","className":"is-style-default slot-image-1","style":{"spacing":{"padding":{"top":"var:preset|spacing|30","right":"var:preset|spacing|30","bottom":"var:preset|spacing|30","left":"var:preset|spacing|30"}},"dimensions":{"aspectRatio":"4/5"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-cover is-light has-custom-content-position is-position-bottom-center is-style-default slot-image-1" style="padding-top:var(--wp--preset--spacing--30);padding-right:var(--wp--preset--spacing--30);padding-bottom:var(--wp--preset--spacing--30);padding-left:var(--wp--preset--spacing--30)"><span aria-hidden="true" class="wp-block-cover__background has-background-dim-0 has-background-dim"></span><div class="wp-block-cover__inner-container"><!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"className":"slot-cta-1"} -->
<div class="wp-block-button slot-cta-1"><a class="wp-block-button__link wp-element-button" href="#">Shop Cardigans</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div></div>
<!-- /wp:cover --></div>
<!-- /wp:column -->

<!-- wp:column {"verticalAlignment":"top"} -->
<div class="wp-block-column is-vertically-aligned-top"><!-- wp:cover {"alt":"Category campaign image two","dimRatio":0,"isUserOverlayColor":true,"contentPosition":"bottom center","isDark":false,"sizeSlug":"full","className":"is-style-default slot-image-2","style":{"spacing":{"padding":{"top":"var:preset|spacing|30","right":"var:preset|spacing|30","bottom":"var:preset|spacing|30","left":"var:preset|spacing|30"}},"dimensions":{"aspectRatio":"1"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-cover is-light has-custom-content-position is-position-bottom-center is-style-default slot-image-2" style="padding-top:var(--wp--preset--spacing--30);padding-right:var(--wp--preset--spacing--30);padding-bottom:var(--wp--preset--spacing--30);padding-left:var(--wp--preset--spacing--30)"><span aria-hidden="true" class="wp-block-cover__background has-background-dim-0 has-background-dim"></span><div class="wp-block-cover__inner-container"><!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"className":"slot-cta-2"} -->
<div class="wp-block-button slot-cta-2"><a class="wp-block-button__link wp-element-button" href="#">Shop Sweaters</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div></div>
<!-- /wp:cover --></div>
<!-- /wp:column -->

<!-- wp:column {"verticalAlignment":"top","style":{"spacing":{"margin":{"top":"var:preset|spacing|60"}}}} -->
<div class="wp-block-column is-vertically-aligned-top" style="margin-top:var(--wp--preset--spacing--60)"><!-- wp:cover {"alt":"Category campaign image three","dimRatio":0,"isUserOverlayColor":true,"contentPosition":"bottom center","isDark":false,"sizeSlug":"full","className":"is-style-default slot-image-3","style":{"spacing":{"padding":{"top":"var:preset|spacing|30","right":"var:preset|spacing|30","bottom":"var:preset|spacing|30","left":"var:preset|spacing|30"}},"dimensions":{"aspectRatio":"3/4"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-cover is-light has-custom-content-position is-position-bottom-center is-style-default slot-image-3" style="padding-top:var(--wp--preset--spacing--30);padding-right:var(--wp--preset--spacing--30);padding-bottom:var(--wp--preset--spacing--30);padding-left:var(--wp--preset--spacing--30)"><span aria-hidden="true" class="wp-block-cover__background has-background-dim-0 has-background-dim"></span><div class="wp-block-cover__inner-container"><!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"className":"slot-cta-3"} -->
<div class="wp-block-button slot-cta-3"><a class="wp-block-button__link wp-element-button" href="#">Shop Accessories</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div></div>
<!-- /wp:cover --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->
