#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考试通知邮件一键导入脚本
直接将邮件注入到收件箱，而不是通过发送
支持自定义时间戳
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加路径以便导入send_exam_notification_smtp模块
sys.path.append(str(Path(__file__).parent))

from send_exam_notification_smtp import inject_exam_emails_from_config


def inject_with_custom_time():
    """使用自定义时间注入邮件"""
    
    # 配置文件路径
    config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
    
    print("🕐 一键导入考试通知邮件 - 自定义时间模式")
    print("=" * 50)
    
    # 设置不同的时间点示例
    email_scenarios = [
        {
            "name": "期末考试通知（发送于12月1日上午）",
            "time": datetime(2024, 12, 1, 10, 0, 0),
            "description": "学期末期，正式通知期末考试安排"
        },
        {
            "name": "考试提醒（发送于12月15日下午）", 
            "time": datetime(2024, 12, 15, 15, 30, 0),
            "description": "考试前一个月提醒"
        },
        {
            "name": "最后提醒（发送于1月10日早上）",
            "time": datetime(2025, 1, 10, 8, 0, 0), 
            "description": "考试前几天的最后提醒"
        }
    ]
    
    print("请选择要导入的邮件场景：")
    for i, scenario in enumerate(email_scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   时间: {scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   说明: {scenario['description']}")
        print()
    
    print("4. 使用当前时间")
    print("5. 手动输入时间")
    print()
    
    try:
        choice = input("请输入选择 (1-5): ").strip()
        
        if choice == "1":
            selected_scenario = email_scenarios[0]
            timestamp = selected_scenario["time"].timestamp()
            print(f"📅 选择场景: {selected_scenario['name']}")
            print(f"⏰ 邮件时间: {selected_scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "2":
            selected_scenario = email_scenarios[1]
            timestamp = selected_scenario["time"].timestamp()
            print(f"📅 选择场景: {selected_scenario['name']}")
            print(f"⏰ 邮件时间: {selected_scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "3":
            selected_scenario = email_scenarios[2]
            timestamp = selected_scenario["time"].timestamp()
            print(f"📅 选择场景: {selected_scenario['name']}")
            print(f"⏰ 邮件时间: {selected_scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "4":
            timestamp = None
            print("📅 使用当前时间")
            
        elif choice == "5":
            print("请输入时间 (格式: YYYY-MM-DD HH:MM:SS)")
            time_str = input("时间: ").strip()
            custom_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            timestamp = custom_time.timestamp()
            print(f"⏰ 自定义时间: {custom_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        else:
            print("❌ 无效选择")
            return False
            
        print("\n🚀 开始导入邮件...")
        print("-" * 50)
        
        # 执行邮件注入
        success = inject_exam_emails_from_config(str(config_file), timestamp)
        
        return success
        
    except ValueError as e:
        print(f"❌ 时间格式错误: {e}")
        print("请使用格式: YYYY-MM-DD HH:MM:SS，例如: 2024-12-01 10:00:00")
        return False
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return False


def inject_current_time():
    """使用当前时间注入邮件"""
    
    config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
    
    print("🕐 一键导入考试通知邮件 - 当前时间模式")
    print("=" * 50)
    
    # 使用当前时间注入
    success = inject_exam_emails_from_config(str(config_file), None)
    
    return success


def main():
    """主函数"""
    print("📧 考试通知邮件一键导入工具")
    print("🎯 直接将邮件注入到收件箱，无需SMTP发送")
    print("⏰ 支持自定义邮件时间戳")
    print("=" * 60)
    print()
    
    print("请选择导入模式：")
    print("1. 自定义时间模式 (可选择预设场景或手动输入时间)")
    print("2. 当前时间模式 (立即导入)")
    print("3. 退出")
    print()
    
    try:
        mode = input("请输入选择 (1-3): ").strip()
        
        if mode == "1":
            success = inject_with_custom_time()
        elif mode == "2":
            success = inject_current_time()
        elif mode == "3":
            print("👋 再见！")
            return
        else:
            print("❌ 无效选择")
            return
            
        if success:
            print("\n" + "=" * 60)
            print("🎉 邮件导入成功完成！")
            print("📬 请检查收件箱确认邮件已成功导入")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("💥 邮件导入失败！")
            print("🔍 请检查配置文件和网络连接")
            print("=" * 60)
            
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")


if __name__ == "__main__":
    main() 