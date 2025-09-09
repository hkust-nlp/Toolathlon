#!/usr/bin/env python3
"""
工厂物联网传感器数据生成器 - 高可配置版本

生成以下文件：
1. live_sensor_data.csv - 传感器实时数据
2. machine_operating_parameters.xlsx - 机器操作参数配置

包含多种传感器类型和异常模式，用于测试异常检测系统。
支持大规模数据生成和复杂度调整。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import argparse
from typing import Dict, List, Tuple
import json

class DataGenerationConfig:
    """数据生成配置类"""
    def __init__(self):
        # 基础配置
        self.random_seed = 42
        self.time_duration_hours = 2
        self.sampling_interval_minutes = 5
        self.anomaly_probability = 0.15
        
        # 扩展配置
        self.additional_machines = 0  # 额外添加的机器数量
        self.additional_sensors = []  # 额外的传感器类型
        self.complexity_multiplier = 1.0  # 复杂度倍数
        self.output_prefix = ""  # 输出文件前缀
        
        # 高难度模式配置
        self.enable_multi_anomaly = False  # 多重异常
        self.enable_cascade_failure = False  # 级联故障
        self.enable_seasonal_patterns = False  # 季节性模式
        self.enable_noise_injection = False  # 噪声注入

# 设置随机种子以保证可重现性
config = DataGenerationConfig()

class IndustrialSensorDataGenerator:
    def __init__(self, config: DataGenerationConfig):
        self.config = config
        
        # 设置随机种子
        np.random.seed(config.random_seed)
        random.seed(config.random_seed)
        
        # 基础机器配置
        self.base_machines = {
            'M001': 'Assembly Line A - Component Insertion',
            'M002': 'Assembly Line B - Circuit Board Assembly', 
            'M003': 'Packaging Unit 1 - Primary Packaging',
            'M004': 'Packaging Unit 2 - Secondary Packaging',
            'M005': 'Quality Control Station - Inspection',
            'M006': 'Welding Robot 1 - Chassis Welding',
            'M007': 'Welding Robot 2 - Frame Welding',
            'M008': 'Paint Booth - Spray Coating',
            'M009': 'Cooling System - Temperature Control',
            'M010': 'Compressor Unit - Air Supply'
        }
        
        # 先初始化基础机器
        self.machines = self.base_machines.copy()
        
        print(f"配置信息: {len(self.machines)}台机器, {config.time_duration_hours}小时数据, {config.sampling_interval_minutes}分钟间隔")
        
        # 基础传感器类型和正常范围
        self.base_sensor_types = {
            'temperature': {
                'unit': '°C',
                'normal_ranges': {
                    'M001': (18, 25),    # 精密装配，温度要求严格
                    'M002': (20, 28),    # 电路板装配
                    'M003': (15, 30),    # 包装单元
                    'M004': (15, 30),    
                    'M005': (20, 24),    # 质检站，精密环境
                    'M006': (25, 45),    # 焊接机器人，温度较高
                    'M007': (25, 45),
                    'M008': (22, 35),    # 喷漆房
                    'M009': (5, 15),     # 冷却系统，温度较低
                    'M010': (20, 35)     # 压缩机
                }
            },
            'pressure': {
                'unit': 'bar',
                'normal_ranges': {
                    'M001': (0.8, 1.2),
                    'M002': (0.9, 1.1),
                    'M003': (0.7, 1.3),
                    'M004': (0.7, 1.3),
                    'M005': (0.95, 1.05),
                    'M006': (1.5, 2.5),   # 焊接需要更高压力
                    'M007': (1.5, 2.5),
                    'M008': (2.0, 3.0),   # 喷漆需要高压
                    'M009': (0.5, 1.0),
                    'M010': (6.0, 8.0)    # 压缩机高压
                }
            },
            'vibration': {
                'unit': 'mm/s',
                'normal_ranges': {
                    'M001': (0.1, 0.8),
                    'M002': (0.1, 0.6),
                    'M003': (0.2, 1.0),
                    'M004': (0.2, 1.0),
                    'M005': (0.05, 0.3),  # 质检站振动要很小
                    'M006': (0.5, 2.0),   # 焊接机器人振动较大
                    'M007': (0.5, 2.0),
                    'M008': (0.3, 1.5),
                    'M009': (0.1, 0.5),
                    'M010': (1.0, 3.0)    # 压缩机振动最大
                }
            },
            'rpm': {
                'unit': 'rpm',
                'normal_ranges': {
                    'M001': (1200, 1800),
                    'M002': (1000, 1500),
                    'M003': (800, 1200),
                    'M004': (800, 1200),
                    'M005': (500, 800),
                    'M006': (0, 100),     # 焊接机器人转速低
                    'M007': (0, 100),
                    'M008': (2000, 3000), # 喷漆高转速
                    'M009': (1500, 2500), # 冷却风扇
                    'M010': (3000, 4500)  # 压缩机高转速
                }
            },
            'current': {
                'unit': 'A',
                'normal_ranges': {
                    'M001': (2.0, 5.0),
                    'M002': (1.5, 4.0),
                    'M003': (3.0, 6.0),
                    'M004': (3.0, 6.0),
                    'M005': (1.0, 2.5),
                    'M006': (15, 25),     # 焊接大电流
                    'M007': (15, 25),
                    'M008': (8.0, 12.0),
                    'M009': (5.0, 10.0),
                    'M010': (20, 30)      # 压缩机大电流
                }
            },
            'flow_rate': {
                'unit': 'L/min',
                'normal_ranges': {
                    'M001': (10, 20),
                    'M002': (8, 15),
                    'M003': (5, 12),
                    'M004': (5, 12),
                    'M005': (2, 8),
                    'M006': (25, 40),     # 焊接冷却液流量
                    'M007': (25, 40),
                    'M008': (50, 80),     # 喷漆流量大
                    'M009': (100, 150),   # 冷却系统流量最大
                    'M010': (15, 30)
                }
            }
        }
        
        # 生成扩展传感器类型
        self.sensor_types = self.base_sensor_types.copy()
        self._generate_additional_sensors()
        
        # 现在可以安全地生成额外的机器（传感器类型已初始化）
        self._generate_additional_machines()
        
        # 扩展异常模式定义（基于复杂度倍数）
        self.anomaly_patterns = {
            'sudden_spike': {
                'description': '突发性峰值异常',
                'duration': (1, 3),  # 1-3个时间点
                'severity': (1.5, 3.0)  # 超出正常范围的倍数
            },
            'gradual_drift': {
                'description': '渐变漂移异常',
                'duration': (10, 30),  # 10-30个时间点
                'severity': (1.2, 2.0)
            },
            'oscillation': {
                'description': '振荡异常',
                'duration': (5, 15),
                'severity': (1.3, 2.5)
            },
            'sensor_failure': {
                'description': '传感器故障',
                'duration': (3, 8),
                'severity': (0.1, 0.3)  # 读数异常低或为0
            }
        }
        
        # 如果启用了高难度模式，添加更复杂的异常模式
        if config.enable_multi_anomaly:
            self._add_complex_anomaly_patterns()

    def _generate_additional_machines(self):
        """生成额外的机器"""
        machine_types = [
            'Conveyor Belt', 'Sorting Unit', 'Cutting Machine', 'Drilling Unit',
            'Polishing Station', 'Heating Furnace', 'Cooling Tower', 'Pump Station',
            'Generator Unit', 'Motor Drive', 'Hydraulic System', 'Pneumatic System',
            'Laser Cutter', 'CNC Machine', 'Testing Equipment', 'Packaging Robot'
        ]
        
        for i in range(self.config.additional_machines):
            machine_id = f"M{len(self.machines) + 1:03d}"
            machine_type = random.choice(machine_types)
            section = chr(65 + (i // 5))  # A, B, C, ...
            
            self.machines[machine_id] = f"{machine_type} {section} - Extended Unit {i+1}"
            
            # 为新机器生成传感器范围
            self._generate_sensor_ranges_for_machine(machine_id)

    def _generate_sensor_ranges_for_machine(self, machine_id: str):
        """为新机器生成传感器范围"""
        for sensor_type, config in self.sensor_types.items():
            if machine_id not in config['normal_ranges']:
                # 基于机器类型和随机变化生成合理的范围
                base_ranges = list(config['normal_ranges'].values())
                if base_ranges:
                    # 选择一个相似的基础范围作为模板
                    template_range = random.choice(base_ranges)
                    min_val, max_val = template_range
                    
                    # 添加变化 (±20%)
                    variation = 0.2 * random.uniform(-1, 1)
                    new_min = min_val * (1 + variation)
                    new_max = max_val * (1 + variation)
                    
                    # 确保最小值小于最大值
                    if new_min > new_max:
                        new_min, new_max = new_max, new_min
                    
                    config['normal_ranges'][machine_id] = (
                        round(new_min, 2), round(new_max, 2)
                    )

    def _generate_additional_sensors(self):
        """生成额外的传感器类型"""
        additional_sensor_configs = {
            'humidity': {
                'unit': '%RH',
                'base_range': (30, 70)
            },
            'power': {
                'unit': 'kW',
                'base_range': (1, 50)
            },
            'efficiency': {
                'unit': '%',
                'base_range': (75, 95)
            },
            'noise_level': {
                'unit': 'dB',
                'base_range': (40, 80)
            },
            'oil_pressure': {
                'unit': 'psi',
                'base_range': (20, 60)
            },
            'speed': {
                'unit': 'm/s',
                'base_range': (0.5, 5.0)
            }
        }
        
        for sensor_name in self.config.additional_sensors:
            if sensor_name in additional_sensor_configs and sensor_name not in self.sensor_types:
                sensor_config = additional_sensor_configs[sensor_name]
                base_min, base_max = sensor_config['base_range']
                
                # 为每台机器生成此传感器的范围
                normal_ranges = {}
                for machine_id in self.machines.keys():
                    # 基于机器类型调整范围
                    machine_multiplier = self._get_machine_type_multiplier(machine_id, sensor_name)
                    
                    min_val = base_min * machine_multiplier * random.uniform(0.8, 1.2)
                    max_val = base_max * machine_multiplier * random.uniform(0.8, 1.2)
                    
                    if min_val > max_val:
                        min_val, max_val = max_val, min_val
                    
                    normal_ranges[machine_id] = (round(min_val, 2), round(max_val, 2))
                
                self.sensor_types[sensor_name] = {
                    'unit': sensor_config['unit'],
                    'normal_ranges': normal_ranges
                }

    def _get_machine_type_multiplier(self, machine_id: str, sensor_type: str) -> float:
        """根据机器类型获取传感器的倍数"""
        machine_desc = self.machines[machine_id].lower()
        
        multipliers = {
            'humidity': {
                'cooling': 1.5, 'paint': 0.7, 'welding': 0.5, 'quality': 1.2
            },
            'power': {
                'welding': 3.0, 'compressor': 2.5, 'assembly': 0.5, 'quality': 0.3
            },
            'efficiency': {
                'quality': 1.1, 'assembly': 1.0, 'welding': 0.8, 'paint': 0.9
            },
            'noise_level': {
                'compressor': 1.8, 'welding': 1.5, 'quality': 0.6, 'assembly': 1.0
            },
            'oil_pressure': {
                'welding': 1.5, 'compressor': 2.0, 'assembly': 0.8, 'paint': 1.2
            },
            'speed': {
                'assembly': 1.5, 'packaging': 2.0, 'quality': 0.5, 'cooling': 1.0
            }
        }
        
        if sensor_type in multipliers:
            for keyword, multiplier in multipliers[sensor_type].items():
                if keyword in machine_desc:
                    return multiplier
        
        return 1.0  # 默认倍数

    def _add_complex_anomaly_patterns(self):
        """添加复杂的异常模式"""
        complex_patterns = {
            'intermittent_failure': {
                'description': '间歇性故障',
                'duration': (2, 8),
                'severity': (0.1, 0.5),
                'gap_duration': (3, 10)  # 故障间隔
            },
            'thermal_runaway': {
                'description': '热失控',
                'duration': (15, 50),
                'severity': (2.0, 4.0)
            },
            'harmonic_resonance': {
                'description': '谐波共振',
                'duration': (8, 20),
                'severity': (1.8, 3.5)
            },
            'cascade_failure': {
                'description': '级联故障',
                'duration': (20, 60),
                'severity': (1.5, 2.5),
                'spread_probability': 0.3
            }
        }
        
        self.anomaly_patterns.update(complex_patterns)

    def generate_normal_reading(self, machine_id: str, sensor_type: str) -> float:
        """生成正常范围内的传感器读数"""
        min_val, max_val = self.sensor_types[sensor_type]['normal_ranges'][machine_id]
        
        # 使用正态分布，让大部分读数在正常范围中央
        center = (min_val + max_val) / 2
        std = (max_val - min_val) / 6  # 3-sigma规则
        
        reading = np.random.normal(center, std)
        # 确保在正常范围内
        reading = np.clip(reading, min_val, max_val)
        
        return round(reading, 2)

    def generate_anomaly_reading(self, machine_id: str, sensor_type: str, 
                               pattern: str, intensity: float) -> float:
        """生成异常读数"""
        min_val, max_val = self.sensor_types[sensor_type]['normal_ranges'][machine_id]
        
        if pattern == 'sensor_failure':
            # 传感器故障：读数异常低或接近0
            return round(random.uniform(0, min_val * intensity), 2)
        else:
            # 其他异常：超出正常范围
            if random.choice([True, False]):
                # 超出上限
                return round(max_val * intensity, 2)
            else:
                # 低于下限
                return round(min_val / intensity, 2)

    def inject_anomalies(self, data: List[Dict]):
        """在数据中注入异常"""
        anomaly_probability = self.config.anomaly_probability * self.config.complexity_multiplier
        anomaly_sessions = {}  # 跟踪正在进行的异常会话
        
        for i, record in enumerate(data):
            machine_id = record['machine_id']
            sensor_type = record['sensor_type']
            session_key = f"{machine_id}_{sensor_type}"
            
            # 检查是否有正在进行的异常会话
            if session_key in anomaly_sessions:
                session = anomaly_sessions[session_key]
                
                if session['remaining_duration'] > 0:
                    # 继续异常模式
                    pattern = session['pattern']
                    progress = 1 - (session['remaining_duration'] / session['total_duration'])
                    
                    if pattern == 'gradual_drift':
                        # 渐变异常：逐渐增加强度
                        intensity = 1 + (session['intensity'] - 1) * progress
                    elif pattern == 'oscillation':
                        # 振荡异常
                        intensity = 1 + (session['intensity'] - 1) * \
                                  abs(np.sin(2 * np.pi * progress * 3))
                    else:
                        intensity = session['intensity']
                    
                    record['reading'] = self.generate_anomaly_reading(
                        machine_id, sensor_type, pattern, intensity
                    )
                    record['is_anomaly'] = True
                    
                    session['remaining_duration'] -= 1
                    
                    if session['remaining_duration'] <= 0:
                        del anomaly_sessions[session_key]
                
            elif random.random() < anomaly_probability:
                # 开始新的异常会话
                pattern = random.choice(list(self.anomaly_patterns.keys()))
                pattern_config = self.anomaly_patterns[pattern]
                
                duration = random.randint(*pattern_config['duration'])
                intensity = random.uniform(*pattern_config['severity'])
                
                anomaly_sessions[session_key] = {
                    'pattern': pattern,
                    'intensity': intensity,
                    'total_duration': duration,
                    'remaining_duration': duration - 1
                }
                
                record['reading'] = self.generate_anomaly_reading(
                    machine_id, sensor_type, pattern, intensity
                )
                record['is_anomaly'] = True

    def generate_sensor_data(self) -> pd.DataFrame:
        """生成传感器数据"""
        hours = self.config.time_duration_hours
        interval_minutes = self.config.sampling_interval_minutes
        
        print(f"生成 {hours} 小时的传感器数据，采样间隔 {interval_minutes} 分钟...")
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # 按配置的间隔生成数据点
        time_points = []
        current_time = start_time
        while current_time <= end_time:
            time_points.append(current_time)
            current_time += timedelta(minutes=interval_minutes)
        
        data = []
        
        # 为每个时间点、每台机器、每种传感器生成数据
        for timestamp in time_points:
            for machine_id in self.machines.keys():
                for sensor_type in self.sensor_types.keys():
                    reading = self.generate_normal_reading(machine_id, sensor_type)
                    
                    data.append({
                        'timestamp': timestamp,
                        'machine_id': machine_id,
                        'sensor_type': sensor_type,
                        'reading': reading,
                        'is_anomaly': False
                    })
        
        # 注入异常
        print("注入异常数据...")
        self.inject_anomalies(data)
        
        # 转换为DataFrame
        df = pd.DataFrame(data)
        
        # 如果启用噪声注入，添加随机噪声
        if self.config.enable_noise_injection:
            print("注入随机噪声...")
            self._inject_noise(df)
        
        df = df.sort_values(['timestamp', 'machine_id', 'sensor_type'])
        
        # 移除is_anomaly列（这是内部标记）
        final_df = df[['timestamp', 'machine_id', 'sensor_type', 'reading']].copy()
        
        print(f"生成了 {len(final_df)} 条传感器记录")
        print(f"包含 {df['is_anomaly'].sum()} 条异常记录 ({df['is_anomaly'].mean()*100:.1f}%)")
        
        return final_df

    def _inject_noise(self, df: pd.DataFrame):
        """注入随机噪声"""
        for idx, row in df.iterrows():
            if not row.get('is_anomaly', False):  # 只对正常数据添加噪声
                machine_id = row['machine_id']
                sensor_type = row['sensor_type']
                
                # 获取正常范围
                min_val, max_val = self.sensor_types[sensor_type]['normal_ranges'][machine_id]
                range_size = max_val - min_val
                
                # 添加小幅噪声 (±1% of range)
                noise = np.random.normal(0, range_size * 0.01)
                df.at[idx, 'reading'] = round(row['reading'] + noise, 2)

    def generate_parameters_config(self) -> pd.DataFrame:
        """生成机器操作参数配置"""
        print("生成机器操作参数配置...")
        
        config_data = []
        
        for machine_id, description in self.machines.items():
            for sensor_type, config in self.sensor_types.items():
                min_val, max_val = config['normal_ranges'][machine_id]
                unit = config['unit']
                
                config_data.append({
                    'machine_id': machine_id,
                    'machine_description': description,
                    'sensor_type': sensor_type,
                    'unit': unit,
                    'min_value': min_val,
                    'max_value': max_val,
                    'calibration_date': '2024-01-15',
                    'next_maintenance': '2024-07-15'
                })
        
        df = pd.DataFrame(config_data)
        print(f"生成了 {len(df)} 个参数配置项")
        
        return df

    def save_data(self, sensor_data: pd.DataFrame, config_data: pd.DataFrame):
        """保存数据到文件"""
        print("保存数据文件...")
        
        # 添加文件前缀
        prefix = self.config.output_prefix
        if prefix and not prefix.endswith('_'):
            prefix += '_'
        
        # 保存传感器数据为CSV
        sensor_file = f'{prefix}live_sensor_data.csv'
        sensor_data.to_csv(sensor_file, index=False)
        print(f"传感器数据已保存到: {sensor_file}")
        
        # 保存配置数据为Excel
        config_file = f'{prefix}machine_operating_parameters.xlsx'
        with pd.ExcelWriter(config_file, engine='openpyxl') as writer:
            config_data.to_excel(writer, sheet_name='Operating Parameters', index=False)
            
            # 添加一个汇总表
            summary_data = []
            for machine_id, description in self.machines.items():
                sensor_count = len(self.sensor_types)
                summary_data.append({
                    'machine_id': machine_id,
                    'description': description,
                    'sensor_count': sensor_count,
                    'status': 'Active'
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Machine Summary', index=False)
        
        print(f"参数配置已保存到: {config_file}")

    def generate_data_stats(self, sensor_data: pd.DataFrame) -> Dict:
        """生成数据统计信息"""
        stats = {
            'total_records': len(sensor_data),
            'time_range': {
                'start': sensor_data['timestamp'].min().isoformat(),
                'end': sensor_data['timestamp'].max().isoformat()
            },
            'machines': list(sensor_data['machine_id'].unique()),
            'sensor_types': list(sensor_data['sensor_type'].unique()),
            'records_per_machine': sensor_data['machine_id'].value_counts().to_dict(),
            'records_per_sensor': sensor_data['sensor_type'].value_counts().to_dict()
        }
        
        # 保存统计信息
        stats_file = f'{self.config.output_prefix}_data_generation_stats.json' if self.config.output_prefix else 'data_generation_stats.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        return stats

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='工厂物联网传感器数据生成器 - 高可配置版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础用法
  python main.py
  
  # 生成大规模数据集
  python main.py --hours 24 --interval 1 --machines 50 --complexity 2.0
  
  # 高难度模式
  python main.py --hours 12 --machines 20 --sensors humidity,power,efficiency \\
                 --multi-anomaly --cascade-failure --noise
  
  # 自定义输出
  python main.py --hours 6 --prefix "large_dataset" --anomaly-rate 0.25
        """
    )
    
    # 基础配置
    parser.add_argument('--hours', type=float, default=2,
                        help='数据时间跨度（小时），默认: 2')
    parser.add_argument('--interval', type=float, default=5,
                        help='采样间隔（分钟），默认: 5')
    parser.add_argument('--anomaly-rate', type=float, default=0.15,
                        help='异常概率，默认: 0.15')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子，默认: 42')
    
    # 扩展配置
    parser.add_argument('--machines', type=int, default=0,
                        help='额外添加的机器数量，默认: 0')
    parser.add_argument('--sensors', type=str, default='',
                        help='额外的传感器类型，用逗号分隔 (humidity,power,efficiency,noise_level,oil_pressure,speed)')
    parser.add_argument('--complexity', type=float, default=1.0,
                        help='复杂度倍数，默认: 1.0')
    parser.add_argument('--prefix', type=str, default='',
                        help='输出文件前缀，默认: 无')
    
    # 高难度模式
    parser.add_argument('--multi-anomaly', action='store_true',
                        help='启用多重异常模式')
    parser.add_argument('--cascade-failure', action='store_true',
                        help='启用级联故障模式')
    parser.add_argument('--seasonal-patterns', action='store_true',
                        help='启用季节性模式')
    parser.add_argument('--noise', action='store_true',
                        help='启用噪声注入')
    
    # 预设模式
    parser.add_argument('--preset', choices=['small', 'medium', 'large', 'extreme'],
                        help='预设配置模式')
    
    return parser.parse_args()

