import imaplib
import json
import random
import re
from pathlib import Path
from datetime import datetime, timedelta
from time import sleep
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate

def parse_relative_time(time_str, reference_date):
    """Parse relative time strings like '5 days before current date'"""
    
    # Handle various patterns
    patterns = [
        r'(\d+)\s+(days?)\s+before\s+current\s+date',
        r'(\d+)\s+(hours?)\s+before\s+current\s+date',
        r'(\d+)\s+(minutes?)\s+before\s+current\s+date',
        r'(\d+)\s+(weeks?)\s+before\s+current\s+date',
        r'(\d+)\s+(months?)\s+before\s+current\s+date'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, time_str)
        if match:
            amount = int(match.group(1))
            unit = match.group(2).lower()
            
            if 'day' in unit:
                return reference_date - timedelta(days=amount)
            elif 'hour' in unit:
                return reference_date - timedelta(hours=amount)
            elif 'minute' in unit:
                return reference_date - timedelta(minutes=amount)
            elif 'week' in unit:
                return reference_date - timedelta(weeks=amount)
            elif 'month' in unit:
                return reference_date - timedelta(days=amount*30)  # Approximate
    
    # If no pattern matches, return reference date
    return reference_date

def resolve_date_placeholders(text, reference_date):
    """Replace date placeholders in text with actual dates"""
    
    # Find all date patterns in the text
    patterns = [
        r'(\d+)\s+(days?)\s+before\s+current\s+date',
        r'(\d+)\s+(hours?)\s+before\s+current\s+date', 
        r'(\d+)\s+(weeks?)\s+before\s+current\s+date',
        r'(\d+)\s+(months?)\s+before\s+current\s+date'
    ]
    
    result_text = text
    
    for pattern in patterns:
        matches = re.finditer(pattern, result_text)
        for match in matches:
            full_match = match.group(0)
            calculated_date = parse_relative_time(full_match, reference_date)
            date_str = calculated_date.strftime('%Y-%m-%d')
            result_text = result_text.replace(full_match, date_str)
    
    return result_text

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
                
                # Handle sender name and email
                sender_name = email_data.get('sender_name', email_data.get('from', 'Unknown Sender'))
                if '@' in sender_name:
                    # If sender_name contains @, it's already an email
                    sender_email = sender_name
                    sender_name = sender_name.split('@')[0].replace('.', ' ').title()
                else:
                    # Generate email from name
                    sender_email = f"{sender_name.lower().replace(' ', '.')}@example.com"
                
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
                content = email_data.get('content', email_data.get('body', ''))
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

def load_and_process_fake_emails(fake_emails_file, num_emails=None):
    """Load fake emails and process date placeholders"""
    
    with open(fake_emails_file, 'r', encoding='utf-8') as f:
        fake_emails = json.load(f)
    
    if num_emails is None:
        num_emails = random.randint(50, 100)
    
    # Randomly select emails
    selected_emails = random.sample(fake_emails, min(num_emails, len(fake_emails)))
    
    current_date = datetime.now()
    processed_emails = []
    
    for fake_email in selected_emails:
        # Process the email
        processed_email = {
            'sender_name': fake_email.get('from', 'unknown@example.com'),
            'subject': fake_email.get('subject', 'No Subject'),
            'content': resolve_date_placeholders(fake_email.get('body', ''), current_date),
            'content_type': 'html'
        }
        
        # Set send time
        if 'send_time' in fake_email:
            send_time = parse_relative_time(fake_email['send_time'], current_date)
            processed_email['send_time'] = send_time
        else:
            # Random time in the past month
            days_ago = random.randint(1, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            send_time = current_date - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            processed_email['send_time'] = send_time
        
        processed_emails.append(processed_email)
    
    print(f"✅ Processed {len(processed_emails)} fake emails with resolved date placeholders")
    return processed_emails

def inject_fake_emails(email_config, fake_emails_file, num_emails=None):
    """
    Main function to inject fake emails into IMAP inbox
    
    Args:
        email_config (dict): IMAP configuration
        fake_emails_file (Path): Path to fake emails JSON file
        num_emails (int, optional): Number of fake emails to inject (50-100 if None)
    
    Returns:
        tuple: (success: bool, count: int) - Success status and number of emails injected
    """
    print("🎲 Loading and processing fake emails...")
    
    # Load and process fake emails
    fake_emails = load_and_process_fake_emails(fake_emails_file, num_emails)
    
    if not fake_emails:
        print("❌ No fake emails loaded")
        return False, 0
    
    # Sort fake emails by send_time (newest first - closest to current time)
    print(f"📅 Sorting {len(fake_emails)} fake emails by timestamp (newest first)...")
    fake_emails.sort(key=lambda x: x.get('send_time'), reverse=True)
    
    if fake_emails:
        newest_time = fake_emails[0].get('send_time')
        oldest_time = fake_emails[-1].get('send_time')
        print(f"   📧 Newest fake: {fake_emails[0].get('sender_name', 'Unknown')} ({newest_time.strftime('%Y-%m-%d %H:%M') if newest_time else 'No time'})")
        print(f"   📧 Oldest fake: {fake_emails[-1].get('sender_name', 'Unknown')} ({oldest_time.strftime('%Y-%m-%d %H:%M') if oldest_time else 'No time'})")
    
    print(f"\n📥 Injecting {len(fake_emails)} fake emails...")
    
    # Inject emails
    success = inject_emails_to_imap(email_config, fake_emails)
    
    return success, len(fake_emails)

if __name__ == "__main__":
    # Example usage
    from argparse import ArgumentParser
    
    parser = ArgumentParser(description="Inject fake emails into IMAP inbox")
    parser.add_argument("--email_config", required=True, help="Email configuration JSON file")
    parser.add_argument("--fake_emails_file", required=True, help="Fake emails JSON file")
    parser.add_argument("--num_emails", type=int, default=None, help="Number of fake emails to inject (50-100 if not specified)")
    
    args = parser.parse_args()
    
    # Load email config
    with open(args.email_config, 'r', encoding='utf-8') as f:
        email_config = json.load(f)
    
    # Inject fake emails
    success, count = inject_fake_emails(email_config, Path(args.fake_emails_file), args.num_emails)
    
    if success:
        print(f"🎉 Successfully injected {count} fake emails!")
    else:
        print("❌ Failed to inject fake emails")
        exit(1)