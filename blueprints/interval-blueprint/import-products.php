<?php
require '/wordpress/wp-load.php';

if ( ! class_exists( 'WooCommerce' ) ) {
	exit( 'WooCommerce is required.' );
}

if ( class_exists( 'WC_Install' ) ) {
	WC_Install::create_pages();
}

update_option( 'permalink_structure', '/%postname%/' );
global $wp_rewrite;
$wp_rewrite->init();
$wp_rewrite->flush_rules();

$csv = '/tmp/interval-products.csv';
if ( ! file_exists( $csv ) ) {
	exit( 'Missing CSV.' );
}

$handle = fopen( $csv, 'r' );
if ( ! $handle ) {
	exit( 'Unable to open CSV.' );
}

$headers = fgetcsv( $handle );
while ( ( $row = fgetcsv( $handle ) ) !== false ) {
	$data = array_combine( $headers, $row );
	if ( empty( $data['sku'] ) ) {
		continue;
	}

	$product_id = wc_get_product_id_by_sku( $data['sku'] );
	$product    = $product_id ? wc_get_product( $product_id ) : new WC_Product_Simple();
	if ( ! $product ) {
		$product = new WC_Product_Simple();
	}

	$product->set_name( $data['name'] );
	$product->set_slug( $data['slug'] );
	$product->set_sku( $data['sku'] );
	$product->set_regular_price( (string) $data['regular_price'] );
	$product->set_description( $data['description'] );
	$product->set_short_description( $data['short_description'] );
	$product->set_status( 'publish' );
	$product->set_catalog_visibility( 'visible' );
	$product->set_manage_stock( false );
	$product->set_stock_status( 'instock' );
	$product->set_featured( ! empty( $data['featured'] ) && '1' === trim( $data['featured'] ) );
	$product_id = $product->save();

	$categories = array_filter( array_map( 'trim', explode( '|', $data['categories'] ) ) );
	$term_ids   = array();

	foreach ( $categories as $category_name ) {
		$term = term_exists( $category_name, 'product_cat' );
		if ( ! $term ) {
			$term = wp_insert_term( $category_name, 'product_cat' );
		}
		if ( ! is_wp_error( $term ) ) {
			$term_ids[] = (int) ( is_array( $term ) ? $term['term_id'] : $term );
		}
	}
	if ( $term_ids ) {
		wp_set_object_terms( $product_id, $term_ids, 'product_cat' );
	}

	$tags = array_filter( array_map( 'trim', explode( '|', $data['tags'] ) ) );
	if ( $tags ) {
		wp_set_object_terms( $product_id, $tags, 'product_tag' );
	}

	if ( ! empty( $data['image_url'] ) && ! has_post_thumbnail( $product_id ) ) {
		require_once ABSPATH . 'wp-admin/includes/file.php';
		require_once ABSPATH . 'wp-admin/includes/media.php';
		require_once ABSPATH . 'wp-admin/includes/image.php';

		$tmp = download_url( $data['image_url'] );
		if ( ! is_wp_error( $tmp ) ) {
			$file_array = array(
				'name'     => basename( parse_url( $data['image_url'], PHP_URL_PATH ) ?: 'interval-image.jpg' ),
				'tmp_name' => $tmp,
			);
			$attachment_id = media_handle_sideload( $file_array, $product_id, $data['name'] );
			if ( ! is_wp_error( $attachment_id ) ) {
				set_post_thumbnail( $product_id, $attachment_id );
			}
		}
	}
}

fclose( $handle );

$shop_page_id = wc_get_page_id( 'shop' );
if ( $shop_page_id && $shop_page_id > 0 ) {
	update_option( 'woocommerce_shop_page_display', '' );
}

update_option( 'blogname', 'Interval' );
update_option( 'blogdescription', 'Urban run-club gear and race-day systems' );
