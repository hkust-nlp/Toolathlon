# 🏭 Factory IoT Sensor Data Generator - User Guide

## 📋 Overview

The extended data generator now supports flexible configuration and large-scale data production. You can freely adjust the generated data volume, complexity, and features as needed.

## 🚀 Quick Start

### Basic Usage
```bash
# Generate data with default settings
python main.py

# View all available options
python main.py --help
```

### Preset Modes
```bash
# Small-scale dataset (for quick testing)
python main.py --preset small

# Medium-scale dataset (6 hours, 10 extra machines)
python main.py --preset medium

# Large-scale dataset (24 hours, 25 extra machines)
python main.py --preset large

# Extreme dataset (72 hours, 50 extra machines, all advanced features)
python main.py --preset extreme
```

## ⚙️ Configuration Options

### Basic Settings

| Parameter      | Description                 | Default | Example                          |
|----------------|----------------------------|---------|-----------------------------------|
| `--hours`      | Duration (hours)           | 2       | `--hours 24`                      |
| `--interval`   | Sampling interval (minutes)| 5       | `--interval 1`                    |
| `--anomaly-rate` | Anomaly probability      | 0.15    | `--anomaly-rate 0.25`             |
| `--seed`       | Random seed                | 42      | `--seed 123`                      |

### Extended Settings

| Parameter      | Description                                | Default | Example                                |
|----------------|--------------------------------------------|---------|-----------------------------------------|
| `--machines`   | Number of additional machines              | 0       | `--machines 20`                        |
| `--sensors`    | Additional sensor types (comma-separated)  | None    | `--sensors humidity,power,efficiency`   |
| `--complexity` | Complexity multiplier                      | 1.0     | `--complexity 2.0`                      |
| `--prefix`     | Prefix for output files                    | None    | `--prefix large_dataset`                |

### Advanced Features

| Parameter            | Description                   | Default   | Effect                                                        |
|----------------------|------------------------------|-----------|---------------------------------------------------------------|
| `--multi-anomaly`    | Multiple anomaly mode         | Off       | Add intermittent faults, thermal runaway, and other patterns  |
| `--cascade-failure`  | Cascade failure mode          | Off       | Anomaly may affect related equipment                          |
| `--seasonal-patterns`| Seasonal patterns             | Off       | Introduce time-dependent patterns                             |
| `--noise`            | Noise injection               | Off       | Add minor random noise to normal data                         |

## 📊 Data Volume Estimation

### Record Count Formula
```
Total Records = (Duration(hours) × 60 / Sampling Interval(min)) × Number of Machines × Number of Sensor Types
```

### Scale Examples

| Mode    | Hours | Interval | Machines | Sensors | Est. Records | File Size |
|---------|-------|----------|----------|---------|--------------|-----------|
| Default | 2     | 5 min    | 10       | 6       | 1,440        | ~100KB    |
| Medium  | 6     | 5 min    | 20       | 8       | 11,520       | ~800KB    |
| Large   | 24    | 2 min    | 35       | 10      | 252,000      | ~18MB     |
| Extreme | 72    | 1 min    | 60       | 12      | 3,110,400    | ~220MB    |

## 🔧 Usage Examples

### 1. Quick Test Dataset
```bash
python main.py --hours 0.5 --prefix quick_test
```

### 2. High-Frequency Sampling Dataset
```bash
python main.py --hours 4 --interval 1 --machines 5 --prefix high_freq
```

### 3. Multi-Sensor Complex Dataset
```bash
python main.py --hours 8 --machines 15 \
  --sensors humidity,power,efficiency,noise_level \
  --complexity 1.8 --prefix multi_sensor
```

### 4. Hard Anomaly Detection Training Set
```bash
python main.py --hours 12 --machines 20 \
  --sensors humidity,power,efficiency \
  --multi-anomaly --cascade-failure --noise \
  --anomaly-rate 0.3 --prefix training_hard
```

