#!/usr/bin/env python3
"""
Cinema Culture Appreciation Course - Email Reminder System
This script sends reminder emails to students with incomplete assignments.


"""

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def create_reminder_email_script():
    """
    Create email reminder script for students with incomplete assignments
    """
    
    # Load user configuration data
    with open(os.path.join(os.path.dirname(__file__), 'files', 'user_config.json'), 'r') as f:
        data = json.load(f)
    
    # Print system title and separator
    print("📧 Email Reminder System - Cinema Culture Appreciation")
    print("=" * 60)
    
    # Email template function - creates personalized reminder email content
    def create_email_content(student_name, missing_assignments, completion_rate):
        """
        Create email content template
        
        Args:
            student_name
            missing_assignments
            completion_rate
        """
        # Set email subject
        subject = "Reminder: Missing Assignments in Cinema Culture Appreciation"
        
        # Create email body content with personalized information
        body = f"""
Dear {student_name},

I hope this email finds you well. I am writing to remind you about some missing assignments in our Cinema Culture Appreciation (FILM101) course.

📚 MISSING ASSIGNMENTS:
{chr(10).join([f"• {assignment}" for assignment in missing_assignments])}

📊 CURRENT STATUS:
• Completion Rate: {completion_rate}
• Class Average: 64.3%

🎯 NEXT STEPS:
Please complete your missing assignments as soon as possible. Each assignment is designed to enhance your understanding of cinema culture and contributes to your overall grade.

📅 UPCOMING DEADLINES:
• Assignment 5: International Cinema (Due: Feb 12, 2025)
• Assignment 6: Contemporary Cinema Trends (Due: Feb 19, 2025)

If you need any assistance or have questions about the assignments, please don't hesitate to reach out during office hours or via email.

Best regards,
Course Instructor
Cinema Culture Appreciation (FILM101)
📧 mcpcanvasadmin2@mcp.com
"""
        # Return email subject and body
        return subject, body
    
    # Process students with incomplete assignments
    students_to_email = []
    
    # Iterate through all students and filter those who need reminder emails
    for student in data['students']:
        # Check if student is in the list of students with incomplete assignments
        if student['email'] in data['statistics']['students_with_incomplete_assignments']:
            # Find assignments with score 0 (i.e., incomplete assignments)
            missing_assignments = [name for name, score in student['assignment_scores'].items() if score == 0]
            
            # Create personalized email content for this student
            subject, body = create_email_content(student['name'], missing_assignments, student['completion_rate'])
            
            # Add student information to the email sending list
            students_to_email.append({
                'name': student['name'],
                'email': student['email'],
                'subject': subject,
                'body': body,
                'missing_count': len(missing_assignments),
                'missing_assignments': missing_assignments
            })
    
    # Display email summary information
    print(f"📊 EMAIL SUMMARY:")
    print(f"Total students: {data['statistics']['total_students']}")
    print(f"Students needing reminders: {len(students_to_email)}")
    print(f"Students with complete assignments: {len(data['statistics']['fully_completed_students'])}")
    print()
    
    # Display list of students who will receive reminder emails
    print("🎯 STUDENTS TO RECEIVE REMINDER EMAILS:")
    print("-" * 60)
    
    # Iterate through the list of students to send emails and display detailed information
    for i, student_info in enumerate(students_to_email, 1):
        # Determine priority based on number of missing assignments
        urgency = ""
        if student_info['missing_count'] >= 4:
            urgency = " ⚠️ HIGH PRIORITY" 
        elif student_info['missing_count'] >= 2:
            urgency = " ⚠️ MEDIUM PRIORITY" 
        
        # Print student information and missing assignment details
        print(f"{i}. {student_info['name']} ({student_info['email']})")
        print(f"   Missing: {student_info['missing_count']} assignments{urgency}")
        print(f"   Assignments: {', '.join([name.split(': ')[0] for name in student_info['missing_assignments']])}")
        print()
    
    # Create individual email files for each student for review
    email_folder = os.path.join(os.path.dirname(__file__), 'initial_workspace', 'reminder_emails')
    os.makedirs(email_folder, exist_ok=True)
    
    # Create individual email files for each student who needs to receive emails
    for student_info in students_to_email:
        # Create filename-safe version of student name (replace spaces and commas)
        safe_name = student_info['name'].replace(' ', '_').replace(',', '')
        filename = f"{email_folder}reminder_email_{safe_name}.txt"
        
        # Write email file with header information and body
        with open(filename, 'w') as f:
            f.write(f"TO: {student_info['email']}\n")
            f.write(f"FROM: mcpcanvasadmin2@mcp.com\n")
            f.write(f"SUBJECT: {student_info['subject']}\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(student_info['body'])
    
    # Display email files creation completion information
    print(f"📁 Individual email files created in: {email_folder}")
    print()
    
    # Create batch email sending script
    batch_script = f"""#!/usr/bin/env python3
# Batch Email Sender for Cinema Culture Appreciation Course
# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_reminder_emails():
    # email configuration (update with actual SMTP settings)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "mcpcanvasadmin2@mcp.com"
    sender_password = "your_password_here"
    
    # email data to be sent
    emails_to_send = {json.dumps(students_to_email, indent=2)}
    
    # Initialize success and failure counters
    success_count = 0
    failed_count = 0
    
    print("📧 Starting batch email sending...")
    
    # Try to connect to SMTP server and send emails
    try:
        server = smtplib.SMTP(smtp_server, smtp_port) 
        server.starttls()  
        server.login(sender_email, sender_password)  
        
        # Iterate through each student to send personalized emails
        for student_info in emails_to_send:
            try:
                # Create email message object
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = student_info['email']
                msg['Subject'] = student_info['subject']
                
                # Add email body
                msg.attach(MIMEText(student_info['body'], 'plain'))
                
                # Send email
                server.send_message(msg)
                print(f"✅ Email sent to {{student_info['name']}} ({{student_info['email']}})")
                success_count += 1
                
            except Exception as e:
                # Handle sending failure
                print(f"❌ Failed to send email to {{student_info['name']}}: {{e}}")
                failed_count += 1
        
        server.quit()  
        
    except Exception as e:
        # Handle SMTP connection failure
        print(f"❌ SMTP connection failed: {{e}}")
        print("Please check your email configuration settings.")
    
    # Display email sending results summary
    print(f"\\n📊 EMAIL SENDING SUMMARY:")
    print(f"✅ Successfully sent: {{success_count}} emails")
    print(f"❌ Failed to send: {{failed_count}} emails")

if __name__ == "__main__":
    send_reminder_emails()
"""
    
    # Save batch email sending script to file
    batch_script_path = f"{email_folder}send_batch_reminders.py"
    with open(batch_script_path, 'w') as f:
        f.write(batch_script)
    
    # Display script creation completion information and next steps
    print(f"📧 Batch email script created: {batch_script_path}")
    print()
    print("⚠️  NOTE: To actually send emails, you need to:")
    print("1. Update SMTP server settings in the batch script")
    print("2. Configure authentication credentials")
    print("3. Run the batch script: python send_batch_reminders.py")
    print()
    
    # Generate final summary report
    print("📋 FINAL SUMMARY REPORT:")
    print("=" * 60)
    print(f"Course: Cinema Culture Appreciation (FILM101)")
    print(f"Total Students: {data['statistics']['total_students']}")
    print(f"Class Average: {data['statistics']['class_average']:.1f}%")
    print(f"Students with Complete Work: {len(data['statistics']['fully_completed_students'])}")
    print(f"Students Needing Reminders: {len(students_to_email)}")
    print()
    
    # Display list of students with complete assignments
    print("🏆 STUDENTS WITH COMPLETE ASSIGNMENTS:")
    for email in data['statistics']['fully_completed_students']:
        student_name = next((s['name'] for s in data['students'] if s['email'] == email), email)
        print(f"  ✅ {student_name}")
    print()
    
    # Display list of students with incomplete assignments and their priority
    print("⚠️  STUDENTS WITH INCOMPLETE ASSIGNMENTS:")
    for student_info in students_to_email:
        # Determine priority indicator based on number of missing assignments
        priority = ""
        if student_info['missing_count'] >= 4:
            priority = " (HIGH PRIORITY)" 
        elif student_info['missing_count'] >= 2:
            priority = " (MEDIUM PRIORITY)" 
        print(f"  📧 {student_info['name']} - Missing {student_info['missing_count']} assignments{priority}")

# Program entry point - execute main function when running this script directly
if __name__ == "__main__":
    create_reminder_email_script()