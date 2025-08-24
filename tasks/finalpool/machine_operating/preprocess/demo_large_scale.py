#!/usr/bin/env python3
"""
大规模数据生成演示脚本

展示如何使用扩展后的main.py生成不同规模和复杂度的数据集
"""

import subprocess
import os
import time

def run_generation(description, command, estimate_time=None):
    """运行数据生成命令"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"命令: {command}")
    
    if estimate_time:
        print(f"预估用时: {estimate_time}")
        
    print("\n开始执行...")
    start_time = time.time()
    
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 执行成功！")
            print(result.stdout)
        else:
            print("❌ 执行失败！")
            print(result.stderr)
            
        elapsed = time.time() - start_time
        print(f"\n实际用时: {elapsed:.1f} 秒")
        
    except Exception as e:
        print(f"❌ 执行出错: {e}")

def main():
    """演示主函数"""
    print("🏭 工厂物联网传感器数据生成器 - 大规模数据演示")
    print("📊 将生成不同规模的数据集来展示系统能力")
    
    demos = [
        {
            "description": "小规模数据集 (适合快速测试)",
            "command": "python main.py --preset small --prefix demo_small",
            "estimate": "< 10秒"
        },
        {
            "description": "中等规模数据集 (包含额外传感器)",
            "command": "python main.py --preset medium --prefix demo_medium", 
            "estimate": "10-30秒"
        },
        {
            "description": "自定义大规模数据集 (高频采样)",
            "command": "python main.py --hours 8 --interval 2 --machines 15 --sensors humidity,power,efficiency --complexity 1.5 --prefix demo_custom",
            "estimate": "30-60秒"
        },
        {
            "description": "高难度复杂数据集 (多重异常模式)",
            "command": "python main.py --hours 4 --machines 10 --sensors humidity,power --multi-anomaly --noise --cascade-failure --prefix demo_complex",
            "estimate": "20-40秒"
        }
    ]
    
    print(f"\n将执行 {len(demos)} 个演示:")
    for i, demo in enumerate(demos, 1):
        print(f"{i}. {demo['description']}")
    
    input("\n按 Enter 继续执行演示...")
    
    for i, demo in enumerate(demos, 1):
        run_generation(f"演示 {i}: {demo['description']}", demo['command'], demo['estimate'])
        
        if i < len(demos):
            print(f"\n⏳ 等待 2 秒后继续下一个演示...")
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("🎉 所有演示完成！")
    print(f"{'='*60}")
    
    # 显示生成的文件
    print("\n📁 生成的文件:")
    files = []
    for file in os.listdir('.'):
        if file.startswith('demo_') and (file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.json')):
            size = os.path.getsize(file) / 1024  # KB
            files.append((file, size))
    
    files.sort(key=lambda x: x[1], reverse=True)  # 按大小排序
    
    for file, size in files:
        if size >= 1024:
            print(f"  📊 {file:<40} ({size/1024:.1f} MB)")
        else:
            print(f"  📄 {file:<40} ({size:.1f} KB)")
    
    print(f"\n💡 提示:")
    print(f"   - 使用 'python verify_data.py' 验证数据质量")
    print(f"   - 使用 'python anomaly_detection.py' 进行异常检测")
    print(f"   - 大文件建议使用分批处理")

if __name__ == "__main__":
    main() 