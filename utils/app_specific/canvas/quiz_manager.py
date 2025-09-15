#!/usr/bin/env python3
"""
Canvas Quiz/Exam Manager

This module provides functionality for managing Canvas quizzes and exams.
Extracted from tasks/finalpool/canvas-arrange-exam for reuse.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from .api_client import CanvasAPI


class QuizManager:
    """Manager for Canvas quizzes and exams"""

    def __init__(self, canvas_api: CanvasAPI):
        """
        Initialize Quiz Manager

        Args:
            canvas_api: CanvasAPI instance
        """
        self.canvas = canvas_api

    def create_quiz(self, course_id: int, title: str, description: str = "",
                   quiz_type: str = "assignment", time_limit: Optional[int] = None,
                   shuffle_answers: bool = False, allowed_attempts: int = 1,
                   scoring_policy: str = "keep_highest", due_at: Optional[str] = None,
                   unlock_at: Optional[str] = None, lock_at: Optional[str] = None,
                   published: bool = False, points_possible: int = 100) -> Optional[Dict]:
        """
        Create a quiz/exam in a course

        Args:
            course_id: Course ID
            title: Quiz title
            description: Quiz description/instructions
            quiz_type: Type of quiz ('practice_quiz', 'assignment', 'graded_survey', 'survey')
            time_limit: Time limit in minutes (None for no limit)
            shuffle_answers: Whether to shuffle answer choices
            allowed_attempts: Number of attempts allowed (-1 for unlimited)
            scoring_policy: How to handle multiple attempts ('keep_highest', 'keep_latest', 'keep_average')
            due_at: Due date in ISO format
            unlock_at: When quiz becomes available in ISO format
            lock_at: When quiz locks in ISO format
            published: Whether to publish immediately
            points_possible: Total points for the quiz

        Returns:
            Quiz data or None if error
        """
        quiz_data = {
            'quiz': {
                'title': title,
                'description': description,
                'quiz_type': quiz_type,
                'time_limit': time_limit,
                'shuffle_answers': shuffle_answers,
                'allowed_attempts': allowed_attempts,
                'scoring_policy': scoring_policy,
                'published': published,
                'points_possible': points_possible
            }
        }

        if due_at:
            quiz_data['quiz']['due_at'] = due_at
        if unlock_at:
            quiz_data['quiz']['unlock_at'] = unlock_at
        if lock_at:
            quiz_data['quiz']['lock_at'] = lock_at

        result = self.canvas._make_request(
            'POST',
            f'courses/{course_id}/quizzes',
            quiz_data
        )

        if result:
            print(f"✅ Quiz created: {title} (ID: {result.get('id')})")
        else:
            print(f"❌ Failed to create quiz: {title}")

        return result

    def create_exam(self, course_id: int, exam_info: Dict[str, Any]) -> Optional[Dict]:
        """
        Create an exam (formal quiz) with standard exam settings

        Args:
            course_id: Course ID
            exam_info: Dictionary containing exam information:
                - title: Exam title
                - exam_type: Type of exam (e.g., "Final Exam", "Midterm")
                - exam_date: Date of exam (used for due_at)
                - exam_time: Time of exam
                - duration: Duration in minutes
                - points: Total points (default 100)
                - instructions: Exam instructions (optional)
                - password: Access code for the exam (optional)

        Returns:
            Quiz data or None if error
        """
        # Parse exam date and time for due_at
        due_at = None
        if 'exam_date' in exam_info and 'exam_time' in exam_info:
            try:
                # Combine date and time
                datetime_str = f"{exam_info['exam_date']} {exam_info['exam_time']}"
                exam_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                due_at = exam_datetime.isoformat() + 'Z'
            except:
                pass

        # Build instructions
        instructions = exam_info.get('instructions', '')
        if not instructions:
            instructions = f"""
