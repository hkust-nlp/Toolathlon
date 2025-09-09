#!/usr/bin/env python3
"""
订单模拟脚本 - 用于测试系统
"""

import os
import sys
import argparse

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from main_workflow import MaterialInventorySystem

def main():
    """模拟订单主函数"""
    parser = argparse.ArgumentParser(description='原材料库存管理系统 - 订单模拟器')
    parser.add_argument('--count', type=int, default=3, help='模拟订单数量 (默认: 3)')
    parser.add_argument('--interval', type=int, default=30, help='订单间隔秒数 (默认: 30)')
    
    args = parser.parse_args()
    
    print("🎯 订单模拟器")
    print("=" * 30)
    print(f"订单数量: {args.count}")
    print(f"间隔时间: {args.interval} 秒")
    print("=" * 30)
    
    try:
        # 创建系统实例
        system = MaterialInventorySystem()
        
        # 加载配置和初始化
        if not system.load_config():
            print("❌ 配置加载失败")
            return 1
        
        if not system.initialize_clients():
            print("❌ 客户端初始化失败")
            return 1
        
        # 模拟订单
        success = system.simulate_orders(args.count, args.interval)
        
        if success:
            print("✅ 订单模拟完成")
            return 0
        else:
            print("❌ 订单模拟失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n👋 用户中断")
    except Exception as e:
        print(f"❌ 模拟过程出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
