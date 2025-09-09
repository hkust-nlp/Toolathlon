#!/usr/bin/env python3
"""
数据验证脚本 - 检查生成的传感器数据质量
"""

import pandas as pd
import numpy as np

def verify_sensor_data():
    """验证传感器数据"""
    print("正在验证传感器数据...")
    
    # 读取数据
    sensor_data = pd.read_csv('live_sensor_data.csv')
    params_data = pd.read_excel('machine_operating_parameters.xlsx', sheet_name='Operating Parameters')
    
    print(f"传感器数据记录数: {len(sensor_data)}")
    print(f"参数配置记录数: {len(params_data)}")
    
    # 检查数据结构
    print("\n传感器数据列:", sensor_data.columns.tolist())
    print("参数配置列:", params_data.columns.tolist())
    
    # 检查机器和传感器类型
    machines = sensor_data['machine_id'].unique()
    sensor_types = sensor_data['sensor_type'].unique()
    
    print(f"\n机器数量: {len(machines)}")
    print(f"传感器类型数量: {len(sensor_types)}")
    print(f"机器ID: {sorted(machines)}")
    print(f"传感器类型: {sorted(sensor_types)}")
    
    # 检查异常数据
    print("\n检查异常数据...")
    
    # 合并数据以便比较
    merged = sensor_data.merge(
        params_data[['machine_id', 'sensor_type', 'min_value', 'max_value']], 
        on=['machine_id', 'sensor_type']
    )
    
    # 标识异常
    merged['is_below_min'] = merged['reading'] < merged['min_value']
    merged['is_above_max'] = merged['reading'] > merged['max_value']
    merged['is_anomaly'] = merged['is_below_min'] | merged['is_above_max']
    
    anomaly_count = merged['is_anomaly'].sum()
    anomaly_rate = merged['is_anomaly'].mean() * 100
    
    print(f"异常数据点数量: {anomaly_count}")
    print(f"异常数据比例: {anomaly_rate:.1f}%")
    
    # 按机器分析异常
    print("\n各机器异常统计:")
    anomaly_by_machine = merged.groupby('machine_id')['is_anomaly'].agg(['sum', 'count', 'mean'])
    anomaly_by_machine['anomaly_rate'] = anomaly_by_machine['mean'] * 100
    print(anomaly_by_machine[['sum', 'anomaly_rate']].round(1))
    
    # 按传感器类型分析异常
    print("\n各传感器类型异常统计:")
    anomaly_by_sensor = merged.groupby('sensor_type')['is_anomaly'].agg(['sum', 'count', 'mean'])
    anomaly_by_sensor['anomaly_rate'] = anomaly_by_sensor['mean'] * 100
    print(anomaly_by_sensor[['sum', 'anomaly_rate']].round(1))
    
    # 显示一些异常样本
    print("\n异常数据样本:")
    anomalies = merged[merged['is_anomaly']].copy()
    anomalies['normal_range'] = anomalies['min_value'].astype(str) + ' - ' + anomalies['max_value'].astype(str)
    sample_anomalies = anomalies[['timestamp', 'machine_id', 'sensor_type', 'reading', 'normal_range']].head(10)
    print(sample_anomalies.to_string(index=False))
    
    # 检查时间范围
    print(f"\n时间范围:")
    print(f"开始时间: {sensor_data['timestamp'].min()}")
    print(f"结束时间: {sensor_data['timestamp'].max()}")
    
    # 检查数据分布
    print(f"\n数据分布检查:")
    for sensor_type in sensor_types:
        type_data = sensor_data[sensor_data['sensor_type'] == sensor_type]['reading']
        print(f"{sensor_type}: 最小值={type_data.min():.2f}, 最大值={type_data.max():.2f}, 平均值={type_data.mean():.2f}")

def verify_parameters_config():
    """验证参数配置"""
    print("\n" + "="*50)
    print("验证参数配置文件...")
    
    params_data = pd.read_excel('machine_operating_parameters.xlsx', sheet_name='Operating Parameters')
    
    # 检查每台机器是否有所有传感器类型的配置
    machines = params_data['machine_id'].unique()
    sensor_types = params_data['sensor_type'].unique()
    
    print(f"配置中的机器数量: {len(machines)}")
    print(f"配置中的传感器类型数量: {len(sensor_types)}")
    
    # 检查完整性
    expected_configs = len(machines) * len(sensor_types)
    actual_configs = len(params_data)
    
    print(f"期望配置数量: {expected_configs}")
    print(f"实际配置数量: {actual_configs}")
    
    if expected_configs == actual_configs:
        print("✅ 配置完整性检查通过")
    else:
        print("❌ 配置不完整")
    
    # 显示参数配置样本
    print("\n参数配置样本:")
    sample_params = params_data[['machine_id', 'sensor_type', 'min_value', 'max_value', 'unit']].head(10)
    print(sample_params.to_string(index=False))

if __name__ == "__main__":
    verify_sensor_data()
    verify_parameters_config()
    print("\n" + "="*50)
    print("数据验证完成！") 