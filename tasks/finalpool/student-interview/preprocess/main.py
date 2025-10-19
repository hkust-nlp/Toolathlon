import imaplib
import json
from pathlib import Path
from datetime import datetime, timedelta
from time import sleep
from argparse import ArgumentParser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
import random
random.seed(42)
import asyncio
from utils.app_specific.poste.email_import_utils import clear_all_email_folders

from .setup_calendar_events import setup_calendar_events
CALENDAR_AVAILABLE = True

def inject_emails_to_imap(imap_config, emails_data):
    """
    Directly inject emails into IMAP server
    """
    try:
        # Connect to IMAP server
        if imap_config.get("use_ssl"):
            imap = imaplib.IMAP4_SSL(imap_config["imap_server"], imap_config["imap_port"])
        else:
            imap = imaplib.IMAP4(imap_config["imap_server"], imap_config["imap_port"])

        if imap_config.get("use_starttls"):
            imap.starttls()

        # Login
        imap.login(imap_config["email"], imap_config["password"])
        print(f"✅ Connected to IMAP server as {imap_config['email']}")
        
        # Select INBOX
        imap.select("INBOX")
        
        for email_data in emails_data:
            try:
                # Create email message
                msg = MIMEMultipart()
                
                # Handle unified email format
                sender_name = email_data.get('sender_name', 'Unknown Sender')
                sender_email = email_data.get('sender_email', f"{sender_name.lower().replace(' ', '.')}@example.com")
                
                msg['From'] = formataddr((sender_name, sender_email))
                msg['To'] = imap_config["email"]
                msg['Subject'] = email_data['subject']
                
                # Set date
                if 'send_time' in email_data:
                    send_time = email_data['send_time']
                    if isinstance(send_time, datetime):
                        msg['Date'] = formatdate(send_time.timestamp())
                    else:
                        msg['Date'] = formatdate(send_time)
                else:
                    msg['Date'] = formatdate()
                
                # Add body
                content = email_data.get('content', '')
                content_type = email_data.get('content_type', 'html')
                
                msg.attach(MIMEText(content, content_type, 'utf-8'))
                
                # Convert to string and append to mailbox
                email_string = msg.as_string()
                
                # Append to INBOX
                imap.append("INBOX", None, None, email_string.encode('utf-8'))
                print(f"✅ Injected: {sender_name} - {email_data['subject']}")
                
                # Small delay to avoid overwhelming the server
                sleep(0.1)
                
            except Exception as e:
                print(f"❌ Failed to inject email '{email_data.get('subject', 'Unknown')}': {e}")
                continue
        
        imap.close()
        imap.logout()
        print(f"✅ Successfully injected {len(emails_data)} emails")
        return True
        
    except Exception as e:
        print(f"❌ IMAP connection failed: {e}")
        return False

