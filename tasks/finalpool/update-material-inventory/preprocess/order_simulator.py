#!/usr/bin/env python3
"""
订单模拟器 - 模拟WooCommerce订单创建和付款
"""

import random
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class OrderItem:
    """订单项目"""
    sku: str
    name: str
    quantity: int
    price: float

@dataclass 
class SimulatedOrder:
    """模拟订单"""
    order_id: str
    items: List[OrderItem]
    total: float
    status: str
    payment_status: str
    created_at: datetime
    customer_info: Dict

class OrderSimulator:
    """订单模拟器"""
    
    def __init__(self, wc_client=None):
        """
        初始化订单模拟器
        
        Args:
            wc_client: WooCommerce客户端（可选）
        """
        self.wc_client = wc_client
        self.logger = self._setup_logging()
        self.available_products = [
            {"sku": "CHAIR_001", "name": "Classic Wooden Chair", "price": 299.00},
            {"sku": "TABLE_001", "name": "Oak Dining Table", "price": 899.00},
            {"sku": "DESK_001", "name": "Office Desk", "price": 599.00}
        ]
        self.customers = [
            {"name": "John Smith", "email": "john@example.com", "phone": "138****1234"},
            {"name": "Jane Doe", "email": "jane@example.com", "phone": "139****5678"},
            {"name": "Bob Wilson", "email": "bob@example.com", "phone": "137****9012"},
            {"name": "Alice Brown", "email": "alice@example.com", "phone": "136****3456"}
        ]
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def generate_random_order(self) -> SimulatedOrder:
        """生成随机订单"""
        # 随机选择1-3个产品
        num_items = random.randint(1, 3)
        selected_products = random.sample(self.available_products, num_items)
        
        items = []
        total = 0.0
        
        for product in selected_products:
            quantity = random.randint(1, 5)  # 每个产品1-5个
            item_total = product["price"] * quantity
            total += item_total
            
            items.append(OrderItem(
                sku=product["sku"],
                name=product["name"],
                quantity=quantity,
                price=product["price"]
            ))
        
        # 随机选择客户
        customer = random.choice(self.customers)
        
        # 生成订单ID
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        
        return SimulatedOrder(
            order_id=order_id,
            items=items,
            total=total,
            status="processing",
            payment_status="paid",
            created_at=datetime.now(),
            customer_info=customer
        )
    
    def get_product_id_by_sku(self, sku: str) -> Optional[int]:
        """根据SKU获取产品ID"""
        if not self.wc_client:
            return None
            
        try:
            # 获取所有产品并查找匹配的SKU
            products = self.wc_client.get_all_products()
            for product in products:
                if product.get('sku') == sku:
                    return product.get('id')
            return None
        except Exception as e:
            self.logger.error(f"获取产品ID失败: {e}")
            return None

    def create_woocommerce_order(self, simulated_order: SimulatedOrder) -> Optional[Dict]:
        """在WooCommerce中创建真实订单"""
        if not self.wc_client:
            self.logger.warning("未提供WooCommerce客户端，无法创建真实订单")
            return None
            
        try:
            # 构建WooCommerce订单数据 - 使用product_id而非SKU
            line_items = []
            for item in simulated_order.items:
                # 根据SKU获取产品ID
                product_id = self.get_product_id_by_sku(item.sku)
                if product_id:
                    line_items.append({
                        "product_id": product_id,
                        "quantity": item.quantity
                    })
                else:
                    self.logger.warning(f"未找到SKU为 {item.sku} 的产品")
            
            if not line_items:
                self.logger.error("没有有效的订单项目，无法创建订单")
                return None
            
            # 分割客户姓名
            name_parts = simulated_order.customer_info["name"].split()
            first_name = name_parts[0] if name_parts else "Customer"
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            
            order_data = {
                "status": simulated_order.status,
                "set_paid": simulated_order.payment_status == "paid",
                "payment_method": "bacs",
                "payment_method_title": "Bank Transfer",
                "billing": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": simulated_order.customer_info["email"],
                    "phone": simulated_order.customer_info["phone"],
                    "address_1": "123 Test Street",
                    "city": "Test City",
                    "state": "Test State",
                    "postcode": "100000",
                    "country": "CN"
                },
                "shipping": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "address_1": "123 Test Street",
                    "city": "Test City",
                    "state": "Test State",
                    "postcode": "100000",
                    "country": "CN"
                },
                "line_items": line_items,
                "shipping_lines": [
                    {
                        "method_id": "flat_rate",
                        "method_title": "Standard Shipping",
                        "total": "10.00"
                    }
                ]
            }
            
            success, result = self.wc_client.create_order(order_data)
            if success:
                order_id = result.get('id')
                self.logger.info(f"✅ Successfully created WooCommerce order: #{order_id}")
                self.logger.info(f"   Order status: {result.get('status')}")
                self.logger.info(f"   Payment status: {'Paid' if result.get('date_paid') else 'Unpaid'}")
                return result
            else:
                self.logger.error(f"❌ Failed to create WooCommerce order: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating WooCommerce order: {e}")
            return None
    
    def simulate_order_batch(self, count: int = 5, interval: int = 30) -> List[SimulatedOrder]:
        """Simulate batch order creation"""
        self.logger.info(f"🎯 Starting simulation of {count} orders with {interval}s interval")
        
        orders = []
        for i in range(count):
            # Generate simulated order
            simulated_order = self.generate_random_order()
            orders.append(simulated_order)
            
            # Log order information
            self.logger.info(f"📦 Simulated order {i+1}/{count}: {simulated_order.order_id}")
            for item in simulated_order.items:
                self.logger.info(f"  - {item.name} (SKU: {item.sku}) x{item.quantity} @ ¥{item.price}")
            self.logger.info(f"  Total: ${simulated_order.total:.2f}")
            
            # If WooCommerce client provided, create real order
            if self.wc_client:
                wc_order = self.create_woocommerce_order(simulated_order)
                if wc_order:
                    simulated_order.order_id = str(wc_order.get('id', simulated_order.order_id))
            
            # Wait interval (except for last order)
            if i < count - 1:
                self.logger.info(f"⏱️ Waiting {interval} seconds...")
                time.sleep(interval)
        
        self.logger.info(f"✅ Completed simulation of {count} orders")
        return orders
    
    def save_orders_to_file(self, orders: List[SimulatedOrder], filename: str = "simulated_orders.json"):
        """Save orders to file"""
        try:
            orders_data = []
            for order in orders:
                order_dict = {
                    "order_id": order.order_id,
                    "items": [
                        {
                            "sku": item.sku,
                            "name": item.name,
                            "quantity": item.quantity,
                            "price": item.price
                        } for item in order.items
                    ],
                    "total": order.total,
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "created_at": order.created_at.isoformat(),
                    "customer_info": order.customer_info
                }
                orders_data.append(order_dict)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(orders_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"📄 Order data saved to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save order data: {e}")

if __name__ == "__main__":
    # Test order simulator
    simulator = OrderSimulator()
    
    # Generate test orders
    orders = simulator.simulate_order_batch(count=3, interval=5)
    
    # Save to file
    simulator.save_orders_to_file(orders)
