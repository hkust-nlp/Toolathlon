#!/usr/bin/env python3
"""
主工作流程 - 原材料库存管理系统
"""

import os
import sys
import json
import logging
import signal
import time
from datetime import datetime
from typing import Dict, Optional
import threading

# 添加模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入预处理模块
preprocess_dir = os.path.join(current_dir, 'preprocess')
sys.path.insert(0, preprocess_dir)

from preprocess.woocommerce_client import WooCommerceClient
from preprocess.sheets_setup import GoogleSheetsClient
from bom_calculator import BOMCalculator
from inventory_monitor import InventoryMonitor
from order_simulator import OrderSimulator

class MaterialInventorySystem:
    """原材料库存管理系统"""
    
    def __init__(self, config_file: str = "initial_workspace/config.json"):
        """
        初始化系统
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = {}
        self.logger = self._setup_logging()
        
        # 客户端实例
        self.wc_client: Optional[WooCommerceClient] = None
        self.sheets_client: Optional[GoogleSheetsClient] = None
        self.bom_calculator: Optional[BOMCalculator] = None
        self.inventory_monitor: Optional[InventoryMonitor] = None
        self.order_simulator: Optional[OrderSimulator] = None
        
        # 系统状态
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logging(self):
        """设置日志"""
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 配置日志格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_file = os.path.join(log_dir, f"inventory_system_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到信号 {signum}，正在关闭系统...")
        self.shutdown()
    
    def load_config(self) -> bool:
        """加载配置"""
        try:
            config_path = os.path.join(current_dir, self.config_file)
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            self.logger.info("✅ 配置加载成功")
            return True
            
        except FileNotFoundError:
            self.logger.error(f"❌ 配置文件不存在: {self.config_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ 配置文件格式错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 加载配置失败: {e}")
            return False
    
    def load_woocommerce_config(self) -> Dict:
        """加载WooCommerce配置"""
        try:
            # 尝试从token_key_session.py加载配置
            token_config_path = os.path.join(current_dir, 'token_key_session.py')
            if os.path.exists(token_config_path):
                sys.path.insert(0, current_dir)
                import token_key_session as token_config
                
                return {
                    'site_url': getattr(token_config, 'WOOCOMMERCE_URL', ''),
                    'consumer_key': getattr(token_config, 'WOOCOMMERCE_KEY', ''),
                    'consumer_secret': getattr(token_config, 'WOOCOMMERCE_SECRET', '')
                }
            else:
                self.logger.warning("未找到token_key_session.py，使用默认配置")
                return {
                    'site_url': 'https://your-site.com',
                    'consumer_key': 'your_key',
                    'consumer_secret': 'your_secret'
                }
                
        except Exception as e:
            self.logger.error(f"加载WooCommerce配置失败: {e}")
            return {}
    
    def initialize_clients(self) -> bool:
        """初始化所有客户端"""
        try:
            self.logger.info("🔧 初始化客户端...")
            
            # 1. 初始化Google Sheets客户端
            self.sheets_client = GoogleSheetsClient()
            if not self.sheets_client.authenticate():
                self.logger.error("❌ Google Sheets认证失败")
                return False
            
            # 2. 初始化WooCommerce客户端
            wc_config = self.load_woocommerce_config()
            if not all(wc_config.values()):
                self.logger.error("❌ WooCommerce配置不完整")
                return False
                
            self.wc_client = WooCommerceClient(
                site_url=wc_config['site_url'],
                consumer_key=wc_config['consumer_key'],
                consumer_secret=wc_config['consumer_secret']
            )
            
            if not self.wc_client.test_connection():
                self.logger.error("❌ WooCommerce连接失败")
                return False
            
            # 3. 初始化BOM计算器
            self.bom_calculator = BOMCalculator(self.sheets_client)
            
            # 4. 初始化库存监控器
            spreadsheet_id = self.config.get('spreadsheet_id')
            if not spreadsheet_id:
                self.logger.error("❌ 未找到电子表格ID")
                return False
                
            self.inventory_monitor = InventoryMonitor(
                wc_client=self.wc_client,
                sheets_client=self.sheets_client,
                bom_calculator=self.bom_calculator,
                spreadsheet_id=spreadsheet_id
            )
            
            # 5. 初始化订单模拟器
            self.order_simulator = OrderSimulator(self.wc_client)
            
            self.logger.info("✅ 所有客户端初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 客户端初始化失败: {e}")
            return False
    
    def run_initial_sync(self) -> bool:
        """执行初始同步"""
        try:
            self.logger.info("🔄 执行初始同步...")
            
            # 加载BOM和库存数据
            spreadsheet_id = self.config.get('spreadsheet_id')
            
            if not self.bom_calculator.load_bom_from_sheets(spreadsheet_id):
                self.logger.error("❌ 加载BOM数据失败")
                return False
            
            if not self.bom_calculator.load_inventory_from_sheets(spreadsheet_id):
                self.logger.error("❌ 加载库存数据失败")
                return False
            
            # 计算并同步初始库存
            max_production = self.bom_calculator.calculate_max_production_capacity()
            
            if not self.inventory_monitor.sync_stock_to_woocommerce(max_production):
                self.logger.warning("⚠️ 初始库存同步失败")
                return False
            
            self.logger.info("✅ 初始同步完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 初始同步失败: {e}")
            return False
    
    def start_monitoring(self, check_interval: int = 60):
        """开始监控"""
        try:
            self.logger.info(f"🚀 启动库存监控系统，检查间隔: {check_interval}秒")
            
            self.is_running = True
            
            # 在新线程中启动监控
            self.monitor_thread = threading.Thread(
                target=self.inventory_monitor.start_monitoring,
                args=(check_interval,),
                daemon=True
            )
            self.monitor_thread.start()
            
            # 主线程保持运行
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("👋 收到中断信号")
        except Exception as e:
            self.logger.error(f"❌ 监控过程中出错: {e}")
        finally:
            self.shutdown()
    
    def simulate_orders(self, count: int = 3, interval: int = 30):
        """模拟订单创建"""
        if not self.order_simulator:
            self.logger.error("❌ 订单模拟器未初始化")
            return False
        
        try:
            self.logger.info(f"🎯 开始模拟 {count} 个订单")
            orders = self.order_simulator.simulate_order_batch(count, interval)
            
            # 保存订单记录
            self.order_simulator.save_orders_to_file(
                orders, 
                f"simulated_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            self.logger.info("✅ 订单模拟完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 订单模拟失败: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        status = {
            'system_running': self.is_running,
            'current_time': datetime.now().isoformat(),
            'clients_initialized': {
                'woocommerce': self.wc_client is not None,
                'google_sheets': self.sheets_client is not None,
                'bom_calculator': self.bom_calculator is not None,
                'inventory_monitor': self.inventory_monitor is not None
            }
        }
        
        if self.inventory_monitor:
            status['monitoring_status'] = self.inventory_monitor.get_monitoring_status()
        
        return status
    
    def shutdown(self):
        """关闭系统"""
        self.logger.info("🛑 正在关闭系统...")
        
        self.is_running = False
        
        # 停止监控
        if self.inventory_monitor:
            self.inventory_monitor.stop_monitoring()
        
        # 等待监控线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("✅ 系统已关闭")

def main():
    """主函数"""
    print("🏭 原材料库存管理系统")
    print("=" * 50)
    
    # 创建系统实例
    system = MaterialInventorySystem()
    
    # 加载配置
    if not system.load_config():
        print("❌ 配置加载失败，退出")
        return 1
    
    # 初始化客户端
    if not system.initialize_clients():
        print("❌ 客户端初始化失败，退出")
        return 1
    
    # 执行初始同步
    if not system.run_initial_sync():
        print("❌ 初始同步失败，退出")
        return 1
    
    # 显示菜单
    while True:
        print("\n📋 请选择操作:")
        print("1. 开始监控订单")
        print("2. 模拟订单创建")
        print("3. 查看系统状态")
        print("4. 执行手动同步")
        print("5. 退出系统")
        
        choice = input("请输入选项 (1-5): ").strip()
        
        if choice == '1':
            interval = input("请输入检查间隔（秒，默认60）: ").strip()
            interval = int(interval) if interval.isdigit() else 60
            system.start_monitoring(interval)
            break
            
        elif choice == '2':
            count = input("请输入订单数量（默认3）: ").strip()
            count = int(count) if count.isdigit() else 3
            
            interval = input("请输入订单间隔（秒，默认30）: ").strip()
            interval = int(interval) if interval.isdigit() else 30
            
            system.simulate_orders(count, interval)
            
        elif choice == '3':
            status = system.get_system_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
            
        elif choice == '4':
            print("🔄 执行手动同步...")
            system.run_initial_sync()
            
        elif choice == '5':
            system.shutdown()
            break
            
        else:
            print("❌ 无效选项，请重新选择")
    
    return 0

if __name__ == "__main__":
    exit(main())
