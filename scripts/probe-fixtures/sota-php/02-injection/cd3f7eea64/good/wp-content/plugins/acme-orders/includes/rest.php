<?php
/**
 * Plugin Name: Acme Orders
 */

defined('ABSPATH') || exit;

add_action( 'rest_api_init', function () {
	register_rest_route( 'acme/v1', '/orders/(?P<id>\d+)', array(
		'methods'             => 'DELETE',
		'callback'            => 'acme_delete_order',
		'permission_callback' => function () {
			return current_user_can( 'manage_options' );
		},
	) );
} );
