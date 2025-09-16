#!/usr/bin/env python3
"""
Live Transactions 完整工作流程演示

演示从检测可疑交易到完成调查归档的完整流程：
1. 查询与交易ID相关的所有数据
2. 生成完整的调查档案JSON对象  
3. 上传到fraud-investigation-archive存储桶
4. 写入CRITICAL级别告警日志
"""

import subprocess
import json
import os
from datetime import datetime

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n🔄 {description}")
    print(f"命令: {command}")
    print("=" * 60)
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
        print(f"✅ {description} - 完成")
    else:
        print(f"❌ {description} - 失败")
        print(result.stderr)
    
    return result.returncode == 0

def display_file_content(filename, description, max_lines=20):
    """显示文件内容"""
    print(f"\n📄 {description}")
    print(f"文件: {filename}")
    print("=" * 60)
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        print(f"文件大小: {os.path.getsize(filename)} 字节")
        print(f"总行数: {len(lines)}")
        print(f"显示前{min(max_lines, len(lines))}行:")
        print("-" * 40)
        
        for i, line in enumerate(lines[:max_lines]):
            print(f"{i+1:3d}| {line.rstrip()}")
        
        if len(lines) > max_lines:
            print(f"... 还有 {len(lines) - max_lines} 行")
    else:
        print(f"❌ 文件不存在: {filename}")

def analyze_json_structure(filename, description):
    """分析JSON文件结构"""
    print(f"\n📊 {description}")
    print(f"文件: {filename}")
    print("=" * 60)
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        def analyze_object(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        print(f"{prefix}📁 {key}: {len(value)} 个字段")
                        if len(prefix) < 6:  # 限制递归深度
                            analyze_object(value, prefix + "  ")
                    elif isinstance(value, list):
                        print(f"{prefix}📋 {key}: {len(value)} 个项目")
                        if value and len(prefix) < 6:
                            print(f"{prefix}  └─ 示例项目类型: {type(value[0]).__name__}")
                    else:
                        value_str = str(value)
                        if len(value_str) > 50:
                            value_str = value_str[:47] + "..."
                        print(f"{prefix}📝 {key}: {value_str}")
        
        analyze_object(data)
    else:
        print(f"❌ 文件不存在: {filename}")

def main():
    """主演示流程"""
    print("🚀 Live Transactions 可疑交易调查完整工作流程演示")
    print("=" * 80)
    print(f"开始时间: {datetime.now().isoformat()}")
    print(f"可疑交易ID: T8492XJ3")
    print(f"场景: 大额加密货币兑换 + 高风险商户 + VPN设备")
    
    # 步骤1: 查询可疑交易相关数据
    success = run_command(
        "python query_suspicious_transaction.py --transaction-id T8492XJ3 --show-summary",
        "步骤1: 查询可疑交易T8492XJ3的所有相关数据"
    )
    
    if not success:
        print("❌ 查询失败，终止演示")
        return
    
    # 分析调查报告结构
    analyze_json_structure(
        "T8492XJ3_investigation_report.json",
        "调查报告JSON对象结构分析"
    )
    
    # 步骤2: 上传归档和写入日志
    success = run_command(
        "python upload_to_archive.py --report-file T8492XJ3_investigation_report.json",
        "步骤2: 上传调查档案到存储桶并写入告警日志"
    )
    
    if not success:
        print("❌ 归档失败，终止演示")
        return
    
    # 分析归档文件结构
    analyze_json_structure(
        "archive_T8492XJ3.json",
        "归档文件JSON对象结构分析"
    )
    
    # 显示关键文件内容
    display_file_content(
        "log_fraud_alert_20250818_150327.json",
        "CRITICAL级别告警日志内容",
        50
    )
    
    # 步骤3: 生成处理结果摘要
    print(f"\n📋 处理结果摘要")
    print("=" * 60)
    
    if os.path.exists("processing_result.json"):
        with open("processing_result.json", 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        print(f"✅ 交易ID: {result['transaction_id']}")
        print(f"📅 处理时间: {result['processing_timestamp']}")
        print(f"📤 归档文件: {result['archive_result']['object_name']}")
        print(f"📝 日志文件: {result['logging_result']['log_file']}")
        print(f"⚠️  风险等级: {result['investigation_summary']['risk_assessment']['overall_risk_level']}")
        print(f"💰 交易金额: ${result['investigation_summary']['transaction_pattern']['transaction_amount']:,.2f}")
        print(f"🚨 欺诈概率: {result['investigation_summary']['estimated_fraud_probability']:.1%}")
        
        print(f"\n📝 推荐的后续行动:")
        for action in result['next_steps']:
            print(f"  • {action}")
    
    # 最终统计
    print(f"\n📊 生成的文件统计")
    print("=" * 60)
    
    files = [
        "T8492XJ3_investigation_report.json",
        "archive_T8492XJ3.json", 
        "log_fraud_alert_20250818_150327.json",
        "processing_result.json"
    ]
    
    total_size = 0
    for filename in files:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            total_size += size
            print(f"📄 {filename}: {size / 1024:.1f} KB")
    
    print(f"\n💾 总文件大小: {total_size / 1024:.1f} KB")
    print(f"🎯 完整调查档案已生成并成功归档")
    
    print(f"\n✅ 演示完成！")
    print("=" * 80)
    print("这个演示展示了如何：")
    print("1. 🔍 查询与可疑交易ID相关的所有数据")
    print("2. 📋 将数据组装成完整的JSON调查档案")
    print("3. 📤 上传到fraud-investigation-archive存储桶")
    print("4. 📝 写入CRITICAL级别的结构化告警日志")
    print("5. 📊 生成完整的处理结果报告")

if __name__ == "__main__":
    main() 