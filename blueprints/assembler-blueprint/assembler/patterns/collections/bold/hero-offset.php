<?php
/**
 * Title: Offset Hero
 * Slug: assembler/hero-offset
 * Categories: featured, hero, products
 * Description: Offset ecommerce hero with oversized lineup heading, large image slot, and a compact supporting note.
 *
 * @package Assembler
 */
declare( strict_types = 1 );
?>

<!-- wp:group {"metadata":{"name":"Offset Hero","categories":["featured","hero","products"],"patternName":"assembler/hero-offset"},"align":"full","className":"is-style-default","style":{"spacing":{"margin":{"top":"0","bottom":"0"},"padding":{"top":"var:preset|spacing|40","bottom":"var:preset|spacing|40","left":"var:preset|spacing|50","right":"var:preset|spacing|50"},"blockGap":"var:preset|spacing|40"}},"layout":{"type":"constrained"}} -->
<div class="wp-block-group alignfull is-style-default" style="margin-top:0;margin-bottom:0;padding-top:var(--wp--preset--spacing--40);padding-right:var(--wp--preset--spacing--50);padding-bottom:var(--wp--preset--spacing--40);padding-left:var(--wp--preset--spacing--50)"><!-- wp:columns {"align":"wide"} -->
<div class="wp-block-columns alignwide"><!-- wp:column {"width":"33.33%"} -->
<div class="wp-block-column" style="flex-basis:33.33%"><!-- wp:spacer {"height":"1px"} -->
<div style="height:1px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"66.66%"} -->
<div class="wp-block-column" style="flex-basis:66.66%"><!-- wp:heading {"className":"slot-heading","style":{"spacing":{"margin":{"top":"0","bottom":"0"}},"typography":{"textTransform":"uppercase"}},"fontSize":"xxx-large"} -->
<h2 class="wp-block-heading slot-heading has-xxx-large-font-size" style="margin-top:0;margin-bottom:0;text-transform:uppercase">Shop the lineup</h2>
<!-- /wp:heading --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:columns {"align":"wide"} -->
<div class="wp-block-columns alignwide"><!-- wp:column {"width":"66.66%"} -->
<div class="wp-block-column" style="flex-basis:66.66%"><!-- wp:image {"aspectRatio":"4/3","scale":"cover","sizeSlug":"large","linkDestination":"none","className":"slot-image"} -->
<figure class="wp-block-image size-large slot-image"><img style="aspect-ratio:4/3;object-fit:cover"/></figure>
<!-- /wp:image --></div>
<!-- /wp:column -->

<!-- wp:column {"width":"33.33%"} -->
<div class="wp-block-column" style="flex-basis:33.33%"><!-- wp:paragraph {"align":"left","className":"slot-note"} -->
<p class="has-text-align-left slot-note">A short merchandising note that helps shoppers choose a path without slowing the page down.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->
