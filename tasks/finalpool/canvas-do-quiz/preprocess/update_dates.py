#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Date processing utility for Canvas course configuration
Updates exam_time and due_at dates to the next day of current datetime
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path


def get_next_day() -> datetime:
    """Get the next day from current datetime"""
    return datetime.now() + timedelta(days=1)


def format_exam_time(next_day: datetime, original_time_str: str) -> str:
    """
    Format exam_time to next day with original time
    Args:
        next_day: Next day datetime
        original_time_str: Original time string like "2025-01-14 09:00"
    Returns:
        Formatted datetime string like "2025-09-11 09:00"
    """
    if original_time_str == "TBD":
        return "TBD"
    
    # Extract time part from original string (HH:MM)
    time_match = re.search(r'(\d{2}:\d{2})', original_time_str)
    if time_match:
        time_part = time_match.group(1)
        return f"{next_day.strftime('%Y-%m-%d')} {time_part}"
    else:
        # Default to 09:00 if no time found
        return f"{next_day.strftime('%Y-%m-%d')} 09:00"


def format_due_at(next_day: datetime) -> str:
    """
    Format due_at to next day at 23:59:00Z
    Args:
        next_day: Next day datetime
    Returns:
        ISO format datetime string like "2025-09-11T23:59:00Z"
    """
    return f"{next_day.strftime('%Y-%m-%d')}T23:59:00Z"


def update_course_dates(course: Dict[str, Any], next_day: datetime) -> Dict[str, Any]:
    """
    Update dates in a single course
    Args:
        course: Course dictionary
        next_day: Next day datetime
    Returns:
        Updated course dictionary
    """
    # Update exam_time
    if "exam_time" in course:
        course["exam_time"] = format_exam_time(next_day, course["exam_time"])
    
    # Update quiz due_at
    if "quiz" in course and "due_at" in course["quiz"]:
        course["quiz"]["due_at"] = format_due_at(next_day)
    
    return course


def update_config_dates(config_path: str, output_path: str = None) -> None:
    """
    Update all exam_time and due_at dates in course configuration to next day
    Args:
        config_path: Path to the course_config.json file
        output_path: Optional output path, defaults to same as input
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Read configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Get next day
    next_day = get_next_day()
    print(f"Updating dates to next day: {next_day.strftime('%Y-%m-%d')}")
    
    # Update each course
    if "courses" in config:
        for i, course in enumerate(config["courses"]):
            config["courses"][i] = update_course_dates(course, next_day)
            print(f"Updated course: {course.get('course_code', f'Course {i+1}')}")
    
    # Write updated configuration
    output_path = output_path or config_path
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"Configuration updated and saved to: {output_path}")


def main():
    """Main function for testing"""
    import sys
    from argparse import ArgumentParser
    
    parser = ArgumentParser(description="Update course configuration dates")
    parser.add_argument("--config", required=True, help="Path to course_config.json")
    parser.add_argument("--output", help="Output path (optional)")
    
    args = parser.parse_args()
    
    try:
        update_config_dates(args.config, args.output)
        print("✅ Date update completed successfully")
    except Exception as e:
        print(f"❌ Error updating dates: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()