<p><strong>{exam_info.get('exam_type', 'Exam')} Instructions</strong></p>
<ul>
<li>Date: {exam_info.get('exam_date', 'TBD')}</li>
<li>Time: {exam_info.get('exam_time', 'TBD')}</li>
<li>Duration: {exam_info.get('duration', 'TBD')}</li>
<li>Location: {exam_info.get('exam_location', 'Online')}</li>
</ul>
<p><strong>Important Notes:</strong></p>
<ul>
<li>This is a timed exam. Once you begin, you must complete it within the time limit.</li>
<li>Make sure you have a stable internet connection before starting.</li>
<li>You are allowed only one attempt.</li>
<li>Good luck!</li>
</ul>
"""

        # Extract duration in minutes
        duration_str = exam_info.get('duration', '120 minutes')
        try:
            duration_minutes = int(''.join(filter(str.isdigit, duration_str)))
        except:
            duration_minutes = 120  # Default 2 hours

        # Create the exam as a quiz
        quiz_data = self.create_quiz(
            course_id=course_id,
            title=exam_info.get('title', exam_info.get('exam_type', 'Exam')),
            description=instructions,
            quiz_type='assignment',  # Graded quiz
            time_limit=duration_minutes,
            shuffle_answers=True,  # Shuffle for security
            allowed_attempts=1,  # Only one attempt for exams
            scoring_policy='keep_highest',
            due_at=due_at,
            published=False,  # Don't publish immediately
            points_possible=exam_info.get('points', 100)
        )

        # If password is provided, update quiz with access code
        if quiz_data and 'password' in exam_info:
            self.update_quiz_access_code(course_id, quiz_data['id'], exam_info['password'])

        return quiz_data

    def update_quiz_access_code(self, course_id: int, quiz_id: int, access_code: str) -> bool:
        """
        Set an access code (password) for a quiz

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            access_code: Access code/password

        Returns:
            True if successful, False otherwise
        """
        update_data = {
            'quiz': {
                'access_code': access_code
            }
        }

        result = self.canvas._make_request(
            'PUT',
            f'courses/{course_id}/quizzes/{quiz_id}',
            update_data
        )

        return bool(result)

    def add_quiz_question(self, course_id: int, quiz_id: int,
                         question_name: str, question_text: str,
                         question_type: str = "multiple_choice_question",
                         points_possible: int = 1, answers: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        Add a question to a quiz

        Args:
            course_id: Course ID
            quiz_id: Quiz ID
            question_name: Question name/title
            question_text: Question text/prompt
            question_type: Type of question (multiple_choice_question, true_false_question, etc.)
            points_possible: Points for this question
            answers: List of answer dictionaries with 'answer_text' and 'answer_weight' keys

        Returns:
            Question data or None if error
        """
        question_data = {
            'question': {
                'question_name': question_name,
                'question_text': question_text,
                'question_type': question_type,
                'points_possible': points_possible
            }
        }

        if answers:
            question_data['question']['answers'] = answers

        result = self.canvas._make_request(
            'POST',
            f'courses/{course_id}/quizzes/{quiz_id}/questions',
            question_data
        )

        return result

    def list_quizzes(self, course_id: int) -> List[Dict]:
        """
        List all quizzes for a course

        Args:
            course_id: Course ID

        Returns:
            List of quiz data
        """
        params = {'per_page': 100}

        result = self.canvas._make_request(
            'GET',
            f'courses/{course_id}/quizzes',
            params=params
        )

        return result if result else []

    def get_quiz(self, course_id: int, quiz_id: int) -> Optional[Dict]:
        """
        Get details of a specific quiz

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            Quiz data or None if not found
        """
        return self.canvas._make_request(
            'GET',
            f'courses/{course_id}/quizzes/{quiz_id}'
        )

    def publish_quiz(self, course_id: int, quiz_id: int) -> bool:
        """
        Publish a quiz to make it available to students

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            True if successful, False otherwise
        """
        update_data = {
            'quiz': {
                'published': True
            }
        }

        result = self.canvas._make_request(
            'PUT',
            f'courses/{course_id}/quizzes/{quiz_id}',
            update_data
        )

        if result:
            print(f"✅ Quiz {quiz_id} published")
            return True
        else:
            print(f"❌ Failed to publish quiz {quiz_id}")
            return False

    def delete_quiz(self, course_id: int, quiz_id: int) -> bool:
        """
        Delete a quiz

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            True if successful, False otherwise
        """
        result = self.canvas._make_request(
            'DELETE',
            f'courses/{course_id}/quizzes/{quiz_id}'
        )

        if result:
            print(f"✅ Quiz {quiz_id} deleted")
            return True
        else:
            print(f"❌ Failed to delete quiz {quiz_id}")
            return False

    def batch_create_exams(self, courses_with_exams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create exams for multiple courses

        Args:
            courses_with_exams: List of dictionaries with 'course_id' and 'exam_info' keys

        Returns:
            Statistics dictionary with counts and created exam IDs
        """
        stats = {
            'successful': 0,
            'failed': 0,
            'total': len(courses_with_exams),
            'created_exams': []
        }

        print(f"Creating exams for {len(courses_with_exams)} courses...")

        for course_data in courses_with_exams:
            course_id = course_data['course_id']
            exam_info = course_data['exam_info']

            try:
                result = self.create_exam(course_id, exam_info)
                if result:
                    stats['successful'] += 1
                    stats['created_exams'].append({
                        'course_id': course_id,
                        'quiz_id': result['id'],
                        'title': result['title']
                    })
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"Error creating exam for course {course_id}: {e}")
                stats['failed'] += 1

        print(f"\nExam creation completed:")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")

        return stats