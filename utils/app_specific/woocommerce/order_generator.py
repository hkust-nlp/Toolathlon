#!/usr/bin/env python3
"""
Generic WooCommerce Order Data Generation Utilities

This module provides generic functions for generating test order data
that can be used across multiple WooCommerce-related tasks.
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class CustomerData:
    """Customer data structure"""
    name: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    def __post_init__(self):
        if not self.first_name or not self.last_name:
            name_parts = self.name.split()
            self.first_name = name_parts[0] if name_parts else self.name
            self.last_name = name_parts[-1] if len(name_parts) > 1 else ""


@dataclass
class ProductData:
    """Product data structure"""
    name: str
    price: float
    product_id: Optional[int] = None


@dataclass
class OrderGenerationConfig:
    """Configuration for order generation"""
    order_count: int = 20
    completed_percentage: float = 0.7  # 70% completed orders
    date_range_days: int = 7  # Orders from last 7 days
    min_quantity: int = 1
    max_quantity: int = 3
    order_id_start: int = 100
    shuffle_orders: bool = True
    time_seed: Optional[int] = None  # If None, uses current time


class OrderDataGenerator:
    """Generic order data generator for WooCommerce testing"""

    # Default customer dataset
    DEFAULT_CUSTOMERS = [
        CustomerData("Nancy Hill", "nancy.hill@mcp.com"),
        CustomerData("Cynthia Mendoza", "cynthia.mendoza@mcp.com"),
        CustomerData("Eric Jackson", "ejackson@mcp.com"),
        CustomerData("Amanda Evans", "aevans@mcp.com"),
        CustomerData("Kathleen Jones", "kathleen.jones@mcp.com"),
        CustomerData("Henry Howard", "henry_howard51@mcp.com"),
        CustomerData("Frances Miller", "frances.miller@mcp.com"),
        CustomerData("Jessica Patel", "jessicap@mcp.com"),
        CustomerData("Ryan Myers", "rmyers81@mcp.com"),
        CustomerData("Zachary Baker", "zachary.baker53@mcp.com"),
        CustomerData("Pamela Brooks", "pbrooks@mcp.com"),
        CustomerData("Eric Torres", "etorres4@mcp.com"),
        CustomerData("Tyler Perez", "tyler_perez28@mcp.com"),
        CustomerData("Janet Brown", "brownj@mcp.com"),
        CustomerData("Amanda Wilson", "wilsona@mcp.com"),
        CustomerData("Dorothy Adams", "dorothya69@mcp.com"),
        CustomerData("Aaron Clark", "aaron.clark@mcp.com"),
        CustomerData("Deborah Rodriguez", "drodriguez@mcp.com"),
        CustomerData("David Lopez", "davidl35@mcp.com"),
        CustomerData("Karen White", "karen.white66@mcp.com"),
        CustomerData("Alexander Williams", "alexander_williams@mcp.com"),
    ]

    # Default product dataset
    DEFAULT_PRODUCTS = [
        ProductData("Wireless Bluetooth Earphones", 299.00),
        ProductData("Smart Watch", 899.00),
        ProductData("Portable Power Bank", 129.00),
        ProductData("Wireless Charger", 89.00),
        ProductData("Phone Stand", 39.00),
        ProductData("Cable Set", 49.00),
        ProductData("Bluetooth Speaker", 199.00),
        ProductData("Car Charger", 59.00),
        ProductData("Phone Case", 29.00),
        ProductData("Screen Protector", 19.00),
    ]

    def __init__(self, customers: List[CustomerData] = None, products: List[ProductData] = None):
        """
        Initialize the order generator

        Args:
            customers: List of customer data. If None, uses default customers
            products: List of product data. If None, uses default products
        """
        self.customers = customers or self.DEFAULT_CUSTOMERS.copy()
        self.products = products or self.DEFAULT_PRODUCTS.copy()

    def generate_orders(self, config: OrderGenerationConfig) -> List[Dict]:
        """
        Generate order data based on configuration

        Args:
            config: Order generation configuration

        Returns:
            List of order dictionaries
        """
        print("📦 生成订单数据...")

        # Set random seed
        seed = config.time_seed if config.time_seed is not None else int(time.time())
        random.seed(seed)
        print(f"  🎲 使用随机种子: {seed}")

        orders = []
        now = datetime.now()
        completed_count = int(config.order_count * config.completed_percentage)

        print(f"  创建 {config.order_count} 个订单 ({completed_count} 个已完成, {config.order_count - completed_count} 个处理中)...")

        for i in range(config.order_count):
            # Select customer (cycle through if more orders than customers)
            customer = self.customers[i % len(self.customers)]
            product = random.choice(self.products)

            # Random order date within the specified range
            order_days_ago = random.randint(1, config.date_range_days)
            order_date = now - timedelta(days=order_days_ago)

            # Determine order status based on completion percentage
            if i < completed_count:
                status = "completed"
                # Completion date is 2-5 days after order date
                date_completed = order_date + timedelta(days=random.randint(2, 5))
                # Ensure completion date is not in the future
                if date_completed > now:
                    date_completed = now - timedelta(days=random.randint(0, 2))
            else:
                status = random.choice(["processing", "on-hold"])
                date_completed = None

            order = {
                "order_id": config.order_id_start + i,
                "order_number": f"{config.order_id_start + i}",
                "customer_email": customer.email,
                "customer_name": customer.name,
                "status": status,
                "date_created": order_date.strftime('%Y-%m-%dT%H:%M:%S'),
                "date_completed": date_completed.strftime('%Y-%m-%dT%H:%M:%S') if date_completed else None,
                "product_name": product.name,
                "product_price": product.price,
                "quantity": random.randint(config.min_quantity, config.max_quantity),
                "period": f"recent_{config.date_range_days}_days"
            }
            orders.append(order)

        # Shuffle orders if requested
        if config.shuffle_orders:
            print("  🔀 打乱订单顺序...")
            random.shuffle(orders)

        return orders

    def generate_historical_orders(self,
                                 count: int = 10,
                                 days_ago_start: int = 8,
                                 days_ago_end: int = 30,
                                 order_id_start: int = 200,
                                 status: str = "completed") -> List[Dict]:
        """
        Generate historical orders (older than recent period)

        Args:
            count: Number of historical orders to generate
            days_ago_start: Start of historical period (days ago)
            days_ago_end: End of historical period (days ago)
            order_id_start: Starting order ID for historical orders
            status: Order status for historical orders

        Returns:
            List of historical order dictionaries
        """
        print(f"📜 生成 {count} 个历史订单 ({days_ago_start}-{days_ago_end} 天前)...")

        orders = []
        now = datetime.now()

        for i in range(count):
            customer = self.customers[i % len(self.customers)]
            product = random.choice(self.products)

            # Random date in the historical period
            order_days_ago = random.randint(days_ago_start, days_ago_end)
            order_date = now - timedelta(days=order_days_ago)

            if status == "completed":
                date_completed = order_date + timedelta(days=random.randint(3, 7))
            else:
                date_completed = None

            order = {
                "order_id": order_id_start + i,
                "order_number": f"{order_id_start + i}",
                "customer_email": customer.email,
                "customer_name": customer.name,
                "status": status,
                "date_created": order_date.strftime('%Y-%m-%dT%H:%M:%S'),
                "date_completed": date_completed.strftime('%Y-%m-%dT%H:%M:%S') if date_completed else None,
                "product_name": product.name,
                "product_price": product.price,
                "quantity": random.randint(1, 3),
                "period": f"historical_{days_ago_start}_{days_ago_end}_days"
            }
            orders.append(order)

        return orders

    def create_woocommerce_order_data(self, order: Dict, virtual_product_id: int = 1) -> Dict:
        """
        Convert order data to WooCommerce API format

        Args:
            order: Order data dictionary
            virtual_product_id: Product ID to use for all orders

        Returns:
            WooCommerce API formatted order data
        """
        item_total = float(order["product_price"]) * order["quantity"]

        return {
            "status": order["status"],
            "customer_id": 1,  # Default customer ID
            "payment_method": "bacs",
            "payment_method_title": "Direct Bank Transfer",
            "total": str(item_total),
            "billing": {
                "first_name": order["customer_name"].split()[0] if " " in order["customer_name"] else order["customer_name"],
                "last_name": order["customer_name"].split()[-1] if " " in order["customer_name"] else "",
                "email": order["customer_email"]
            },
            "line_items": [
                {
                    "product_id": virtual_product_id,
                    "name": order["product_name"],
                    "quantity": order["quantity"],
                    "price": str(order["product_price"]),
                    "total": str(item_total),
                    "subtotal": str(item_total)
                }
            ],
            "meta_data": [
                {"key": "test_order", "value": "true"},
                {"key": "original_order_id", "value": str(order["order_id"])},
                {"key": "original_date_created", "value": order["date_created"]},
                {"key": "original_date_completed", "value": order["date_completed"] or ""},
                {"key": "period", "value": order["period"]},
                {"key": "generated_by", "value": "order_generator"}
            ]
        }

    @staticmethod
    def filter_orders_by_status(orders: List[Dict], status: str) -> List[Dict]:
        """
        Filter orders by status

        Args:
            orders: List of order dictionaries
            status: Status to filter by

        Returns:
            Filtered list of orders
        """
        return [order for order in orders if order.get("status") == status]

    @staticmethod
    def get_order_statistics(orders: List[Dict]) -> Dict[str, Any]:
        """
        Get statistics about generated orders

        Args:
            orders: List of order dictionaries

        Returns:
            Dictionary with order statistics
        """
        status_counts = {}
        total_value = 0
        customer_emails = set()

        for order in orders:
            # Count statuses
            status = order.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

            # Calculate total value
            item_total = float(order.get("product_price", 0)) * order.get("quantity", 1)
            total_value += item_total

            # Count unique customers
            customer_emails.add(order.get("customer_email", ""))

        return {
            "total_orders": len(orders),
            "status_counts": status_counts,
            "total_value": total_value,
            "unique_customers": len(customer_emails),
            "customer_emails": list(customer_emails)
        }


# Convenience functions for common use cases
def create_customer_survey_orders(seed: Optional[int] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Create orders specifically for customer survey tasks

    Returns:
        Tuple of (all_orders, completed_orders_only)
    """
    generator = OrderDataGenerator()
    config = OrderGenerationConfig(
        order_count=20,
        completed_percentage=0.7,
        date_range_days=7,
        time_seed=seed
    )

    all_orders = generator.generate_orders(config)
    completed_orders = generator.filter_orders_by_status(all_orders, "completed")

    return all_orders, completed_orders


def create_product_analysis_orders(seed: Optional[int] = None) -> List[Dict]:
    """
    Create orders for product analysis tasks (mix of recent and historical)

    Returns:
        List of all generated orders
    """
    generator = OrderDataGenerator()

    # Recent orders
    recent_config = OrderGenerationConfig(
        order_count=15,
        completed_percentage=0.6,
        date_range_days=30,
        time_seed=seed
    )
    recent_orders = generator.generate_orders(recent_config)

    # Historical orders
    historical_orders = generator.generate_historical_orders(
        count=25,
        days_ago_start=31,
        days_ago_end=120,
        order_id_start=200
    )

    all_orders = recent_orders + historical_orders
    if recent_config.shuffle_orders:
        random.shuffle(all_orders)

    return all_orders