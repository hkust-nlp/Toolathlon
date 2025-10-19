#!/usr/bin/env python3
"""
Generic WooCommerce Order Manager Utilities

This module provides general order management functionality for uploading,
deleting, and managing WooCommerce orders across different tasks.
"""

import time
from typing import Dict, List, Tuple, Any, Optional
from .client import WooCommerceClient
from .order_generator import OrderDataGenerator


class OrderManager:
    """Generic WooCommerce order manager for test data setup and cleanup."""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize the OrderManager.

        Args:
            site_url: WooCommerce site URL.
            consumer_key: WooCommerce API consumer key.
            consumer_secret: WooCommerce API consumer secret.
        """
        self.wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
        self.created_orders = []
        self.generator = OrderDataGenerator()

    def clear_all_orders(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete all existing orders from WooCommerce.

        Args:
            confirm: Safety confirmation flag.

        Returns:
            Dictionary with deletion results.
        """
        if not confirm:
            return {
                "success": False,
                "error": "Confirmation required. Set confirm=True to proceed.",
                "warning": "This operation will delete ALL orders!"
            }

        print("🗑️ Clearing all existing orders...")

        try:
            # Use the generic client's batch delete functionality
            all_orders = self.wc_client.get_all_orders()

            if not all_orders:
                print("ℹ️ No orders found to delete.")
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "No orders to delete"
                }

            print(f"   📋 Found {len(all_orders)} orders to delete.")

            order_ids = [order['id'] for order in all_orders]
            success, result = self.wc_client.batch_delete_orders(order_ids, batch_size=20)

            if success:
                deleted_count = result.get('deleted', 0)
                print(f"✅ Successfully deleted {deleted_count} order(s).")
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "total_found": len(all_orders)
                }
            else:
                print(f"❌ Batch deletion of orders failed: {result}")
                return {
                    "success": False,
                    "error": f"Batch deletion failed: {result}",
                    "deleted_count": 0
                }

        except Exception as e:
            error_msg = f"Error occurred while deleting orders: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "deleted_count": 0
            }

    def upload_orders(
        self,
        orders_data: List[Dict],
        virtual_product_id: int = 1,
        batch_delay: float = 0.8
    ) -> Dict[str, Any]:
        """
        Upload order data to WooCommerce.

        Args:
            orders_data: List of order dictionaries.
            virtual_product_id: Product ID to use for all orders.
            batch_delay: Delay between API calls in seconds.

        Returns:
            Dictionary with upload results.
        """
        print(f"📤 Starting upload of {len(orders_data)} orders to WooCommerce...")

        successful_orders = 0
        failed_orders = 0
        failed_details = []

        for i, order in enumerate(orders_data, 1):
            try:
                # Convert to WooCommerce format
                order_data = self.generator.create_woocommerce_order_data(
                    order, virtual_product_id
                )

                # Create order using the generic client
                success, response = self.wc_client._make_request('POST', 'orders', data=order_data)

                if success:
                    wc_order_id = response.get('id')
                    successful_orders += 1
                    item_total = float(order["product_price"]) * order["quantity"]
                    print(
                        f"✅ Order #{wc_order_id} created successfully - {order['customer_name']} ({order['status']}) - ${item_total:.2f} [{i}/{len(orders_data)}]"
                    )
                    self.created_orders.append({
                        'original_order_id': order['order_id'],
                        'wc_order_id': wc_order_id,
                        'customer_email': order['customer_email'],
                        'customer_name': order['customer_name'],
                        'status': order['status'],
                        'period': order.get('period', 'unknown'),
                        'total': item_total
                    })
                else:
                    failed_orders += 1
                    error_details = {
                        'order_id': order.get('order_id'),
                        'customer_name': order.get('customer_name'),
                        'error': response
                    }
                    failed_details.append(error_details)
                    print(
                        f"❌ Failed to create order: {order['customer_name']} - {response} [{i}/{len(orders_data)}]"
                    )

                # Add delay to avoid API rate limits
                if batch_delay > 0:
                    time.sleep(batch_delay)

            except Exception as e:
                failed_orders += 1
                error_details = {
                    'order_id': order.get('order_id'),
                    'customer_name': order.get('customer_name'),
                    'error': str(e)
                }
                failed_details.append(error_details)
                print(
                    f"❌ Error while processing order: {order.get('customer_name', 'Unknown')} - {e} [{i}/{len(orders_data)}]"
                )

        # Generate statistics
        status_counts = {}
        for order in self.created_orders:
            status = order['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        total_value = sum(order.get('total', 0) for order in self.created_orders)

        result = {
            "success": failed_orders == 0,
            "total_orders": len(orders_data),
            "successful_orders": successful_orders,
            "failed_orders": failed_orders,
            "failed_details": failed_details,
            "status_distribution": status_counts,
            "total_value": total_value,
            "created_orders": self.created_orders.copy()
        }

        print(f"\n📊 Order upload finished:")
        print(f"   ✅ Successfully created: {successful_orders} order(s)")
        print(f"   ❌ Failed to create: {failed_orders} order(s)")
        print(f"   💰 Total order value: ${total_value:.2f}")

        if status_counts:
            print(f"\n📈 WooCommerce order status distribution:")
            for status, count in sorted(status_counts.items()):
                print(f"   {status}: {count} order(s)")

        return result

    def setup_test_environment(
        self,
        orders_data: List[Dict],
        clear_existing: bool = True,
        virtual_product_id: int = 1
    ) -> Dict[str, Any]:
        """
        Complete test environment setup: clear existing orders and upload new orders.

        Args:
            orders_data: List of order dictionaries to upload.
            clear_existing: Whether to clear existing orders first.
            virtual_product_id: Product ID to use for all orders.

        Returns:
            Dictionary with setup results.
        """
        print("🚀 Setting up test environment...")

        results = {
            "clear_result": None,
            "upload_result": None,
            "overall_success": False
        }

        # Step 1: Clear existing orders if requested
        if clear_existing:
            print("\nStep 1: Clearing existing orders")
            clear_result = self.clear_all_orders(confirm=True)
            results["clear_result"] = clear_result

            if not clear_result["success"]:
                print("⚠️ Failed to clear orders, but will continue with new order upload...")

        # Step 2: Upload new orders
        print(f"\nStep 2: Uploading {len(orders_data)} new orders")
        upload_result = self.upload_orders(orders_data, virtual_product_id)
        results["upload_result"] = upload_result

        # Overall success evaluation
        upload_success = upload_result["success"]
        clear_success = True if not clear_existing else clear_result.get("success", False)

        results["overall_success"] = upload_success and clear_success

        print(f"\n🎯 Test environment setup finished:")
        if clear_existing:
            print(f"   Clear existing orders: {'✅' if clear_success else '❌'}")
        print(f"   Upload new orders: {'✅' if upload_success else '❌'}")
        print(f"   Overall status: {'✅ Success' if results['overall_success'] else '⚠️ Partially successful'}")

        return results

    def get_created_orders(self) -> List[Dict]:
        """
        Get a list of orders created by this manager.

        Returns:
            List of created order information.
        """
        return self.created_orders.copy()

    def get_completed_orders(self) -> List[Dict]:
        """
        Get a list of completed orders created by this manager.

        Returns:
            List of completed order information.
        """
        return [order for order in self.created_orders if order.get('status') == 'completed']

    def export_order_data(self, include_wc_ids: bool = True) -> Dict[str, Any]:
        """
        Export order data for use in other components.

        Args:
            include_wc_ids: Whether to include WooCommerce order IDs.

        Returns:
            Dictionary with exportable order data.
        """
        export_data = {
            "total_orders": len(self.created_orders),
            "completed_orders": self.get_completed_orders(),
            "all_orders": self.created_orders.copy(),
            "customer_emails": list(set(order.get('customer_email') for order in self.created_orders)),
            "status_distribution": {}
        }

        # Calculate status distribution
        for order in self.created_orders:
            status = order.get('status', 'unknown')
            export_data["status_distribution"][status] = export_data["status_distribution"].get(status, 0) + 1

        # Remove WooCommerce IDs if not needed
        if not include_wc_ids:
            for order in export_data["all_orders"]:
                order.pop('wc_order_id', None)
            for order in export_data["completed_orders"]:
                order.pop('wc_order_id', None)

        return export_data


# Convenience functions for common operations
def setup_customer_survey_environment(
    site_url: str,
    consumer_key: str,
    consumer_secret: str,
    seed: Optional[int] = None
) -> Tuple[OrderManager, Dict[str, Any]]:
    """
    Set up the environment specifically for customer survey tasks.

    Args:
        site_url: WooCommerce site URL.
        consumer_key: WooCommerce API consumer key.
        consumer_secret: WooCommerce API consumer secret.
        seed: Random seed for reproducible results.

    Returns:
        Tuple of (OrderManager, setup_results).
    """
    from .order_generator import create_customer_survey_orders

    # Generate orders
    all_orders, completed_orders = create_customer_survey_orders(seed)

    # Create manager and setup environment
    manager = OrderManager(site_url, consumer_key, consumer_secret)
    setup_result = manager.setup_test_environment(all_orders, clear_existing=True)

    return manager, setup_result


def setup_product_analysis_environment(
    site_url: str,
    consumer_key: str,
    consumer_secret: str,
    seed: Optional[int] = None
) -> Tuple[OrderManager, Dict[str, Any]]:
    """
    Set up the environment for product analysis tasks.

    Args:
        site_url: WooCommerce site URL.
        consumer_key: WooCommerce API consumer key.
        consumer_secret: WooCommerce API consumer secret.
        seed: Random seed for reproducible results.

    Returns:
        Tuple of (OrderManager, setup_results).
    """
    from .order_generator import create_product_analysis_orders

    # Generate orders
    all_orders = create_product_analysis_orders(seed)

    # Create manager and setup environment
    manager = OrderManager(site_url, consumer_key, consumer_secret)
    setup_result = manager.setup_test_environment(all_orders, clear_existing=True)

    return manager, setup_result