def apply_preset_config(config: DataGenerationConfig, preset: str):
    """应用预设配置"""
    presets = {
        'small': {
            'time_duration_hours': 1,
            'sampling_interval_minutes': 10,
            'additional_machines': 0,
            'additional_sensors': [],
            'complexity_multiplier': 0.8
        },
        'medium': {
            'time_duration_hours': 6,
            'sampling_interval_minutes': 5,
            'additional_machines': 10,
            'additional_sensors': ['humidity', 'power'],
            'complexity_multiplier': 1.5
        },
        'large': {
            'time_duration_hours': 24,
            'sampling_interval_minutes': 2,
            'additional_machines': 25,
            'additional_sensors': ['humidity', 'power', 'efficiency', 'noise_level'],
            'complexity_multiplier': 2.0,
            'enable_multi_anomaly': True,
            'enable_noise_injection': True
        },
        'extreme': {
            'time_duration_hours': 72,
            'sampling_interval_minutes': 1,
            'additional_machines': 50,
            'additional_sensors': ['humidity', 'power', 'efficiency', 'noise_level', 'oil_pressure', 'speed'],
            'complexity_multiplier': 3.0,
            'enable_multi_anomaly': True,
            'enable_cascade_failure': True,
            'enable_seasonal_patterns': True,
            'enable_noise_injection': True,
            'anomaly_probability': 0.25
        }
    }
    
    if preset in presets:
        preset_config = presets[preset]
        for key, value in preset_config.items():
            setattr(config, key, value)
        print(f"应用预设配置: {preset}")

