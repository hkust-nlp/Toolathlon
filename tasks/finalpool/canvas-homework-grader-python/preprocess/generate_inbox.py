#!/usr/bin/env python3
"""
Generate inbox JSON file by merging fake_emails.json and target_emails.json
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import re


def load_json_file(file_path):
    """Load JSON data from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return []


def parse_relative_date(date_str):
    """Parse relative date string like '3 days before current date'"""
    # Extract number and unit from date string
    match = re.match(r'(\d+)\s+(days?)\s+before\s+current\s+date', date_str)
    if not match:
        print(f"⚠️  Cannot parse date: {date_str}")
        return datetime.now()
    
    days_back = int(match.group(1))
    current_time = datetime.now()
    target_time = current_time - timedelta(days=days_back)
    
    return target_time


def format_email_date(dt):
    """Format datetime to email date format like 'Sun, 31 May 2025 17:36:00 +0800'"""
    # Format: DayName, DD Month YYYY HH:MM:SS +0800
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    day_name = day_names[dt.weekday()]
    month_name = month_names[dt.month]
    
    return f"{day_name}, {dt.day:02d} {month_name} {dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} +0800"


def process_emails(emails):
    """Process emails: parse dates and add datetime objects for sorting"""
    processed_emails = []
    
    for email in emails:
        email_copy = email.copy()
        
        # Parse the relative date
        date_str = email['date']
        if 'before current date' in date_str:
            parsed_date = parse_relative_date(date_str)
            email_copy['_datetime'] = parsed_date
            email_copy['date'] = format_email_date(parsed_date)
        else:
            # Handle other date formats if needed
            print(f"⚠️  Unknown date format: {date_str}")
            email_copy['_datetime'] = datetime.now()
            email_copy['date'] = format_email_date(datetime.now())
        
        processed_emails.append(email_copy)
    
    return processed_emails


def main():
    # File paths
    base_dir = Path(__file__).parent.parent
    fake_emails_file = base_dir / "files" / "fake_emails.json"
    target_emails_file = base_dir / "files" / "target_emails.json"
    output_file = base_dir / "files" / "generated_inbox.json"
    
    print("📧 Generating inbox from fake_emails.json and target_emails.json")
    print("=" * 70)
    
    # Load email files
    fake_emails = load_json_file(fake_emails_file)
    target_emails = load_json_file(target_emails_file)
    print(f"✅ Loaded {len(fake_emails)} fake + {len(target_emails)} target emails")
    
    # Merge emails - ensure all target emails are included + random fake emails
    selected_emails = target_emails.copy()
    
    # Randomly select fake emails
    if fake_emails:
        num_fake_to_select = random.randint(100, 150)
        num_fake_to_select = min(num_fake_to_select, len(fake_emails))
        selected_fake_emails = random.sample(fake_emails, num_fake_to_select)
        selected_emails.extend(selected_fake_emails)
        print(f"🎯 Selected {len(target_emails)} target + {num_fake_to_select} fake = {len(selected_emails)} total emails")
    
    # Process emails: parse dates and format them
    processed_emails = process_emails(selected_emails)
    processed_emails.sort(key=lambda x: x['_datetime'], reverse=True)
    
    # Reassign email IDs based on sorted order
    for i, email in enumerate(processed_emails, 1):
        email['email_id'] = str(i)
        del email['_datetime']
    
    # Generate output data
    current_time = datetime.now()
    output_data = {
        "export_date": current_time.isoformat(),
        "total_emails": len(processed_emails),
        "emails": processed_emails
    }
    
    # Write to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully generated {output_file}")
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        return
    
    # Quick summary
    print(f"📊 Generated {len(processed_emails)} emails")
    
    # Show homework submissions found
    homework_count = 0
    for email in processed_emails:
        subject = email.get('subject', '')
        if 'homework 2' in subject.lower() or 'hw2' in subject.lower():
            homework_count += 1
    
    if homework_count > 0:
        print(f"📝 Found {homework_count} homework 2 submissions")
    
    print("✅ Inbox generation completed")


if __name__ == "__main__":
    # Set random seed for reproducible results (optional)
    random.seed(42)
    main()