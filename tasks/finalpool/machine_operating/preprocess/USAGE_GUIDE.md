# 🏭 工厂物联网传感器数据生成器 - 使用指南

## 📋 概述

扩展后的数据生成器现在支持灵活的配置和大规模数据生成，可以根据需要调整数据量、复杂度和特征。

## 🚀 快速开始

### 基础用法
```bash
# 使用默认设置生成数据
python main.py

# 查看所有选项
python main.py --help
```

### 预设模式
```bash
# 小规模数据集 (适合快速测试)
python main.py --preset small

# 中等规模数据集 (6小时，10台额外机器)
python main.py --preset medium

# 大规模数据集 (24小时，25台额外机器)
python main.py --preset large

# 极限数据集 (72小时，50台额外机器，所有高级功能)
python main.py --preset extreme
```

## ⚙️ 配置选项

### 基础配置

| 参数 | 描述 | 默认值 | 示例 |
|-----|------|--------|-----|
| `--hours` | 数据时间跨度（小时） | 2 | `--hours 24` |
| `--interval` | 采样间隔（分钟） | 5 | `--interval 1` |
| `--anomaly-rate` | 异常概率 | 0.15 | `--anomaly-rate 0.25` |
| `--seed` | 随机种子 | 42 | `--seed 123` |

### 扩展配置

| 参数 | 描述 | 默认值 | 示例 |
|-----|------|--------|-----|
| `--machines` | 额外添加的机器数量 | 0 | `--machines 20` |
| `--sensors` | 额外的传感器类型 | 无 | `--sensors humidity,power,efficiency` |
| `--complexity` | 复杂度倍数 | 1.0 | `--complexity 2.0` |
| `--prefix` | 输出文件前缀 | 无 | `--prefix large_dataset` |

### 高级功能

| 参数 | 描述 | 默认 | 效果 |
|-----|------|------|-----|
| `--multi-anomaly` | 多重异常模式 | 禁用 | 添加间歇性故障、热失控等复杂异常 |
| `--cascade-failure` | 级联故障模式 | 禁用 | 异常可能影响相关设备 |
| `--seasonal-patterns` | 季节性模式 | 禁用 | 添加时间相关的模式变化 |
| `--noise` | 噪声注入 | 禁用 | 在正常数据中添加微小随机噪声 |

## 📊 数据规模估算

### 记录数计算公式
```
总记录数 = (时间(小时) × 60 / 采样间隔(分钟)) × 机器数量 × 传感器类型数
```

### 规模示例

| 配置 | 时间 | 间隔 | 机器数 | 传感器数 | 估计记录数 | 文件大小 |
|-----|------|------|--------|----------|-----------|----------|
| 默认 | 2小时 | 5分钟 | 10台 | 6种 | 1,440 | ~100KB |
| Medium | 6小时 | 5分钟 | 20台 | 8种 | 11,520 | ~800KB |
| Large | 24小时 | 2分钟 | 35台 | 10种 | 252,000 | ~18MB |
| Extreme | 72小时 | 1分钟 | 60台 | 12种 | 3,110,400 | ~220MB |

## 🔧 实用示例

### 1. 快速测试数据集
```bash
python main.py --hours 0.5 --prefix quick_test
```

### 2. 高频采样数据集
```bash
python main.py --hours 4 --interval 1 --machines 5 --prefix high_freq
```

### 3. 多传感器复杂数据集
```bash
python main.py --hours 8 --machines 15 \
  --sensors humidity,power,efficiency,noise_level \
  --complexity 1.8 --prefix multi_sensor
```

### 4. 高难度异常检测训练集
```bash
python main.py --hours 12 --machines 20 \
  --sensors humidity,power,efficiency \
  --multi-anomaly --cascade-failure --noise \
  --anomaly-rate 0.3 --prefix training_hard
```

