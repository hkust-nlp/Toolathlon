#!/usr/bin/env python3
"""
原材料库存管理系统 - 简化启动脚本
"""

import os
import sys

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from main_workflow import MaterialInventorySystem

def main():
    """简化的主函数"""
    print("🏭 原材料库存管理系统 - 快速启动")
    print("=" * 50)
    
    try:
        # 创建系统实例
        system = MaterialInventorySystem()
        
        print("📋 初始化系统...")
        
        # 加载配置
        if not system.load_config():
            print("❌ 配置加载失败")
            return 1
        
        # 初始化客户端
        if not system.initialize_clients():
            print("❌ 客户端初始化失败")
            return 1
        
        # 执行初始同步
        if not system.run_initial_sync():
            print("❌ 初始同步失败")
            return 1
        
        print("✅ 系统初始化完成")
        print("\n🚀 开始监控订单...")
        
        # 直接开始监控
        system.start_monitoring(check_interval=60)
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    except Exception as e:
        print(f"❌ 系统运行出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
