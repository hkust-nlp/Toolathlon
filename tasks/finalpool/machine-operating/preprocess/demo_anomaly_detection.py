#!/usr/bin/env python3
"""
异常检测功能演示脚本

展示增强后的anomaly_detection.py的各种功能
"""

import subprocess
import os
import time

def run_command(description, command, show_output=True):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"命令: {command}")
    print()
    
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            if show_output:
                print(result.stdout)
        else:
            print("❌ 执行失败！")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ 执行出错: {e}")

def main():
    """演示主函数"""
    print("🔍 工厂物联网传感器异常检测系统 - 功能演示")
    print("📊 展示增强后的异常检测功能")
    
    # 首先生成一些测试数据
    print(f"\n{'='*60}")
    print("📋 准备测试数据")
    print(f"{'='*60}")
    
    # 检查是否已有数据
    if not os.path.exists('live_sensor_data.csv'):
        print("🔄 生成基础测试数据...")
        subprocess.run(['python', 'main.py', '--hours', '2', '--prefix', 'demo'], 
                      capture_output=True)
        print("✅ 基础数据生成完成")
    
    if not any(f.startswith('extended_') for f in os.listdir('.') if f.endswith('.csv')):
        print("🔄 生成扩展测试数据...")
        subprocess.run(['python', 'main.py', '--hours', '1', '--machines', '5', 
                       '--sensors', 'humidity,power', '--prefix', 'extended'], 
                      capture_output=True)
        print("✅ 扩展数据生成完成")
    
    demos = [
        {
            "description": "查看可用数据集",
            "command": "python anomaly_detection.py --list-datasets",
            "show_output": True
        },
        {
            "description": "显示默认数据集概览",
            "command": "python anomaly_detection.py --overview-only",
            "show_output": True
        },
        {
            "description": "基础异常检测（全时间范围）",
            "command": "python anomaly_detection.py --output-prefix basic",
            "show_output": False  # 输出太长，只显示命令
        },
        {
            "description": "指定时间范围的异常检测",
            "command": "python anomaly_detection.py --start-time 11:30 --end-time 12:30 --output-prefix time_range",
            "show_output": False
        },
        {
            "description": "扩展数据集异常检测",
            "command": "python anomaly_detection.py --prefix extended --output-prefix extended_analysis",
            "show_output": False
        }
    ]
    
    print(f"\n🎯 将执行 {len(demos)} 个演示:")
    for i, demo in enumerate(demos, 1):
        print(f"{i}. {demo['description']}")
    
    input("\n按 Enter 开始演示...")
    
    for i, demo in enumerate(demos, 1):
        run_command(f"演示 {i}: {demo['description']}", 
                   demo['command'], demo['show_output'])
        
        if demo['show_output'] and i < len(demos):
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("📊 演示完成，查看生成的报告文件")
    print(f"{'='*60}")
    
    # 显示生成的报告文件
    report_files = [f for f in os.listdir('.') if f.startswith('anomaly_report_') or 
                   f.endswith('_anomaly_report_')]
    
    if report_files:
        print("📄 生成的异常报告文件:")
        for file in sorted(report_files)[-5:]:  # 显示最新的5个
            size = os.path.getsize(file) / 1024
            print(f"  📋 {file:<50} ({size:.1f}KB)")
    else:
        print("⚠️ 未找到生成的报告文件")
    
    print(f"\n💡 提示:")
    print(f"   - 查看报告文件了解详细的异常信息")
    print(f"   - 使用 --help 查看更多参数选项")
    print(f"   - 结合不同参数组合进行灵活的异常分析")

if __name__ == "__main__":
    main() 