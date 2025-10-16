import imaplib
import email
from email.header import decode_header
from typing import Dict, List, Tuple
import re

from utils.general.helper import print_color
from utils.general.helper import normalize_str


def clear_folder(folder_name: str, config: Dict) -> None:
    """
    Clear the specified IMAP folder with the provided email configuration.

    Expected config keys:
    - "email": Email account address
    - "password": Account password
    - "imap_server": IMAP server
    - "imap_port": IMAP port
    - "use_ssl": Use SSL or not (bool)
    - "use_starttls": Use STARTTLS or not (bool)
    """

    server = config.get("imap_server")
    port = config.get("imap_port")
    email_addr = config.get("email") or config.get("username")
    password = config.get("password")
    use_ssl = bool(config.get("use_ssl"))
    use_starttls = bool(config.get("use_starttls"))

    if not server or not port or not email_addr or not password:
        raise ValueError("IMAP configuration incomplete: email/password/imap_server/imap_port required")

    imap = None
    try:
        if use_ssl:
            imap = imaplib.IMAP4_SSL(server, port)
        else:
            imap = imaplib.IMAP4(server, port)
            if use_starttls:
                imap.starttls()

        imap.login(email_addr, password)

        status, _ = imap.select(folder_name)
        if status != "OK":
            print_color(f"Failed to select folder: {folder_name}", "red")
            return

        # If the folder is empty, some servers may return BAD/NO for 1:* sequence; check beforehand
        s_status, s_data = imap.search(None, "ALL")
        if s_status == "OK":
            if not s_data or s_data[0] is None or s_data[0].strip() == b"":
                print_color(f"Mailbox {email_addr}'s `{folder_name}` is empty, no cleanup needed", "yellow")
                return

        # Mark all emails as deleted and expunge
        imap.store("1:*", "+FLAGS.SILENT", r"(\Deleted)")
        imap.expunge()

        print_color(f"Cleared mailbox {email_addr}'s `{folder_name}` folder", "green")
    except Exception as e:
        print_color(f"Failed to clear `{folder_name}` ({email_addr}): {e}", "red")
        raise
    finally:
        try:
            if imap is not None:
                try:
                    imap.close()
                except Exception:
                    # Ignore if not selected or already closed by server
                    pass
                imap.logout()
        except Exception:
            pass



def _connect_imap(config: Dict) -> imaplib.IMAP4:
    """
    Establish an IMAP connection and log in with the given configuration.

    Expected config keys:
    - "email" or "username"
    - "password"
    - "imap_server"
    - "imap_port"
    - "use_ssl" (bool)
    - "use_starttls" (bool)
    """
    server = config.get("imap_server")
    port = config.get("imap_port")
    email_addr = config.get("email") or config.get("username")
    password = config.get("password")
    use_ssl = bool(config.get("use_ssl"))
    use_starttls = bool(config.get("use_starttls"))

    if not server or not port or not email_addr or not password:
        raise ValueError("IMAP configuration incomplete: email/password/imap_server/imap_port required")

    if use_ssl:
        imap = imaplib.IMAP4_SSL(server, port)
    else:
        imap = imaplib.IMAP4(server, port)
        if use_starttls:
            imap.starttls()

    imap.login(email_addr, password)
    return imap


def _close_imap_safely(imap) -> None:
    try:
        if imap is not None:
            try:
                imap.close()
            except Exception:
                pass
            imap.logout()
    except Exception:
        pass


def _decode_mime_words(value: str) -> str:
    if not value:
        return ""
    try:
        decoded_parts = decode_header(value)
        subject = ""
        for part, enc in decoded_parts:
            if isinstance(part, bytes):
                subject += part.decode(enc or "utf-8", errors="replace")
            else:
                subject += part
        return subject
    except Exception:
        return value


def _extract_text_from_message(msg: email.message.Message) -> str:
    """
    Prefer extracting text/plain. If not found, try decoding text/html and remove basic HTML tags.
    """
    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or "utf-8"
                    return part.get_payload(decode=True).decode(charset, errors="replace")
            # Fallback: use the first text/html part
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    html = part.get_payload(decode=True).decode(charset, errors="replace")
                    # Simple HTML tag removal
                    return _strip_html(html)
        else:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload is None:
                # Some servers do not require decode=True
                payload = msg.get_payload()
                if isinstance(payload, str):
                    return payload
                return ""
            text = payload.decode(charset, errors="replace")
            if content_type == "text/html":
                return _strip_html(text)
            return text
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    """
    Non-strict HTML tag stripper, suitable for basic comparison.
    """
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def find_emails_from_sender(config: Dict, sender_query: str, folder: str = "INBOX", fetch_limit: int = 200) -> List[Dict]:
    """
    Find emails from a specific sender in a given folder, according to the mailbox configuration.

    Args:
        config: IMAP mailbox configuration (must include email/password/imap_server/imap_port, etc.)
        sender_query: May be the sender's email or name, used in IMAP FROM search
        folder: Target folder (default "INBOX")
        fetch_limit: Maximum emails to fetch (tail slice from the result)

    Returns:
        List[Dict]: [{"subject": str, "body": str, "raw_subject": str}] in order from newest to oldest (approximate)
    """
    imap = None
    results: List[Dict] = []
    try:
        imap = _connect_imap(config)
        status, _ = imap.select(folder)
        if status != "OK":
            print_color(f"Failed to select folder: {folder}", "red")
            return []

        typ, data = imap.search(None, f'(FROM "{sender_query}")')
        if typ != "OK" or not data or data[0] is None or data[0].strip() == b"":
            return []

        msg_ids = data[0].split()
        # Take the latest fetch_limit emails
        msg_ids = msg_ids[-fetch_limit:]

        for msg_id in msg_ids:
            typ, msg_data = imap.fetch(msg_id, '(RFC822)')
            if typ != 'OK' or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            raw_subject = msg.get('Subject', '')
            subject = _decode_mime_words(raw_subject)
            body = _extract_text_from_message(msg)
            results.append({
                "subject": subject,
                "body": body,
                "raw_subject": raw_subject
            })
        # Reverse so newest messages come first
        results.reverse()
        return results
    except imaplib.IMAP4.error as e:
        print_color(f"IMAP error for {config.get('email') or config.get('username')}: {str(e)}", "red")
        return []
    except Exception as e:
        print_color(f"Error fetching emails for {config.get('email') or config.get('username')}: {str(e)}", "red")
        return []
    finally:
        _close_imap_safely(imap)


