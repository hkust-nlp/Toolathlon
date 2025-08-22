#!/usr/bin/env python3
"""
Live Transactions CSV格式工作流程演示

演示如何使用CSV格式进行数据分析和可疑交易调查：
1. 生成CSV格式的数据集
2. 使用pandas进行数据分析
3. 查询可疑交易并生成报告
4. 展示CSV格式的优势
"""

import subprocess
import pandas as pd
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

def analyze_csv_data(csv_dir):
    """使用pandas分析CSV数据"""
    print(f"\n📊 使用pandas分析CSV数据")
    print("=" * 60)
    
    # 读取主要的表
    tables = {}
    for table_name in ['live_transactions', 'users', 'merchants', 'devices']:
        csv_file = os.path.join(csv_dir, f"{table_name}.csv")
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            tables[table_name] = df
            print(f"📄 {table_name}: {len(df)} 行, {len(df.columns)} 列")
    
    print(f"\n📈 数据统计分析:")
    
    # 交易金额分析
    if 'live_transactions' in tables:
        tx_df = tables['live_transactions']
        print(f"\n💰 交易金额分析:")
        print(f"  • 总交易数: {len(tx_df)}")
        print(f"  • 平均金额: ${tx_df['amount'].mean():,.2f}")
        print(f"  • 最大金额: ${tx_df['amount'].max():,.2f}")
        print(f"  • 最小金额: ${tx_df['amount'].min():,.2f}")
        print(f"  • 高风险交易数 (>$100K): {len(tx_df[tx_df['amount'] > 100000])}")
        
        # 风险评分分析
        print(f"\n⚠️  风险评分分析:")
        high_risk = tx_df[tx_df['risk_score'] >= 8.0]
        print(f"  • 高风险交易 (≥8.0): {len(high_risk)} 笔")
        print(f"  • 平均风险评分: {tx_df['risk_score'].mean():.2f}")
        print(f"  • 最高风险评分: {tx_df['risk_score'].max():.2f}")
        
        # 显示高风险交易
        if len(high_risk) > 0:
            print(f"\n🚨 高风险交易详情:")
            for _, row in high_risk.iterrows():
                print(f"  • {row['transaction_id']}: ${row['amount']:,.2f} (风险: {row['risk_score']}/10)")
    
    # 用户风险分析
    if 'users' in tables:
        users_df = tables['users']
        print(f"\n👥 用户风险分析:")
        risk_counts = users_df['risk_level'].value_counts()
        for risk_level, count in risk_counts.items():
            print(f"  • {risk_level}: {count} 用户")
    
    # 商户风险分析
    if 'merchants' in tables:
        merchants_df = tables['merchants']
        print(f"\n🏪 商户风险分析:")
        merchant_risk_counts = merchants_df['risk_rating'].value_counts()
        for risk_level, count in merchant_risk_counts.items():
            print(f"  • {risk_level}: {count} 商户")
    
    # 设备风险分析
    if 'devices' in tables:
        devices_df = tables['devices']
        print(f"\n💻 设备风险分析:")
        vpn_count = devices_df['vpn_detected'].sum()
        tor_count = devices_df['tor_detected'].sum()
        proxy_count = devices_df['proxy_detected'].sum()
        print(f"  • VPN检测: {vpn_count} 设备")
        print(f"  • Tor检测: {tor_count} 设备")
        print(f"  • 代理检测: {proxy_count} 设备")
    
    return tables

def demonstrate_csv_advantages():
    """演示CSV格式的优势"""
    print(f"\n💡 CSV格式的优势展示")
    print("=" * 60)
    
    print(f"✅ 1. 通用性强:")
    print(f"  • Excel可直接打开分析")
    print(f"  • 所有数据库都支持CSV导入")
    print(f"  • pandas/R等数据科学工具原生支持")
    
    print(f"\n✅ 2. 体积小巧:")
    csv_size = sum(os.path.getsize(os.path.join('test_csv', f)) 
                   for f in os.listdir('test_csv') if f.endswith('.csv'))
    json_size = os.path.getsize('live_transactions_dataset.json') if os.path.exists('live_transactions_dataset.json') else 0
    print(f"  • CSV总大小: {csv_size / 1024:.1f} KB")
    print(f"  • JSON大小: {json_size / 1024:.1f} KB")
    print(f"  • 压缩比: {(json_size - csv_size) / json_size * 100:.1f}% 更小" if json_size > 0 else "")
    
    print(f"\n✅ 3. 易于处理:")
    print(f"  • 结构化数据，列式存储")
    print(f"  • 可以单独处理每个表")
    print(f"  • 便于数据清洗和预处理")
    
    print(f"\n✅ 4. 分析友好:")
    print(f"  • 支持SQL查询（如使用DuckDB）")
    print(f"  • 可视化工具直接读取")
    print(f"  • 机器学习模型训练数据格式")

