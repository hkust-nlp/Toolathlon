#!/usr/bin/env python3
"""
Industrial IoT Sensor Data Generator - Highly Configurable Version

Generates the following files:
1. live_sensor_data.csv - Live sensor data
2. machine_operating_parameters.xlsx - Machine operating parameters config

Includes multiple sensor types and anomaly patterns for anomaly detection system testing.
Supports large scale data generation and complexity adjustment.
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
    """Data generation configuration"""
    def __init__(self):
        # Basic config
        self.random_seed = 42
        self.time_duration_hours = 2
        self.sampling_interval_minutes = 5
        self.anomaly_probability = 0.15
        
        # Extended config
        self.additional_machines = 0  # Number of additional machines
        self.additional_sensors = []  # List of extra sensor types
        self.complexity_multiplier = 1.0  # Complexity multiplier
        self.output_prefix = ""  # Output file prefix
        
        # Advanced mode config
        self.enable_multi_anomaly = False  # Multi-anomaly mode
        self.enable_cascade_failure = False  # Cascade failure
        self.enable_seasonal_patterns = False  # Seasonal patterns
        self.enable_noise_injection = False  # Noise injection

# Set random seed for reproducibility
config = DataGenerationConfig()

class IndustrialSensorDataGenerator:
    def __init__(self, config: DataGenerationConfig):
        self.config = config
        
        # Set random seeds
        np.random.seed(config.random_seed)
        random.seed(config.random_seed)
        
        # Base machine config
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
        
        # Initialize base machines
        self.machines = self.base_machines.copy()
        
        print(f"Config info: {len(self.machines)} machines, {config.time_duration_hours} hours data, {config.sampling_interval_minutes} minute interval")
        
        # Base sensor types and normal ranges
        self.base_sensor_types = {
            'temperature': {
                'unit': '°C',
                'normal_ranges': {
                    'M001': (18, 25),    
                    'M002': (20, 28),    
                    'M003': (15, 30),    
                    'M004': (15, 30),    
                    'M005': (20, 24),    
                    'M006': (25, 45),    
                    'M007': (25, 45),
                    'M008': (22, 35),    
                    'M009': (5, 15),     
                    'M010': (20, 35)     
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
                    'M006': (1.5, 2.5),
                    'M007': (1.5, 2.5),
                    'M008': (2.0, 3.0),
                    'M009': (0.5, 1.0),
                    'M010': (6.0, 8.0)
                }
            },
            'vibration': {
                'unit': 'mm/s',
                'normal_ranges': {
                    'M001': (0.1, 0.8),
                    'M002': (0.1, 0.6),
                    'M003': (0.2, 1.0),
                    'M004': (0.2, 1.0),
                    'M005': (0.05, 0.3),
                    'M006': (0.5, 2.0),
                    'M007': (0.5, 2.0),
                    'M008': (0.3, 1.5),
                    'M009': (0.1, 0.5),
                    'M010': (1.0, 3.0)
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
                    'M006': (0, 100),
                    'M007': (0, 100),
                    'M008': (2000, 3000),
                    'M009': (1500, 2500),
                    'M010': (3000, 4500)
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
                    'M006': (15, 25),
                    'M007': (15, 25),
                    'M008': (8.0, 12.0),
                    'M009': (5.0, 10.0),
                    'M010': (20, 30)
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
                    'M006': (25, 40),
                    'M007': (25, 40),
                    'M008': (50, 80),
                    'M009': (100, 150),
                    'M010': (15, 30)
                }
            }
        }
        
        # Add extended sensors
        self.sensor_types = self.base_sensor_types.copy()
        self._generate_additional_sensors()
        
        # Generate additional machines (sensors must be ready)
        self._generate_additional_machines()
        
        # Anomaly pattern definitions (based on complexity)
        self.anomaly_patterns = {
            'sudden_spike': {
                'description': 'Sudden spike anomaly',
                'duration': (1, 3),
                'severity': (1.5, 3.0)
            },
            'gradual_drift': {
                'description': 'Gradual drift anomaly',
                'duration': (10, 30),
                'severity': (1.2, 2.0)
            },
            'oscillation': {
                'description': 'Oscillation anomaly',
                'duration': (5, 15),
                'severity': (1.3, 2.5)
            },
            'sensor_failure': {
                'description': 'Sensor failure',
                'duration': (3, 8),
                'severity': (0.1, 0.3)
            }
        }
        
        # Add advanced anomaly patterns if enabled
        if config.enable_multi_anomaly:
            self._add_complex_anomaly_patterns()

    def _generate_additional_machines(self):
        """Generate additional machines"""
        machine_types = [
            'Conveyor Belt', 'Sorting Unit', 'Cutting Machine', 'Drilling Unit',
            'Polishing Station', 'Heating Furnace', 'Cooling Tower', 'Pump Station',
            'Generator Unit', 'Motor Drive', 'Hydraulic System', 'Pneumatic System',
            'Laser Cutter', 'CNC Machine', 'Testing Equipment', 'Packaging Robot'
        ]
        
        for i in range(self.config.additional_machines):
            machine_id = f"M{len(self.machines) + 1:03d}"
            machine_type = random.choice(machine_types)
            section = chr(65 + (i // 5))
            
            self.machines[machine_id] = f"{machine_type} {section} - Extended Unit {i+1}"
            
            # Generate sensor ranges for new machine
            self._generate_sensor_ranges_for_machine(machine_id)

    def _generate_sensor_ranges_for_machine(self, machine_id: str):
        """Generate sensor ranges for a new machine"""
        for sensor_type, config in self.sensor_types.items():
            if machine_id not in config['normal_ranges']:
                base_ranges = list(config['normal_ranges'].values())
                if base_ranges:
                    template_range = random.choice(base_ranges)
                    min_val, max_val = template_range
                    
                    variation = 0.2 * random.uniform(-1, 1)
                    new_min = min_val * (1 + variation)
                    new_max = max_val * (1 + variation)
                    
                    if new_min > new_max:
                        new_min, new_max = new_max, new_min
                    
                    config['normal_ranges'][machine_id] = (
                        round(new_min, 2), round(new_max, 2)
                    )

    def _generate_additional_sensors(self):
        """Generate additional sensor types"""
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
                
                # Generate a range for each machine
                normal_ranges = {}
                for machine_id in self.machines.keys():
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
        """Get multiplier for a sensor type based on machine type"""
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
        
        return 1.0  # Default multiplier

    def _add_complex_anomaly_patterns(self):
        """Add complex anomaly patterns"""
        complex_patterns = {
            'intermittent_failure': {
                'description': 'Intermittent failure',
                'duration': (2, 8),
                'severity': (0.1, 0.5),
                'gap_duration': (3, 10)
            },
            'thermal_runaway': {
                'description': 'Thermal runaway',
                'duration': (15, 50),
                'severity': (2.0, 4.0)
            },
            'harmonic_resonance': {
                'description': 'Harmonic resonance',
                'duration': (8, 20),
                'severity': (1.8, 3.5)
            },
            'cascade_failure': {
                'description': 'Cascade failure',
                'duration': (20, 60),
                'severity': (1.5, 2.5),
                'spread_probability': 0.3
            }
        }
        
        self.anomaly_patterns.update(complex_patterns)

    def generate_normal_reading(self, machine_id: str, sensor_type: str) -> float:
        """Generate a sensor reading within normal range"""
        min_val, max_val = self.sensor_types[sensor_type]['normal_ranges'][machine_id]
        center = (min_val + max_val) / 2
        std = (max_val - min_val) / 6
        
        reading = np.random.normal(center, std)
        reading = np.clip(reading, min_val, max_val)
        
        return round(reading, 2)

    def generate_anomaly_reading(self, machine_id: str, sensor_type: str, 
                               pattern: str, intensity: float) -> float:
        """Generate an anomalous sensor reading"""
        min_val, max_val = self.sensor_types[sensor_type]['normal_ranges'][machine_id]
        
        if pattern == 'sensor_failure':
            # Sensor failure: abnormally low or near-zero
            return round(random.uniform(0, min_val * intensity), 2)
        else:
            # Other anomaly: outside normal range
            if random.choice([True, False]):
                # Exceed max
                return round(max_val * intensity, 2)
            else:
                # Below min
                return round(min_val / intensity, 2)

    def inject_anomalies(self, data: List[Dict]):
        """Inject anomalies into data"""
        anomaly_probability = self.config.anomaly_probability * self.config.complexity_multiplier
        anomaly_sessions = {}
        
        for i, record in enumerate(data):
            machine_id = record['machine_id']
            sensor_type = record['sensor_type']
            session_key = f"{machine_id}_{sensor_type}"
            
            if session_key in anomaly_sessions:
                session = anomaly_sessions[session_key]
                
                if session['remaining_duration'] > 0:
                    pattern = session['pattern']
                    progress = 1 - (session['remaining_duration'] / session['total_duration'])
                    
                    if pattern == 'gradual_drift':
                        intensity = 1 + (session['intensity'] - 1) * progress
                    elif pattern == 'oscillation':
                        intensity = 1 + (session['intensity'] - 1) * abs(np.sin(2 * np.pi * progress * 3))
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
        """Generate sensor data"""
        hours = self.config.time_duration_hours
        interval_minutes = self.config.sampling_interval_minutes
        
        print(f"Generating {hours} hours of sensor data, sampling interval {interval_minutes} minutes...")
        
        # Time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Generate time points
        time_points = []
        current_time = start_time
        while current_time <= end_time:
            time_points.append(current_time)
            current_time += timedelta(minutes=interval_minutes)
        
        data = []
        
        # For each time, each machine, each sensor, generate data
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
        
        # Inject anomalies
        print("Injecting anomalies...")
        self.inject_anomalies(data)
        
        df = pd.DataFrame(data)
        
        # Add noise if enabled
        if self.config.enable_noise_injection:
            print("Injecting random noise...")
            self._inject_noise(df)
        
        df = df.sort_values(['timestamp', 'machine_id', 'sensor_type'])
        
        # Remove is_anomaly column (internal use only)
        final_df = df[['timestamp', 'machine_id', 'sensor_type', 'reading']].copy()
        
        print(f"Generated {len(final_df)} sensor records")
        print(f"Included {df['is_anomaly'].sum()} anomaly records ({df['is_anomaly'].mean()*100:.1f}%)")
        
        return final_df

    def _inject_noise(self, df: pd.DataFrame):
        """Inject random noise"""
        for idx, row in df.iterrows():
            if not row.get('is_anomaly', False):  # Only apply to normal data
                machine_id = row['machine_id']
                sensor_type = row['sensor_type']
                
                min_val, max_val = self.sensor_types[sensor_type]['normal_ranges'][machine_id]
                range_size = max_val - min_val
                
                noise = np.random.normal(0, range_size * 0.01)
                df.at[idx, 'reading'] = round(row['reading'] + noise, 2)

    def generate_parameters_config(self) -> pd.DataFrame:
        """Generate machine operating parameter config"""
        print("Generating machine operating parameter configuration...")
        
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
        print(f"Generated {len(df)} parameter config entries")
        
        return df

    def save_data(self, sensor_data: pd.DataFrame, config_data: pd.DataFrame):
        """Save generated data to files"""
        print("Saving data files...")
        
        # Add file prefix
        prefix = self.config.output_prefix
        if prefix and not prefix.endswith('_'):
            prefix += '_'
        
        # Save sensor data as CSV
        sensor_file = f'{prefix}live_sensor_data.csv'
        sensor_data.to_csv(sensor_file, index=False)
        print(f"Sensor data saved to: {sensor_file}")
        
        # Save config data as Excel
        config_file = f'{prefix}machine_operating_parameters.xlsx'
        with pd.ExcelWriter(config_file, engine='openpyxl') as writer:
            config_data.to_excel(writer, sheet_name='Operating Parameters', index=False)
            
            # Add a summary sheet
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
        
        print(f"Parameter config saved to: {config_file}")

    def generate_data_stats(self, sensor_data: pd.DataFrame) -> Dict:
        """Generate data statistics"""
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
        
        # Save stats to file
        stats_file = f'{self.config.output_prefix}_data_generation_stats.json' if self.config.output_prefix else 'data_generation_stats.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        return stats

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Industrial IoT Sensor Data Generator - Highly Configurable Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Basic usage
  python main.py
  
  # Generate a large-scale dataset
  python main.py --hours 24 --interval 1 --machines 50 --complexity 2.0
  
  # Advanced anomaly modes
  python main.py --hours 12 --machines 20 --sensors humidity,power,efficiency \\
                 --multi-anomaly --cascade-failure --noise
  
  # Custom output
  python main.py --hours 6 --prefix "large_dataset" --anomaly-rate 0.25
        """
    )
    
    # Basic config
    parser.add_argument('--hours', type=float, default=2,
                        help='Time duration in hours (default: 2)')
    parser.add_argument('--interval', type=float, default=5,
                        help='Sampling interval in minutes (default: 5)')
    parser.add_argument('--anomaly-rate', type=float, default=0.15,
                        help='Anomaly probability (default: 0.15)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    
    # Extended config
    parser.add_argument('--machines', type=int, default=0,
                        help='Number of additional machines (default: 0)')
    parser.add_argument('--sensors', type=str, default='',
                        help='Additional sensor types, comma separated (humidity,power,efficiency,noise_level,oil_pressure,speed)')
    parser.add_argument('--complexity', type=float, default=1.0,
                        help='Complexity multiplier (default: 1.0)')
    parser.add_argument('--prefix', type=str, default='',
                        help='File prefix for output files (default: none)')
    
    # Advanced modes
    parser.add_argument('--multi-anomaly', action='store_true',
                        help='Enable multi-anomaly mode')
    parser.add_argument('--cascade-failure', action='store_true',
                        help='Enable cascade failure mode')
    parser.add_argument('--seasonal-patterns', action='store_true',
                        help='Enable seasonal patterns')
    parser.add_argument('--noise', action='store_true',
                        help='Enable noise injection')
    
    # Preset mode
    parser.add_argument('--preset', choices=['small', 'medium', 'large', 'extreme'],
                        help='Preset configuration mode')
    
    return parser.parse_args()

def apply_preset_config(config: DataGenerationConfig, preset: str):
    """Apply a preset configuration"""
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
        print(f"Applied preset configuration: {preset}")

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Create config
    config = DataGenerationConfig()
    
    # Apply preset config if provided
    if args.preset:
        apply_preset_config(config, args.preset)
    
    # Apply command line arguments
    config.random_seed = args.seed
    config.time_duration_hours = args.hours
    config.sampling_interval_minutes = args.interval
    config.anomaly_probability = args.anomaly_rate
    config.additional_machines = args.machines
    config.complexity_multiplier = args.complexity
    config.output_prefix = args.prefix
    
    # Parse extra sensors
    if args.sensors:
        config.additional_sensors = [s.strip() for s in args.sensors.split(',')]
    
    # Advanced mode config
    config.enable_multi_anomaly = args.multi_anomaly
    config.enable_cascade_failure = args.cascade_failure
    config.enable_seasonal_patterns = args.seasonal_patterns
    config.enable_noise_injection = args.noise
    
    # Print config summary
    print("=" * 80)
    print("Industrial IoT Sensor Data Generator - Highly Configurable Version")
    print("=" * 80)
    
    total_machines = 10 + config.additional_machines
    total_sensors = 6 + len(config.additional_sensors)
    estimated_records = int((config.time_duration_hours * 60 / config.sampling_interval_minutes) * total_machines * total_sensors)
    
    print(f"Configuration Summary:")
    print(f"  Time duration: {config.time_duration_hours} hours")
    print(f"  Sampling interval: {config.sampling_interval_minutes} minutes")
    print(f"  Number of machines: {total_machines} (10 base + {config.additional_machines} extra)")
    print(f"  Sensor types: {total_sensors} (6 base + {len(config.additional_sensors)} extra)")
    print(f"  Estimated records: {estimated_records:,}")
    print(f"  Anomaly probability: {config.anomaly_probability:.1%}")
    print(f"  Complexity multiplier: {config.complexity_multiplier}")
    if config.additional_sensors:
        print(f"  Additional sensors: {', '.join(config.additional_sensors)}")
    
    advanced_features = []
    if config.enable_multi_anomaly:
        advanced_features.append("Multi-anomaly")
    if config.enable_cascade_failure:
        advanced_features.append("Cascade failure")
    if config.enable_seasonal_patterns:
        advanced_features.append("Seasonal patterns")
    if config.enable_noise_injection:
        advanced_features.append("Noise injection")
    
    if advanced_features:
        print(f"  Advanced features: {', '.join(advanced_features)}")
    
    print("\nStarting data generation...")
    
    # Create generator
    generator = IndustrialSensorDataGenerator(config)
    
    # Generate data
    sensor_data = generator.generate_sensor_data()
    config_data = generator.generate_parameters_config()
    
    # Save data
    generator.save_data(sensor_data, config_data)
    
    # Generate stats
    stats = generator.generate_data_stats(sensor_data)
    
    print("\n" + "=" * 80)
    print("Data generation complete!")
    print("=" * 80)
    print(f"Total sensor records: {stats['total_records']:,}")
    print(f"Time range: {stats['time_range']['start']} to {stats['time_range']['end']}")
    print(f"Number of machines: {len(stats['machines'])}")
    print(f"Sensor types: {len(stats['sensor_types'])}")
    
    # Estimate data size
    estimated_size_mb = stats['total_records'] * 0.1 / 1000
    print(f"Estimated data size: ~{estimated_size_mb:.1f} MB")
    
    prefix = config.output_prefix + '_' if config.output_prefix else ''
    print(f"\nGenerated files:")
    print(f"1. {prefix}live_sensor_data.csv - Live sensor data")
    print(f"2. {prefix}machine_operating_parameters.xlsx - Machine operating parameter config")
    print(f"3. {prefix}data_generation_stats.json - Data generation statistics")
    
    if estimated_records > 100000:
        print(f"\n💡 Large-scale dataset generation complete!")
        print(f"   Tip: Specify a time range with the anomaly detection script for better performance.")

if __name__ == "__main__":
    main() 