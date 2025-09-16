#!/usr/bin/env python3
"""
Cinema Culture Appreciation Course - Email Reminder System
This script sends reminder emails to students with incomplete assignments.

电影文化欣赏课程 - 邮件提醒系统
此脚本向未完成作业的学生发送提醒邮件。
"""

import json  # 用于处理JSON数据格式
import smtplib  # 用于发送邮件的SMTP库
from email.mime.text import MIMEText  # 用于创建纯文本邮件
from email.mime.multipart import MIMEMultipart  # 用于创建多部分邮件
from datetime import datetime  # 用于处理日期和时间

def create_reminder_email_script():
    """
    创建邮件提醒脚本，用于向未完成作业的学生发送提醒邮件
    Create email reminder script for students with incomplete assignments
    """
    
    # 加载用户配置数据
    # Load user configuration data
    with open(os.path.join(os.path.dirname(__file__), 'files', 'user_config.json'), 'r') as f:
        data = json.load(f)
    
    # 打印系统标题和分隔线
    # Print system title and separator
    print("📧 Email Reminder System - Cinema Culture Appreciation")
    print("=" * 60)
    
    # 邮件模板函数 - 用于创建个性化的提醒邮件内容
    # Email template function - creates personalized reminder email content
    def create_email_content(student_name, missing_assignments, completion_rate):
        """
        创建邮件内容模板
        Create email content template
        
        Args:
            student_name: 学生姓名
            missing_assignments: 缺失的作业列表
            completion_rate: 完成率
        """
        # 设置邮件主题
        # Set email subject
        subject = "Reminder: Missing Assignments in Cinema Culture Appreciation"
        
        # 创建邮件正文内容，包含个性化信息
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
        # 返回邮件主题和正文
        # Return email subject and body
        return subject, body
    
    # 处理未完成作业的学生数据
    # Process students with incomplete assignments
    students_to_email = []
    
    # 遍历所有学生，筛选出需要发送提醒邮件的学生
    # Iterate through all students and filter those who need reminder emails
    for student in data['students']:
        # 检查学生是否在未完成作业的学生列表中
        # Check if student is in the list of students with incomplete assignments
        if student['email'] in data['statistics']['students_with_incomplete_assignments']:
            # 找出得分为0的作业（即未完成的作业）
            # Find assignments with score 0 (i.e., incomplete assignments)
            missing_assignments = [name for name, score in student['assignment_scores'].items() if score == 0]
            
            # 为该学生创建个性化的邮件内容
            # Create personalized email content for this student
            subject, body = create_email_content(student['name'], missing_assignments, student['completion_rate'])
            
            # 将学生信息添加到待发送邮件列表
            # Add student information to the email sending list
            students_to_email.append({
                'name': student['name'],
                'email': student['email'],
                'subject': subject,
                'body': body,
                'missing_count': len(missing_assignments),
                'missing_assignments': missing_assignments
            })
    
    # 显示邮件发送摘要信息
    # Display email summary information
    print(f"📊 EMAIL SUMMARY:")
    print(f"Total students: {data['statistics']['total_students']}")
    print(f"Students needing reminders: {len(students_to_email)}")
    print(f"Students with complete assignments: {len(data['statistics']['fully_completed_students'])}")
    print()
    
    # 显示需要接收提醒邮件的学生列表
    # Display list of students who will receive reminder emails
    print("🎯 STUDENTS TO RECEIVE REMINDER EMAILS:")
    print("-" * 60)
    
    # 遍历待发送邮件的学生列表，显示详细信息
    # Iterate through the list of students to send emails and display detailed information
    for i, student_info in enumerate(students_to_email, 1):
        # 根据缺失作业数量确定优先级
        # Determine priority based on number of missing assignments
        urgency = ""
        if student_info['missing_count'] >= 4:
            urgency = " ⚠️ HIGH PRIORITY"  # 高优先级
        elif student_info['missing_count'] >= 2:
            urgency = " ⚠️ MEDIUM PRIORITY"  # 中等优先级
        
        # 打印学生信息和缺失作业详情
        # Print student information and missing assignment details
        print(f"{i}. {student_info['name']} ({student_info['email']})")
        print(f"   Missing: {student_info['missing_count']} assignments{urgency}")
        print(f"   Assignments: {', '.join([name.split(': ')[0] for name in student_info['missing_assignments']])}")
        print()
    
    # 为每个学生创建单独的邮件文件供审查
    # Create individual email files for each student for review
    email_folder = os.path.join(os.path.dirname(__file__), 'initial_workspace', 'reminder_emails')
    import os  # 导入os模块用于文件操作
    os.makedirs(email_folder, exist_ok=True)  # 创建邮件文件夹，如果不存在的话
    
    # 为每个需要发送邮件的学生创建单独的邮件文件
    # Create individual email files for each student who needs to receive emails
    for student_info in students_to_email:
        # 创建文件名安全版本的学生姓名（替换空格和逗号）
        # Create filename-safe version of student name (replace spaces and commas)
        safe_name = student_info['name'].replace(' ', '_').replace(',', '')
        filename = f"{email_folder}reminder_email_{safe_name}.txt"
        
        # 写入邮件文件，包含邮件头信息和正文
        # Write email file with header information and body
        with open(filename, 'w') as f:
            f.write(f"TO: {student_info['email']}\n")
            f.write(f"FROM: mcpcanvasadmin2@mcp.com\n")
            f.write(f"SUBJECT: {student_info['subject']}\n")
            f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(student_info['body'])
    
    # 显示邮件文件创建完成信息
    # Display email files creation completion information
    print(f"📁 Individual email files created in: {email_folder}")
    print()
    
    # 创建批量邮件发送脚本
    # Create batch email sending script
    batch_script = f"""#!/usr/bin/env python3
# Batch Email Sender for Cinema Culture Appreciation Course
# 电影文化欣赏课程批量邮件发送器
# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_reminder_emails():
    # 邮件配置（需要更新为实际的SMTP设置）
    # Email configuration (update with actual SMTP settings)
    smtp_server = "smtp.gmail.com"  # 更新为实际的SMTP服务器
    smtp_port = 587
    sender_email = "mcpcanvasadmin2@mcp.com"  # 更新为实际的邮箱地址
    sender_password = "your_password_here"  # 更新为实际的密码
    
    # 要发送的邮件数据
    # Email data to be sent
    emails_to_send = {json.dumps(students_to_email, indent=2)}
    
    # 初始化成功和失败计数器
    # Initialize success and failure counters
    success_count = 0
    failed_count = 0
    
    print("📧 Starting batch email sending...")
    
    # 尝试连接SMTP服务器并发送邮件
    # Try to connect to SMTP server and send emails
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)  # 连接SMTP服务器
        server.starttls()  # 启用TLS加密
        server.login(sender_email, sender_password)  # 登录邮箱
        
        # 遍历每个学生发送个性化邮件
        # Iterate through each student to send personalized emails
        for student_info in emails_to_send:
            try:
                # 创建邮件消息对象
                # Create email message object
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = student_info['email']
                msg['Subject'] = student_info['subject']
                
                # 添加邮件正文
                # Add email body
                msg.attach(MIMEText(student_info['body'], 'plain'))
                
                # 发送邮件
                # Send email
                server.send_message(msg)
                print(f"✅ Email sent to {{student_info['name']}} ({{student_info['email']}})")
                success_count += 1
                
            except Exception as e:
                # 处理发送失败的情况
                # Handle sending failure
                print(f"❌ Failed to send email to {{student_info['name']}}: {{e}}")
                failed_count += 1
        
        server.quit()  # 关闭SMTP连接
        
    except Exception as e:
        # 处理SMTP连接失败的情况
        # Handle SMTP connection failure
        print(f"❌ SMTP connection failed: {{e}}")
        print("Please check your email configuration settings.")
    
    # 显示邮件发送结果摘要
    # Display email sending results summary
    print(f"\\n📊 EMAIL SENDING SUMMARY:")
    print(f"✅ Successfully sent: {{success_count}} emails")
    print(f"❌ Failed to send: {{failed_count}} emails")

if __name__ == "__main__":
    send_reminder_emails()
"""
    
    # 保存批量邮件发送脚本到文件
    # Save batch email sending script to file
    batch_script_path = f"{email_folder}send_batch_reminders.py"
    with open(batch_script_path, 'w') as f:
        f.write(batch_script)
    
    # 显示脚本创建完成信息和后续步骤说明
    # Display script creation completion information and next steps
    print(f"📧 Batch email script created: {batch_script_path}")
    print()
    print("⚠️  NOTE: To actually send emails, you need to:")
    print("1. Update SMTP server settings in the batch script")
    print("2. Configure authentication credentials")
    print("3. Run the batch script: python send_batch_reminders.py")
    print()
    
    # 生成最终摘要报告
    # Generate final summary report
    print("📋 FINAL SUMMARY REPORT:")
    print("=" * 60)
    print(f"Course: Cinema Culture Appreciation (FILM101)")
    print(f"Total Students: {data['statistics']['total_students']}")
    print(f"Class Average: {data['statistics']['class_average']:.1f}%")
    print(f"Students with Complete Work: {len(data['statistics']['fully_completed_students'])}")
    print(f"Students Needing Reminders: {len(students_to_email)}")
    print()
    
    # 显示已完成作业的学生列表
    # Display list of students with complete assignments
    print("🏆 STUDENTS WITH COMPLETE ASSIGNMENTS:")
    for email in data['statistics']['fully_completed_students']:
        student_name = next((s['name'] for s in data['students'] if s['email'] == email), email)
        print(f"  ✅ {student_name}")
    print()
    
    # 显示未完成作业的学生列表及其优先级
    # Display list of students with incomplete assignments and their priority
    print("⚠️  STUDENTS WITH INCOMPLETE ASSIGNMENTS:")
    for student_info in students_to_email:
        # 根据缺失作业数量确定优先级标识
        # Determine priority indicator based on number of missing assignments
        priority = ""
        if student_info['missing_count'] >= 4:
            priority = " (HIGH PRIORITY)"  # 高优先级
        elif student_info['missing_count'] >= 2:
            priority = " (MEDIUM PRIORITY)"  # 中等优先级
        print(f"  📧 {student_info['name']} - Missing {student_info['missing_count']} assignments{priority}")

# 程序入口点 - 当直接运行此脚本时执行主函数
# Program entry point - execute main function when running this script directly
if __name__ == "__main__":
    create_reminder_email_script()