def show_excel_import_guide():
    """显示Excel导入指导"""
    print(f"\n📊 Excel分析指导")
    print("=" * 60)
    
    print(f"在Excel中分析数据的步骤:")
    print(f"1. 📂 打开Excel，选择 '数据' > '从文本/CSV'")
    print(f"2. 📄 选择 'test_csv/live_transactions.csv' 文件")
    print(f"3. 🔧 Excel会自动识别分隔符，点击'加载'")
    print(f"4. 📈 使用数据透视表分析:")
    print(f"   • 行: transaction_type")
    print(f"   • 值: amount (求和)")
    print(f"   • 筛选器: risk_score > 8")
    print(f"5. 📊 创建图表:")
    print(f"   • 选择amount列，插入柱状图")
    print(f"   • 按risk_score分组显示")

def show_database_import_examples():
    """显示数据库导入示例"""
    print(f"\n🗄️  数据库导入示例")
    print("=" * 60)
    
    print(f"MySQL导入:")
    print(f"```sql")
    print(f"LOAD DATA INFILE 'test_csv/live_transactions.csv'")
    print(f"INTO TABLE live_transactions")
    print(f"FIELDS TERMINATED BY ','")
    print(f"ENCLOSED BY '\"'")
    print(f"LINES TERMINATED BY '\\n'")
    print(f"IGNORE 1 ROWS;")
    print(f"```")
    
    print(f"\nPostgreSQL导入:")
    print(f"```sql")
    print(f"COPY live_transactions FROM 'test_csv/live_transactions.csv'")
    print(f"DELIMITER ',' CSV HEADER;")
    print(f"```")
    
    print(f"\nSQLite导入:")
    print(f"```bash")
    print(f"sqlite3 transactions.db")
    print(f".mode csv")
    print(f".import test_csv/live_transactions.csv live_transactions")
    print(f"```")
    
    print(f"\nPandas读取:")
    print(f"```python")
    print(f"import pandas as pd")
    print(f"df = pd.read_csv('test_csv/live_transactions.csv')")
    print(f"# JSON字段解析")
    print(f"df['flags_parsed'] = df['flags'].apply(json.loads)")
    print(f"```")

def main():
    """主演示流程"""
    print("🚀 Live Transactions CSV格式工作流程演示")
    print("=" * 80)
    print(f"开始时间: {datetime.now().isoformat()}")
    print(f"演示内容: CSV数据生成、分析、查询和使用指导")
    
    # 步骤1: 生成CSV数据
    success = run_command(
        "python construct_data.py --scale 3 --suspicious-count 2 --export-csv --output-dir demo_csv",
        "步骤1: 生成CSV格式的数据集"
    )
    
    if not success:
        print("❌ CSV生成失败，终止演示")
        return
    
    # 步骤2: 使用pandas分析数据
    tables = analyze_csv_data("demo_csv")
    
    # 步骤3: 查询可疑交易
    success = run_command(
        "python query_suspicious_transaction.py --transaction-id T8492XJ1 --csv-dir demo_csv --show-summary",
        "步骤3: 从CSV数据查询可疑交易"
    )
    
    # 步骤4: 展示CSV优势
    demonstrate_csv_advantages()
    
    # 步骤5: 使用指导
    show_excel_import_guide()
    show_database_import_examples()
    
    print(f"\n📋 CSV文件列表:")
    print("=" * 60)
    if os.path.exists("demo_csv"):
        for filename in sorted(os.listdir("demo_csv")):
            if filename.endswith('.csv'):
                filepath = os.path.join("demo_csv", filename)
                size = os.path.getsize(filepath)
                df = pd.read_csv(filepath)
                print(f"📄 {filename}: {size / 1024:.1f} KB ({len(df)} 行 × {len(df.columns)} 列)")
    
    print(f"\n✅ CSV格式演示完成！")
    print("=" * 80)
    print("CSV格式的主要优势：")
    print("1. 📊 可直接在Excel中打开和分析")
    print("2. 🗄️  所有数据库都支持导入")
    print("3. 🐍 pandas等数据科学工具原生支持")
    print("4. 💾 文件体积更小，存储效率高")
    print("5. 🔍 结构清晰，便于数据探索")
    print("6. 🛠️  易于数据清洗和预处理")

if __name__ == "__main__":
    main() 