### 5. 大规模生产数据集
```bash
python main.py --hours 48 --interval 2 --machines 30 \
  --sensors humidity,power,efficiency,noise_level,oil_pressure \
  --complexity 2.0 --prefix production_scale
```

## 📈 可用传感器类型

### 基础传感器（默认包含）
- `temperature` - 温度（°C）
- `pressure` - 压力（bar）
- `vibration` - 振动（mm/s）
- `rpm` - 转速（rpm）
- `current` - 电流（A）
- `flow_rate` - 流量（L/min）

### 扩展传感器（可选添加）
- `humidity` - 湿度（%RH）
- `power` - 功率（kW）
- `efficiency` - 效率（%）
- `noise_level` - 噪音水平（dB）
- `oil_pressure` - 油压（psi）
- `speed` - 速度（m/s）

## 🎯 不同应用场景的配置建议

### 算法开发和测试
```bash
# 小规模，快速迭代
python main.py --preset small --prefix dev_test

# 中等规模，功能验证
python main.py --hours 4 --machines 5 --sensors humidity,power --prefix feature_test
```

### 异常检测训练
```bash
# 高异常率，复杂模式
python main.py --hours 12 --machines 15 \
  --multi-anomaly --cascade-failure \
  --anomaly-rate 0.35 --complexity 2.0 --prefix anomaly_training

# 真实场景模拟
python main.py --hours 24 --interval 3 --machines 25 \
  --sensors humidity,power,efficiency --noise \
  --prefix realistic_scenario
```

### 性能测试
```bash
# 大数据量测试
python main.py --hours 48 --interval 1 --machines 40 \
  --sensors humidity,power,efficiency,noise_level,oil_pressure,speed \
  --prefix performance_test

# 极限数据量
python main.py --preset extreme --prefix stress_test
```

### 可视化和仪表板开发
```bash
# 实时模拟数据
python main.py --hours 6 --interval 2 --machines 10 \
  --sensors humidity,power --noise --prefix dashboard_demo

# 多样化展示数据
python main.py --hours 12 --machines 8 \
  --sensors humidity,power,efficiency,noise_level \
  --multi-anomaly --prefix visualization_rich
```

## 🚨 注意事项

### 性能考虑
- **大数据集生成**：时间可能较长，建议先用小规模测试
- **内存使用**：极大数据集可能消耗大量内存
- **存储空间**：确保有足够的磁盘空间

### 最佳实践
1. **逐步扩展**：从小规模开始，逐步增加复杂度
2. **使用前缀**：为不同用途的数据集使用不同前缀
3. **验证数据**：生成后使用 `verify_data.py` 验证数据质量
4. **监控资源**：生成大数据集时监控系统资源使用

### 错误处理
- 如果遇到内存不足，减少时间跨度或采样频率
- 如果生成时间过长，考虑使用预设模式
- 如果异常率不符合预期，调整复杂度倍数

## 📝 输出文件说明

每次运行会生成三个文件：

1. **`[prefix_]live_sensor_data.csv`**
   - 主要的传感器数据文件
   - 包含时间戳、机器ID、传感器类型、读数值

2. **`[prefix_]machine_operating_parameters.xlsx`**
   - 机器操作参数配置文件
   - 包含正常操作范围、单位、维护信息
   - 两个工作表：Operating Parameters 和 Machine Summary

3. **`[prefix_]data_generation_stats.json`**
   - 数据生成统计信息
   - 包含记录总数、时间范围、机器和传感器统计

## 🔗 相关工具

- `verify_data.py` - 验证生成数据的质量和完整性
- `anomaly_detection.py` - 对生成的数据进行异常检测
- `demo_large_scale.py` - 演示不同规模的数据生成

## 💡 提示

- 使用 `--help` 查看最新的参数说明
- 大数据集建议在后台运行：`nohup python main.py --preset large &`
- 可以结合 shell 脚本批量生成不同配置的数据集
- 生成的数据具有确定性（相同种子产生相同结果） 