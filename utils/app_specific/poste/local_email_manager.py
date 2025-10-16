import imaplib
import smtplib
import json
import email
import time
import re
from email import policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple


class EmailSendError(Exception):
    pass


class LocalEmailManager:
    
    def __init__(self, config_file: str, verbose: bool = True):

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.email = self.config['email']
        self.password = self.config.get('password') or ""  # Allow empty password (local uncertified)
        self.name = self.config.get('name') or self.email
        self.verbose = verbose

        # IMAP configuration
        self.imap_server = self.config['imap_server']
        self.imap_port = int(self.config['imap_port'])

        # SMTP configuration
        self.smtp_server = self.config['smtp_server']
        self.smtp_port = int(self.config['smtp_port'])

        # Connection options
        self.use_ssl = self.config.get('use_ssl', False)
        self.use_starttls = self.config.get('use_starttls', False)

    def _log(self, message: str, force: bool = False):
        """Print log information"""
        if self.verbose or force:
            print(message)

    # ========================================
    # IMAP related functions
    # ========================================
    
    def connect_imap(self) -> imaplib.IMAP4:
        """Connect to IMAP server and login (if necessary)"""
        if self.use_ssl:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        else:
            mail = imaplib.IMAP4(self.imap_server, self.imap_port)

        try:
            mail.login(self.email, self.password)
        except imaplib.IMAP4.error as e:
            raise RuntimeError(f"IMAP login failed: {e}")
        return mail

    def list_mailboxes(self) -> List[str]:
        """List all available email folders"""
        mail = self.connect_imap()
        try:
            typ, mailboxes = mail.list()
            if typ != 'OK':
                raise RuntimeError("Unable to get mailbox list")

            mailbox_names = []
            for mailbox in mailboxes:
                # Parse mailbox string, extract folder name
                # Format usually is: (\\HasNoChildren) "." "INBOX"
                mailbox_str = mailbox.decode() if isinstance(mailbox, bytes) else str(mailbox)
                self._log(f"Debug: Original mailbox information: {mailbox_str}")

                # Try multiple parsing methods
                if '"' in mailbox_str:
                    # Method 1: Use quotes to split
                    parts = mailbox_str.split('"')
                    if len(parts) >= 3:
                        # Usually the last quote contains the folder name
                        for i in range(len(parts)-1, 0, -1):
                            if parts[i-1] == '"' or (i == len(parts)-1 and parts[i].strip()):
                                name = parts[i] if i == len(parts)-1 else parts[i-1]
                                if name and name not in ['.', '']:
                                    mailbox_names.append(name)
                                    break
                else:
                    # Method 2: Simple split, take the last non-empty part
                    parts = mailbox_str.split()
                    if parts:
                        name = parts[-1]
                        if name and name not in ['.', '']:
                            mailbox_names.append(name)

            # Remove duplicates and ensure INBOX always exists
            mailbox_names = list(set(mailbox_names))
            if 'INBOX' not in mailbox_names:
                mailbox_names.append('INBOX')

            self._log(f"📁 Available email folders: {mailbox_names}")
            return mailbox_names
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()

    def clear_all_emails(self, mailbox: str = 'INBOX') -> None:
        """Clear a specific mailbox (default INBOX)"""
        mail = self.connect_imap()
        try:
            typ, _ = mail.select(mailbox)
            if typ != 'OK':
                raise RuntimeError(f"Unable to select mailbox {mailbox}")

            typ, data = mail.search(None, 'ALL')
            if typ != 'OK':
                raise RuntimeError("Search email failed")

            ids = data[0].split()
            if not ids:
                self._log("ℹ️ Inbox is empty, no cleanup needed.")
            else:
                for num in ids:
                    mail.store(num, '+FLAGS', r'(\Deleted)')
                mail.expunge()
                self._log("✅ All emails in the mailbox have been cleared")
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()

    def get_all_emails(self, mailbox: str = 'INBOX') -> List[Dict[str, str]]:
        """Get all emails in the mailbox (subject/sender/date/body)"""
        mail = self.connect_imap()
        emails = []
        try:
            typ, _ = mail.select(mailbox)
            if typ != 'OK':
                raise RuntimeError(f"Unable to select mailbox {mailbox}")

            typ, data = mail.search(None, 'ALL')
            if typ != 'OK':
                raise RuntimeError("Search email failed")

            ids = data[0].split()
            if not ids:
                return []

            for num in ids:
                typ, msg_data = mail.fetch(num, '(RFC822)')
                if typ != 'OK' or not msg_data or not msg_data[0]:
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email, policy=policy.default)

                emails.append({
                    'subject': msg['Subject'],
                    'from': msg['From'],
                    'date': msg['Date'],
                    'body': self._extract_body(msg),
                })
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()
        return emails

    # ========================================
    # SMTP related functions
    # ========================================
    
    def send_email(self, to_email: str, subject: str, content: str, 
                   content_type: str = 'html', sender_name: Optional[str] = None) -> bool:
        """
        Send email to local SMTP
        
        Args:
            to_email: Receiver email
            subject: Email title
            content: Email content
            content_type: Content type 'plain' or 'html'
            sender_name: Sender display name, default using the name in the configuration
            
        Returns:
            bool: Whether the email was sent successfully
        """
        try:
            # Build email
            msg = MIMEMultipart()
            display_name = sender_name or self.name
            # Only display the sender name, not the email address
            msg['From'] = display_name
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(content, _subtype=content_type, _charset='utf-8'))

            # Establish SMTP connection
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
                server.ehlo()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                server.ehlo_or_helo_if_needed()

                # STARTTLS: Only try if enabled in configuration
                if self.use_starttls:
                    if 'starttls' in getattr(server, 'esmtp_features', {}):
                        server.starttls()
                        server.ehlo()
                    else:
                        self._log("ℹ️ Server does not support STARTTLS, continue with plain text.")

            # Login: Only try if server claims to support AUTH
            esmtp_features = getattr(server, 'esmtp_features', {})
            if 'auth' in esmtp_features and self.password:
                try:
                    server.login(self.email, self.password)
                except smtplib.SMTPNotSupportedError:
                    self._log("ℹ️ Server does not support AUTH, skip login.")
                except smtplib.SMTPException as e:
                    self._log(f"ℹ️ SMTP login failed (will try uncertified send): {e}")

            # Send email, use the real email address as the sender but display a custom name
            server.send_message(msg, from_addr=self.email)
            server.quit()
            self._log(f"✅ Email sent successfully: {subject}")
            self._log(f"    Sender: {display_name}")
            self._log(f"    Receiver: {to_email}")
            self._log("-" * 50)
            return True

        except Exception as e:
            self._log(f"❌ Email sent failed: {e}", force=True)
            self._log(f"    Sender: {sender_name or self.name}")
            self._log(f"    Subject: {subject}")
            self._log("-" * 50)
            return False

    def send_batch_emails(self, receiver_email: str, email_list: List[Dict[str, Any]], 
                         delay: float = 1) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        Batch send emails
        
        Args:
            receiver_email: Receiver email
            email_list: Email list, each element is a dictionary
            delay: Delay between each email (seconds)
            
        Returns:
            Tuple[success_count, fail_count, failed_emails]
        """
        self._log(f"Start batch sending {len(email_list)} emails...\n")

        success_count = 0
        fail_count = 0
        failed_emails = []

        for i, email_data in enumerate(email_list, 1):
            self._log(f"Sending the {i}/{len(email_list)} email...")

            # Automatically detect content type
            content_type = email_data.get('content_type', 'plain')
            if content_type == 'auto':
                content = email_data['content']
                if ('<html>' in content.lower() or '<body>' in content.lower() or 
                    '<p>' in content or '<div>' in content):
                    content_type = 'html'
                else:
                    content_type = 'plain'

            success = self.send_email(
                to_email=receiver_email,
                subject=email_data['subject'],
                content=email_data['content'],
                content_type=content_type,
                sender_name=email_data['sender_name']
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
                self._log(f"Wait {delay} seconds before sending the next email...\n")
                time.sleep(delay)

        self._log("\nBatch sending completed!")
        self._log(f"Success: {success_count} emails, Fail: {fail_count} emails")

        return success_count, fail_count, failed_emails

    # ========================================
    # Data processing related functions
    # ========================================
    
    def format_email_with_placeholders(self, email_data: Dict[str, Any], 
                                     placeholder_values: Dict[str, str], 
                                     today: str) -> Dict[str, Any]:
        """
        Format email data with placeholders
        Placeholder format: <<<<||||key||||>>>>
        
        Args:
            email_data: Original email data dictionary
            placeholder_values: Placeholder key-value pairs
            today: Today's date (ISO format)
            
        Returns:
            Formatted email data dictionary
        """
        formatted_email = email_data.copy()

        try:
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
                            elif match == 'year' or match.startswith('today+') or match.startswith('today-'):
                                try:
                                    if match == 'year':
                                        today_date = datetime.fromisoformat(today)
                                        future_date = today_date + timedelta(days=30)
                                        replacement = str(future_date.year)
                                    elif match.startswith('today+'):
                                        days_to_add = int(match[6:])  # Remove 'today+' prefix
                                        today_date = datetime.fromisoformat(today)
                                        future_date = today_date + timedelta(days=days_to_add)
                                        replacement = future_date.strftime('%Y-%m-%d')
                                    elif match.startswith('today-'):
                                        days_to_subtract = int(match[6:])  # Remove 'today-' prefix
                                        today_date = datetime.fromisoformat(today)
                                        past_date = today_date - timedelta(days=days_to_subtract)
                                        replacement = past_date.strftime('%Y-%m-%d')
                                    else:
                                        replacement = placeholder

                                    formatted_value = formatted_value.replace(placeholder, replacement)
                                except (ValueError, TypeError) as e:
                                    self._log(f"⚠️ Date processing error: {e}", force=True)
                            else:
                                self._log(f"⚠️ Placeholder key not found: {match}", force=True)

                        formatted_email[key] = formatted_value

                    except Exception as e:
                        self._log(f"⚠️ Error formatting field '{key}': {e}", force=True)

            return formatted_email

        except Exception as e:
            self._log(f"⚠️ Error formatting email data: {e}", force=True)
            return email_data

    def load_emails_from_jsonl(self, file_path: str, placeholder_file_path: str = None, 
                              save_today_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load email data from JSONL file
        
        Args:
            file_path: JSONL file path
            placeholder_file_path: Placeholder file path
            save_today_to: File path to save today's date
            
        Returns:
            Email list
        """
        emails = []
        placeholder_values = {}
        
        if placeholder_file_path:
            with open(placeholder_file_path, 'r', encoding='utf-8') as f:
                placeholder_values = json.load(f)

        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')

        # Save today's date to specified file
        if save_today_to:
            today_path = Path(save_today_to)
            today_path.parent.mkdir(parents=True, exist_ok=True)
            with open(today_path, 'w', encoding='utf-8') as f:
                f.write(today)
            self._log(f"✅ Today's date saved to: {today_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    try:
                        email_data = json.loads(line)

                        # Verify required fields
                        required_fields = ['sender_name', 'subject', 'content']
                        missing_fields = [field for field in required_fields if field not in email_data]

                        if missing_fields:
                            self._log(f"⚠️ Line {line_num} missing required fields: {missing_fields}", force=True)
                            continue

                        # Set default content type
                        if 'content_type' not in email_data:
                            email_data['content_type'] = 'auto'

                        # Format email data with placeholders
                        if placeholder_values:
                            formatted_email = self.format_email_with_placeholders(
                                email_data, placeholder_values, today)
                            emails.append(formatted_email)
                        else:
                            emails.append(email_data)

                    except json.JSONDecodeError as e:
                        self._log(f"⚠️ Line {line_num} JSON parsing error: {e}", force=True)
                        continue

            self._log(f"✅ Successfully loaded {len(emails)} emails")
            return emails

        except FileNotFoundError:
            self._log(f"❌ File not found: {file_path}", force=True)
            raise
        except Exception as e:
            self._log(f"❌ Error reading file: {e}", force=True)
            raise

    # ========================================
    # Helper methods
    # ========================================
    
    def _extract_body(self, msg: email.message.EmailMessage) -> str:
        """
        Prioritize returning text/plain; if none, return text/html; if none, return empty string.
        Skip attachments when traversing multipart.
        """
        if msg.is_multipart():
            plain_text = None
            html_text = None
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = (part.get('Content-Disposition') or '').lower()
                if 'attachment' in disp:
                    continue
                if ctype == 'text/plain' and plain_text is None:
                    plain_text = self._safe_decode(part)
                elif ctype == 'text/html' and html_text is None:
                    html_text = self._safe_decode(part)
            return plain_text if plain_text is not None else (html_text or "")
        else:
            ctype = msg.get_content_type()
            if ctype in ('text/plain', 'text/html'):
                return self._safe_decode(msg)
            return ""

    def _safe_decode(self, part: email.message.Message) -> str:
        """Decode according to declared charset, default utf-8, use replacement strategy if error"""
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ""
            charset = part.get_content_charset() or 'utf-8'
            return payload.decode(charset, errors='replace')
        except Exception:
            try:
                return payload.decode('utf-8', errors='replace')
            except Exception:
                return ""

    def get_emails_with_attachments(self, subject_keyword: str = None, 
                                  mailbox: str = 'INBOX') -> List[Dict[str, Any]]:
        """
        Get emails with attachments
        
        Args:
            subject_keyword: Subject keyword
            mailbox: Email box name
            
        Returns:
            Email list with attachment information
        """
        mail = self.connect_imap()
        emails = []
        try:
            typ, _ = mail.select(mailbox)
            if typ != 'OK':
                raise RuntimeError(f"Unable to select mailbox {mailbox}")

            # Search emails
            if subject_keyword:
                typ, data = mail.search(None, f'SUBJECT "{subject_keyword}"')
            else:
                typ, data = mail.search(None, 'ALL')
            
            if typ != 'OK':
                raise RuntimeError("Search email failed")

            ids = data[0].split()
            if not ids:
                return []

            for num in ids:
                typ, msg_data = mail.fetch(num, '(RFC822)')
                if typ != 'OK' or not msg_data or not msg_data[0]:
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email, policy=policy.default)

                # Extract attachment information
                attachments = self._extract_attachments_info(msg)
                
                if attachments:  # Only return emails with attachments
                    emails.append({
                        'id': num.decode(),
                        'subject': msg['Subject'],
                        'from': msg['From'],
                        'date': msg['Date'],
                        'body': self._extract_body(msg),
                        'attachments': attachments,
                        'raw_message': msg
                    })
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()
        return emails

    def _extract_attachments_info(self, msg: email.message.EmailMessage) -> List[Dict[str, str]]:
        """
        Extract attachment information from email (without downloading)
        
        Args:
            msg: Email object
            
        Returns:
            Attachment information list, each element contains filename, content_type, size
        """
        attachments = []
        
        for part in msg.walk():
            disp = (part.get('Content-Disposition') or '').lower()
            if 'attachment' in disp:
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        'filename': filename,
                        'content_type': part.get_content_type(),
                        'size': len(part.get_payload(decode=False)) if part.get_payload(decode=False) else 0
                    })
        return attachments

    def download_attachments_from_email(self, email_data: Dict[str, Any], 
                                      download_dir: str) -> List[str]:
        """
        Download attachments from email
        
        Args:
            email_data: Email data containing raw_message
            download_dir: Download directory
            
        Returns:
            Downloaded file path list
        """
        import os
        
        msg = email_data['raw_message']
        download_path = Path(download_dir)
        download_path.mkdir(parents=True, exist_ok=True)
        
        downloaded_files = []
        
        for part in msg.walk():
            disp = (part.get('Content-Disposition') or '').lower()
            if 'attachment' in disp:
                filename = part.get_filename()
                if filename:
                    try:
                        file_path = download_path / filename
                        with open(file_path, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        downloaded_files.append(str(file_path))
                        self._log(f"✅ Downloaded attachment: {filename}")
                    except Exception as e:
                        self._log(f"❌ Download attachment failed {filename}: {e}", force=True)
        
        return downloaded_files