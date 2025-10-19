#!/usr/bin/env python3
"""
Anomaly Detection Demo Script

Demonstrates the enhanced features of anomaly_detection.py
"""

import subprocess
import os
import time

def run_command(description, command, show_output=True):
    """Run a shell command and display its result"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {command}")
    print()
    
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            if show_output:
                print(result.stdout)
        else:
            print("❌ Command failed!")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")

def main():
    """Main demo function"""
    print("🔍 Factory IoT Sensor Anomaly Detection System - Feature Demo")
    print("📊 Showcasing enhanced anomaly detection capabilities")
    
    # First, generate some test data
    print(f"\n{'='*60}")
    print("📋 Prepare test data")
    print(f"{'='*60}")
    
    # Check whether data exists
    if not os.path.exists('live_sensor_data.csv'):
        print("🔄 Generating basic test dataset...")
        subprocess.run(['python', 'main.py', '--hours', '2', '--prefix', 'demo'], 
                      capture_output=True)
        print("✅ Basic dataset generated")
    
    if not any(f.startswith('extended_') for f in os.listdir('.') if f.endswith('.csv')):
        print("🔄 Generating extended test dataset...")
        subprocess.run(['python', 'main.py', '--hours', '1', '--machines', '5', 
                       '--sensors', 'humidity,power', '--prefix', 'extended'], 
                      capture_output=True)
        print("✅ Extended dataset generated")
    
    demos = [
        {
            "description": "List available datasets",
            "command": "python anomaly_detection.py --list-datasets",
            "show_output": True
        },
        {
            "description": "Show default dataset overview",
            "command": "python anomaly_detection.py --overview-only",
            "show_output": True
        },
        {
            "description": "Basic anomaly detection (full time range)",
            "command": "python anomaly_detection.py --output-prefix basic",
            "show_output": False  # Output may be too long; only show the command
        },
        {
            "description": "Anomaly detection for a specific time range",
            "command": "python anomaly_detection.py --start-time 11:30 --end-time 12:30 --output-prefix time_range",
            "show_output": False
        },
        {
            "description": "Extended dataset anomaly detection",
            "command": "python anomaly_detection.py --prefix extended --output-prefix extended_analysis",
            "show_output": False
        }
    ]
    
    print(f"\n🎯 {len(demos)} demo steps will be executed:")
    for i, demo in enumerate(demos, 1):
        print(f"{i}. {demo['description']}")
    
    input("\nPress Enter to start the demo...")

    for i, demo in enumerate(demos, 1):
        run_command(f"Demo {i}: {demo['description']}", 
                   demo['command'], demo['show_output'])
        
        if demo['show_output'] and i < len(demos):
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("📊 Demo finished! Listing generated report files")
    print(f"{'='*60}")
    
    # Show generated anomaly report files
    report_files = [f for f in os.listdir('.') if f.startswith('anomaly_report_') or 
                   f.endswith('_anomaly_report_')]
    
    if report_files:
        print("📄 Generated anomaly report files:")
        for file in sorted(report_files)[-5:]:  # Show the latest 5
            size = os.path.getsize(file) / 1024
            print(f"  📋 {file:<50} ({size:.1f}KB)")
    else:
        print("⚠️ No anomaly report files found")
    
    print(f"\n💡 Tips:")
    print(f"   - Check the report files for detailed anomaly information")
    print(f"   - Use --help for more parameter options")
    print(f"   - Try different parameter combinations for more flexible anomaly analysis")

if __name__ == "__main__":
    main() 