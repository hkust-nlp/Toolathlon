import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from email.utils import formataddr
import argparse
import json
import sys
from pathlib import Path
import re
from datetime import datetime, timedelta

class EmailSendError(Exception):
    """Error occurred during sending emails."""
    pass

class LocalEmailSender:
    def __init__(self, sender_email, password, smtp_server='localhost', smtp_port=1587, use_ssl=False, use_starttls=False, use_auth=True, verbose=True):
        """
        Initialize local email sender.
        :param sender_email: Sender email address
        :param password: Email password
        :param smtp_server: SMTP server address
        :param smtp_port: SMTP server port
        :param use_ssl: Use SSL
        :param use_starttls: Use STARTTLS
        :param use_auth: Use authentication
        :param verbose: Print verbose information
        """
        self.sender_email = sender_email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self.use_starttls = use_starttls
        self.use_auth = use_auth
        self.verbose = verbose
    
    def _log(self, message, force=False):
        """Print log information."""
        if self.verbose or force:
            print(message)
    
    def send_email(self, receiver_email, sender_name, subject, content, content_type='plain'):
        """
        Send a single email.
        :param receiver_email: Receiver's email address
        :param sender_name: Sender's display name
        :param subject: Email subject
        :param content: Email content
        :param content_type: 'plain' or 'html'
        """
        try:
            # Create email message
            msg = MIMEMultipart()
            
            # Set sender info (with custom sender name)
            msg['From'] = formataddr((sender_name, self.sender_email))
            msg['To'] = receiver_email
            msg['Subject'] = subject
            
            # Attach content
            msg.attach(MIMEText(content, content_type, 'utf-8'))
            
            # Connect to the mail server
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.use_starttls:
                    server.starttls()  # Enable TLS
            
            # Login if authentication is required
            if self.use_auth:
                server.login(self.sender_email, self.password)
            
            # Send the email
            server.send_message(msg)
            server.quit()
            
            self._log("✅ Email sent successfully!")
            self._log(f"   From: {sender_name}")
            self._log(f"   To: {receiver_email}")
            self._log(f"   Subject: {subject}")
            self._log("-" * 50)
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to send email - From: {sender_name}, Subject: {subject}, Error: {str(e)}"
            self._log(f"❌ {error_msg}", force=True)
            self._log("-" * 50)
            return False
    
    def send_batch_emails(self, receiver_email, email_list, delay=1):
        """
        Send a batch of emails.
        :param receiver_email: Receiver's email address
        :param email_list: List of emails, each as a dict
        :param delay: Delay in seconds between emails
        :return: (success_count, fail_count, failed_emails)
        """
        self._log(f"Starting batch send for {len(email_list)} emails...\n")
        
        success_count = 0
        fail_count = 0
        failed_emails = []
        
        for i, email_data in enumerate(email_list, 1):
            self._log(f"Sending email {i}/{len(email_list)}...")
            
            # Detect content type automatically
            content_type = email_data.get('content_type', 'plain')
            if content_type == 'auto':
                # Simple detection for HTML tags
                content = email_data['content']
                if '<html>' in content.lower() or '<body>' in content.lower() or '<p>' in content or '<div>' in content:
                    content_type = 'html'
                else:
                    content_type = 'plain'
            
            success = self.send_email(
                receiver_email=receiver_email,
                sender_name=email_data['sender_name'],
                subject=email_data['subject'],
                content=email_data['content'],
                content_type=content_type
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                failed_emails.append({
                    'index': i,
                    'sender_name': email_data['sender_name'],
                    'subject': email_data['subject']
                })
            
            if i < len(email_list):
                self._log(f"Waiting {delay} seconds before sending the next email...\n")
                time.sleep(delay)
        
        self._log("\nBatch sending completed!")
        self._log(f"Success: {success_count}, Failed: {fail_count}")
        
        return success_count, fail_count, failed_emails

def format_email_with_personal_info(email_data, 
                                    placeholder_values, 
                                    today,
                                    verbose=True):
    """
    Format email data with values from `personal_info` style dict.
    Placeholder format: <<<<||||key||||>>>>
    :param email_data: Original email data dict
    :param placeholder_values: Placeholder key-value mapping
    :param today: Today's date (ISO string)
    :param verbose: Print verbose information
    :return: Formatted email data dict
    """
    def _log(message, force=False):
        if verbose or force:
            print(message)
    
    formatted_email = email_data.copy()
    
    try:
        # Format each string field
        for key, value in formatted_email.items():
            if isinstance(value, str):
                try:
                    # Find all placeholders <<<<||||key||||>>>>
                    pattern = r'<<<<\|\|\|\|([\w+-]+)\|\|\|\|>>>>'
                    matches = re.findall(pattern, value)
                    
                    formatted_value = value
                    for match in matches:
                        placeholder = f'<<<<||||{match}||||>>>>'
                        if match in placeholder_values:
                            replacement = str(placeholder_values[match])
                            formatted_value = formatted_value.replace(placeholder, replacement)
                        # Date/year placeholders
                        elif match == 'year' or match.startswith('today+') or match.startswith('today-'):
                            # 'today' is passed as ISO format string (e.g. 2025-06-30)
                            try:
                                if match == 'year':
                                    # Replace with year 30 days from today
                                    today_date = datetime.fromisoformat(today)
                                    future_date = today_date + timedelta(days=30)
                                    replacement = str(future_date.year)
                                elif match.startswith('today+'):
                                    days_to_add = int(match[6:])
                                    today_date = datetime.fromisoformat(today)
                                    future_date = today_date + timedelta(days=days_to_add)
                                    replacement = future_date.strftime('%Y-%m-%d')
                                elif match.startswith('today-'):
                                    days_to_subtract = int(match[6:])
                                    today_date = datetime.fromisoformat(today)
                                    past_date = today_date - timedelta(days=days_to_subtract)
                                    replacement = past_date.strftime('%Y-%m-%d')
                                else:
                                    replacement = placeholder
                                
                                formatted_value = formatted_value.replace(placeholder, replacement)
                            except (ValueError, TypeError) as e:
                                _log(f"⚠️  Date processing error: {e}", force=True)
                                pass
                        else:
                            _log(f"⚠️  Key not found in placeholder info: {match}", force=True)
                    
                    formatted_email[key] = formatted_value
                    
                except Exception as e:
                    _log(f"⚠️  Error formatting field '{key}': {e}", force=True)
                    pass
        
        return formatted_email
        
    except Exception as e:
        _log(f"⚠️  Error formatting email data: {e}", force=True)
        return email_data

def load_emails_from_jsonl(file_path, placeholder_file_path, verbose=True):
    """
    Load email data from JSONL file.
    :param file_path: JSONL file path
    :param placeholder_file_path: Placeholder file path
    :param verbose: Print verbose information
    :return: List of emails
    """
    def _log(message, force=False):
        if verbose or force:
            print(message)
    
    emails = []
    placeholder_values = {}
    with open(placeholder_file_path, 'r', encoding='utf-8') as f:
        placeholder_values = json.load(f)

    # Get today's date in ISO format (YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Save today's date to file for later use
    # Relative to send_email.py: ../groundtruth_workspace/today.txt
    script_dir = Path(__file__).parent.parent
    today_file_path = script_dir / 'groundtruth_workspace' / 'today.txt'
    today_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(today_file_path, 'w', encoding='utf-8') as f:
        f.write(today)
    _log(f"✅ Saved today's date to: {today_file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                try:
                    email_data = json.loads(line)
                    
                    # Check required fields
                    required_fields = ['sender_name', 'subject', 'content']
                    missing_fields = [field for field in required_fields if field not in email_data]
                    
                    if missing_fields:
                        _log(f"⚠️  Line {line_num}: Missing required field(s): {missing_fields}", force=True)
                        continue
                    
                    # If content_type is not specified, set to 'auto'
                    if 'content_type' not in email_data:
                        email_data['content_type'] = 'auto'
                    
                    # Format email with personal info
                    formatted_email = format_email_with_personal_info(email_data, placeholder_values, today, verbose=verbose)
                    emails.append(formatted_email)
                    
                except json.JSONDecodeError as e:
                    _log(f"⚠️  Line {line_num}: JSON decode error: {e}", force=True)
                    continue
                    
        _log(f"✅ Successfully loaded {len(emails)} emails")
        return emails
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error while reading file: {e}")
        sys.exit(1)

def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Local Email Batch Sending Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python gmail_sender.py --sender your@gmail.com --password "your_app_password" --receiver target@example.com --jsonl emails.jsonl

JSONL File Format Example:
  {"sender_name": "Zhang San", "subject": "Test Email", "content": "This is the content"}
  {"sender_name": "Li Si", "subject": "HTML Email", "content": "<h1>HTML Title</h1><p>Body</p>", "content_type": "html"}
  
Placeholder Format:
  Use <<<<||||key||||>>>> as placeholder, where key is the key in the personal_info json.
  Example: "Hello <<<<||||name||||>>>>, your email is <<<<||||email||||>>>>"
        '''
    )
    
    parser.add_argument(
        '--sender', '-s',
        required=True,
        help='Sender email address'
    )
    
    parser.add_argument(
        '--password', '-p',
        required=True,
        help='Email password'
    )
    
    parser.add_argument(
        '--receiver', '-r',
        required=True,
        help='Receiver email address'
    )
    
    parser.add_argument(
        '--jsonl', '-j',
        required=True,
        help='Path to JSONL file containing emails'
    )

    parser.add_argument(
        '--placeholder', '-pl',
        required=True,
        help='Path to json file containing placeholder key-values'
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=2.0,
        help='Delay in seconds between consecutive emails (default: 2 seconds)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Check JSONL file and show email preview, don\'t actually send emails'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Quiet mode, only print when error occurs'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Send emails without confirmation'
    )
    
    return parser

def main():
    # Parse CLI arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Set verbose mode
    verbose = not args.quiet
    
    # Print configuration
    if verbose:
        print("=" * 60)
        print("Local Email Batch Sending Tool")
        print("=" * 60)
        print(f"Sender: {args.sender}")
        print(f"Receiver: {args.receiver}")
        print(f"Email data file: {args.jsonl}")
        print(f"Placeholder file: {args.placeholder}")
        print(f"Send delay: {args.delay} seconds")
        print("=" * 60)
        print()
    
    # Load emails
    if verbose:
        print("Loading email data...")
    
    emails = load_emails_from_jsonl(args.jsonl, args.placeholder, verbose=verbose)

    if not emails:
        print("❌ No valid emails to send.")
        sys.exit(1)
    
    # Dry run mode - preview only
    if args.dry_run:
        if verbose:
            print("\n🔍 Dry-run mode - Email Preview:\n")
            for i, email in enumerate(emails, 1):
                print(f"Email {i}:")
                print(f"  Sender Name: {email['sender_name']}")
                print(f"  Subject: {email['subject']}")
                print(f"  Content-Type: {email.get('content_type', 'auto')}")
                preview = email['content'][:100]
                print(f"  Content Preview: {preview}{'...' if len(email['content']) > 100 else ''}")
                print("-" * 40)
            print(f"\nTotal: {len(emails)} emails")
        else:
            print(f"Dry-run: {len(emails)} emails loaded")
        return
    
    # Confirmation before sending
    if not args.no_confirm:
        if verbose:
            print(f"\nReady to send {len(emails)} emails to {args.receiver}")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != 'y':
            if verbose:
                print("Sending aborted.")
            sys.exit(0)
    
    # Create sender and send emails
    if verbose:
        print("\nStarting to send emails...\n")
    
    sender = LocalEmailSender(args.sender, args.password, use_auth=False, verbose=verbose)
    success_count, fail_count, failed_emails = sender.send_batch_emails(
        receiver_email=args.receiver,
        email_list=emails,
        delay=args.delay
    )
    
    # Final result
    if verbose:
        print("\n" + "=" * 60)
        print("Send completed!")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
        print("=" * 60)
    else:
        # Quiet mode just print summary
        print(f"Finished: {success_count} successful / {len(emails)} total")
    
    # Print details and raise error if any failures
    if fail_count > 0:
        print(f"\n❌ {fail_count} emails failed to send:")
        for failed in failed_emails:
            print(f"  - Email {failed['index']}: {failed['sender_name']} - {failed['subject']}")
        
        # Raise error so the program exits with nonzero status
        raise EmailSendError(f"{fail_count} email(s) failed to send.")

if __name__ == "__main__":
    try:
        main()
    except EmailSendError:
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Program Error: {e}")
        sys.exit(1)