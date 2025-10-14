#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exam Notification Email Injector Script
Directly injects exam notification emails into the inbox, without sending
Supports custom timestamps
"""

import sys
from pathlib import Path
from datetime import datetime

# Add path to import send_exam_notification_smtp module
sys.path.append(str(Path(__file__).parent))

from send_exam_notification_smtp import inject_exam_emails_from_config


def inject_with_custom_time():
    """Inject exam notification emails with a custom timestamp"""
    
    # Path to the config file
    config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
    
    print("🕐 Exam Notification Email Injector - Custom Time Mode")
    print("=" * 50)
    
    # Example scenarios with different timestamps
    email_scenarios = [
        {
            "name": "Final Exam Notification (Sent on Dec 1 Morning)",
            "time": datetime(2024, 12, 1, 10, 0, 0),
            "description": "End of term: Official final exam arrangement notification"
        },
        {
            "name": "Exam Reminder (Sent on Dec 15 Afternoon)", 
            "time": datetime(2024, 12, 15, 15, 30, 0),
            "description": "Reminder one month before the exam"
        },
        {
            "name": "Last Reminder (Sent on Jan 10 Morning)",
            "time": datetime(2025, 1, 10, 8, 0, 0), 
            "description": "Final reminder days before the exam"
        }
    ]
    
    print("Please select which email scenario to inject:")
    for i, scenario in enumerate(email_scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   Time: {scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Description: {scenario['description']}")
        print()
    
    print("4. Use current time")
    print("5. Enter custom time manually")
    print()
    
    try:
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == "1":
            selected_scenario = email_scenarios[0]
            timestamp = selected_scenario["time"].timestamp()
            print(f"📅 Selected scenario: {selected_scenario['name']}")
            print(f"⏰ Email time: {selected_scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "2":
            selected_scenario = email_scenarios[1]
            timestamp = selected_scenario["time"].timestamp()
            print(f"📅 Selected scenario: {selected_scenario['name']}")
            print(f"⏰ Email time: {selected_scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "3":
            selected_scenario = email_scenarios[2]
            timestamp = selected_scenario["time"].timestamp()
            print(f"📅 Selected scenario: {selected_scenario['name']}")
            print(f"⏰ Email time: {selected_scenario['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "4":
            timestamp = None
            print("📅 Using current time")
            
        elif choice == "5":
            print("Please input a timestamp (format: YYYY-MM-DD HH:MM:SS)")
            time_str = input("Time: ").strip()
            custom_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            timestamp = custom_time.timestamp()
            print(f"⏰ Custom time: {custom_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        else:
            print("❌ Invalid choice")
            return False
            
        print("\n🚀 Starting email injection ...")
        print("-" * 50)
        
        # Execute email injection
        success = inject_exam_emails_from_config(str(config_file), timestamp)
        
        return success
        
    except ValueError as e:
        print(f"❌ Timestamp format error: {e}")
        print("Please use format: YYYY-MM-DD HH:MM:SS, e.g.: 2024-12-01 10:00:00")
        return False
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        return False


def inject_current_time():
    """Inject exam notification emails with current timestamp"""
    
    config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
    
    print("🕐 Exam Notification Email Injector - Current Time Mode")
    print("=" * 50)
    
    # Inject with current time
    success = inject_exam_emails_from_config(str(config_file), None)
    
    return success


def main():
    """Main entry point"""
    print("📧 Exam Notification Email Bulk Injector Tool")
    print("🎯 Directly injects exam emails into the inbox, no SMTP sending required")
    print("⏰ Custom timestamp supported")
    print("=" * 60)
    print()
    
    print("Please select an injection mode:")
    print("1. Custom time mode (pick a preset scenario or enter time manually)")
    print("2. Current time mode (inject immediately)")
    print("3. Exit")
    print()
    
    try:
        mode = input("Enter your choice (1-3): ").strip()
        
        if mode == "1":
            success = inject_with_custom_time()
        elif mode == "2":
            success = inject_current_time()
        elif mode == "3":
            print("👋 Bye!")
            return
        else:
            print("❌ Invalid choice")
            return
            
        if success:
            print("\n" + "=" * 60)
            print("🎉 Email injection completed successfully!")
            print("📬 Please check the inbox to confirm emails were injected")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("💥 Email injection failed!")
            print("🔍 Please check the config file and network connection")
            print("=" * 60)
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Program execution failed: {e}")


if __name__ == "__main__":
    main() 