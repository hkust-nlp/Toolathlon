#!/usr/bin/env python3
"""
库存监控器 - 监听WooCommerce订单并更新库存
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import threading

@dataclass
class OrderEvent:
    """订单事件"""
    order_id: str
    status: str
    payment_status: str
    items: List[Dict]  # [{'sku': str, 'quantity': int}, ...]
    timestamp: datetime

class InventoryMonitor:
    """库存监控器"""
    
    def __init__(self, wc_client, sheets_client, bom_calculator, spreadsheet_id: str):
        """
        初始化库存监控器
        
        Args:
            wc_client: WooCommerce客户端
            sheets_client: Google Sheets客户端
            bom_calculator: BOM计算器
            spreadsheet_id: 电子表格ID
        """
        self.wc_client = wc_client
        self.sheets_client = sheets_client
        self.bom_calculator = bom_calculator
        self.spreadsheet_id = spreadsheet_id
        self.logger = self._setup_logging()
        
        # 监控状态
        self.is_monitoring = False
        self.processed_orders: Set[str] = set()  # 已处理的订单ID
        self.last_check_time = datetime.now()
        
        # 线程锁
        self.lock = threading.Lock()
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def load_processed_orders(self, filename: str = "processed_orders.json"):
        """加载已处理的订单记录"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.processed_orders = set(data.get('processed_orders', []))
                
                # 加载最后检查时间
                last_check_str = data.get('last_check_time')
                if last_check_str:
                    self.last_check_time = datetime.fromisoformat(last_check_str)
                
            self.logger.info(f"📂 加载了 {len(self.processed_orders)} 个已处理订单记录")
            
        except FileNotFoundError:
            self.logger.info("📂 未找到已处理订单记录文件，从头开始监控")
        except Exception as e:
            self.logger.warning(f"加载已处理订单记录失败: {e}")
    
    def save_processed_orders(self, filename: str = "processed_orders.json"):
        """保存已处理的订单记录"""
        try:
            data = {
                'processed_orders': list(self.processed_orders),
                'last_check_time': self.last_check_time.isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"保存已处理订单记录失败: {e}")
    
    def get_new_paid_orders(self) -> List[OrderEvent]:
        """获取新的已付款订单"""
        try:
            # 获取最近的订单（过去24小时内）
            after_date = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')
            
            # 使用WooCommerce API获取订单
            params = {
                'after': after_date,
                'status': 'processing,completed',  # 已付款的订单状态
                'per_page': 100
            }
            
            orders_response = self.wc_client.session.get(
                f"{self.wc_client.api_base}/orders",
                params=params,
                timeout=30
            )
            
            if orders_response.status_code != 200:
                self.logger.error(f"获取订单失败: {orders_response.status_code}")
                return []
            
            orders = orders_response.json()
            new_orders = []
            
            for order in orders:
                order_id = str(order['id'])
                
                # 跳过已处理的订单
                if order_id in self.processed_orders:
                    continue
                
                # 检查是否已付款
                if not order.get('date_paid'):
                    continue
                
                # 解析订单项目
                items = []
                for line_item in order.get('line_items', []):
                    sku = line_item.get('sku')
                    if sku:  # 只处理有SKU的产品
                        items.append({
                            'sku': sku,
                            'name': line_item.get('name', ''),
                            'quantity': int(line_item.get('quantity', 0))
                        })
                
                if items:  # 只处理有有效项目的订单
                    order_event = OrderEvent(
                        order_id=order_id,
                        status=order['status'],
                        payment_status='paid',
                        items=items,
                        timestamp=datetime.fromisoformat(order['date_paid'].replace('T', ' ').replace('Z', ''))
                    )
                    new_orders.append(order_event)
            
            if new_orders:
                self.logger.info(f"🆕 发现 {len(new_orders)} 个新的已付款订单")
            
            return new_orders
            
        except Exception as e:
            self.logger.error(f"获取新订单失败: {e}")
            return []
    
    def process_order(self, order_event: OrderEvent) -> bool:
        """
        处理单个订单
        
        Args:
            order_event: 订单事件
            
        Returns:
            处理是否成功
        """
        self.logger.info(f"🔄 处理订单 #{order_event.order_id}")
        
        try:
            # 1. 检查订单可行性（原材料是否充足）
            feasible, requirements = self.bom_calculator.check_order_feasibility(order_event.items)
            
            if not feasible:
                self.logger.error(f"❌ 订单 #{order_event.order_id} 原材料不足，无法处理")
                return False
            
            # 2. 扣减原材料库存
            success = self.bom_calculator.update_inventory_after_order(
                self.spreadsheet_id, 
                requirements
            )
            
            if not success:
                self.logger.error(f"❌ 更新库存失败，订单 #{order_event.order_id}")
                return False
            
            # 3. 重新计算产品最大生产能力
            max_production = self.bom_calculator.calculate_max_production_capacity()
            
            # 4. 同步库存到WooCommerce
            sync_success = self.sync_stock_to_woocommerce(max_production)
            
            if sync_success:
                self.logger.info(f"✅ 订单 #{order_event.order_id} 处理完成")
                return True
            else:
                self.logger.warning(f"⚠️ 订单 #{order_event.order_id} 库存更新完成，但同步到WooCommerce失败")
                return True  # 库存已更新，视为成功
                
        except Exception as e:
            self.logger.error(f"处理订单 #{order_event.order_id} 时出错: {e}")
            return False
    
    def sync_stock_to_woocommerce(self, max_production: Dict[str, int]) -> bool:
        """
        将最大生产能力同步到WooCommerce产品库存
        
        Args:
            max_production: {product_sku: max_quantity}
            
        Returns:
            同步是否成功
        """
        try:
            self.logger.info("🔄 同步库存到WooCommerce...")
            
            # 获取所有产品
            products = self.wc_client.get_all_products()
            
            sync_count = 0
            for product in products:
                sku = product.get('sku')
                if sku in max_production:
                    product_id = product['id']
                    new_stock = max_production[sku]
                    current_stock = product.get('stock_quantity', 0)
                    
                    # 只有库存发生变化时才更新
                    if new_stock != current_stock:
                        update_data = {
                            'stock_quantity': new_stock,
                            'stock_status': 'instock' if new_stock > 0 else 'outofstock'
                        }
                        
                        success, result = self.wc_client.update_product(str(product_id), update_data)
                        if success:
                            self.logger.info(f"  📦 {sku}: {current_stock} → {new_stock}")
                            sync_count += 1
                        else:
                            self.logger.error(f"  ❌ 更新 {sku} 库存失败: {result}")
            
            self.logger.info(f"✅ 成功同步 {sync_count} 个产品库存")
            return True
            
        except Exception as e:
            self.logger.error(f"同步库存到WooCommerce失败: {e}")
            return False
    
    def start_monitoring(self, check_interval: int = 60):
        """
        开始监控订单
        
        Args:
            check_interval: 检查间隔（秒）
        """
        self.logger.info(f"🚀 开始监控WooCommerce订单，检查间隔: {check_interval}秒")
        
        # 加载已处理的订单记录
        self.load_processed_orders()
        
        # 初始化BOM和库存数据
        self.bom_calculator.load_bom_from_sheets(self.spreadsheet_id)
        self.bom_calculator.load_inventory_from_sheets(self.spreadsheet_id)
        
        self.is_monitoring = True
        
        try:
            while self.is_monitoring:
                with self.lock:
                    # 获取新订单
                    new_orders = self.get_new_paid_orders()
                    
                    # 处理每个新订单
                    for order_event in new_orders:
                        success = self.process_order(order_event)
                        
                        # 标记为已处理（无论成功与否，避免重复处理）
                        self.processed_orders.add(order_event.order_id)
                        
                        if success:
                            self.logger.info(f"✅ 订单 #{order_event.order_id} 处理成功")
                        else:
                            self.logger.error(f"❌ 订单 #{order_event.order_id} 处理失败")
                    
                    # 更新最后检查时间
                    self.last_check_time = datetime.now()
                    
                    # 保存处理记录
                    self.save_processed_orders()
                
                # 等待下次检查
                if self.is_monitoring:
                    time.sleep(check_interval)
                    
        except KeyboardInterrupt:
            self.logger.info("👋 收到中断信号，停止监控")
        except Exception as e:
            self.logger.error(f"监控过程中出错: {e}")
        finally:
            self.is_monitoring = False
            self.save_processed_orders()
            self.logger.info("📄 已保存处理记录")
    
    def stop_monitoring(self):
        """停止监控"""
        self.logger.info("🛑 停止订单监控")
        self.is_monitoring = False
    
    def get_monitoring_status(self) -> Dict:
        """获取监控状态"""
        return {
            'is_monitoring': self.is_monitoring,
            'processed_orders_count': len(self.processed_orders),
            'last_check_time': self.last_check_time.isoformat(),
            'current_time': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 这里只是示例，实际使用时需要正确的客户端实例
    print("库存监控器模块已加载")
    print("使用方法:")
    print("1. 创建WooCommerce客户端、Google Sheets客户端和BOM计算器")
    print("2. 创建InventoryMonitor实例")
    print("3. 调用start_monitoring()开始监控")
