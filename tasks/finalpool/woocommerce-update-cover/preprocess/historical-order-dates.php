<?php
/**
 * Plugin Name: Historical Order Dates
 * Description: 允许通过 meta_data 设置订单的历史创建日期
 * Version: 1.0
 * Author: Auto Generated
 */

// 防止直接访问
if (!defined('ABSPATH')) {
    exit;
}

/**
 * 钩子：订单创建后处理历史日期
 */
add_action('woocommerce_checkout_order_processed', 'set_historical_order_date', 10, 1);
add_action('woocommerce_rest_insert_shop_order_object', 'set_historical_order_date_rest', 10, 1);

/**
 * 为通过 REST API 创建的订单设置历史日期
 */
function set_historical_order_date_rest($order) {
    set_historical_order_date($order->get_id());
}

/**
 * 设置订单的历史创建日期
 */
function set_historical_order_date($order_id) {
    // 获取订单对象
    $order = wc_get_order($order_id);
    
    if (!$order) {
        return;
    }
    
    // 检查是否有原始创建日期的 meta 数据
    $original_date = $order->get_meta('original_date_created');
    $is_simulated = $order->get_meta('simulated_historical_order');
    
    if ($original_date && $is_simulated === 'true') {
        // 转换日期格式
        $date_created = new WC_DateTime($original_date);
        
        // 直接更新数据库中的日期
        global $wpdb;
        
        $result = $wpdb->update(
            $wpdb->posts,
            array(
                'post_date' => $date_created->date('Y-m-d H:i:s'),
                'post_date_gmt' => $date_created->getTimestamp() > 0 ? gmdate('Y-m-d H:i:s', $date_created->getTimestamp()) : $date_created->date('Y-m-d H:i:s'),
                'post_modified' => $date_created->date('Y-m-d H:i:s'),
                'post_modified_gmt' => $date_created->getTimestamp() > 0 ? gmdate('Y-m-d H:i:s', $date_created->getTimestamp()) : $date_created->date('Y-m-d H:i:s')
            ),
            array('ID' => $order_id),
            array('%s', '%s', '%s', '%s'),
            array('%d')
        );
        
        if ($result !== false) {
            // 清除缓存
            wp_cache_delete($order_id, 'posts');
            
            // 记录日志
            error_log("Historical order date set for order #{$order_id}: {$original_date}");
            
            // 添加订单备注
            $order->add_order_note("订单创建日期已设置为历史日期: {$original_date}");
            
            // 移除临时 meta 数据（可选）
            // $order->delete_meta_data('original_date_created');
            // $order->delete_meta_data('simulated_historical_order');
            // $order->save();
        }
    }
}

/**
 * 为管理员添加一个手动工具来批量更新历史日期
 */
add_action('admin_menu', 'add_historical_dates_admin_menu');

function add_historical_dates_admin_menu() {
    add_submenu_page(
        'woocommerce',
        '历史订单日期',
        '历史订单日期',
        'manage_woocommerce',
        'historical-order-dates',
        'historical_dates_admin_page'
    );
}

function historical_dates_admin_page() {
    if (isset($_POST['update_historical_dates'])) {
        $updated_count = 0;
        
        // 获取所有带有历史日期标记的订单
        $orders = wc_get_orders(array(
            'limit' => -1,
            'meta_key' => 'simulated_historical_order',
            'meta_value' => 'true'
        ));
        
        foreach ($orders as $order) {
            set_historical_order_date($order->get_id());
            $updated_count++;
        }
        
        echo "<div class='notice notice-success'><p>已更新 {$updated_count} 个订单的历史日期。</p></div>";
    }
    
    ?>
    <div class="wrap">
        <h1>历史订单日期管理</h1>
        <p>此工具可以将存储在 meta_data 中的历史日期应用到订单的实际创建日期。</p>
        
        <form method="post">
            <p>
                <input type="submit" name="update_historical_dates" class="button button-primary" 
                       value="批量更新历史日期" 
                       onclick="return confirm('确定要更新所有标记为历史订单的创建日期吗？');">
            </p>
        </form>
        
        <h2>说明</h2>
        <ul>
            <li>只有包含 <code>simulated_historical_order</code> = 'true' 元数据的订单会被处理</li>
            <li>历史日期从 <code>original_date_created</code> 元数据中读取</li>
            <li>更新后的日期会反映在 WooCommerce 的报表和分析中</li>
        </ul>
    </div>
    <?php
} 