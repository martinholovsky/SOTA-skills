<?php
/**
 * Plugin Name: Acme Orders
 */

defined('ABSPATH') || exit;

function acme_orders_for( $author ) {
	global $wpdb;
	return $wpdb->get_results( $wpdb->prepare( "SELECT * FROM {$wpdb->prefix}acme_orders WHERE author = %d", $author ) );
}
