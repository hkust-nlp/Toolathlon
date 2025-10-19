#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exam Notification Email Script
Send exam notification emails using Poste.io SMTP/IMAP services

New Feature: Distraction Email Injection
=======================================
To simulate a realistic inbox, random irrelevant distraction emails can be injected before and after the exam notification email.

Distraction Email Types (25 types):
📦 Online Shopping: Amazon, eBay, Target, Etsy
🎬 Entertainment Media: Netflix, YouTube, Spotify, TikTok
👥 Social Networks: LinkedIn, Facebook, Instagram, Twitter
💰 Financial & Banking: Chase Bank, PayPal, Wells Fargo
🍕 Food Delivery: Uber Eats, DoorDash, Grubhub
✈️ Travel & Accommodation: Booking.com, Airbnb, Delta Airlines
📰 News: The New York Times, Medium
🎯 Deals: Groupon, LivingSocial
💬 Community Forums: Reddit, Stack Overflow
💪 Health & Fitness: MyFitnessPal, Headspace
🎮 Gaming: Steam, Twitch

Email count and time distribution:
- Before exam notification: 6-12 distraction emails, randomly injected 0.5-5 days before the exam message
- After exam notification: 4-8 emails, injected 1-48 hours after the exam message
- Total: 10-20 distraction emails + 1 genuine exam notification

Usage:
```python
# Recommended: Clear inbox + inject distractions (for realistic simulation)
inject_exam_emails_from_config('config.json', clear_inbox=True, add_distractions=True)

# Only inject the exam mail, no distraction
inject_exam_emails_from_config('config.json', clear_inbox=True, add_distractions=False)
```

Test mode:
```bash
python send_exam_notification_smtp.py --test
```

Sample output:
```
📋 Mode: Clear inbox and inject new emails
🎭 Distraction mode: Enabled - Add distraction emails for realism

🎭 Step 1: Injecting distraction emails (before exam notice)...
📮 Injecting 9 distraction emails (before exam)...
  ✅ Amazon: Your order has been shipped! Track your package... (11-27 09:15)
  ✅ Chase Bank: Account Alert: Large purchase detected... (11-28 14:32)
  ✅ Netflix: New shows added to your list - Watch now!... (11-29 11:45)
  ✅ MyFitnessPal: Weekly progress: You're on track! 💪... (11-29 19:20)
  ✅ Instagram: Your Story highlights got 50+ views! 📸... (11-30 08:30)
  ✅ Steam: Weekend Deal: 75% off indie games! 🎮... (11-30 16:45)
  ✅ Booking.com: Price drop alert! Save $45 on your Tokyo tri... (11-30 22:10)
  ✅ Target: Weekend sale: Up to 50% off home essentials... (12-01 06:22)
  ✅ PayPal: You've received $25.00 from Mom... (12-01 07:55)

📧 Step 2: Injecting exam notification email...
✅ Email injection successful!

🎭 Step 3: Injecting distraction emails (after exam notice)...
📮 Injecting 6 distraction emails (after exam)...
  ✅ DoorDash: Your order from Thai Garden is on the way! 🚗... (12-01 12:30)
  ✅ Facebook: You have 3 friend requests and 8 notification... (12-01 15:45)
  ✅ YouTube: Your video got 1,000 views! 🎉... (12-01 20:15)
  ✅ Reddit: Trending posts you might have missed... (12-02 08:30)
  ✅ LinkedIn: Someone viewed your profile... (12-02 14:20)
  ✅ Twitch: Your favorite streamer is live! 🔴... (12-02 19:45)

🎭 Distraction emails added for a realistic inbox
```

Total emails: 15 distraction + 1 exam notification = 16 emails
"""

import smtplib
import imaplib
import json
import logging
import time
import ssl
import email
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class ExamNotificationSender:
    """Exam notification email sender"""
    
    def __init__(self, config_file: str):
        """
        Initialize email sender
        :param config_file: Config file path
        """
        self.logger = logging.getLogger('ExamNotificationSender')
        self.setup_logging()
        self.config = self._load_config(config_file)
        self.smtp_connection = None
        self.imap_connection = None
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load config from file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info("Config file loaded successfully")
            return config
        except Exception as e:
            raise Exception(f"Failed to load config file: {e}")
    
    def get_recipient_credentials(self) -> Dict[str, str]:
        """Get recipient mailbox credentials"""
        try:
            recipient = self.config['recipient']
            if 'password' in recipient:
                credentials = {
                    'email': recipient['email'],
                    'password': recipient['password']
                }
                self.logger.info(f"Successfully got credentials for recipient: {recipient['email']}")
                return credentials
            else:
                self.logger.warning("Recipient config missing password")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to get recipient credentials: {e}")
            return None
    
    def setup_logging(self):
        """Set up logger system"""
        log_file = 'email_send.log'
        log_level = logging.INFO
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.setLevel(log_level)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Logging system initialized")
    
    def connect_smtp(self) -> bool:
        """Connect to SMTP server"""
        try:
            server_config = self.config['server_config']
            self.logger.info(f"Connecting to SMTP server: {server_config['smtp_server']}:{server_config['smtp_port']}")
            
            self.smtp_connection = smtplib.SMTP(
                server_config['smtp_server'],
                server_config['smtp_port'],
                timeout=server_config.get('timeout', 30)
            )
            self.smtp_connection.set_debuglevel(1)
            self.smtp_connection.ehlo()
            
            if self.smtp_connection.has_extn('STARTTLS'):
                self.logger.info("Server supports STARTTLS, enabling...")
                self.smtp_connection.starttls()
                self.smtp_connection.ehlo()
                self.logger.info("STARTTLS enabled")
            else:
                self.logger.info("Server does not support STARTTLS")
            
            self.logger.info("SMTP server connected")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SMTP server: {e}")
            return False
    
    def authenticate_smtp(self) -> bool:
        """SMTP server authentication"""
        try:
            sender_account = self.config['sender_account']
            self.logger.info(f"Authenticating SMTP account: {sender_account['email']}")
            
            if not self.smtp_connection.has_extn('AUTH'):
                self.logger.warning("Server doesn't support AUTH extension, will try sending without auth...")
                return True
            
            self.smtp_connection.login(
                sender_account['email'],
                sender_account['password']
            )
            self.logger.info("SMTP authentication succeeded")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            self.logger.info("Trying sending mail without authentication...")
            return True
    
    def load_email_template(self) -> str:
        """Load email template"""
        try:
            template_file = self.config['email_content']['template_file']
            template_path = Path(__file__).parent.parent / 'files' / template_file
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            self.logger.info("Email template loaded")
            return template
        except Exception as e:
            self.logger.error(f"Failed to load email template: {e}")
            default_template = """Dear {recipient_name},