def mailbox_has_email_matching_body(config: Dict, sender_query: str, expected_body: str, subject: str = None, folder: str = "INBOX") -> Tuple[bool, Dict]:
    """
    Check whether there is an email from sender_query whose body matches expected_body (after normalize_str).
    If subject is not None, the email subject must also match.

    Returns:
        (matched: bool, detail: Dict)
    """
    expected_body_norm = normalize_str(expected_body)
    expected_subject_norm = normalize_str(subject) if subject is not None else None

    emails = find_emails_from_sender(config, sender_query, folder)
    for item in emails:
        body_matched = normalize_str(item.get("body", "")) == expected_body_norm
        subject_matched = True

        if expected_subject_norm is not None:
            # item["subject"] is already a decoded subject, compare using normalized version;
            # if not present, fall back to decoded original subject
            email_subject = item.get("subject", "")
            if not email_subject and item.get("raw_subject"):
                email_subject = _decode_mime_words(item.get("raw_subject", ""))
            subject_matched = normalize_str(email_subject) == expected_subject_norm

        if body_matched and subject_matched:
            return True, item

    return False, {"emails_checked": len(emails)}


def decode_email_subject(subject: str) -> str:
    """Decode MIME-encoded email subject to plain text."""
    if not subject:
        return ""
    try:
        decoded_parts = email.header.decode_header(subject)
        decoded_subject = ""
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                charset = charset or 'utf-8'
                decoded_subject += part.decode(charset, errors='replace')
            else:
                decoded_subject += str(part)
        return decoded_subject.lower()
    except Exception:
        # On failure, fall back to original subject
        return subject.lower()

def check_sender_outbox(sender_config: dict, interference_emails: set) -> Tuple[bool, list]:
    """
    Scan the sender's outbox to ensure no emails were sent to the provided interference addresses.
    Returns (True, []) if none detected; otherwise (False, list of unexpected sends).
    """
    passed = True
    unexpected_sends = []

    try:
        if sender_config['use_ssl']:
            imap_connection = imaplib.IMAP4_SSL(sender_config['imap_server'], sender_config['imap_port'])
        else:
            imap_connection = imaplib.IMAP4(sender_config['imap_server'], sender_config['imap_port'])

        imap_connection.login(sender_config['email'], sender_config['password'])
        imap_connection.select('Sent')

        status, all_message_numbers = imap_connection.search(None, 'ALL')
        if status != 'OK':
            print(f"[OUTBOX][{sender_config['email']}] Search failed")
            return False, []

        all_messages = all_message_numbers[0].split()

        for num in all_messages:
            try:
                status, message_data = imap_connection.fetch(num, '(RFC822)')
                if status == 'OK':
                    email_message = email.message_from_bytes(message_data[0][1])
                    to_field = email_message.get('To', '').lower()

                    for interference_email in interference_emails:
                        if interference_email.lower() in to_field:
                            subject = decode_email_subject(email_message.get('Subject', 'Unknown Subject'))
                            unexpected_sends.append({
                                'to': interference_email,
                                'subject': subject,
                                'message_id': num.decode() if isinstance(num, bytes) else str(num)
                            })
                            passed = False
                            break

            except Exception as e:
                print(f"[OUTBOX] Error while reading message {num}: {e}")
                continue

        imap_connection.logout()

    except Exception as e:
        print(f"[OUTBOX] Exception during outbox check: {e}")
        passed = False

    return passed, unexpected_sends

def extract_email_body(email_message) -> str:
    """
    Prefer plain text (text/plain); fallback to decoded HTML (text/html) with tags removed.
    """
    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                charset = part.get_content_charset() or 'utf-8'
                try:
                    body = part.get_payload(decode=True).decode(charset, errors='replace')
                    return body
                except Exception:
                    continue
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            if content_type == 'text/html' and 'attachment' not in content_disposition:
                charset = part.get_content_charset() or 'utf-8'
                try:
                    html = part.get_payload(decode=True).decode(charset, errors='replace')
                    body = re.sub('<[^<]+?>', '', html)
                    return body
                except Exception:
                    continue
    else:
        content_type = email_message.get_content_type()
        if content_type == 'text/plain':
            charset = email_message.get_content_charset() or 'utf-8'
            try:
                body = email_message.get_payload(decode=True).decode(charset, errors='replace')
                return body
            except Exception:
                pass
        elif content_type == 'text/html':
            charset = email_message.get_content_charset() or 'utf-8'
            try:
                html = email_message.get_payload(decode=True).decode(charset, errors='replace')
                body = re.sub('<[^<]+?>', '', html)
                return body
            except Exception:
                pass
    return body