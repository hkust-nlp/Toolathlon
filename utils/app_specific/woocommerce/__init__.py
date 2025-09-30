"""
WooCommerce utilities for MCPBench tasks
"""

from .client import WooCommerceClient
from .order_generator import (
    OrderDataGenerator,
    CustomerData,
    ProductData,
    OrderGenerationConfig,
    create_customer_survey_orders,
    create_product_analysis_orders,
    create_new_welcome_orders
)
from .order_manager import (
    OrderManager,
    setup_customer_survey_environment,
    setup_product_analysis_environment
)

__all__ = [
    'WooCommerceClient',
    'OrderDataGenerator',
    'CustomerData',
    'ProductData',
    'OrderGenerationConfig',
    'OrderManager',
    'create_customer_survey_orders',
    'create_product_analysis_orders',
    'create_new_welcome_orders',
    'setup_customer_survey_environment',
    'setup_product_analysis_environment'
]