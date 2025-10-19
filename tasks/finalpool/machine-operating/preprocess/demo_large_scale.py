#!/usr/bin/env python3
"""
Large-Scale Data Generation Demo Script

Demonstrates how to use the extended main.py to generate datasets of various sizes and complexities.
"""

import subprocess
import os
import time

def run_generation(description, command, estimate_time=None):
    """Run data generation command"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {command}")
    
    if estimate_time:
        print(f"Estimated time: {estimate_time}")
        
    print("\nStarting execution...")
    start_time = time.time()
    
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Success!")
            print(result.stdout)
        else:
            print("❌ Failed!")
            print(result.stderr)
            
        elapsed = time.time() - start_time
        print(f"\nActual elapsed time: {elapsed:.1f} seconds")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")

def main():
    """Main demo function"""
    print("🏭 Factory IoT Sensor Data Generator - Large Scale Data Demo")
    print("📊 Generating datasets of different sizes to showcase system capabilities")
    
    demos = [
        {
            "description": "Small-scale dataset (for quick testing)",
            "command": "python main.py --preset small --prefix demo_small",
            "estimate": "< 10s"
        },
        {
            "description": "Medium-scale dataset (includes additional sensors)",
            "command": "python main.py --preset medium --prefix demo_medium",
            "estimate": "10-30s"
        },
        {
            "description": "Custom large-scale dataset (high-frequency sampling)",
            "command": "python main.py --hours 8 --interval 2 --machines 15 --sensors humidity,power,efficiency --complexity 1.5 --prefix demo_custom",
            "estimate": "30-60s"
        },
        {
            "description": "Highly complex dataset (multiple anomaly patterns)",
            "command": "python main.py --hours 4 --machines 10 --sensors humidity,power --multi-anomaly --noise --cascade-failure --prefix demo_complex",
            "estimate": "20-40s"
        }
    ]
    
    print(f"\n{len(demos)} demo steps will be executed:")
    for i, demo in enumerate(demos, 1):
        print(f"{i}. {demo['description']}")
    
    input("\nPress Enter to continue with the demo...")
    
    for i, demo in enumerate(demos, 1):
        run_generation(f"Demo {i}: {demo['description']}", demo['command'], demo['estimate'])
        
        if i < len(demos):
            print(f"\n⏳ Waiting 2 seconds before the next demo...")
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("🎉 All demos completed!")
    print(f"{'='*60}")
    
    # Display generated files
    print("\n📁 Generated files:")
    files = []
    for file in os.listdir('.'):
        if file.startswith('demo_') and (file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.json')):
            size = os.path.getsize(file) / 1024  # KB
            files.append((file, size))
    
    files.sort(key=lambda x: x[1], reverse=True)  # sort by size
    
    for file, size in files:
        if size >= 1024:
            print(f"  📊 {file:<40} ({size/1024:.1f} MB)")
        else:
            print(f"  📄 {file:<40} ({size:.1f} KB)")
    
    print(f"\n💡 Tips:")
    print(f"   - Use 'python verify_data.py' to verify data quality")
    print(f"   - Use 'python anomaly_detection.py' for anomaly detection")
    print(f"   - For very large files, consider batch processing")

if __name__ == "__main__":
    main() 