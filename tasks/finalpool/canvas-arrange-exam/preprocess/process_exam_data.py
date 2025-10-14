#!/usr/bin/env python3
"""
Exam Information Processing Script
Extract exam information from course_config.json and write into exam_schedule.csv according to preprocess/result.csv columns.
"""

import json
import csv
from pathlib import Path
from datetime import datetime

def load_course_config():
    """Load the course configuration file."""
    config_file = Path(__file__).parent.parent / "files" / "course_config copy.json"
    
    if not config_file.exists():
        raise FileNotFoundError(f"Course configuration file does not exist: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_exam_info(course_data):
    """Extract exam information from course data."""
    exam_records = []
    
    for course in course_data.get('courses', []):
        # Basic information
        course_code = course.get('course_code', '')
        course_name = course.get('name', '')
        exam_time = course.get('exam_time', '')
        teacher = course.get('teacher', '')
        
        # Handle exam type
        exam_type = course.get('exam_type', 'closed_book')
        if exam_type == 'closed_book':
            open_closed_book = 'Closed-book'
        elif exam_type == 'open_book':
            open_closed_book = 'Open-book'
        elif exam_type == 'no_exam':
            open_closed_book = 'No Exam'
        else:
            open_closed_book = exam_type.title()
        
        # Handle duration
        duration_value = course.get('duration', '')
        duration_unit = course.get('duration_unit', 'minutes')
        if duration_value and duration_unit:
            duration = f"{duration_value} {duration_unit}"
        else:
            duration = 'TBD'
        
        # Handle location
        location = course.get('location', 'TBD')
        
        # Handle time
        if exam_time:
            try:
                # Parse time format
                dt = datetime.strptime(exam_time, "%Y-%m-%d %H:%M")
                final_date = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M")
            except ValueError:
                final_date = exam_time
                time_str = 'TBD'
        else:
            final_date = 'TBD'
            time_str = 'TBD'
        
        # Information source (default Announcement)
        information_source = 'Announcement'
        
        # Course credit
        course_credit = str(course.get('credits', 'TBD'))
        
        # Create exam record
        exam_record = {
            'Course Code': course_code,
            'Course Name': course_name,
            'Teacher': teacher,
            'Open-book/Closed-book': open_closed_book,
            'Final Date': final_date,
            'Time': time_str,
            'Duration': duration,
            'Location': location,
            'Information Source(Announcement/Email/Message)': information_source,
            'Course Credit': course_credit
        }
        
        exam_records.append(exam_record)
    
    return exam_records

def write_to_csv(exam_records, output_file):
    """Write exam records to a CSV file."""
    if not exam_records:
        print("No exam records to write.")
        return
    
    # Define column order (according to preprocess/result.csv)
    columns = [
        'Course Code',
        'Course Name',
        'Teacher',
        'Open-book/Closed-book',
        'Final Date',
        'Time',
        'Duration',
        'Location',
        'Information Source(Announcement/Email/Message)',
        'Course Credit'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        
        # Write header
        writer.writeheader()
        
        # Write records
        for record in exam_records:
            writer.writerow(record)
    
    print(f"Exam information successfully written to: {output_file}")

def main():
    """Main function."""
    try:
        print("Start processing exam information...")
        
        # 1. Load course configuration
        print("Loading course configuration file...")
        course_data = load_course_config()
        print(f"Successfully loaded {len(course_data.get('courses', []))} courses")
        
        # 2. Extract exam information
        print("Extracting exam information...")
        exam_records = extract_exam_info(course_data)
        print(f"Extracted {len(exam_records)} exam records")
        
        # 3. Write to CSV
        output_file = Path(__file__).parent / "exam_schedule.csv"
        print(f"Writing exam information to: {output_file}")
        write_to_csv(exam_records, output_file)
        
        # 4. Show summary statistics
        print("\nExam Information Statistics:")
        print(f"Total number of courses: {len(course_data.get('courses', []))}")
        print(f"Number of exam records: {len(exam_records)}")
        
        # 5. Preview top records
        if exam_records:
            print("\nPreview of the first 3 exam records:")
            for i, record in enumerate(exam_records[:3]):
                print(f"\nRecord {i+1}:")
                for key, value in record.items():
                    print(f"  {key}: {value}")
        
        print("\n✅ Exam information processing completed!")
        
    except Exception as e:
        print(f"❌ An error occurred during processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()