This is a notification about your upcoming exam:

Course: {course_name}
Date: {exam_date}
Time: {exam_time}
Location: {exam_location}
Type: {exam_type}
Duration: {duration}

Please arrive 15 minutes before the exam time.

Best regards,
Course Instructor"""
            return default_template
    
    def format_email_content(self, template: str) -> str:
        """Format exam email content with config"""
        try:
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            exam_info = self.config['email_content']['exam_info']
            content = template.format(
                recipient_name=recipient['name'],
                course_name=exam_info['course_name'],
                exam_type=exam_info['exam_type'],
                exam_date=exam_info['exam_date'],
                exam_time=exam_info['exam_time'],
                duration=exam_info['duration'],
                exam_location=exam_info['exam_location'],
                sender_email=sender_account['email'],
                sender_name=sender_account['name'],
                send_time=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            self.logger.info("Email content formatted")
            return content
        except Exception as e:
            self.logger.error(f"Failed to format email content: {e}")
            raise
    
    def send_email(self, content: str) -> bool:
        """Send mail"""
        try:
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            subject = self.config['email_content']['subject']
            
            msg = MIMEMultipart()
            msg['From'] = f"{sender_account['name']} <{sender_account['email']}>"
            msg['To'] = f"{recipient['name']} <{recipient['email']}>"
            msg['Subject'] = subject
            
            text_part = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            self.logger.info(f"Sending mail to: {recipient['email']}")
            self.smtp_connection.send_message(msg)
            
            self.logger.info("Mail sent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send mail: {e}")
            return False
    
    def connect_imap(self) -> bool:
        """Connect to IMAP server"""
        try:
            server_config = self.config['server_config']
            self.logger.info(f"Connecting to IMAP server: {server_config['imap_server']}:{server_config['imap_port']}")
            if server_config.get('use_ssl', False):
                self.imap_connection = imaplib.IMAP4_SSL(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            else:
                self.imap_connection = imaplib.IMAP4(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            self.logger.info("IMAP server connected")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to IMAP server: {e}")
            return False
    
    def authenticate_imap(self) -> bool:
        """Authenticate IMAP server"""
        try:
            sender_account = self.config['sender_account']
            self.logger.info(f"Authenticate IMAP account: {sender_account['email']}")
            self.imap_connection.login(
                sender_account['email'],
                sender_account['password']
            )
            self.logger.info("IMAP authentication succeeded")
            return True
        except Exception as e:
            self.logger.error(f"IMAP authentication failed: {e}")
            return False
    
    def delete_recipient_inbox_emails(self) -> bool:
        """Delete all emails in recipient inbox"""
        try:
            recipient_credentials = self.get_recipient_credentials()
            if not recipient_credentials:
                self.logger.warning("Failed to get recipient credentials, skipping deletion")
                return False
            
            server_config = self.config['server_config']
            self.logger.info(f"Connecting to recipient IMAP server: {server_config['imap_server']}:{server_config['imap_port']}")
            
            if server_config.get('use_ssl', False):
                recipient_imap = imaplib.IMAP4_SSL(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            else:
                recipient_imap = imaplib.IMAP4(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            
            recipient_imap.login(
                recipient_credentials['email'],
                recipient_credentials['password']
            )
            
            self.logger.info("Recipient IMAP connected")
            recipient_imap.select('INBOX')
            _, message_numbers = recipient_imap.search(None, 'ALL')
            
            if message_numbers[0]:
                email_nums = message_numbers[0].split()
                total_emails = len(email_nums)
                if total_emails > 0:
                    self.logger.info(f"Found {total_emails} emails, deleting...")
                    for email_num in email_nums:
                        recipient_imap.store(email_num, '+FLAGS', '\\Deleted')
                    recipient_imap.expunge()
                    self.logger.info(f"Deleted {total_emails} email(s) in inbox")
                else:
                    self.logger.info("Inbox empty, nothing to delete")
            else:
                self.logger.info("Inbox empty")
            
            recipient_imap.close()
            recipient_imap.logout()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete recipient inbox emails: {e}")
            return False
    
    def verify_email_sent(self) -> bool:
        """Verify that mail was sent successfully (via IMAP Sent box)"""
        try:
            self.logger.info("Verifying mail send status...")
            self.imap_connection.select('Sent')
            search_criteria = f'TO "{self.config["recipient"]["email"]}"'
            _, message_numbers = self.imap_connection.search(None, search_criteria)
            if message_numbers[0]:
                latest_email_num = message_numbers[0].split()[-1]
                _, msg_data = self.imap_connection.fetch(latest_email_num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                subject = email_message.get('Subject', '')
                expected_subject = self.config['email_content']['subject']
                if expected_subject in subject:
                    self.logger.info("Mail send verification succeeded")
                    return True
                else:
                    self.logger.warning(f"Subject mismatch: expected '{expected_subject}', got '{subject}'")
                    return False
            else:
                self.logger.warning("No sent mail found to recipient")
                return False
        except Exception as e:
            self.logger.error(f"Mail verification failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup connections"""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                self.logger.info("SMTP connection closed")
            if self.imap_connection:
                self.imap_connection.close()
                self.imap_connection.logout()
                self.logger.info("IMAP connection closed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    def send_exam_notification(self) -> bool:
        """Main process: send exam notification email"""
        try:
            self.logger.info("Starting to send exam notification email...")
            
            if not self.connect_smtp():
                return False
            
            if not self.authenticate_smtp():
                return False
            
            self.logger.info("Deleting emails in recipient's inbox...")
            delete_success = self.delete_recipient_inbox_emails()
            if delete_success:
                self.logger.info("Recipient inbox emails deleted")
            else:
                self.logger.warning("Failed to delete recipient inbox, will continue anyway")
            
            template = self.load_email_template()
            content = self.format_email_content(template)
            
            # 5. Send email
            if not self.send_email(content):
                return False
            
            # Email sent successfully
            self.logger.info("🎉 Exam notification email sent successfully!")
            print("✅ Email sent successfully!")
            print(f"📧 Sender: {self.config['sender_account']['email']}")
            print(f"📧 Recipient: {self.config['recipient']['email']}")
            print(f"📝 Subject: {self.config['email_content']['subject']}")
            print(f"📅 Exam time: {self.config['email_content']['exam_info']['exam_date']} {self.config['email_content']['exam_info']['exam_time']}")
            print(f"📍 Exam location: {self.config['email_content']['exam_info']['exam_location']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending exam notification email: {e}")
            print(f"❌ Email sent failed: {e}")
            return False
        
        finally:
            self.cleanup()

def main():
    """Main function"""
    try:
        # Config file path
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        # Create email sender
        sender = ExamNotificationSender(str(config_file))
        
        # Send exam notification email
        success = sender.send_exam_notification()
        
        if success:
            print("\n🎯 Exam notification email processing completed!")
        else:
            print("\n💥 Exam notification email processing failed!")
            exit(1)
            
    except Exception as e:
        print(f"❌ Program execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()

class ExamNotificationInjector:
    """Exam notification email direct injector - directly inject email into inbox, support custom timestamp"""
    
    def __init__(self, config_file: str):
        """
        Initialize email injector
        :param config_file: Config file path
        """
        self.logger = logging.getLogger('ExamNotificationInjector')
        self.setup_logging()
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load config file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info("Config file loaded successfully")
            return config
        except Exception as e:
            raise Exception(f"Failed to load config file: {e}")
    
    def setup_logging(self):
        """Setup logging"""
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def load_email_template(self) -> str:
        """Load email template"""
        try:
            template_file = self.config['email_content']['template_file']
            template_path = Path(__file__).parent.parent / 'files' / template_file
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            self.logger.info("Email template loaded successfully")
            return template
        except Exception as e:
            self.logger.error(f"Failed to load email template: {e}")
            return """Dear {recipient_name},

This is a notification about your upcoming exam:

Course: {course_name}
Date: {exam_date}
Time: {exam_time}
Location: {exam_location}
Type: {exam_type}
Duration: {duration}

Please arrive 15 minutes before the exam time.

Best regards,
Course Instructor"""
    
    def format_email_content(self, template: str) -> str:
        """Format email content"""
        try:
            exam_info = self.config['email_content']['exam_info']
            recipient = self.config['recipient']
            
            content = template.format(
                recipient_name=recipient['name'],
                course_name=exam_info['course_name'],
                exam_type=exam_info['exam_type'],
                exam_date=exam_info['exam_date'],
                exam_time=exam_info['exam_time'],
                duration=exam_info['duration'],
                exam_location=exam_info['exam_location'],
                sender_email=self.config['sender_account']['email'],
                sender_name=self.config['sender_account']['name'],
                send_time=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            self.logger.info("Email content formatted successfully")
            return content
        except Exception as e:
            self.logger.error(f"Failed to format email content: {e}")
            raise
    
    def inject_email_to_imap(self, content: str, custom_timestamp: Optional[float] = None) -> bool:
        """
        Directly inject email into IMAP server inbox
        :param content: Email content
        :param custom_timestamp: Custom timestamp (Unix timestamp), if None then use current time
        """
        try:
            # Get config
            server_config = self.config['server_config']
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            subject = self.config['email_content']['subject']
            
            # Connect to IMAP server
            if server_config.get("use_ssl"):
                imap = imaplib.IMAP4_SSL(server_config["imap_server"], server_config["imap_port"])
            else:
                imap = imaplib.IMAP4(server_config["imap_server"], server_config["imap_port"])
            
            if server_config.get("use_starttls"):
                imap.starttls()
            
            # Use recipient credentials to login
            imap.login(recipient['email'], recipient['password'])
            self.logger.info(f"✅ Connected to IMAP server as {recipient['email']}")
            
            # Select inbox
            imap.select("INBOX")
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = f"{sender_account['name']} <{sender_account['email']}>"
            msg['To'] = f"{recipient['name']} <{recipient['email']}>"
            msg['Subject'] = subject
            
            # Set timestamp
            if custom_timestamp:
                from email.utils import formatdate
                msg['Date'] = formatdate(custom_timestamp)
                self.logger.info(f"Using custom timestamp: {formatdate(custom_timestamp)}")
            else:
                from email.utils import formatdate
                msg['Date'] = formatdate()
                self.logger.info("Using current timestamp")
            
            # Add email body
            text_part = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Inject email into inbox
            email_string = msg.as_string()
            imap.append("INBOX", None, None, email_string.encode('utf-8'))
            
            # Close connection
            imap.close()
            imap.logout()
            
            self.logger.info("✅ Email successfully injected into inbox")
            return True
            
        except Exception as e:
            self.logger.error(f"Email injection failed: {e}")
            return False
    
    def delete_recipient_inbox_emails(self) -> bool:
        """Delete all emails in recipient inbox"""
        try:
            # Get recipient credentials
            recipient = self.config['recipient']
            server_config = self.config['server_config']
            
            self.logger.info(f"Connecting to recipient IMAP server: {server_config['imap_server']}:{server_config['imap_port']}")
            
            # Create new IMAP connection (using recipient credentials)
            if server_config.get('use_ssl', False):
                recipient_imap = imaplib.IMAP4_SSL(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            else:
                recipient_imap = imaplib.IMAP4(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            
            # Use recipient credentials to authenticate
            recipient_imap.login(
                recipient['email'],
                recipient['password']
            )
            
            self.logger.info("Recipient IMAP connection successful")
            print("🗑️ Clearing all emails in recipient inbox...")
            
            # Select inbox
            recipient_imap.select('INBOX')
            
            # Search all emails
            _, message_numbers = recipient_imap.search(None, 'ALL')
            
            if message_numbers[0]:
                # Get all email numbers
                email_nums = message_numbers[0].split()
                total_emails = len(email_nums)
                
                if total_emails > 0:
                    self.logger.info(f"Found {total_emails} emails, starting deletion...")
                    print(f"📧 Found {total_emails} emails, starting deletion...")
                    
                    # Delete all emails
                    for email_num in email_nums:
                        recipient_imap.store(email_num, '+FLAGS', '\\Deleted')
                    
                    # Permanent delete marked emails
                    recipient_imap.expunge()
                    
                    self.logger.info(f"Successfully deleted {total_emails} emails in recipient inbox")
                    print(f"✅ Successfully deleted {total_emails} emails in recipient inbox")
                else:
                    self.logger.info("No emails need to be deleted in recipient inbox")
                    print("📭 No emails need to be deleted in recipient inbox")
            else:
                self.logger.info("No emails in recipient inbox")
                print("📭 No emails in recipient inbox")
            
            # Close recipient IMAP connection
            recipient_imap.close()
            recipient_imap.logout()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete recipient inbox emails: {e}")
            print(f"❌ Failed to delete recipient inbox emails: {e}")
            return False

    def generate_distraction_emails(self) -> list:
        """Generate distraction email templates"""
        distraction_emails = [
            # ===== Shopping e-commerce =====
            {
                "from_name": "Amazon",
                "from_email": "no-reply@amazon.com",
                "subject": "Your order has been shipped! Track your package",
                "content": """Dear Customer,

Good news! Your recent order has been shipped and is on its way to you.

Order Details:
- Order Number: #123-4567890-1234567
- Shipping Carrier: UPS
- Tracking Number: 1Z999AA1234567890
- Estimated Delivery: 2-3 business days

You can track your package using the tracking number above on the carrier's website.

Thank you for choosing Amazon!

Best regards,
Amazon Customer Service Team"""
            },
            {
                "from_name": "eBay",
                "from_email": "ebay@ebay.com",
                "subject": "You've been outbid! Act fast to win this item",
                "content": """Hi,

Someone has placed a higher bid on the item you're watching:

Item: Vintage Leather Jacket - Size M
Current bid: $45.00
Your maximum bid: $40.00
Time left: 2 hours 34 minutes

Don't let this item slip away! Place a higher bid now to stay in the lead.

Happy bidding!
eBay Team"""
            },
            {
                "from_name": "Target",
                "from_email": "target@target.com",
                "subject": "Weekend sale: Up to 50% off home essentials",
                "content": """Don't miss out on these amazing deals!

This Weekend Only:
🏠 Home & Garden: Up to 50% off
👕 Clothing: Buy 2, get 1 free
🧴 Beauty products: 30% off select items
🍯 Grocery essentials: $5 off $50+

Plus, free shipping on orders over $35!
Sale ends Sunday at midnight.

Shop now - Target"""
            },
            {
                "from_name": "Etsy",
                "from_email": "transaction@etsy.com",
                "subject": "Your Etsy order is ready for pickup!",
                "content": """Great news!

Your order from ArtisanCraftsStudio is ready for pickup.

Order #ET789456123
- Handmade ceramic mug set (2 pieces)
- Custom name engraving
- Total: $34.95

Pickup available at the seller's studio or choose shipping.
Leave a review after pickup to help other buyers!

Thanks for supporting small businesses,
Etsy Team"""
            },

            # ===== Entertainment media =====
            {
                "from_name": "Netflix",
                "from_email": "info@netflix.com", 
                "subject": "New shows added to your list - Watch now!",
                "content": """Hi there,

We've added some new shows and movies that we think you'll love!

New This Week:
🎬 The Crown - Season 6 (Drama)
🎭 Comedy Special: Dave Chappelle
🎯 True Crime: The Vanishing 
🚀 Sci-Fi Series: Space Force Returns

Don't forget to check out your personalized recommendations.

Happy watching!
The Netflix Team"""
            },
            {
                "from_name": "YouTube",
                "from_email": "noreply@youtube.com",
                "subject": "Your video got 1,000 views! 🎉",
                "content": """Congratulations!

Your video "How to Make Perfect Coffee at Home" just reached 1,000 views!

Video Stats:
📊 1,047 views
👍 89 likes  
💬 23 comments
⏱️ Average watch time: 3:42

Keep creating amazing content. Your subscribers love it!

YouTube Creator Team"""
            },
            {
                "from_name": "Spotify",
                "from_email": "noreply@spotify.com",
                "subject": "Your Weekly Music Discovery is ready!",
                "content": """Hey Music Lover!

Your personalized playlist is ready with 30 new songs picked just for you.

This Week's Highlights:
🎵 Trending Pop hits
🎸 Indie rock discoveries  
🎤 Hip-hop favorites
🎹 Chill electronic vibes

Plus, check out your 2024 listening stats - you've discovered 847 new artists this year!

Start listening now and discover your next favorite song.

Keep the music playing,
Spotify"""
            },
            {
                "from_name": "TikTok",
                "from_email": "no-reply@tiktok.com",
                "subject": "Your video is trending! 🔥",
                "content": """Amazing news!

Your TikTok video is taking off:

📱 "Quick morning routine hack"
👀 25.3K views in 24 hours
❤️ 3.2K likes
🔄 892 shares
💭 156 comments

Your content is resonating with viewers! Keep up the great work.

TikTok Creator Fund Team"""
            },

            # ===== Social networks =====
            {
                "from_name": "LinkedIn",
                "from_email": "notifications@linkedin.com",
                "subject": "Someone viewed your profile",
                "content": """Hi,

A professional in your network recently viewed your LinkedIn profile.

Profile Views This Week: 5
- 2 from your industry
- 1 from a recruiter 
- 2 from your extended network

Keep your profile updated to make a great impression!

Grow your professional network:
- Connect with colleagues
- Share industry insights
- Engage with posts

Best regards,
LinkedIn Team"""
            },
            {
                "from_name": "Facebook",
                "from_email": "notification@facebookmail.com",
                "subject": "You have 3 friend requests and 8 notifications",
                "content": """What's happening on Facebook

👥 Friend Requests (3):
• Sarah Johnson (2 mutual friends)
• Mike Chen (1 mutual friend)  
• Emma Rodriguez (5 mutual friends)

🔔 Recent Activity:
• John liked your photo
• 5 people commented on your post
• Lisa shared your article
• You have 3 event invitations

Don't miss out on what your friends are sharing!

The Facebook Team"""
            },
            {
                "from_name": "Instagram",
                "from_email": "no-reply@mail.instagram.com",
                "subject": "Your Story highlights got 50+ views! 📸",
                "content": """Your content is performing great!

Story Highlights Performance:
📊 "Travel Memories" - 67 views
🍕 "Food Adventures" - 52 views
🐕 "Pet Photos" - 89 views

Recent Activity:
• @alex_photo liked 3 of your posts
• @sarah_travels started following you
• 12 people viewed your latest story

Keep sharing those amazing moments!

Instagram Team"""
            },
            {
                "from_name": "Twitter",
                "from_email": "info@twitter.com",
                "subject": "Your tweet is getting attention! 🐦",
                "content": """Tweet Performance Update

Your recent tweet about coffee brewing tips:

📈 2.1K impressions
🔄 45 retweets
❤️ 178 likes
💬 23 replies

Top reply: "This actually works! Thanks for the tip 🙌"

Your engagement is up 67% this week. Keep the conversations going!

Twitter Team"""
            },

            # ===== Financial & banking =====
            {
                "from_name": "Chase Bank",
                "from_email": "alerts@chase.com",
                "subject": "Account Alert: Large purchase detected",
                "content": """Security Notice

We detected a large purchase on your Chase account:

Transaction Details:
• Amount: $847.32
• Merchant: Best Buy Electronics
• Date: Today, 2:34 PM
• Location: Downtown Mall

If this was you, no action needed.
If this wasn't you, please contact us immediately at 1-800-CHASE-24.

Your security is our priority.
Chase Fraud Protection Team"""
            },
            {
                "from_name": "PayPal",
                "from_email": "service@paypal.com",
                "subject": "You've received $25.00 from Mom",
                "content": """You've got money!

Payment Details:
From: Linda Smith (Mom)
Amount: $25.00
Note: "Coffee money for this week ☕"

The money is now available in your PayPal balance.
You can transfer it to your bank account or use it for your next purchase.

Thanks for using PayPal!
PayPal Team"""
            },
            {
                "from_name": "Wells Fargo",
                "from_email": "wellsfargo@wellsfargo.com",
                "subject": "Monthly statement is ready",
                "content": """Your statement is now available

Wells Fargo Checking Account
Statement Period: Nov 1 - Nov 30, 2024

Account Summary:
• Beginning Balance: $2,847.63
• Total Deposits: $3,200.00
• Total Withdrawals: $2,156.84
• Ending Balance: $3,890.79

View your complete statement online or in the Wells Fargo mobile app.

Wells Fargo Customer Service"""
            },

            # ===== Food delivery =====
            {
                "from_name": "Uber Eats",
                "from_email": "orders@ubereats.com",
                "subject": "20% off your next order - Limited time!",
                "content": """Hungry? We've got you covered! 🍕

Get 20% off your next Uber Eats order with code: SAVE20

Valid on orders over $25 from participating restaurants.

Popular near you:
🍔 Joe's Burger Joint (4.8★)
🍜 Dragon Noodle House (4.9★) 
🥗 Fresh Garden Cafe (4.7★)
🍕 Tony's Pizza Palace (4.6★)

Offer expires in 48 hours - Order now!

Bon appétit,
Uber Eats Team"""
            },
            {
                "from_name": "DoorDash",
                "from_email": "no-reply@doordash.com",
                "subject": "Your order from Thai Garden is on the way! 🚗",
                "content": """Great news! Your order is on the way.

Order Details:
• Pad Thai with chicken
• Spring rolls (4 pieces)  
• Thai iced tea
• Total: $28.47

Your Dasher Mike is 8 minutes away.
Track your order in real-time in the app.

Enjoy your meal!
DoorDash Team"""
            },
            {
                "from_name": "Grubhub",
                "from_email": "orders@grubhub.com",
                "subject": "Free delivery weekend! Order from 50+ restaurants",
                "content": """Free delivery all weekend long! 🚚

No delivery fees on orders from participating restaurants:

🌮 Mexican: Taco Bell, Chipotle, Local Taqueria
🍝 Italian: Papa John's, Local Pasta House
🍗 American: KFC, Five Guys, Local Grill
🍱 Asian: Panda Express, Local Sushi Bar

Minimum order $15. Offer valid Sat-Sun only.

Order now and save!
Grubhub Team"""
            },

            # ===== Travel & accommodation =====
            {
                "from_name": "Booking.com",
                "from_email": "customer.service@booking.com",
                "subject": "Price drop alert! Save $45 on your Tokyo trip",
                "content": """Good news! Prices dropped for your saved search.

Tokyo, Japan - Dec 15-22, 2024

Hotel Price Drops:
🏨 Tokyo Grand Hotel: Was $180/night → Now $135/night
🏨 Shibuya Business Hotel: Was $95/night → Now $78/night  
🏨 Asakusa Traditional Inn: Was $120/night → Now $89/night

Book now to lock in these lower prices!
Prices may go up again.

Happy travels,
Booking.com Team"""
            },
            {
                "from_name": "Airbnb",
                "from_email": "automated@airbnb.com",
                "subject": "Your host is excited to welcome you! 🏠",
                "content": """Your trip is coming up soon!

Booking Details:
📍 Cozy downtown apartment in Portland
📅 Check-in: Dec 8, 2024 (3:00 PM)
📅 Check-out: Dec 11, 2024 (11:00 AM)
🏠 Host: Jennifer

Check-in Instructions:
• Key lockbox code: 5847
• WiFi password: CoffeeCity2024
• Parking spot #12 in back lot

Your host says: "Welcome! There's fresh coffee and local restaurant recommendations on the counter."

Have a great stay!
Airbnb Team"""
            },
            {
                "from_name": "Delta Airlines",
                "from_email": "noreply@delta.com",
                "subject": "Flight DL1284 - Check-in now available ✈️",
                "content": """You can now check in for your flight!

Flight Information:
✈️ DL1284: New York (JFK) → Los Angeles (LAX)
📅 Tomorrow, Dec 2, 2024
🕐 Departure: 8:30 AM
🕒 Arrival: 11:45 AM (local time)
💺 Seat: 12F (Window)

Check in now to:
• Select your seat preferences
• Add bags if needed
• Get your mobile boarding pass

Safe travels!
Delta Air Lines"""
            },

            # ===== News & information =====
            {
                "from_name": "The New York Times",
                "from_email": "nyt@nytimes.com",
                "subject": "Morning Briefing: Today's top stories",
                "content": """Good morning! Here's what you need to know:

🌍 World News:
• Climate summit reaches breakthrough agreement
• Tech innovation drives economic growth
• Space mission discovers new planetary system

🏛️ Politics:
• Congressional budget talks continue
• New infrastructure projects announced
• International trade agreements updated

📊 Business:
• Stock markets hit record highs
• Consumer confidence rises
• Tech sector leads gains

☀️ Weather: Sunny, high 72°F

Read more at nytimes.com
The New York Times"""
            },
            {
                "from_name": "Medium",
                "from_email": "noreply@medium.com",
                "subject": "Top stories in Technology this week 📱",
                "content": """Your weekly digest from Medium

📱 Technology highlights:

Most Popular:
• "The Future of Remote Work: 5 Trends to Watch"
• "AI Tools That Actually Save Time (Not Hype)"
• "Building Better Apps: Lessons from 100 User Interviews"

Trending Topics:
#MachineLearning #RemoteWork #Productivity #StartupLife

Based on your reading history, you might also like:
• "From Burnout to Balance: A Developer's Journey"
• "Why Every Team Needs a Documentation Strategy"

Happy reading!
Medium Team"""
            },

            # ===== Deals & discounts =====
            {
                "from_name": "Groupon",
                "from_email": "deals@groupon.com",
                "subject": "Weekend Flash Sale - Up to 70% off activities!",
                "content": """Weekend Plans? We've got deals! ⚡

Flash Sale ends Sunday midnight:

🎯 Activities & Entertainment:
- Escape Rooms: $15 (reg. $45)
- Mini Golf: $8 (reg. $20) 
- Bowling: $12 (reg. $35)
- Movie Tickets: $7 (reg. $15)

🍽️ Dining Deals:
- Italian Restaurant: 50% off dinner
- Sushi Bar: $25 for $50 worth
- Steakhouse: 40% off weekend brunch

⚽ Fitness & Wellness:
- Yoga Classes: $20 for 5 sessions
- Massage Therapy: 60% off
- Rock Climbing: $18 (reg. $40)

Limited quantities - grab yours now!
Groupon Deals Team"""
            },
            {
                "from_name": "LivingSocial",
                "from_email": "deals@livingsocial.com",
                "subject": "Local adventure deals - 60% off outdoor activities",
                "content": """Adventure awaits! 🏞️

Limited-time outdoor deals in your area:

🚴 Bike Tours:
• City highlights tour: $25 (reg. $65)
• Wine country cycling: $45 (reg. $95)

🛶 Water Sports:
• Kayak rental (2 hours): $18 (reg. $40)
• Stand-up paddleboard lesson: $22 (reg. $50)

🏔️ Hiking & Nature:
• Guided nature walk: $12 (reg. $30)
• Rock climbing intro class: $35 (reg. $80)

Book by Sunday to secure these prices!

Get outside and explore,
LivingSocial Adventures"""
            },

            # ===== Community forums =====
            {
                "from_name": "Reddit",
                "from_email": "noreply@reddit.com",
                "subject": "Trending posts you might have missed",
                "content": """What's happening on Reddit

Here are the top posts from communities you follow:

🔥 Hot Posts:
• r/funny: Cat accidentally orders 50 pizzas
• r/technology: New smartphone breaks durability records
• r/movies: Behind-the-scenes secrets from latest blockbuster
• r/gaming: Indie game becomes overnight sensation

💬 Active Discussions:
• What's the best life advice you've received?
• Share your most embarrassing moment
• What skill should everyone learn?

Jump back into the conversation!
Reddit Team"""
            },
            {
                "from_name": "Stack Overflow",
                "from_email": "noreply@stackoverflow.com",
                "subject": "Weekly digest: Top Python questions",
                "content": """This week in Python development

🐍 Top Questions:
• "How to optimize database queries in Django?"
• "Best practices for handling API rate limits"
• "Memory management in large dataset processing"
• "Testing async functions properly"

💡 Popular Answers:
• List comprehensions vs generator expressions
• When to use async/await in Python
• Docker setup for Python microservices

Keep coding and keep learning!
Stack Overflow Team"""
            },

            # ===== Health & fitness =====
            {
                "from_name": "MyFitnessPal",
                "from_email": "noreply@myfitnesspal.com",
                "subject": "Weekly progress: You're on track! 💪",
                "content": """Great work this week!

📊 Weekly Summary:
• Logged 6 out of 7 days
• Average calories: 1,847 (goal: 1,800)
• Protein goal met 5 days
• Water intake: 95% of goal

🏃 Activity:
• 4 workouts completed
• 23,456 steps total
• 2.1 lbs lost this month

Keep up the momentum! Small consistent changes lead to big results.

Your health journey team,
MyFitnessPal"""
            },
            {
                "from_name": "Headspace",
                "from_email": "hello@headspace.com",
                "subject": "3-minute meditation break? 🧘‍♀️",
                "content": """Take a moment for yourself

You've been working hard. How about a quick meditation break?

🧘 Suggested sessions:
• "Desk Stress Relief" (3 min)
• "Focus Boost" (5 min)  
• "Gratitude Pause" (3 min)
• "Energy Reset" (7 min)

Research shows even 3 minutes of mindfulness can:
✓ Reduce stress levels
✓ Improve focus
✓ Boost creativity

Ready to press pause?

Mindfully yours,
Headspace Team"""
            },

            # ===== Gaming & entertainment =====
            {
                "from_name": "Steam",
                "from_email": "noreply@steampowered.com",
                "subject": "Weekend Deal: 75% off indie games! 🎮",
                "content": """Steam Weekend Sale is here!

🎮 Featured Deals (up to 75% off):
• "Pixel Adventure Quest" - $4.99 (was $19.99)
• "Space Strategy Empire" - $7.49 (was $29.99)
• "Cozy Farming Simulator" - $3.74 (was $14.99)
• "Mystery Detective Story" - $5.99 (was $23.99)

⭐ Highly Rated:
• All games 85%+ positive reviews
• Perfect for weekend gaming sessions
• Support independent developers

Sale ends Monday at 10 AM PST.

Happy gaming!
Steam Team"""
            },
            {
                "from_name": "Twitch",
                "from_email": "no-reply@twitch.tv",
                "subject": "Your favorite streamer is live! 🔴",
                "content": """GameMaster_Pro is now live!

🎮 Currently Playing: "Cyberpunk Adventure Redux"
👥 1,247 viewers watching
⏱️ Stream started 23 minutes ago

Recent highlights:
• Epic boss battle victory
• Viewer challenge accepted
• New speedrun attempt starting

Don't miss the action! Join the chat and be part of the community.

See you in the stream!
Twitch Notifications"""
            }
        ]
        return distraction_emails

    def inject_distraction_email(self, email_template: dict, timestamp: float) -> bool:
        """Inject single distraction email"""
        try:
            # Get config
            server_config = self.config['server_config']
            recipient = self.config['recipient']
            
            # Connect to IMAP server
            if server_config.get("use_ssl"):
                imap = imaplib.IMAP4_SSL(server_config["imap_server"], server_config["imap_port"])
            else:
                imap = imaplib.IMAP4(server_config["imap_server"], server_config["imap_port"])
            
            if server_config.get("use_starttls"):
                imap.starttls()
            
            # Use recipient credentials to login
            imap.login(recipient['email'], recipient['password'])
            
            # Select inbox
            imap.select("INBOX")
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = f"{email_template['from_name']} <{email_template['from_email']}>"
            msg['To'] = f"{recipient['name']} <{recipient['email']}>"
            msg['Subject'] = email_template['subject']
            
            # Set timestamp
            from email.utils import formatdate
            msg['Date'] = formatdate(timestamp)
            
            # Add email body
            text_part = MIMEText(email_template['content'], 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Inject email into inbox
            email_string = msg.as_string()
            imap.append("INBOX", None, None, email_string.encode('utf-8'))
            
            # Close connection
            imap.close()
            imap.logout()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to inject distraction email: {e}")
            return False

    def inject_exam_notification(self, custom_timestamp: Optional[float] = None, clear_inbox: bool = False, add_distractions: bool = True) -> bool:
        """
        Inject exam notification email into inbox
        :param custom_timestamp: Custom timestamp (Unix timestamp)
        :param clear_inbox: Whether to clear all emails in inbox before injection
        :param add_distractions: Whether to add distraction emails
        """
        try:
            self.logger.info("Starting to inject exam notification email...")
            
            # 0. If clear inbox option is enabled, clear inbox first
            if clear_inbox:
                print("\n🗑️ Step 0: Clear inbox emails...")
                delete_success = self.delete_recipient_inbox_emails()
                if delete_success:
                    print("✅ Inbox emails cleared successfully")
                    self.logger.info("Inbox emails cleared successfully")
                else:
                    print("⚠️ Inbox emails clear failed, but continue with email injection")
                    self.logger.warning("Inbox emails clear failed, but continue with email injection")
            
            # Determine exam email timestamp
            if custom_timestamp:
                exam_timestamp = custom_timestamp
            else:
                exam_timestamp = time.time()
            
            random.seed(42) # fix a seed to make the results reproducible

            # 1. Inject distraction emails (before exam email)
            if add_distractions:
                print("\n🎭 Step 1: Inject distraction emails (before exam notification)...")
                self.inject_distraction_emails_before(exam_timestamp)
            
            # 2. Load and format exam email template
            print("\n📧 Step 2: Inject exam notification email...")
            template = self.load_email_template()
            content = self.format_email_content(template)
            
            # 3. Inject exam email
            if not self.inject_email_to_imap(content, exam_timestamp):
                return False
            
            # 4. Inject distraction emails (after exam email)
            if add_distractions:
                print("\n🎭 Step 3: Inject distraction emails (after exam notification)...")
                self.inject_distraction_emails_after(exam_timestamp)
            
            # Email injection successful
            self.logger.info("🎉 Exam notification email injection successful!")
            print("\n✅ Email injection successful!")
            print(f"📧 Sender: {self.config['sender_account']['email']}")
            print(f"📧 Recipient: {self.config['recipient']['email']}")
            print(f"📝 Subject: {self.config['email_content']['subject']}")
            print(f"📅 Exam time: {self.config['email_content']['exam_info']['exam_date']} {self.config['email_content']['exam_info']['exam_time']}")
            print(f"📍 Exam location: {self.config['email_content']['exam_info']['exam_location']}")
            
            if custom_timestamp:
                from datetime import datetime
                dt = datetime.fromtimestamp(custom_timestamp)
                print(f"⏰ Email timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if add_distractions:
                print("🎭 Added distraction emails to simulate real inbox environment")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error injecting exam notification email: {e}")
            print(f"❌ Email injection failed: {e}")
            return False

    def inject_distraction_emails_before(self, exam_timestamp: float):
        """Inject distraction emails before exam email"""
        try:
            distraction_emails = self.generate_distraction_emails()
            
            # Inject 6-12 distraction emails 1-5 days before exam email, increase number to make inbox more chaotic
            num_emails = random.randint(6, 12)
            selected_emails = random.sample(distraction_emails, min(num_emails, len(distraction_emails)))
            
            print(f"📮 Injecting {len(selected_emails)} distraction emails (before exam notification)...")
            
            for i, email_template in enumerate(selected_emails):
                # Random time 0.5-5 days before exam email, expand time range
                days_before = random.uniform(0.5, 5.0)  # 0.5-5 days before exam email
                hours_offset = random.uniform(0, 24)    # Add 0-24 hour random offset
                total_seconds_before = (days_before * 24 * 3600) + (hours_offset * 3600)
                
                distraction_timestamp = exam_timestamp - total_seconds_before
                
                success = self.inject_distraction_email(email_template, distraction_timestamp)
                if success:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(distraction_timestamp)
                    print(f"  ✅ {email_template['from_name']}: {email_template['subject'][:50]}... ({dt.strftime('%m-%d %H:%M')})")
                else:
                    print(f"  ❌ Failed: {email_template['from_name']}")
                
                # Add small delay to avoid server pressure
                time.sleep(0.3)
                
        except Exception as e:
            self.logger.error(f"Failed to inject distraction emails before exam email: {e}")
            print("⚠️ Some distraction emails injection failed, but continue execution")

    def inject_distraction_emails_after(self, exam_timestamp: float):
        """Inject distraction emails after exam email"""
        try:
            distraction_emails = self.generate_distraction_emails()
            
            # Inject 4-8 distraction emails 1-2 hours after exam email, increase number
            num_emails = random.randint(4, 8)
            # Select different emails to avoid duplicates
            remaining_emails = [e for e in distraction_emails]
            random.shuffle(remaining_emails)  # Shuffle to ensure diversity
            selected_emails = remaining_emails[:min(num_emails, len(remaining_emails))]
            
            print(f"📮 Injecting {len(selected_emails)} distraction emails (after exam notification)...")
            
            for i, email_template in enumerate(selected_emails):
                # Random time 1-2 hours after exam email, expand time range
                hours_after = random.uniform(1, 48)     # 1-48 hours after exam email (2 days)
                minutes_offset = random.uniform(0, 60)  # Add 0-60 minute random offset
                total_seconds_after = (hours_after * 3600) + (minutes_offset * 60)
                
                distraction_timestamp = exam_timestamp + total_seconds_after
                
                success = self.inject_distraction_email(email_template, distraction_timestamp)
                if success:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(distraction_timestamp)
                    print(f"  ✅ {email_template['from_name']}: {email_template['subject'][:50]}... ({dt.strftime('%m-%d %H:%M')})")
                else:
                    print(f"  ❌ Failed: {email_template['from_name']}")
                
                # Add small delay to avoid server pressure
                time.sleep(0.3)
                
        except Exception as e:
            self.logger.error(f"Failed to inject distraction emails after exam email: {e}")
            print("⚠️ Some distraction emails injection failed, but continue execution")


def inject_exam_emails_from_config(config_file_path: str, custom_timestamp: Optional[float] = None, clear_inbox: bool = False, add_distractions: bool = True):
    """
    Inject exam notification email from email_config.json
    :param config_file_path: email_config.json file path
    :param custom_timestamp: Custom timestamp (Unix timestamp), if None use current time
    :param clear_inbox: Whether to clear all emails in inbox before injection
                       - True: Clear inbox before injection (recommended for test environment)
                       - False: Directly inject new email, keep existing emails
    :param add_distractions: Whether to add distraction emails
                           - True: Add irrelevant emails before and after exam notification to simulate real inbox environment
                           - False: Only inject exam notification email
    
    Example usage:
    # Clear inbox before injection, include distraction emails (recommended)
    inject_exam_emails_from_config('config.json', clear_inbox=True, add_distractions=True)
    
    # Keep existing emails, only inject exam notification email
    inject_exam_emails_from_config('config.json', clear_inbox=False, add_distractions=False)
    """
    try:
        print("Starting to inject exam notification email...")
        if clear_inbox:
            print("📋 Mode: Clear inbox before injection (recommended for test environment)")
        else:
            print("📋 Mode: Keep existing emails, directly inject exam notification email")
            
        if add_distractions:
            print("🎭 Distraction mode: Enabled - Add irrelevant emails to increase realism")
        else:
            print("🎯 Distraction mode: Closed - Only inject exam notification email")
        
        # Create email injector
        injector = ExamNotificationInjector(config_file_path)
        
        # Inject exam notification email
        success = injector.inject_exam_notification(custom_timestamp, clear_inbox, add_distractions)
        
        if success:
            print("\n🎯 Exam notification email injection completed!")
            return True
        else:
            print("\n💥 Exam notification email injection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Program execution failed: {e}")
        return False


def main_inject():
    """Main function - email injection mode"""
    try:
        # Config file path
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        # Example: Use custom timestamp (here set to 2024-12-1 10:00:00)
        from datetime import datetime
        custom_time = datetime(2024, 12, 1, 10, 0, 0)
        custom_timestamp = custom_time.timestamp()
        
        print(f"📅 Set email time to: {custom_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Inject exam notification email - enable clear inbox option and distraction emails
        success = inject_exam_emails_from_config(str(config_file), custom_timestamp, clear_inbox=True, add_distractions=True)
        
        if not success:
            exit(1)
            
    except Exception as e:
        print(f"❌ Program execution failed: {e}")
        exit(1)

def test_inject_with_options():
    """Test function - demonstrate different email injection options"""
    try:
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        print("=" * 60)
        print("📧 Email injection feature test")
        print("=" * 60)
        
        while True:
            print("\nPlease select operation:")
            print("1. Clear inbox before injection + distraction emails (recommended)")
            print("2. Clear inbox before injection (no distractions)")
            print("3. Direct injection email + distraction emails (keep existing emails)")
            print("4. Direct injection email (keep existing emails, no distractions)")
            print("5. Only clear inbox (no email injection)")
            print("6. Exit")
            
            choice = input("\nPlease enter option (1-6): ").strip()
            
            if choice == '1':
                print("\n🗑️+🎭 Select: Clear inbox before injection + distraction emails")
                inject_exam_emails_from_config(str(config_file), clear_inbox=True, add_distractions=True)
            
            elif choice == '2':
                print("\n🗑️ Select: Clear inbox before injection (no distractions)")
                inject_exam_emails_from_config(str(config_file), clear_inbox=True, add_distractions=False)
            
            elif choice == '3':
                print("\n📧+🎭 Select: Direct injection email + distraction emails")
                inject_exam_emails_from_config(str(config_file), clear_inbox=False, add_distractions=True)
                
            elif choice == '4':
                print("\n📧 Select: Direct injection email (no distractions)")
                inject_exam_emails_from_config(str(config_file), clear_inbox=False, add_distractions=False)
            
            elif choice == '5':
                print("\n🗑️ Select: Only clear inbox (no email injection)")
                injector = ExamNotificationInjector(str(config_file))
                injector.delete_recipient_inbox_emails()
            
            elif choice == '6':
                print("\n👋 Exit test")
                break
            
            else:
                print("\n❌ Invalid option, please select again")
    
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    # If run this file directly, start test mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_inject_with_options()
    else:
        main()
