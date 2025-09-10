# 工厂物联网传感器数据集

本数据集模拟了一个工厂生产线的物联网传感器数据，用于测试异常检测和监控系统。

## 数据集概述

### 生成的文件

1. **`live_sensor_data.csv`** - 传感器实时数据
2. **`machine_operating_parameters.xlsx`** - 机器操作参数配置
3. **`data_generation_stats.json`** - 数据生成统计信息

## 数据特性

### 机器配置
- **10台工业设备**，涵盖完整的生产线：
  - M001: Assembly Line A - Component Insertion（装配线A - 元件插入）
  - M002: Assembly Line B - Circuit Board Assembly（装配线B - 电路板装配）
  - M003: Packaging Unit 1 - Primary Packaging（包装单元1 - 初级包装）
  - M004: Packaging Unit 2 - Secondary Packaging（包装单元2 - 二级包装）
  - M005: Quality Control Station - Inspection（质控站 - 检验）
  - M006: Welding Robot 1 - Chassis Welding（焊接机器人1 - 底盘焊接）
  - M007: Welding Robot 2 - Frame Welding（焊接机器人2 - 框架焊接）
  - M008: Paint Booth - Spray Coating（喷漆房 - 喷涂）
  - M009: Cooling System - Temperature Control（冷却系统 - 温度控制）
  - M010: Compressor Unit - Air Supply（压缩机组 - 供气）

### 传感器类型
每台机器配备6种传感器：

1. **温度传感器** (°C)
   - 精密装配：18-25°C
   - 焊接作业：25-45°C
   - 冷却系统：5-15°C

2. **压力传感器** (bar)
   - 常规作业：0.7-1.3 bar
   - 焊接作业：1.5-2.5 bar
   - 喷漆作业：2.0-3.0 bar
   - 压缩机：6.0-8.0 bar

3. **振动传感器** (mm/s)
   - 质检站：0.05-0.3 mm/s
   - 装配线：0.1-0.8 mm/s
   - 压缩机：1.0-3.0 mm/s

4. **转速传感器** (rpm)
   - 焊接机器人：0-100 rpm
   - 装配线：800-1800 rpm
   - 喷漆设备：2000-3000 rpm
   - 压缩机：3000-4500 rpm

5. **电流传感器** (A)
   - 质检站：1.0-2.5 A
   - 装配线：1.5-6.0 A
   - 焊接设备：15-25 A
   - 压缩机：20-30 A

6. **流量传感器** (L/min)
   - 质检站：2-8 L/min
   - 装配线：5-20 L/min
   - 焊接冷却：25-40 L/min
   - 喷漆系统：50-80 L/min
   - 冷却系统：100-150 L/min

## 异常模式

数据集包含4种类型的异常模式，总异常率约50%：

### 1. 突发性峰值异常 (Sudden Spike)
- **特征**: 数值突然超出正常范围
- **持续时间**: 1-3个时间点
- **强度**: 正常范围的1.5-3.0倍

### 2. 渐变漂移异常 (Gradual Drift)
- **特征**: 数值逐渐偏离正常范围
- **持续时间**: 10-30个时间点
- **强度**: 逐渐增加到正常范围的1.2-2.0倍

### 3. 振荡异常 (Oscillation)
- **特征**: 数值呈现周期性振荡
- **持续时间**: 5-15个时间点
- **强度**: 正弦波形式，峰值达正常范围的1.3-2.5倍

### 4. 传感器故障 (Sensor Failure)
- **特征**: 读数异常低或接近零
- **持续时间**: 3-8个时间点
- **强度**: 正常最小值的0.1-0.3倍

## 数据质量指标

基于验证脚本的分析结果：

- **总记录数**: 1,500条
- **时间跨度**: 2小时（每5分钟一个数据点）
- **异常数据比例**: ~50%
- **数据完整性**: 100%（所有机器的所有传感器都有数据）

### 各机器异常分布
不同机器的异常率在35%-66%之间，符合真实工厂环境中不同设备故障率的差异。

### 各传感器类型异常分布
- 电流传感器异常率最高（66%）
- 振动传感器异常率相对较低（40%）

## 使用场景

这个数据集适用于以下任务：

1. **异常检测算法测试**
   - 实时异常识别
   - 异常模式分类
   - 阈值调优

2. **监控系统开发**
   - 仪表板可视化
   - 报警系统测试
   - 趋势分析

3. **机器学习模型训练**
   - 有监督异常检测
   - 时序数据分析
   - 多变量异常检测

4. **数据处理管道测试**
   - BigQuery数据导入
   - Excel配置文件解析
   - 云存储上传

## 任务示例

原始任务场景：
> 工厂的一条生产线通过物联网传感器，将实时数据流式传输到BigQuery的 live_sensor_data 表中。每台机器上各个传感器的正常工作参数范围（最小值/最大值）被定义在一个名为 machine_operating_parameters.xlsx 的配置文件中。请您查询过去一小时最新的传感器数据，并结合Excel中的参数范围，识别出所有超出其正常范围的异常读数。请将最终的异常报告（包含时间戳、机器ID、传感器类型、读数值、正常范围）整理成 anomaly_report.csv 文件，并上传至名为 iot_anomaly_reports 的云存储桶中。

## 文件结构

```
preprocess/
├── main.py                           # 数据生成主脚本
├── verify_data.py                    # 数据验证脚本
├── README.md                         # 本文档
├── live_sensor_data.csv              # 传感器数据（时序数据）
├── machine_operating_parameters.xlsx # 参数配置（包含两个工作表）
└── data_generation_stats.json       # 数据统计信息
```

## 使用方法

### 重新生成数据
```bash
python main.py
```

### 验证数据质量
```bash
python verify_data.py
```

### 调整参数
在 `main.py` 中可以调整：
- 时间范围（默认2小时）
- 异常概率（默认15%）
- 采样间隔（默认5分钟）
- 机器配置和传感器范围

## 数据格式

### live_sensor_data.csv
```csv
timestamp,machine_id,sensor_type,reading
2025-08-19 11:18:59.878906,M001,temperature,22.08
2025-08-19 11:18:59.878906,M001,pressure,1.88
...
```

### machine_operating_parameters.xlsx
**Operating Parameters 工作表：**
```
machine_id | machine_description | sensor_type | unit | min_value | max_value | calibration_date | next_maintenance
M001       | Assembly Line A...  | temperature | °C   | 18.0      | 25.0      | 2024-01-15      | 2024-07-15
...
```

**Machine Summary 工作表：**
```
machine_id | description        | sensor_count | status
M001       | Assembly Line A... | 6           | Active
...
```

## 技术说明

- **随机种子**: 固定为42，确保数据可重现
- **正态分布**: 正常数据遵循正态分布，中心在参数范围中央
- **异常注入**: 基于会话的异常注入，确保异常的连续性和真实性
- **数据类型**: 所有数值保留2位小数，时间戳精确到微秒 