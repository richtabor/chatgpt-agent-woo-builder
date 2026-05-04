<?php
/**
 * Interval functions and definitions
 *
 * @package Interval
 * @since   Interval 0.1.0
 */

declare( strict_types = 1 );

if ( ! defined( 'WP_DEVELOPMENT_MODE' ) ) {
	define( 'WP_DEVELOPMENT_MODE', 'theme' );
}

if ( ! function_exists( 'interval_setup' ) ) :
	/**
	 * Register theme support and editor styles.
	 *
	 * @return void
	 */
	function interval_setup() {
		load_theme_textdomain( 'interval', get_template_directory() . '/languages' );

		// Editor styles use the same stylesheet as the front end.
		add_editor_style( 'style.css' );

		// Drop bundled core/Jetpack patterns we don't want in this theme.
		remove_theme_support( 'core-block-patterns' );
	}
endif;
add_action( 'after_setup_theme', 'interval_setup' );

if ( ! function_exists( 'interval_styles' ) ) :
	/**
	 * Enqueue the theme stylesheet and Google Fonts (Archivo + Inter).
	 *
	 * @return void
	 */
	function interval_styles() {
		wp_register_style(
			'interval-google-fonts',
			'https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;650;700;750;800&family=Inter:wght@400;500;600;700&display=swap',
			array(),
			null
		);
		wp_enqueue_style( 'interval-google-fonts' );

		wp_register_style(
			'interval-style',
			get_stylesheet_directory_uri() . '/style.css',
			array( 'interval-google-fonts' ),
			wp_get_theme()->get( 'Version' )
		);
		wp_enqueue_style( 'interval-style' );
	}
endif;
add_action( 'wp_enqueue_scripts', 'interval_styles' );

if ( ! function_exists( 'interval_preconnect_google_fonts' ) ) :
	/**
	 * Preconnect Google Fonts for faster typography render.
	 *
	 * @return void
	 */
	function interval_preconnect_google_fonts() {
		echo '<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>' . "\n";
		echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>' . "\n";
	}
endif;
add_action( 'wp_head', 'interval_preconnect_google_fonts', 1 );

if ( ! function_exists( 'interval_remove_upsells' ) ) :
	/**
	 * Quiet down WooCommerce single-product upsells (the brand voice owns merchandising).
	 *
	 * @return void
	 */
	function interval_remove_upsells() {
		remove_action( 'woocommerce_after_single_product_summary', 'woocommerce_upsell_display', 15 );
	}
endif;
add_action( 'init', 'interval_remove_upsells' );
