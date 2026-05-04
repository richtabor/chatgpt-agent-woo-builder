<?php
/**
 * Title: Header Wordmark
 * Slug: assembler/header-wordmark
 * Categories: header, woo-commerce
 * Block Types: core/template-part/header
 * Description: Bold header with the site tagline, compact navigation, and oversized wordmark below.
 *
 * @package Assembler
 */
declare( strict_types = 1 );
?>

<!-- wp:group {"metadata":{"categories":["header","woo-commerce"],"patternName":"assembler/header-wordmark","name":"Header Wordmark"},"align":"full","className":"is-style-section-3","style":{"spacing":{"margin":{"top":"0","bottom":"0"},"padding":{"top":"var:preset|spacing|40","bottom":"var:preset|spacing|40"},"blockGap":"var:preset|spacing|20"}},"layout":{"type":"constrained","justifyContent":"center"}} -->
<div class="wp-block-group alignfull is-style-section-3" style="margin-top:0;margin-bottom:0;padding-top:var(--wp--preset--spacing--40);padding-bottom:var(--wp--preset--spacing--40)"><!-- wp:group {"align":"wide","style":{"spacing":{"blockGap":"4px"}},"layout":{"type":"flex","flexWrap":"wrap","justifyContent":"space-between"}} -->
<div class="wp-block-group alignwide"><!-- wp:site-tagline {"fontSize":"medium"} /-->

<!-- wp:group {"style":{"spacing":{"blockGap":"var:preset|spacing|20"},"layout":{"selfStretch":"fit","flexSize":null}},"layout":{"type":"flex","flexWrap":"wrap","justifyContent":"left"}} -->
<div class="wp-block-group"><!-- wp:paragraph {"className":"no-underline slot-nav-link-1","fontSize":"medium"} -->
<p class="no-underline slot-nav-link-1 has-medium-font-size"><a href="#">Shop</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"no-underline slot-nav-link-2","fontSize":"medium"} -->
<p class="no-underline slot-nav-link-2 has-medium-font-size"><a href="#">Journal</a></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph {"className":"no-underline slot-nav-link-3","fontSize":"medium"} -->
<p class="no-underline slot-nav-link-3 has-medium-font-size"><a href="#">Contact</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->

<!-- wp:heading {"align":"wide","className":"slot-wordmark","style":{"typography":{"textTransform":"uppercase"}},"fitText":true} -->
<h2 class="wp-block-heading alignwide slot-wordmark has-fit-text" style="text-transform:uppercase">SHOP TITLE</h2>
<!-- /wp:heading --></div>
<!-- /wp:group -->
