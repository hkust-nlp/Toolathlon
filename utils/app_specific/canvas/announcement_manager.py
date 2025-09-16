#!/usr/bin/env python3
"""
Canvas Announcement Manager

This module provides functionality for managing Canvas course announcements.
Extracted from tasks/finalpool/canvas-arrange-exam for reuse.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from .api_client import CanvasAPI


class AnnouncementManager:
    """Manager for Canvas course announcements"""

    def __init__(self, canvas_api: CanvasAPI):
        """
        Initialize Announcement Manager

        Args:
            canvas_api: CanvasAPI instance
        """
        self.canvas = canvas_api

    def create_announcement(self, course_id: int, title: str, message: str,
                           is_announcement: bool = True, delayed_post_at: Optional[str] = None,
                           require_initial_post: bool = False) -> Optional[Dict]:
        """
        Create an announcement in a course

        Args:
            course_id: Course ID
            title: Announcement title
            message: Announcement message/content
            is_announcement: Whether this is an announcement (True) or discussion (False)
            delayed_post_at: Optional delayed post date in ISO format
            require_initial_post: Whether students must post before seeing other replies

        Returns:
            Announcement data or None if error
        """
        announcement_data = {
            'title': title,
            'message': message,
            'is_announcement': is_announcement,
            'published': True,
            'discussion_type': 'threaded',
            'require_initial_post': require_initial_post
        }

        if delayed_post_at:
            announcement_data['delayed_post_at'] = delayed_post_at

        result = self.canvas._make_request(
            'POST',
            f'courses/{course_id}/discussion_topics',
            announcement_data
        )

        if result:
            print(f"✅ Announcement created: {title} (ID: {result.get('id')})")
        else:
            print(f"❌ Failed to create announcement: {title}")

        return result

    def create_exam_announcement(self, course_id: int, exam_info: Dict[str, Any],
                                template: Optional[str] = None) -> Optional[Dict]:
        """
        Create an exam notification announcement

        Args:
            course_id: Course ID
            exam_info: Dictionary containing exam information with keys:
                - exam_type: Type of exam (e.g., "Final Exam", "Midterm")
                - exam_date: Date of exam
                - exam_time: Time of exam
                - exam_location: Location of exam
                - duration: Duration of exam
                - course_name: Name of the course (optional)
                - additional_notes: Any additional notes (optional)
            template: Optional custom template string with {key} placeholders

        Returns:
            Announcement data or None if error
        """
        if template is None:
            template = """Dear Students,

This is an important announcement regarding your upcoming {exam_type} for {course_name}.

📅 **Date:** {exam_date}
⏰ **Time:** {exam_time}
📍 **Location:** {exam_location}
⏱️ **Duration:** {duration}

**Important Reminders:**
- Please arrive at least 15 minutes before the exam starts
- Bring your student ID and necessary writing materials
- Review all course materials and practice problems
- No electronic devices allowed except approved calculators

{additional_notes}

If you have any questions or concerns, please contact me directly.

Good luck with your preparation!

Best regards,
Course Instructor"""

        # Fill in course name if not provided
        if 'course_name' not in exam_info:
            course = self.canvas.get_course(course_id)
            if course:
                exam_info['course_name'] = course.get('name', 'this course')
            else:
                exam_info['course_name'] = 'this course'

        # Add default additional notes if not provided
        if 'additional_notes' not in exam_info:
            exam_info['additional_notes'] = ""

        # Format the message
        message = template.format(**exam_info)

        # Create title
        title = f"{exam_info['exam_type']} - {exam_info['exam_date']}"

        return self.create_announcement(course_id, title, message)

    def list_announcements(self, course_id: int, only_announcements: bool = True) -> List[Dict]:
        """
        List all announcements for a course

        Args:
            course_id: Course ID
            only_announcements: If True, only return announcements (not discussions)

        Returns:
            List of announcement data
        """
        params = {
            'per_page': 100,
            'order_by': 'recent_activity'
        }

        if only_announcements:
            params['only_announcements'] = 'true'

        result = self.canvas._make_request(
            'GET',
            f'courses/{course_id}/discussion_topics',
            params=params
        )

        return result if result else []

    def delete_announcement(self, course_id: int, announcement_id: int) -> bool:
        """
        Delete an announcement

        Args:
            course_id: Course ID
            announcement_id: Announcement ID

        Returns:bu
            True if successful, False otherwise
        """
        result = self.canvas._make_request(
            'DELETE',
            f'courses/{course_id}/discussion_topics/{announcement_id}'
        )

        # DELETE requests often return empty response on success
        # Check if result is not None OR if it has success indicators
        if result is not None:
            print(f"✅ Announcement {announcement_id} deleted")
            return True
        else:
            print(f"❌ Failed to delete announcement {announcement_id}")
            return False

    def batch_create_exam_announcements(self, courses_with_exams: List[Dict[str, Any]],
                                       template: Optional[str] = None) -> Dict[str, int]:
        """
        Create exam announcements for multiple courses

        Args:
            courses_with_exams: List of dictionaries with 'course_id' and 'exam_info' keys
            template: Optional custom template for all announcements

        Returns:
            Statistics dictionary with counts
        """
        stats = {'successful': 0, 'failed': 0, 'total': len(courses_with_exams)}

        print(f"Creating exam announcements for {len(courses_with_exams)} courses...")

        for course_data in courses_with_exams:
            course_id = course_data['course_id']
            exam_info = course_data['exam_info']

            try:
                result = self.create_exam_announcement(course_id, exam_info, template)
                if result:
                    stats['successful'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"Error creating announcement for course {course_id}: {e}")
                stats['failed'] += 1

        print(f"\nAnnouncement creation completed:")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")

        return stats

    def update_announcement(self, course_id: int, announcement_id: int,
                          title: Optional[str] = None, message: Optional[str] = None) -> Optional[Dict]:
        """
        Update an existing announcement

        Args:
            course_id: Course ID
            announcement_id: Announcement ID
            title: New title (optional)
            message: New message (optional)

        Returns:
            Updated announcement data or None if error
        """
        update_data = {}
        if title:
            update_data['title'] = title
        if message:
            update_data['message'] = message

        if not update_data:
            print("No updates provided")
            return None

        result = self.canvas._make_request(
            'PUT',
            f'courses/{course_id}/discussion_topics/{announcement_id}',
            update_data
        )

        if result:
            print(f"✅ Announcement {announcement_id} updated")
        else:
            print(f"❌ Failed to update announcement {announcement_id}")

        return result