def main():
    """主函数"""
    args = parse_arguments()
    
    # 创建配置
    config = DataGenerationConfig()
    
    # 应用预设配置
    if args.preset:
        apply_preset_config(config, args.preset)
    
    # 应用命令行参数
    config.random_seed = args.seed
    config.time_duration_hours = args.hours
    config.sampling_interval_minutes = args.interval
    config.anomaly_probability = args.anomaly_rate
    config.additional_machines = args.machines
    config.complexity_multiplier = args.complexity
    config.output_prefix = args.prefix
    
    # 解析额外传感器
    if args.sensors:
        config.additional_sensors = [s.strip() for s in args.sensors.split(',')]
    
    # 高难度模式配置
    config.enable_multi_anomaly = args.multi_anomaly
    config.enable_cascade_failure = args.cascade_failure
    config.enable_seasonal_patterns = args.seasonal_patterns
    config.enable_noise_injection = args.noise
    
    # 显示配置信息
    print("=" * 80)
    print("工厂物联网传感器数据生成器 - 高可配置版本")
    print("=" * 80)
    
    total_machines = 10 + config.additional_machines
    total_sensors = 6 + len(config.additional_sensors)
    estimated_records = int((config.time_duration_hours * 60 / config.sampling_interval_minutes) * total_machines * total_sensors)
    
    print(f"配置摘要:")
    print(f"  时间跨度: {config.time_duration_hours} 小时")
    print(f"  采样间隔: {config.sampling_interval_minutes} 分钟")
    print(f"  机器数量: {total_machines} ({10} 基础 + {config.additional_machines} 扩展)")
    print(f"  传感器类型: {total_sensors} ({6} 基础 + {len(config.additional_sensors)} 扩展)")
    print(f"  预估记录数: {estimated_records:,}")
    print(f"  异常概率: {config.anomaly_probability:.1%}")
    print(f"  复杂度倍数: {config.complexity_multiplier}")
    if config.additional_sensors:
        print(f"  额外传感器: {', '.join(config.additional_sensors)}")
    
    advanced_features = []
    if config.enable_multi_anomaly:
        advanced_features.append("多重异常")
    if config.enable_cascade_failure:
        advanced_features.append("级联故障")
    if config.enable_seasonal_patterns:
        advanced_features.append("季节性模式")
    if config.enable_noise_injection:
        advanced_features.append("噪声注入")
    
    if advanced_features:
        print(f"  高级功能: {', '.join(advanced_features)}")
    
    print("\n开始生成数据...")
    
    # 创建生成器
    generator = IndustrialSensorDataGenerator(config)
    
    # 生成数据
    sensor_data = generator.generate_sensor_data()
    config_data = generator.generate_parameters_config()
    
    # 保存数据
    generator.save_data(sensor_data, config_data)
    
    # 生成统计信息
    stats = generator.generate_data_stats(sensor_data)
    
    print("\n" + "=" * 80)
    print("数据生成完成！")
    print("=" * 80)
    print(f"传感器记录总数: {stats['total_records']:,}")
    print(f"时间范围: {stats['time_range']['start']} 到 {stats['time_range']['end']}")
    print(f"机器数量: {len(stats['machines'])}")
    print(f"传感器类型: {len(stats['sensor_types'])}")
    
    # 估算数据大小
    estimated_size_mb = stats['total_records'] * 0.1 / 1000  # 粗略估算
    print(f"估计数据大小: ~{estimated_size_mb:.1f} MB")
    
    prefix = config.output_prefix + '_' if config.output_prefix else ''
    print(f"\n生成的文件:")
    print(f"1. {prefix}live_sensor_data.csv - 传感器实时数据")
    print(f"2. {prefix}machine_operating_parameters.xlsx - 机器操作参数配置")
    print(f"3. {prefix}data_generation_stats.json - 数据生成统计")
    
    if estimated_records > 100000:
        print(f"\n💡 大规模数据集生成完成！")
        print(f"   建议使用异常检测脚本时指定时间范围以提高性能")

if __name__ == "__main__":
    main() 