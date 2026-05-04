<?php
/**
 * Import Woo Creator products from a hosted WooCommerce CSV.
 *
 * The Blueprint/local wrapper should define WO_CONTENT_BASE_URL. Hosted bundles
 * point it at blueprints/<slug>-blueprint/. Local Studio apply may point it at a
 * temporary server with content/products.csv.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! class_exists( 'WooCommerce' ) ) {
	WP_CLI::error( 'WooCommerce is not active.' );
}

$woo_creator_base_url = defined( 'WO_CONTENT_BASE_URL' ) ? rtrim( WO_CONTENT_BASE_URL, '/' ) . '/' : '';

function woo_creator_csv_value( array $row, string $key, string $default = '' ): string {
	return isset( $row[ $key ] ) ? trim( (string) $row[ $key ] ) : $default;
}

function woo_creator_truthy( $value ): bool {
	return in_array( strtolower( trim( (string) $value ) ), array( '1', 'yes', 'true' ), true );
}

function woo_creator_fetch_csv( string $base_url ): string {
	$candidates = array(
		$base_url . 'products.csv',
		$base_url . 'content/products.csv',
	);

	foreach ( $candidates as $url ) {
		$response = wp_remote_get( $url, array( 'timeout' => 60 ) );
		if ( is_wp_error( $response ) ) {
			continue;
		}
		if ( 200 !== (int) wp_remote_retrieve_response_code( $response ) ) {
			continue;
		}
		$body = wp_remote_retrieve_body( $response );
		if ( '' !== trim( $body ) ) {
			return $body;
		}
	}

	WP_CLI::error( 'Could not fetch products.csv from ' . $base_url );
}

function woo_creator_parse_csv( string $csv ): array {
	$lines = preg_split( '/\r\n|\r|\n/', trim( $csv ) );
	if ( ! $lines || count( $lines ) < 2 ) {
		return array();
	}

	$headers = str_getcsv( array_shift( $lines ) );
	$count   = count( $headers );
	$rows    = array();

	foreach ( $lines as $line ) {
		if ( '' === trim( $line ) ) {
			continue;
		}
		$cells = str_getcsv( $line );
		if ( count( $cells ) < $count ) {
			$cells = array_pad( $cells, $count, '' );
		} elseif ( count( $cells ) > $count ) {
			$cells = array_slice( $cells, 0, $count );
		}
		$rows[] = array_combine( $headers, $cells );
	}

	return $rows;
}

function woo_creator_resolve_term_path( string $taxonomy, string $path ): int {
	$segments = array_values( array_filter( array_map( 'trim', explode( '>', $path ) ), 'strlen' ) );
	$parent   = 0;
	$term_id  = 0;

	foreach ( $segments as $name ) {
		$existing = get_terms(
			array(
				'taxonomy'   => $taxonomy,
				'name'       => $name,
				'parent'     => $parent,
				'hide_empty' => false,
				'number'     => 1,
			)
		);
		if ( ! is_wp_error( $existing ) && $existing ) {
			$term_id = (int) $existing[0]->term_id;
		} else {
			$inserted = wp_insert_term( $name, $taxonomy, array( 'parent' => $parent ) );
			if ( is_wp_error( $inserted ) ) {
				return 0;
			}
			$term_id = (int) $inserted['term_id'];
		}
		$parent = $term_id;
	}

	return $term_id;
}

function woo_creator_resolve_flat_term( string $taxonomy, string $name ): int {
	$name = trim( $name );
	if ( '' === $name ) {
		return 0;
	}
	$existing = get_term_by( 'name', $name, $taxonomy );
	if ( $existing ) {
		return (int) $existing->term_id;
	}
	$inserted = wp_insert_term( $name, $taxonomy );
	return is_wp_error( $inserted ) ? 0 : (int) $inserted['term_id'];
}

function woo_creator_image_url( string $value, string $base_url ): string {
	$value = trim( $value );
	if ( str_starts_with( $value, 'woo-assets://' ) ) {
		return $base_url . 'assets/' . rawurlencode( substr( $value, strlen( 'woo-assets://' ) ) );
	}
	return $value;
}

function woo_creator_attach_images( WC_Product $product, string $image_cell, string $base_url ): void {
	$urls = array_values( array_filter( array_map( 'trim', explode( ',', $image_cell ) ), 'strlen' ) );
	if ( ! $urls ) {
		return;
	}

	require_once ABSPATH . 'wp-admin/includes/file.php';
	require_once ABSPATH . 'wp-admin/includes/image.php';
	require_once ABSPATH . 'wp-admin/includes/media.php';

	$ids = array();
	foreach ( $urls as $url ) {
		$url      = woo_creator_image_url( $url, $base_url );
		$existing = get_posts(
			array(
				'post_type'      => 'attachment',
				'meta_key'       => '_woo_creator_source_url',
				'meta_value'     => $url,
				'fields'         => 'ids',
				'posts_per_page' => 1,
			)
		);
		$id = $existing ? (int) $existing[0] : 0;
		if ( ! $id ) {
			$id = media_sideload_image( $url, $product->get_id(), null, 'id' );
			if ( is_wp_error( $id ) ) {
				WP_CLI::warning( 'Could not sideload image: ' . $url );
				continue;
			}
			update_post_meta( (int) $id, '_woo_creator_source_url', $url );
		}
		$ids[] = (int) $id;
	}

	if ( $ids ) {
		$product->set_image_id( array_shift( $ids ) );
		$product->set_gallery_image_ids( $ids );
		$product->save();
	}
}

function woo_creator_collect_attributes( array $row ): array {
	$out = array();
	for ( $index = 1; $index <= 3; $index++ ) {
		$name   = woo_creator_csv_value( $row, "Attribute $index name" );
		$values = woo_creator_csv_value( $row, "Attribute $index value(s)" );
		if ( '' === $name || '' === $values ) {
			continue;
		}
		$out[] = array(
			'name'    => $name,
			'values'  => array_values( array_filter( array_map( 'trim', explode( '|', $values ) ), 'strlen' ) ),
			'visible' => woo_creator_truthy( woo_creator_csv_value( $row, "Attribute $index visible", '1' ) ),
			'default' => woo_creator_csv_value( $row, "Attribute $index default" ),
		);
	}
	return $out;
}

function woo_creator_apply_common_product_fields( WC_Product $product, array $row ): void {
	$product->set_name( woo_creator_csv_value( $row, 'Name' ) );
	$product->set_status( woo_creator_truthy( woo_creator_csv_value( $row, 'Published', '1' ) ) ? 'publish' : 'draft' );
	if ( method_exists( $product, 'set_description' ) ) {
		$product->set_description( woo_creator_csv_value( $row, 'Description' ) );
	}
	if ( method_exists( $product, 'set_short_description' ) ) {
		$product->set_short_description( woo_creator_csv_value( $row, 'Short description' ) );
	}
	if ( method_exists( $product, 'set_featured' ) ) {
		$product->set_featured( woo_creator_truthy( woo_creator_csv_value( $row, 'Is featured?' ) ) );
	}

	$sku = woo_creator_csv_value( $row, 'SKU' );
	if ( '' !== $sku ) {
		$product->set_sku( $sku );
	}

	$regular = woo_creator_csv_value( $row, 'Regular price' );
	$sale    = woo_creator_csv_value( $row, 'Sale price' );
	if ( '' !== $regular ) {
		$product->set_regular_price( $regular );
	}
	if ( '' !== $sale ) {
		$product->set_sale_price( $sale );
	}

	if ( method_exists( $product, 'set_stock_status' ) ) {
		$product->set_stock_status( woo_creator_truthy( woo_creator_csv_value( $row, 'In stock?', '1' ) ) ? 'instock' : 'outofstock' );
	}
	$stock = woo_creator_csv_value( $row, 'Stock' );
	if ( '' !== $stock && is_numeric( $stock ) && method_exists( $product, 'set_manage_stock' ) ) {
		$product->set_manage_stock( true );
		$product->set_stock_quantity( (int) $stock );
	}

	$cat_ids = array();
	foreach ( array_filter( array_map( 'trim', explode( ',', woo_creator_csv_value( $row, 'Categories' ) ) ), 'strlen' ) as $path ) {
		$term_id = woo_creator_resolve_term_path( 'product_cat', $path );
		if ( $term_id ) {
			$cat_ids[] = $term_id;
		}
	}
	if ( $cat_ids && method_exists( $product, 'set_category_ids' ) ) {
		$product->set_category_ids( array_values( array_unique( $cat_ids ) ) );
	}

	$tag_ids = array();
	foreach ( array_filter( array_map( 'trim', explode( ',', woo_creator_csv_value( $row, 'Tags' ) ) ), 'strlen' ) as $name ) {
		$term_id = woo_creator_resolve_flat_term( 'product_tag', $name );
		if ( $term_id ) {
			$tag_ids[] = $term_id;
		}
	}
	if ( $tag_ids && method_exists( $product, 'set_tag_ids' ) ) {
		$product->set_tag_ids( array_values( array_unique( $tag_ids ) ) );
	}
}

if ( '' === $woo_creator_base_url ) {
	WP_CLI::error( 'WO_CONTENT_BASE_URL is not defined.' );
}

$rows                  = woo_creator_parse_csv( woo_creator_fetch_csv( $woo_creator_base_url ) );
$row_id_to_product_id  = array();
$variation_parent_ids  = array();
$created               = 0;
$skipped               = 0;
$variations_created    = 0;
$variations_skipped    = 0;

foreach ( $rows as $row ) {
	$type = strtolower( woo_creator_csv_value( $row, 'Type', 'simple' ) );
	if ( 'variation' === $type ) {
		continue;
	}

	$sku      = woo_creator_csv_value( $row, 'SKU' );
	$existing = '' !== $sku ? wc_get_product_id_by_sku( $sku ) : 0;
	if ( $existing ) {
		$row_id = (int) woo_creator_csv_value( $row, 'ID' );
		if ( $row_id ) {
			$row_id_to_product_id[ $row_id ] = (int) $existing;
		}
		$skipped++;
		continue;
	}

	$product = 'variable' === $type ? new WC_Product_Variable() : new WC_Product_Simple();
	woo_creator_apply_common_product_fields( $product, $row );

	if ( $product instanceof WC_Product_Variable ) {
		$attributes = array();
		$defaults   = array();
		foreach ( woo_creator_collect_attributes( $row ) as $position => $spec ) {
			$attribute = new WC_Product_Attribute();
			$attribute->set_name( $spec['name'] );
			$attribute->set_options( $spec['values'] );
			$attribute->set_position( $position );
			$attribute->set_visible( $spec['visible'] );
			$attribute->set_variation( '' !== $spec['default'] );
			$attributes[] = $attribute;
			if ( '' !== $spec['default'] ) {
				$defaults[ 'attribute_' . sanitize_title( $spec['name'] ) ] = $spec['default'];
			}
		}
		$product->set_attributes( $attributes );
		$product->set_default_attributes( $defaults );
	}

	$product_id = $product->save();
	$row_id     = (int) woo_creator_csv_value( $row, 'ID' );
	if ( $row_id ) {
		$row_id_to_product_id[ $row_id ] = (int) $product_id;
	}
	woo_creator_attach_images( $product, woo_creator_csv_value( $row, 'Images' ), $woo_creator_base_url );
	$created++;
}

foreach ( $rows as $row ) {
	if ( 'variation' !== strtolower( woo_creator_csv_value( $row, 'Type' ) ) ) {
		continue;
	}

	$sku = woo_creator_csv_value( $row, 'SKU' );
	if ( '' !== $sku && wc_get_product_id_by_sku( $sku ) ) {
		$variations_skipped++;
		continue;
	}

	if ( ! preg_match( '/^id:(\d+)$/', woo_creator_csv_value( $row, 'Parent' ), $matches ) ) {
		continue;
	}
	$parent_id = $row_id_to_product_id[ (int) $matches[1] ] ?? 0;
	if ( ! $parent_id ) {
		continue;
	}

	$variation = new WC_Product_Variation();
	$variation->set_parent_id( $parent_id );
	woo_creator_apply_common_product_fields( $variation, $row );

	$attributes = array();
	foreach ( woo_creator_collect_attributes( $row ) as $spec ) {
		$attributes[ 'attribute_' . sanitize_title( $spec['name'] ) ] = $spec['values'][0] ?? '';
	}
	$variation->set_attributes( $attributes );
	$variation->save();
	$variation_parent_ids[ $parent_id ] = true;
	$variations_created++;
}

foreach ( array_keys( $variation_parent_ids ) as $parent_id ) {
	WC_Product_Variable::sync( (int) $parent_id );
}

WP_CLI::success(
	sprintf(
		'Woo Creator import complete. Products created=%d skipped=%d variations created=%d skipped=%d',
		$created,
		$skipped,
		$variations_created,
		$variations_skipped
	)
);
