<?php
/**
 * WordPress Sync Endpoint for ESP Product Importer
 * 
 * This endpoint handles sync functionality for WordPress users to sync products
 * based on scrapedDate comparison with the latest scraped data.
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Register sync endpoint
 */
function esp_register_sync_endpoint() {
    register_rest_route(
        'promostandards-importer/v1',
        '/sync',
        [
            'methods' => 'POST',
            'callback' => 'esp_handle_sync_request',
            'permission_callback' => function () {
                return current_user_can('manage_options');
            },
        ]
    );
}
add_action('rest_api_init', 'esp_register_sync_endpoint');

/**
 * Handle sync request
 */
function esp_handle_sync_request($request) {
    // Check API key
    $headers = $request->get_headers();
    $auth = $headers['authorization'][0] ?? '';
    $expected = 'Bearer ' . getenv('PROMOSTANDARDS_API_KEY');
    
    if (!$auth || $auth !== $expected) {
        return new WP_Error('unauthorized', 'Invalid API key', ['status' => 401]);
    }
    
    // Get the uploaded file
    $file = $request->get_file_params()['file'] ?? null;
    if (!$file || empty($file['tmp_name'])) {
        return new WP_Error('no_file', 'No file uploaded', ['status' => 400]);
    }
    
    // Read and decode the JSONL batch
    $lines = file($file['tmp_name'], FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    $scraped_products = [];
    
    foreach ($lines as $line) {
        $data = json_decode($line, true);
        if ($data) {
            $scraped_products[] = $data;
        }
    }
    
    if (empty($scraped_products)) {
        return new WP_Error('no_products', 'No valid products in batch', ['status' => 400]);
    }
    
    // Get existing products with their scraped dates
    $existing_products = esp_get_existing_products_with_dates();
    
    // Compare scraped dates and determine actions
    $products_to_create = [];
    $products_to_update = [];
    $products_skipped = 0;
    $errors = 0;
    
    foreach ($scraped_products as $scraped_product) {
        $product_id = $scraped_product['ProductID'] ?? '';
        $scraped_date = $scraped_product['ScrapedDate'] ?? '';
        
        if (!$product_id || !$scraped_date) {
            $errors++;
            continue;
        }
        
        $existing_product = $existing_products[$product_id] ?? null;
        
        if (!$existing_product) {
            // Product doesn't exist in WordPress - create it
            $products_to_create[] = $scraped_product;
        } else {
            // Product exists - compare dates
            $existing_date = $existing_product['scraped_date'] ?? '';
            
            if (!$existing_date) {
                // No scraped date in WordPress - update it
                $products_to_update[] = $scraped_product;
            } else {
                // Compare dates
                try {
                    $scraped_dt = new DateTime($scraped_date);
                    $existing_dt = new DateTime($existing_date);
                    
                    if ($scraped_dt > $existing_dt) {
                        // Scraped data is newer - update it
                        $products_to_update[] = $scraped_product;
                    } else {
                        // WordPress data is current - skip it
                        $products_skipped++;
                    }
                } catch (Exception $e) {
                    // On date comparison error, update the product
                    $products_to_update[] = $scraped_product;
                }
            }
        }
    }
    
    // Process products
    $importer = new Promostandards_Importer_Processor();
    $created = 0;
    $updated = 0;
    $sync_errors = 0;
    
    // Create new products
    foreach ($products_to_create as $product) {
        $result = $importer->_importProduct($product, false);
        if (is_wp_error($result)) {
            $sync_errors++;
        } else {
            $created++;
        }
    }
    
    // Update existing products
    foreach ($products_to_update as $product) {
        $result = $importer->_importProduct($product, true); // Force update
        if (is_wp_error($result)) {
            $sync_errors++;
        } else {
            $updated++;
        }
    }
    
    return new WP_REST_Response([
        'success' => true,
        'sync_results' => [
            'total_products' => count($scraped_products),
            'products_to_create' => count($products_to_create),
            'products_to_update' => count($products_to_update),
            'products_skipped' => $products_skipped,
            'errors' => $errors,
            'created' => $created,
            'updated' => $updated,
            'sync_errors' => $sync_errors
        ],
        'message' => "Sync completed: $created created, $updated updated, $products_skipped skipped, " . ($errors + $sync_errors) . " errors."
    ]);
}

/**
 * Get existing products with their scraped dates
 */
function esp_get_existing_products_with_dates() {
    global $wpdb;
    
    $existing_products = [];
    
    // Get all products with external_product_id meta
    $query = "
        SELECT p.ID, p.post_title, pm1.meta_value as external_product_id, pm2.meta_value as scraped_date
        FROM {$wpdb->posts} p
        LEFT JOIN {$wpdb->postmeta} pm1 ON p.ID = pm1.post_id AND pm1.meta_key = 'external_product_id'
        LEFT JOIN {$wpdb->postmeta} pm2 ON p.ID = pm2.post_id AND pm2.meta_key = 'scraped_date'
        WHERE p.post_type = 'product' 
        AND p.post_status = 'publish'
        AND pm1.meta_value IS NOT NULL
    ";
    
    $results = $wpdb->get_results($query);
    
    foreach ($results as $result) {
        $product_id = $result->external_product_id;
        if ($product_id) {
            $existing_products[$product_id] = [
                'product_id' => $product_id,
                'name' => $result->post_title,
                'wordpress_id' => $result->ID,
                'scraped_date' => $result->scraped_date
            ];
        }
    }
    
    return $existing_products;
}

/**
 * Enhanced existing products endpoint that includes scraped dates
 */
function esp_get_existing_products_enhanced($request) {
    $api_key = $request->get_header('X-API-Key');
    $expected = getenv('PROMOSTANDARDS_API_KEY') ?: (defined('PROMOSTANDARDS_API_KEY') ? PROMOSTANDARDS_API_KEY : '');
    
    if (!$api_key || $api_key !== $expected) {
        return new WP_Error('unauthorized', 'Invalid API key', ['status' => 401]);
    }
    
    $existing_products = esp_get_existing_products_with_dates();
    
    $products = [];
    foreach ($existing_products as $product) {
        $products[] = [
            'product_id' => $product['product_id'],
            'name' => $product['name'],
            'wp_id' => $product['wordpress_id'],
            'scraped_date' => $product['scraped_date'],
            'last_modified' => get_the_modified_date('c', $product['wordpress_id'])
        ];
    }
    
    return [
        'total_products' => count($products),
        'products' => $products
    ];
}

// Register enhanced endpoint
add_action('rest_api_init', function () {
    register_rest_route(
        'promostandards-importer/v1',
        '/existing-products-enhanced',
        [
            'methods' => 'GET',
            'callback' => 'esp_get_existing_products_enhanced',
            'permission_callback' => '__return_true',
        ]
    );
});

/**
 * Add sync button to admin interface
 */
function esp_add_sync_button() {
    ?>
    <div class="wrap">
        <h2>ESP Product Sync</h2>
        <p>Sync products with the latest scraped data based on scrapedDate comparison.</p>
        
        <div id="sync-status" style="display: none;">
            <div class="notice notice-info">
                <p><strong>Sync in progress...</strong> <span id="sync-progress">0%</span></p>
            </div>
        </div>
        
        <div id="sync-results" style="display: none;">
            <div class="notice notice-success">
                <h3>Sync Results</h3>
                <ul id="sync-results-list"></ul>
            </div>
        </div>
        
        <button type="button" id="start-sync" class="button button-primary">Start Sync</button>
        
        <script>
        jQuery(document).ready(function($) {
            $('#start-sync').click(function() {
                var button = $(this);
                button.prop('disabled', true).text('Syncing...');
                
                $('#sync-status').show();
                $('#sync-results').hide();
                
                // Get the latest scraped data file
                $.ajax({
                    url: ajaxurl,
                    type: 'POST',
                    data: {
                        action: 'esp_get_latest_scraped_file',
                        nonce: '<?php echo wp_create_nonce('esp_sync_nonce'); ?>'
                    },
                    success: function(response) {
                        if (response.success && response.data.file_url) {
                            // Perform sync with the file
                            performSync(response.data.file_url);
                        } else {
                            alert('No scraped data file found. Please run the scraper first.');
                            button.prop('disabled', false).text('Start Sync');
                            $('#sync-status').hide();
                        }
                    },
                    error: function() {
                        alert('Error getting scraped data file.');
                        button.prop('disabled', false).text('Start Sync');
                        $('#sync-status').hide();
                    }
                });
            });
            
            function performSync(fileUrl) {
                // Create form data with the file
                var formData = new FormData();
                formData.append('file', fileUrl);
                
                $.ajax({
                    url: '<?php echo rest_url('promostandards-importer/v1/sync'); ?>',
                    type: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    headers: {
                        'Authorization': 'Bearer <?php echo getenv('PROMOSTANDARDS_API_KEY') ?: (defined('PROMOSTANDARDS_API_KEY') ? PROMOSTANDARDS_API_KEY : ''); ?>'
                    },
                    success: function(response) {
                        showSyncResults(response.sync_results);
                        $('#start-sync').prop('disabled', false).text('Start Sync');
                        $('#sync-status').hide();
                    },
                    error: function(xhr) {
                        alert('Sync failed: ' + (xhr.responseJSON?.message || 'Unknown error'));
                        $('#start-sync').prop('disabled', false).text('Start Sync');
                        $('#sync-status').hide();
                    }
                });
            }
            
            function showSyncResults(results) {
                var list = $('#sync-results-list');
                list.empty();
                
                list.append('<li>Total products: ' + results.total_products + '</li>');
                list.append('<li>Created: ' + results.created + '</li>');
                list.append('<li>Updated: ' + results.updated + '</li>');
                list.append('<li>Skipped: ' + results.products_skipped + '</li>');
                list.append('<li>Errors: ' + (results.errors + results.sync_errors) + '</li>');
                
                $('#sync-results').show();
            }
        });
        </script>
    </div>
    <?php
}

// Add sync page to admin menu
add_action('admin_menu', function() {
    add_submenu_page(
        'promostandards-importer',
        'ESP Sync',
        'Sync Products',
        'manage_options',
        'esp-sync',
        'esp_add_sync_button'
    );
});

// AJAX handler for getting latest scraped file
add_action('wp_ajax_esp_get_latest_scraped_file', function() {
    check_ajax_referer('esp_sync_nonce', 'nonce');
    
    // Look for the latest scraped data file
    $upload_dir = wp_upload_dir();
    $data_dir = $upload_dir['basedir'] . '/promostandards-importer';
    
    if (is_dir($data_dir)) {
        $files = glob($data_dir . '/api_product_details_*.jsonl');
        if ($files) {
            // Sort by modification time
            usort($files, function($a, $b) {
                return filemtime($b) - filemtime($a);
            });
            
            $latest_file = $files[0];
            wp_send_json_success(['file_url' => $latest_file]);
        }
    }
    
    wp_send_json_error('No scraped data file found');
}); 