### 5. Large-Scale Production Dataset
```bash
python main.py --hours 48 --interval 2 --machines 30 \
  --sensors humidity,power,efficiency,noise_level,oil_pressure \
  --complexity 2.0 --prefix production_scale
```

## 📈 Available Sensor Types

### Basic Sensors (included by default)
- `temperature` - Temperature (°C)
- `pressure` - Pressure (bar)
- `vibration` - Vibration (mm/s)
- `rpm` - Rotational speed (rpm)
- `current` - Current (A)
- `flow_rate` - Flow rate (L/min)

### Additional Sensors (optional)
- `humidity` - Humidity (%RH)
- `power` - Power (kW)
- `efficiency` - Efficiency (%)
- `noise_level` - Noise level (dB)
- `oil_pressure` - Oil pressure (psi)
- `speed` - Speed (m/s)

## 🎯 Configuration Recommendations for Different Scenarios

### Algorithm Development and Testing
```bash
# Small scale, fast iteration
python main.py --preset small --prefix dev_test

# Medium scale, feature verification
python main.py --hours 4 --machines 5 --sensors humidity,power --prefix feature_test
```

### Anomaly Detection Training
```bash
# High anomaly rate, complex patterns
python main.py --hours 12 --machines 15 \
  --multi-anomaly --cascade-failure \
  --anomaly-rate 0.35 --complexity 2.0 --prefix anomaly_training

# Real-world simulation
python main.py --hours 24 --interval 3 --machines 25 \
  --sensors humidity,power,efficiency --noise \
  --prefix realistic_scenario
```

### Performance Testing
```bash
# Large dataset performance test
python main.py --hours 48 --interval 1 --machines 40 \
  --sensors humidity,power,efficiency,noise_level,oil_pressure,speed \
  --prefix performance_test

# Maximum size stress test
python main.py --preset extreme --prefix stress_test
```

### Visualization & Dashboard Development
```bash
# Real-time simulation data
python main.py --hours 6 --interval 2 --machines 10 \
  --sensors humidity,power --noise --prefix dashboard_demo

# Diverse showcase data
python main.py --hours 12 --machines 8 \
  --sensors humidity,power,efficiency,noise_level \
  --multi-anomaly --prefix visualization_rich
```

## 🚨 Tips & Precautions

### Performance Considerations
- **Large dataset generation**: Can take a long time; test with small data first
- **Memory usage**: Huge datasets may consume substantial RAM
- **Storage requirements**: Ensure enough disk space is available

### Best Practices
1. **Scale up gradually**: Start small, increase complexity progressively
2. **Use prefixes**: Distinguish datasets for different use cases with unique prefixes
3. **Verify output**: Run `verify_data.py` after generation to check data quality
4. **Monitor resources**: Watch system utilization during large-scale generation

### Error Handling
- If you encounter out-of-memory errors, reduce duration or increase sampling interval
- If generation is too slow, try preset modes
- If the anomaly rate is not as expected, adjust the complexity multiplier

## 📝 Output Files Description

Each run produces three files:

1. **`[prefix_]live_sensor_data.csv`**
   - Main sensor data file
   - Includes timestamp, machine ID, sensor type, reading value

2. **`[prefix_]machine_operating_parameters.xlsx`**
   - Machine operating parameter configuration
   - Contains normal operation range, unit, maintenance info
   - Two sheets: Operating Parameters and Machine Summary

3. **`[prefix_]data_generation_stats.json`**
   - Data generation statistics
   - Includes total records, time range, machine and sensor statistics

## 🔗 Related Tools

- `verify_data.py` - Verify the quality and integrity of generated data
- `anomaly_detection.py` - Detect anomalies in generated sensor data
- `demo_large_scale.py` - Demo of data generation at various scales

## 💡 Additional Tips

- Use `--help` to view the latest parameter instructions
- For large datasets, consider running in the background: `nohup python main.py --preset large &`
- Utilize shell scripts to batch generate datasets with different settings
- Data generation is deterministic (the same seed produces the same result) 