def load_user_emails_mapping(user_list_file):
    """Load mapping of student names to their proper mcp.com email addresses"""
    import csv
    
    email_mapping = {}
    with open(user_list_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Position'] == 'student':
                name = row['Name']
                email = row['email']
                email_mapping[name] = email
    
    return email_mapping

def create_unified_email_list(current_time, student_emails_file, fake_emails_file, user_list_file, num_fake_emails=None):
    """
    Create a unified email list mixing student and fake emails with proper formatting and timestamps
    """
    current_date = current_time
    all_emails = []
    
    # Load email mapping from user_list.csv
    email_mapping = load_user_emails_mapping(user_list_file)
    
    # 1. Load and process student emails
    print(f"📝 Loading student emails...")
    with open(student_emails_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            email_data = json.loads(line)
            sender_name = email_data.get('sender_name', 'Unknown')
            
            # Get proper email from CSV mapping
            sender_email = email_mapping.get(sender_name, f"{sender_name.lower().replace(' ', '.')}@mcp.com")
            
            # Process send_time - either convert placeholder or assign random time
            if 'send_time' in email_data and isinstance(email_data['send_time'], str):
                # Parse placeholder like "25 days before current date" 
                if "days before current date" in email_data['send_time']:
                    days_str = email_data['send_time'].split()[0]
                    try:
                        days_ago = int(days_str)
                    except ValueError:
                        days_ago = random.randint(1, 60)  # fallback
                else:
                    days_ago = random.randint(1, 60)  # fallback for other formats
            else:
                # Assign random time if no send_time specified
                days_ago = random.randint(1, 60)
            
            # Generate random time within the day (business hours)
            hours_ago = random.randint(8, 18)  # Business hours
            minutes_ago = random.randint(0, 59)
            send_time = current_date - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            unified_email = {
                'sender_name': sender_name,
                'sender_email': sender_email,
                'subject': email_data['subject'],
                'content': email_data['content'],
                'content_type': email_data.get('content_type', 'html'),
                'send_time': send_time,
                'email_type': 'student'
            }
            all_emails.append(unified_email)
    
    print(f"✅ Loaded {len(all_emails)} student emails")
    
    # 2. Load and process fake emails 
    print(f"🎲 Loading fake emails...")
    with open(fake_emails_file, 'r', encoding='utf-8') as f:
        fake_emails = json.load(f)
    
    if num_fake_emails is None:
        num_fake_emails = random.randint(50, 100)
    
    # Randomly select fake emails
    selected_fake_emails = random.sample(fake_emails, min(num_fake_emails, len(fake_emails)))
    
    for fake_email in selected_fake_emails:
        # Process the fake email similar to inject_fake_emails.py
        sender_name = fake_email.get('from', 'unknown@example.com')
        
        # Set send time for fake emails (1-30 days ago)
        if 'send_time' in fake_email:
            from .inject_fake_emails import parse_relative_time
            send_time = parse_relative_time(fake_email['send_time'], current_date)
        else:
            # Random time in the past month
            days_ago = random.randint(1, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            send_time = current_date - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        from .inject_fake_emails import resolve_date_placeholders
        
        unified_email = {
            'sender_name': sender_name,
            'sender_email': sender_name,  # Fake emails keep their original sender
            'subject': fake_email.get('subject', 'No Subject'),
            'content': resolve_date_placeholders(fake_email.get('body', ''), current_date),
            'content_type': 'html',
            'send_time': send_time,
            'email_type': 'fake'
        }
        all_emails.append(unified_email)
    
    print(f"✅ Loaded {len(selected_fake_emails)} fake emails")
    
    # 3. Sort all emails by send_time (newest last)
    print(f"📅 Sorting {len(all_emails)} total emails by timestamp (newest last)...")
    all_emails.sort(key=lambda x: x.get('send_time'), reverse=False)
    
    if all_emails:
        newest_time = all_emails[-1].get('send_time')
        oldest_time = all_emails[0].get('send_time')
        print(f"   📧 Newest: {all_emails[-1].get('sender_name', 'Unknown')} ({newest_time.strftime('%Y-%m-%d %H:%M') if newest_time else 'No time'})")
        print(f"   📧 Oldest: {all_emails[0].get('sender_name', 'Unknown')} ({oldest_time.strftime('%Y-%m-%d %H:%M') if oldest_time else 'No time'})")
    
    student_count = sum(1 for email in all_emails if email.get('email_type') == 'student')
    fake_count = sum(1 for email in all_emails if email.get('email_type') == 'fake')
    print(f"📊 Final mix: {student_count} student emails + {fake_count} fake emails = {len(all_emails)} total")
    
    return all_emails

async def main():
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    
    args = parser.parse_args()
    args.num_fake_emails = None  # 50-100 if not specified)
    args.setup_calendar = True

    print("🚀 Starting comprehensive email preprocessing...")
    if args.setup_calendar and CALENDAR_AVAILABLE:
        print("📅 Calendar setup will be included")
    else:
        print("📅 Note: Use --setup_calendar flag to also set up calendar events")
    
    # Read email configuration
    base_path = Path(__file__).parent.parent
    email_config_file = base_path / "email_config.json"
    
    with open(email_config_file, 'r', encoding='utf-8') as f:
        email_config = json.load(f)
    
    print(f"📧 Using email config: {email_config['email']}")
    
    # Save today's date for evaluation first
    current_time = datetime.now()
    today = current_time.strftime('%Y-%m-%d')
    today_file_path = base_path / "groundtruth_workspace" / "today.txt"
    with open(today_file_path, 'w', encoding='utf-8') as f:
        f.write(today)
    print(f"✅ Saved today's date to: {today_file_path}")
    
    # Set up Google Calendar events if requested
    if args.setup_calendar and CALENDAR_AVAILABLE:
        print("\n📅 Setting up Google Calendar events...")
        calendar_success = await setup_calendar_events("configs/google_credentials.json")
        
        if not calendar_success:
            print("❌ Failed to set up calendar events")
            exit(1)
    
    # Clean existing emails first
    print("\n🧹 Cleaning existing emails...")
    clear_all_email_folders(str(email_config_file))
    
    # Create unified email list (mixing student and fake emails properly)
    print(f"\n📧 Creating unified email list...")
    student_emails_file = base_path / "files" / "emails.jsonl"
    fake_emails_file = base_path / "files" / "fake_emails_300_manual.json" 
    user_list_file = base_path / "files" / "user_list.csv"
    num_fake = args.num_fake_emails if hasattr(args, 'num_fake_emails') and args.num_fake_emails else None
    
    all_emails = create_unified_email_list(current_time, student_emails_file, fake_emails_file, user_list_file, num_fake)
    
    # Inject all emails in sorted order
    print(f"\n📥 Injecting {len(all_emails)} emails in chronological order...")
    success = inject_emails_to_imap(email_config, all_emails)
    
    if not success:
        print("❌ Failed to inject emails")
        exit(1)
    
    print(f"\n🎉 Preprocessing completed successfully!")
    print(f"📊 Summary:")
    if args.setup_calendar and CALENDAR_AVAILABLE:
        print(f"   - Calendar events: Academic Committee Meeting (today 3-5PM), PhD Defense (tomorrow 9-11AM)")
    
    student_count = sum(1 for email in all_emails if email.get('email_type') == 'student')
    fake_count = sum(1 for email in all_emails if email.get('email_type') == 'fake')
    
    print(f"   - {fake_count} fake distractor emails injected")
    print(f"   - {student_count} student application emails injected")  
    print(f"   - Total: {len(all_emails)} emails in inbox (properly mixed and sorted)")
    print(f"   - Qualified students: Nicholas Martinez, Stephanie Rogers, Ryan Gonzalez")
    print(f"   - Agent needs to find these 3 students and schedule interviews!")
    
    if not args.setup_calendar:
        print(f"")
        print(f"⚠️  Next step: Set up calendar events with:")
        print(f"   python -m preprocess.main --setup_calendar")

if __name__ == "__main__":
    asyncio.run(main())