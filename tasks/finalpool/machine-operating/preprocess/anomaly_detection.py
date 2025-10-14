#!/usr/bin/env python3
"""
Anomaly Detection Script - Identify Abnormal Sensor Readings (Enhanced Version)

Features:
1. Filter sensor data by specified time range
2. Identify anomalies based on Excel parameter configuration
3. Generate anomaly report
4. Support multi-dataset processing and flexible configuration
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import argparse
import glob
from pathlib import Path

def find_data_files(prefix=""):
    """Find data files based on prefix"""
    if prefix and not prefix.endswith('_'):
        prefix += '_'

    sensor_pattern = f"{prefix}live_sensor_data.csv"
    params_pattern = f"{prefix}machine_operating_parameters.xlsx"

    sensor_files = glob.glob(sensor_pattern)
    params_files = glob.glob(params_pattern)

    if not sensor_files:
        # Try to find any sensor data file
        all_sensor_files = glob.glob("*live_sensor_data.csv")
        if all_sensor_files:
            print(f"Not found: {sensor_pattern}. Available sensor data files:")
            for i, file in enumerate(all_sensor_files):
                print(f"  {i+1}. {file}")
            return None, None
        else:
            print("No sensor data files found.")
            return None, None

    if not params_files:
        print(f"Not found: parameter configuration file: {params_pattern}")
        return None, None

    return sensor_files[0], params_files[0]

def load_data(prefix=""):
    """Load sensor data and parameter configuration"""
    print("Locating and loading data files...")

    sensor_file, params_file = find_data_files(prefix)
    if not sensor_file or not params_file:
        return None, None

    print(f"Using sensor data file: {sensor_file}")
    print(f"Using parameter config file: {params_file}")

    # Load sensor data
    sensor_data = pd.read_csv(sensor_file)
    sensor_data['timestamp'] = pd.to_datetime(sensor_data['timestamp'])

    # Load parameter configuration
    params_data = pd.read_excel(params_file, sheet_name='Operating Parameters')

    print(f"Sensor data records: {len(sensor_data):,}")
    print(f"Parameter config records: {len(params_data):,}")
    print(f"Data time range: {sensor_data['timestamp'].min()} to {sensor_data['timestamp'].max()}")
    print(f"Number of machines: {sensor_data['machine_id'].nunique()}")
    print(f"Sensor types: {sensor_data['sensor_type'].nunique()} ({', '.join(sorted(sensor_data['sensor_type'].unique()))})")

    return sensor_data, params_data

def parse_time_input(time_str):
    """Parse time input, support multiple formats"""
    if not time_str:
        return None

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

    raise ValueError(f"Unable to parse time format: {time_str}")

def filter_time_range(data, start_time=None, end_time=None):
    """Filter data within a specified time range"""
    if not start_time and not end_time:
        print("No time range specified. Using all data.")
        return data

    print(f"\nFiltering time range: {start_time or 'start of data'} to {end_time or 'end of data'}")

    filtered_data = data.copy()

    if start_time:
        try:
            start_dt = parse_time_input(start_time)

            # If only time (no date) use date from data
            if start_dt.date() == datetime(1900, 1, 1).date():
                data_date = data['timestamp'].dt.date.iloc[0]
                start_dt = datetime.combine(data_date, start_dt.time())

            filtered_data = filtered_data[filtered_data['timestamp'] >= start_dt]

        except ValueError as e:
            print(f"Start time parse error: {e}")
            try:
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                filtered_data = filtered_data[filtered_data['timestamp'].dt.time >= start_time_obj]
            except ValueError:
                print("Using default start time.")

    if end_time:
        try:
            end_dt = parse_time_input(end_time)

            if end_dt.date() == datetime(1900, 1, 1).date():
                data_date = data['timestamp'].dt.date.iloc[-1]
                end_dt = datetime.combine(data_date, end_dt.time())

            filtered_data = filtered_data[filtered_data['timestamp'] <= end_dt]

        except ValueError as e:
            print(f"End time parse error: {e}")
            try:
                end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                filtered_data = filtered_data[filtered_data['timestamp'].dt.time <= end_time_obj]
            except ValueError:
                print("Using default end time.")

    print(f"Records after filtering: {len(filtered_data):,}")

    if len(filtered_data) > 0:
        print(f"Actual time range: {filtered_data['timestamp'].min()} to {filtered_data['timestamp'].max()}")

    return filtered_data

def detect_anomalies(sensor_data, params_data):
    """Detect abnormal readings"""
    print("\nStarting anomaly detection...")

    # Merge with parameter configuration
    merged_data = sensor_data.merge(
        params_data[['machine_id', 'sensor_type', 'min_value', 'max_value', 'unit']],
        on=['machine_id', 'sensor_type'],
        how='left'
    )

    # Warn if unmatched records
    unmatched = merged_data[merged_data['min_value'].isna()]
    if len(unmatched) > 0:
        print(f"Warning: {len(unmatched)} records have no matching parameter configuration.")

    # Identify anomalies
    merged_data['is_below_min'] = merged_data['reading'] < merged_data['min_value']
    merged_data['is_above_max'] = merged_data['reading'] > merged_data['max_value']
    merged_data['is_anomaly'] = merged_data['is_below_min'] | merged_data['is_above_max']

    anomalies = merged_data[merged_data['is_anomaly']].copy()

    # Add anomaly type and normal range
    anomalies['anomaly_type'] = anomalies.apply(
        lambda row: 'below_minimum' if row['is_below_min'] else 'above_maximum',
        axis=1
    )
    anomalies['normal_range'] = (
        anomalies['min_value'].astype(str) + ' - ' +
        anomalies['max_value'].astype(str) + ' ' +
        anomalies['unit'].astype(str)
    )

    print(f"Anomaly records detected: {len(anomalies)}")
    print(f"Anomaly rate: {len(anomalies) / len(merged_data) * 100:.1f}%")

    return anomalies, merged_data

def generate_anomaly_report(anomalies, output_prefix=""):
    """Generate anomaly report"""
    print("\nGenerating anomaly report...")

    if len(anomalies) == 0:
        print("⚠️ No anomalies detected, report generation skipped.")
        return pd.DataFrame(), None

    report_columns = [
        'timestamp', 'machine_id', 'sensor_type', 'reading',
        'normal_range', 'anomaly_type', 'unit'
    ]

    report = anomalies[report_columns].copy()
    report = report.sort_values('timestamp')

    # Add severity rating
    def calculate_severity(row):
        try:
            # Parse "min_val - max_val unit" string
            range_parts = row['normal_range'].split(' - ')
            min_val = float(range_parts[0])
            max_part = range_parts[1].split()[0]
            max_val = float(max_part)

            range_size = max_val - min_val
            if range_size <= 0:
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
        except (ValueError, IndexError, ZeroDivisionError):
            return 'Medium'

    report['severity'] = report.apply(calculate_severity, axis=1)

    # Output filename
    if output_prefix and not output_prefix.endswith('_'):
        output_prefix += '_'

    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f'{output_prefix}anomaly_report_{timestamp_str}.csv'

    report.to_csv(report_filename, index=False)

    print(f"Anomaly report saved to: {report_filename}")
    print(f"Report contains {len(report)} anomaly records")

    # Print severity distribution
    severity_counts = report['severity'].value_counts()
    print("Severity distribution:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count} records")

    return report, report_filename

def print_summary_statistics(anomalies, all_data):
    """Print summary statistics"""
    print("\n" + "="*60)
    print("Anomaly Detection Summary Statistics")
    print("="*60)

    if len(anomalies) == 0:
        print("No anomalies detected.")
        return

    total_records = len(all_data)
    anomaly_count = len(anomalies)
    anomaly_rate = anomaly_count / total_records * 100

    print(f"Total data records: {total_records:,}")
    print(f"Anomaly records: {anomaly_count:,}")
    print(f"Anomaly rate: {anomaly_rate:.1f}%")

    # By machine
    print(f"\nAnomaly statistics by machine:")
    machine_stats = anomalies.groupby('machine_id').agg({
        'timestamp': 'count',
        'reading': 'count'
    }).rename(columns={'timestamp': 'anomaly_count'})

    total_by_machine = all_data.groupby('machine_id').size()
    machine_stats['total_records'] = total_by_machine
    machine_stats['anomaly_rate'] = (machine_stats['anomaly_count'] / machine_stats['total_records'] * 100).round(1)

    print(machine_stats[['anomaly_count', 'anomaly_rate']].to_string())

    # By sensor type
    print(f"\nAnomaly statistics by sensor type:")
    sensor_stats = anomalies.groupby('sensor_type').agg({
        'timestamp': 'count',
        'reading': 'count'
    }).rename(columns={'timestamp': 'anomaly_count'})

    total_by_sensor = all_data.groupby('sensor_type').size()
    sensor_stats['total_records'] = total_by_sensor
    sensor_stats['anomaly_rate'] = (sensor_stats['anomaly_count'] / sensor_stats['total_records'] * 100).round(1)

    print(sensor_stats[['anomaly_count', 'anomaly_rate']].to_string())

    # By anomaly type
    print(f"\nAnomaly type distribution:")
    anomaly_type_stats = anomalies['anomaly_type'].value_counts()
    print(anomaly_type_stats.to_string())

    # Most severe anomalies
    print(f"\nMost severe anomaly readings (Top 10):")
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
    """Print sample anomaly records"""
    print(f"\nSample anomalies (first {n}):")

    if len(anomalies) == 0:
        print("No anomalies present.")
        return

    sample = anomalies.head(n)[
        ['timestamp', 'machine_id', 'sensor_type', 'reading', 'normal_range', 'anomaly_type']
    ]

    print(sample.to_string(index=False))

def show_dataset_overview(sensor_data):
    """Show dataset overview"""
    print(f"\n📊 Dataset Overview:")
    print("="*50)

    # Time span
    time_span = sensor_data['timestamp'].max() - sensor_data['timestamp'].min()
    print(f"📅 Time span: {time_span}")

    # Sampling frequency
    time_diffs = sensor_data['timestamp'].diff().dropna()
    avg_interval = time_diffs.median()
    print(f"⏰ Average sampling interval: {avg_interval}")

    # Machine and sensor stats
    machines = sensor_data['machine_id'].unique()
    sensors = sensor_data['sensor_type'].unique()

    print(f"🏭 Number of machines: {len(machines)}")
    print(f"📡 Sensor types: {len(sensors)}")
    print(f"   Types: {', '.join(sorted(sensors))}")

    # Data completeness
    expected_records = len(machines) * len(sensors) * len(sensor_data['timestamp'].unique())
    actual_records = len(sensor_data)
    completeness = (actual_records / expected_records) * 100

    print(f"✅ Data completeness: {completeness:.1f}% ({actual_records:,}/{expected_records:,})")

    # Data quality
    null_count = sensor_data.isnull().sum().sum()
    print(f"❌ Number of missing values: {null_count}")

    if null_count == 0:
        print("🎉 Data quality: Excellent (no missing values)")
    elif null_count < actual_records * 0.01:
        print("👍 Data quality: Good (missing < 1%)")
    else:
        print("⚠️ Data quality: Needs attention (more missing values)")

def list_available_datasets():
    """List available datasets"""
    sensor_files = glob.glob("*live_sensor_data.csv")

    if not sensor_files:
        print("❌ No sensor data files found.")
        return []

    print("📁 Available datasets:")
    datasets = []

    for i, file in enumerate(sensor_files):
        prefix = file.replace('live_sensor_data.csv', '').rstrip('_')
        if not prefix:
            prefix = "default"

        file_size = os.path.getsize(file) / 1024  # KB

        try:
            sample_data = pd.read_csv(file, nrows=100)
            machine_count = sample_data['machine_id'].nunique()
            sensor_count = sample_data['sensor_type'].nunique()

            print(f"  {i+1}. {prefix:<20} ({file_size:.1f}KB, {machine_count} machine(s), {sensor_count} sensor type(s))")
            datasets.append(prefix)

        except Exception as e:
            print(f"  {i+1}. {prefix:<20} ({file_size:.1f}KB, Read error: {e})")

    return datasets

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Factory IoT Sensor Anomaly Detection System (Enhanced Version)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Basic usage (use default data files)
  python anomaly_detection.py

  # Specify dataset prefix
  python anomaly_detection.py --prefix large_dataset

  # Specify time range
  python anomaly_detection.py --start-time "11:30" --end-time "12:30"

  # Full date and time
  python anomaly_detection.py --start-time "2024-08-19 11:30" --end-time "2024-08-19 12:30"

  # Show available datasets
  python anomaly_detection.py --list-datasets

  # Show only overview, skip anomaly detection
  python anomaly_detection.py --overview-only
        """
    )

    parser.add_argument('--prefix', type=str, default='',
                        help='Data file prefix. Default: no prefix.')
    parser.add_argument('--start-time', type=str, default=None,
                        help='Start time (format: HH:MM or YYYY-MM-DD HH:MM)')
    parser.add_argument('--end-time', type=str, default=None,
                        help='End time (format: HH:MM or YYYY-MM-DD HH:MM)')
    parser.add_argument('--output-prefix', type=str, default='',
                        help='Output report file prefix. Default: no prefix.')
    parser.add_argument('--list-datasets', action='store_true',
                        help='List available datasets.')
    parser.add_argument('--overview-only', action='store_true',
                        help='Show dataset overview only, skip anomaly detection.')

    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()

    # Only list datasets if requested
    if args.list_datasets:
        list_available_datasets()
        return

    print("="*80)
    print("🏭 Factory IoT Sensor Anomaly Detection System (Enhanced Version)")
    print("="*80)

    try:
        # Load data
        sensor_data, params_data = load_data(args.prefix)

        if sensor_data is None or params_data is None:
            print("\n💡 Tip: Use --list-datasets to view available datasets.")
            return

        # Show dataset overview
        show_dataset_overview(sensor_data)

        # Overview only, skip rest
        if args.overview_only:
            return

        # Filter by time range
        filtered_data = filter_time_range(sensor_data, args.start_time, args.end_time)

        if len(filtered_data) == 0:
            print("⚠️ Warning: No data in the specified time range.")
            return

        # Detect anomalies
        anomalies, all_filtered_data = detect_anomalies(filtered_data, params_data)

        # Generate report
        output_prefix = args.output_prefix or args.prefix
        report, report_filename = generate_anomaly_report(anomalies, output_prefix)

        if report_filename:
            # Print summary statistics
            print_summary_statistics(anomalies, all_filtered_data)

            # Print anomaly samples
            print_sample_anomalies(anomalies)

            print(f"\n" + "="*80)
            print("🎉 Anomaly detection finished!")
            print("="*80)
            print(f"📄 Generated file: {report_filename}")
            print(f"📊 Total anomalies: {len(anomalies):,}")
            print("💡 Suggestion: Upload the anomaly report to the iot_anomaly_reports cloud storage bucket.")

    except FileNotFoundError as e:
        print(f"❌ Error: Data file not found - {e}")
        print("💡 Tips:")
        print("   1. Check the file path.")
        print("   2. Use --list-datasets to see available datasets.")
        print("   3. Use --prefix to specify the correct dataset prefix.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()