#!/usr/bin/env python3
"""
异常检测脚本 - 识别传感器数据中的异常读数（增强版）

功能：
1. 筛选指定时间范围的传感器数据
2. 结合Excel参数配置识别异常
3. 生成异常报告
4. 支持多数据集处理和灵活配置
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import argparse
import glob
from pathlib import Path

def find_data_files(prefix=""):
    """查找数据文件"""
    if prefix and not prefix.endswith('_'):
        prefix += '_'
    
    sensor_pattern = f"{prefix}live_sensor_data.csv"
    params_pattern = f"{prefix}machine_operating_parameters.xlsx"
    
    sensor_files = glob.glob(sensor_pattern)
    params_files = glob.glob(params_pattern)
    
    if not sensor_files:
        # 尝试查找任何传感器数据文件
        all_sensor_files = glob.glob("*live_sensor_data.csv")
        if all_sensor_files:
            print(f"未找到 {sensor_pattern}，可用的传感器数据文件：")
            for i, file in enumerate(all_sensor_files):
                print(f"  {i+1}. {file}")
            return None, None
        else:
            print("未找到任何传感器数据文件")
            return None, None
    
    if not params_files:
        print(f"未找到参数配置文件: {params_pattern}")
        return None, None
    
    return sensor_files[0], params_files[0]

def load_data(prefix=""):
    """加载传感器数据和参数配置"""
    print("查找和加载数据文件...")
    
    sensor_file, params_file = find_data_files(prefix)
    if not sensor_file or not params_file:
        return None, None
    
    print(f"使用传感器数据文件: {sensor_file}")
    print(f"使用参数配置文件: {params_file}")
    
    # 加载传感器数据
    sensor_data = pd.read_csv(sensor_file)
    sensor_data['timestamp'] = pd.to_datetime(sensor_data['timestamp'])
    
    # 加载参数配置
    params_data = pd.read_excel(params_file, sheet_name='Operating Parameters')
    
    print(f"传感器数据记录数: {len(sensor_data):,}")
    print(f"参数配置记录数: {len(params_data):,}")
    print(f"数据时间范围: {sensor_data['timestamp'].min()} 到 {sensor_data['timestamp'].max()}")
    print(f"机器数量: {sensor_data['machine_id'].nunique()}")
    print(f"传感器类型: {sensor_data['sensor_type'].nunique()} ({', '.join(sorted(sensor_data['sensor_type'].unique()))})")
    
    return sensor_data, params_data

def parse_time_input(time_str):
    """解析时间输入，支持多种格式"""
    if not time_str:
        return None
    
    # 尝试不同的时间格式
    time_formats = [
        '%H:%M',           # 11:30
        '%H:%M:%S',        # 11:30:00
        '%Y-%m-%d %H:%M',  # 2024-08-19 11:30
        '%Y-%m-%d %H:%M:%S',  # 2024-08-19 11:30:00
        '%m-%d %H:%M',     # 08-19 11:30
    ]
    
    for fmt in time_formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"无法解析时间格式: {time_str}")

def filter_time_range(data, start_time=None, end_time=None):
    """筛选指定时间范围的数据"""
    if not start_time and not end_time:
        print("未指定时间范围，使用全部数据")
        return data
    
    print(f"\n筛选时间范围: {start_time or '数据开始'} 到 {end_time or '数据结束'}")
    
    filtered_data = data.copy()
    
    if start_time:
        try:
            start_dt = parse_time_input(start_time)
            
            # 如果只有时间没有日期，使用数据中的日期
            if start_dt.date() == datetime(1900, 1, 1).date():
                data_date = data['timestamp'].dt.date.iloc[0]
                start_dt = datetime.combine(data_date, start_dt.time())
            
            filtered_data = filtered_data[filtered_data['timestamp'] >= start_dt]
            
        except ValueError as e:
            print(f"开始时间解析错误: {e}")
            # 如果解析失败，尝试只比较时间部分
            try:
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                filtered_data = filtered_data[filtered_data['timestamp'].dt.time >= start_time_obj]
            except ValueError:
                print("使用默认开始时间")
    
    if end_time:
        try:
            end_dt = parse_time_input(end_time)
            
            # 如果只有时间没有日期，使用数据中的日期
            if end_dt.date() == datetime(1900, 1, 1).date():
                data_date = data['timestamp'].dt.date.iloc[-1]
                end_dt = datetime.combine(data_date, end_dt.time())
            
            filtered_data = filtered_data[filtered_data['timestamp'] <= end_dt]
            
        except ValueError as e:
            print(f"结束时间解析错误: {e}")
            # 如果解析失败，尝试只比较时间部分
            try:
                end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                filtered_data = filtered_data[filtered_data['timestamp'].dt.time <= end_time_obj]
            except ValueError:
                print("使用默认结束时间")
    
    print(f"筛选后数据记录数: {len(filtered_data):,}")
    
    if len(filtered_data) > 0:
        print(f"实际时间范围: {filtered_data['timestamp'].min()} 到 {filtered_data['timestamp'].max()}")
    
    return filtered_data

def detect_anomalies(sensor_data, params_data):
    """检测异常读数"""
    print("\n开始异常检测...")
    
    # 合并数据
    merged_data = sensor_data.merge(
        params_data[['machine_id', 'sensor_type', 'min_value', 'max_value', 'unit']], 
        on=['machine_id', 'sensor_type'],
        how='left'
    )
    
    # 检查是否有未匹配的数据
    unmatched = merged_data[merged_data['min_value'].isna()]
    if len(unmatched) > 0:
        print(f"警告: 有 {len(unmatched)} 条数据未找到对应的参数配置")
    
    # 识别异常
    merged_data['is_below_min'] = merged_data['reading'] < merged_data['min_value']
    merged_data['is_above_max'] = merged_data['reading'] > merged_data['max_value']
    merged_data['is_anomaly'] = merged_data['is_below_min'] | merged_data['is_above_max']
    
    # 筛选异常数据
    anomalies = merged_data[merged_data['is_anomaly']].copy()
    
    # 添加异常类型和正常范围信息
    anomalies['anomaly_type'] = anomalies.apply(
        lambda row: 'below_minimum' if row['is_below_min'] else 'above_maximum', 
        axis=1
    )
    anomalies['normal_range'] = (
        anomalies['min_value'].astype(str) + ' - ' + 
        anomalies['max_value'].astype(str) + ' ' + 
        anomalies['unit'].astype(str)
    )
    
    print(f"检测到异常数据: {len(anomalies)} 条")
    print(f"异常率: {len(anomalies) / len(merged_data) * 100:.1f}%")
    
    return anomalies, merged_data

def generate_anomaly_report(anomalies, output_prefix=""):
    """生成异常报告"""
    print("\n生成异常报告...")
    
    if len(anomalies) == 0:
        print("⚠️ 未发现异常数据，跳过报告生成")
        return pd.DataFrame(), None
    
    # 选择报告字段
    report_columns = [
        'timestamp', 'machine_id', 'sensor_type', 'reading', 
        'normal_range', 'anomaly_type', 'unit'
    ]
    
    report = anomalies[report_columns].copy()
    
    # 按时间排序
    report = report.sort_values('timestamp')
    
    # 添加严重程度评分
    def calculate_severity(row):
        try:
            # 解析 "min_val - max_val unit" 格式的字符串
            range_parts = row['normal_range'].split(' - ')
            min_val = float(range_parts[0])
            # 第二部分可能包含单位，需要提取数值部分
            max_part = range_parts[1].split()[0]  # 只取第一个空格前的部分
            max_val = float(max_part)
            
            range_size = max_val - min_val
            if range_size <= 0:  # 避免除零错误
                return 'Low'
                
            if row['anomaly_type'] == 'above_maximum':
                deviation = (row['reading'] - max_val) / range_size
            else:
                deviation = (min_val - row['reading']) / range_size
            
            if deviation >= 2.0:
                return 'Critical'
            elif deviation >= 1.0:
                return 'High'
            elif deviation >= 0.5:
                return 'Medium'
            else:
                return 'Low'
        except (ValueError, IndexError, ZeroDivisionError) as e:
            # 如果解析失败，使用简单的方法基于异常类型判断
            return 'Medium'
    
    report['severity'] = report.apply(calculate_severity, axis=1)
    
    # 生成文件名
    if output_prefix and not output_prefix.endswith('_'):
        output_prefix += '_'
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f'{output_prefix}anomaly_report_{timestamp_str}.csv'
    
    # 保存为CSV
    report.to_csv(report_filename, index=False)
    
    print(f"异常报告已保存到: {report_filename}")
    print(f"报告包含 {len(report)} 条异常记录")
    
    # 按严重程度统计
    severity_counts = report['severity'].value_counts()
    print("严重程度分布:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count} 条")
    
    return report, report_filename

def print_summary_statistics(anomalies, all_data):
    """打印汇总统计"""
    print("\n" + "="*60)
    print("异常检测汇总统计")
    print("="*60)
    
    if len(anomalies) == 0:
        print("未检测到任何异常数据")
        return
    
    # 总体统计
    total_records = len(all_data)
    anomaly_count = len(anomalies)
    anomaly_rate = anomaly_count / total_records * 100
    
    print(f"总数据记录数: {total_records:,}")
    print(f"异常数据记录数: {anomaly_count:,}")
    print(f"异常率: {anomaly_rate:.1f}%")
    
    # 按机器统计
    print(f"\n各机器异常统计:")
    machine_stats = anomalies.groupby('machine_id').agg({
        'timestamp': 'count',
        'reading': 'count'
    }).rename(columns={'timestamp': 'anomaly_count'})
    
    # 计算各机器的总数据量
    total_by_machine = all_data.groupby('machine_id').size()
    machine_stats['total_records'] = total_by_machine
    machine_stats['anomaly_rate'] = (machine_stats['anomaly_count'] / machine_stats['total_records'] * 100).round(1)
    
    print(machine_stats[['anomaly_count', 'anomaly_rate']].to_string())
    
    # 按传感器类型统计
    print(f"\n各传感器类型异常统计:")
    sensor_stats = anomalies.groupby('sensor_type').agg({
        'timestamp': 'count',
        'reading': 'count'
    }).rename(columns={'timestamp': 'anomaly_count'})
    
    total_by_sensor = all_data.groupby('sensor_type').size()
    sensor_stats['total_records'] = total_by_sensor
    sensor_stats['anomaly_rate'] = (sensor_stats['anomaly_count'] / sensor_stats['total_records'] * 100).round(1)
    
    print(sensor_stats[['anomaly_count', 'anomaly_rate']].to_string())
    
    # 按异常类型统计
    print(f"\n异常类型分布:")
    anomaly_type_stats = anomalies['anomaly_type'].value_counts()
    print(anomaly_type_stats.to_string())
    
    # 最严重的异常
    print(f"\n最严重的异常读数 (前10条):")
    
    # 计算偏离正常范围的程度
    anomalies_copy = anomalies.copy()
    anomalies_copy['deviation'] = anomalies_copy.apply(
        lambda row: abs(row['reading'] - row['max_value']) if row['anomaly_type'] == 'above_maximum' 
        else abs(row['min_value'] - row['reading']), axis=1
    )
    
    top_anomalies = anomalies_copy.nlargest(10, 'deviation')[
        ['timestamp', 'machine_id', 'sensor_type', 'reading', 'normal_range', 'deviation']
    ]
    
    print(top_anomalies.to_string(index=False))

def print_sample_anomalies(anomalies, n=15):
    """打印异常样本"""
    print(f"\n异常数据样本 (前{n}条):")
    
    if len(anomalies) == 0:
        print("无异常数据")
        return
    
    sample = anomalies.head(n)[
        ['timestamp', 'machine_id', 'sensor_type', 'reading', 'normal_range', 'anomaly_type']
    ]
    
    print(sample.to_string(index=False))

def show_dataset_overview(sensor_data):
    """显示数据集概览"""
    print(f"\n📊 数据集概览:")
    print(f"="*50)
    
    # 时间范围
    time_span = sensor_data['timestamp'].max() - sensor_data['timestamp'].min()
    print(f"📅 时间跨度: {time_span}")
    
    # 采样频率
    time_diffs = sensor_data['timestamp'].diff().dropna()
    avg_interval = time_diffs.median()
    print(f"⏰ 平均采样间隔: {avg_interval}")
    
    # 机器和传感器统计
    machines = sensor_data['machine_id'].unique()
    sensors = sensor_data['sensor_type'].unique()
    
    print(f"🏭 机器数量: {len(machines)}")
    print(f"📡 传感器类型: {len(sensors)}")
    print(f"   类型: {', '.join(sorted(sensors))}")
    
    # 数据完整性
    expected_records = len(machines) * len(sensors) * len(sensor_data['timestamp'].unique())
    actual_records = len(sensor_data)
    completeness = (actual_records / expected_records) * 100
    
    print(f"✅ 数据完整性: {completeness:.1f}% ({actual_records:,}/{expected_records:,})")
    
    # 数据质量
    null_count = sensor_data.isnull().sum().sum()
    print(f"❌ 缺失值数量: {null_count}")
    
    if null_count == 0:
        print("🎉 数据质量: 优秀（无缺失值）")
    elif null_count < actual_records * 0.01:
        print("👍 数据质量: 良好（缺失值 < 1%）")
    else:
        print("⚠️ 数据质量: 需要关注（缺失值较多）")

def list_available_datasets():
    """列出可用的数据集"""
    sensor_files = glob.glob("*live_sensor_data.csv")
    
    if not sensor_files:
        print("❌ 未找到任何传感器数据文件")
        return []
    
    print("📁 可用的数据集:")
    datasets = []
    
    for i, file in enumerate(sensor_files):
        # 提取前缀
        prefix = file.replace('live_sensor_data.csv', '').rstrip('_')
        if not prefix:
            prefix = "default"
        
        # 获取文件信息
        file_size = os.path.getsize(file) / 1024  # KB
        
        # 读取少量数据获取概览
        try:
            sample_data = pd.read_csv(file, nrows=100)
            machine_count = sample_data['machine_id'].nunique()
            sensor_count = sample_data['sensor_type'].nunique()
            
            print(f"  {i+1}. {prefix:<20} ({file_size:.1f}KB, {machine_count}台机器, {sensor_count}种传感器)")
            datasets.append(prefix)
            
        except Exception as e:
            print(f"  {i+1}. {prefix:<20} ({file_size:.1f}KB, 读取错误: {e})")
    
    return datasets

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='工厂物联网传感器异常检测系统（增强版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础用法（使用默认数据文件）
  python anomaly_detection.py
  
  # 指定数据集前缀
  python anomaly_detection.py --prefix large_dataset
  
  # 指定时间范围
  python anomaly_detection.py --start-time "11:30" --end-time "12:30"
  
  # 完整日期时间
  python anomaly_detection.py --start-time "2024-08-19 11:30" --end-time "2024-08-19 12:30"
  
  # 显示可用数据集
  python anomaly_detection.py --list-datasets
  
  # 只显示概览，不进行异常检测
  python anomaly_detection.py --overview-only
        """
    )
    
    parser.add_argument('--prefix', type=str, default='',
                        help='数据文件前缀，默认: 无前缀')
    parser.add_argument('--start-time', type=str, default=None,
                        help='开始时间 (格式: HH:MM 或 YYYY-MM-DD HH:MM)')
    parser.add_argument('--end-time', type=str, default=None,
                        help='结束时间 (格式: HH:MM 或 YYYY-MM-DD HH:MM)')
    parser.add_argument('--output-prefix', type=str, default='',
                        help='输出报告文件前缀，默认: 无前缀')
    parser.add_argument('--list-datasets', action='store_true',
                        help='列出可用的数据集')
    parser.add_argument('--overview-only', action='store_true',
                        help='只显示数据集概览，不进行异常检测')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 如果只是列出数据集
    if args.list_datasets:
        list_available_datasets()
        return
    
    print("="*80)
    print("🏭 工厂物联网传感器异常检测系统（增强版）")
    print("="*80)
    
    try:
        # 加载数据
        sensor_data, params_data = load_data(args.prefix)
        
        if sensor_data is None or params_data is None:
            print("\n💡 提示: 使用 --list-datasets 查看可用的数据集")
            return
        
        # 显示数据集概览
        show_dataset_overview(sensor_data)
        
        # 如果只显示概览
        if args.overview_only:
            return
        
        # 筛选时间范围
        filtered_data = filter_time_range(sensor_data, args.start_time, args.end_time)
        
        if len(filtered_data) == 0:
            print("⚠️ 警告: 指定时间范围内没有数据")
            return
        
        # 检测异常
        anomalies, all_filtered_data = detect_anomalies(filtered_data, params_data)
        
        # 生成报告
        output_prefix = args.output_prefix or args.prefix
        report, report_filename = generate_anomaly_report(anomalies, output_prefix)
        
        if report_filename:
            # 打印统计信息
            print_summary_statistics(anomalies, all_filtered_data)
            
            # 打印异常样本
            print_sample_anomalies(anomalies)
            
            print(f"\n" + "="*80)
            print("🎉 异常检测完成！")
            print("="*80)
            print(f"📄 生成的文件: {report_filename}")
            print(f"📊 异常数据总数: {len(anomalies):,}")
            print("💡 建议: 将异常报告上传至 iot_anomaly_reports 云存储桶")
        
    except FileNotFoundError as e:
        print(f"❌ 错误: 找不到数据文件 - {e}")
        print("💡 提示:")
        print("   1. 检查文件路径是否正确")
        print("   2. 使用 --list-datasets 查看可用数据集")
        print("   3. 使用 --prefix 指定正确的数据集前缀")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 