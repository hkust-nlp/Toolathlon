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
        print("📦 Generating order data...")

        # Set random seed
        seed = config.time_seed if config.time_seed is not None else int(time.time())
        random.seed(seed)
        print(f"  🎲 Using random seed: {seed}")

        orders = []
        now = datetime.now()
        completed_count = int(config.order_count * config.completed_percentage)

        print(f"  Creating {config.order_count} orders ({completed_count} completed, {config.order_count - completed_count} processing)...")

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
            print("  🔀 Shuffling order sequence...")
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
        print(f"📜 Generating {count} historical orders ({days_ago_start}-{days_ago_end} days ago)...")

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

def create_new_welcome_orders(seed: Optional[int] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Create orders for woocommerce-new-welcome task using built-in WooCommerce customer data
    Focus on customers identified as first-time buyers using orders_count=1

    Args:
        seed: Random seed for reproducibility

    Returns:
        Tuple of (all_orders, first_time_completed_orders)
    """
    import json
    import os
    from pathlib import Path

    # Load WooCommerce customer data with built-in attributes
    task_dir = Path(__file__).parent.parent.parent.parent / "tasks" / "finalpool" / "woocommerce-new-welcome" / "preprocess"
    woocommerce_data_file = task_dir / "woocommerce_data.json"
    customers_data_file = task_dir / "customers_data.json"

    if not woocommerce_data_file.exists():
        raise FileNotFoundError(f"WooCommerce data file not found: {woocommerce_data_file}")
    if not customers_data_file.exists():
        raise FileNotFoundError(f"Customers data file not found: {customers_data_file}")

    # Read WooCommerce customer data
    with open(woocommerce_data_file, 'r', encoding='utf-8') as f:
        woocommerce_data = json.load(f)

    # Read BigQuery customer data
    with open(customers_data_file, 'r', encoding='utf-8') as f:
        customers_data = json.load(f)

    print("📊 Using WooCommerce built-in customer attributes for order generation")

    # Create customer mapping
    woocommerce_customers = woocommerce_data.get("customers", [])
    bigquery_customers = {c["woocommerce_id"]: c for c in customers_data}

    # Identify first-time customers using built-in orders_count attribute
    first_time_customers = [c for c in woocommerce_customers if c.get("orders_count", 0) == 1]
    returning_customers = [c for c in woocommerce_customers if c.get("orders_count", 0) > 1]

    print(f"📈 Found {len(first_time_customers)} first-time customers (orders_count=1)")
    print(f"📈 Found {len(returning_customers)} returning customers (orders_count>1)")

    # Set random seed
    if seed is not None:
        random.seed(seed)
        print(f"🎲 Using random seed: {seed}")

    all_orders = []
    first_time_completed_orders = []
    now = datetime.now()

    # Generate orders for first-time customers (all completed)
    for i, customer in enumerate(first_time_customers):
        # Dynamically generate order date within recent 1-6 days (with margin to avoid boundary overlap)
        order_date = now - timedelta(days=random.randint(1, 6))

        # Get total spent and calculate appropriate product
        total_spent = float(customer.get("total_spent", "0").replace('$', '').replace(',', ''))

        # Select product based on total spent
        if total_spent > 500:
            product = ProductData("Premium Smart Watch", total_spent)
        elif total_spent > 200:
            product = ProductData("Wireless Bluetooth Earphones", total_spent)
        elif total_spent > 100:
            product = ProductData("Portable Power Bank", total_spent)
        else:
            product = ProductData("Phone Case", total_spent)

        order = {
            "order_id": 100 + i,
            "order_number": f"{100 + i}",
            "customer_email": customer["email"],
            "customer_name": f"{customer['first_name']} {customer['last_name']}",
            "customer_id": customer["id"],
            "woocommerce_customer_id": customer["id"],
            "status": "completed",
            "date_created": order_date.strftime('%Y-%m-%dT%H:%M:%S'),
            "date_completed": (order_date + timedelta(days=random.randint(1, 3))).strftime('%Y-%m-%dT%H:%M:%S'),
            "product_name": product.name,
            "product_price": product.price,
            "quantity": 1,
            "total_spent": total_spent,
            "orders_count": customer.get("orders_count", 1),
            "is_first_order": True,
            "is_paying_customer": customer.get("is_paying_customer", True),
            "period": "recent_7_days"
        }
        all_orders.append(order)
        first_time_completed_orders.append(order)

    # Generate orders for returning customers (mix of completed and processing)
    for i, customer in enumerate(returning_customers[:5]):  # Only add 5 returning customers
        # Dynamically generate order date from 9-30 days ago (clear separation from first-time customers)
        order_date = now - timedelta(days=random.randint(9, 30))

        total_spent = float(customer.get("total_spent", "0").replace('$', '').replace(',', ''))
        orders_count = customer.get("orders_count", 2)

        # Calculate order value based on customer history
        order_value = total_spent / orders_count if orders_count > 0 else 100.0

        product = ProductData("Additional Product", order_value)

        # Returning customers have mix of completed and processing orders
        status = "completed" if random.random() < 0.7 else "processing"

        order = {
            "order_id": 200 + i,
            "order_number": f"{200 + i}",
            "customer_email": customer["email"],
            "customer_name": f"{customer['first_name']} {customer['last_name']}",
            "customer_id": customer["id"],
            "woocommerce_customer_id": customer["id"],
            "status": status,
            "date_created": order_date.strftime('%Y-%m-%dT%H:%M:%S'),
            "date_completed": (order_date + timedelta(days=random.randint(1, 5))).strftime('%Y-%m-%dT%H:%M:%S') if status == "completed" else None,
            "product_name": product.name,
            "product_price": product.price,
            "quantity": 1,
            "total_spent": total_spent,
            "orders_count": orders_count,
            "is_first_order": False,
            "is_paying_customer": customer.get("is_paying_customer", True),
            "period": "recent_30_days"
        }
        all_orders.append(order)

    print(f"📦 Generated {len(all_orders)} total orders using WooCommerce built-in attributes")
    print(f"   - First-time completed orders: {len(first_time_completed_orders)} (orders_count=1)")
    print(f"   - Returning customer orders: {len(all_orders) - len(first_time_completed_orders)} (orders_count>1)")

    return all_orders, first_time_completed_orders