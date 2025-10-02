import imaplib
import email
from email.header import decode_header
from typing import Dict, List, Tuple
import re

from utils.general.helper import print_color
from utils.general.helper import normalize_str


def clear_folder(folder_name: str, config: Dict) -> None:
    """
    Clear the specified IMAP folder under the given email configuration.

    Expected config keys:
    - "email": Email account
    - "password": Password
    - "imap_server": IMAP server
    - "imap_port": IMAP port
    - "use_ssl": Whether to use SSL (bool)
    - "use_starttls": Whether to use STARTTLS (bool)
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

        # If folder is empty, some servers may return BAD/NO for 1:* sequence, check in advance
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
                    # If not selected or already closed by server, ignore
                    pass
                imap.logout()
        except Exception:
            pass



def _connect_imap(config: Dict) -> imaplib.IMAP4:
    """
    使用配置建立 IMAP 连接并登录。

    期望的 config 字段：
    - "email" 或 "username"
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
    """优先提取 text/plain，如果没有则尝试解码 text/html 并去除简单标签。"""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or "utf-8"
                    return part.get_payload(decode=True).decode(charset, errors="replace")
            # fallback: 取第一个 text/html
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    html = part.get_payload(decode=True).decode(charset, errors="replace")
                    # 简单去标签
                    return _strip_html(html)
        else:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload is None:
                # 有些服务器不需要 decode=True
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
    # 非严格 HTML 去标签，适合简单比较
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def find_emails_from_sender(config: Dict, sender_query: str, folder: str = "INBOX", fetch_limit: int = 200) -> List[Dict]:
    """
    根据收件箱配置，在指定文件夹内查找来自某个发件人的邮件。

    Args:
        config: 邮箱 IMAP 配置（需包含 email/password/imap_server/imap_port 等）
        sender_query: 可为发件邮箱或名称，用于 IMAP FROM 搜索
        folder: 目标文件夹，默认 INBOX
        fetch_limit: 最多抓取的邮件数量（从搜索结果尾部截取）

    Returns:
        List[Dict]: [{"subject": str, "body": str, "raw_subject": str}] 按时间（大致）从新到旧
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
        # 取最近的若干封
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
        # 倒序（新邮件在后）转为新到旧
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


def mailbox_has_email_matching_body(config: Dict, sender_query: str, expected_body: str, subject:str = None,folder: str = "INBOX") -> Tuple[bool, Dict]:
    """
    检查邮箱中是否存在来自 sender_query 且正文与 expected_body（normalize_str 后）一致的邮件。
    如果subject不为None，还需要检查邮件主题是否匹配。

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
            # item["subject"] 已经是解码后的主题，直接标准化后比较
            # 如果没有解码后的主题，回退到解码原始主题
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
        # Decode MIME-encoded subject
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
        # Fallback to original subject if decoding fails
        return subject.lower()

def check_sender_outbox(sender_config: dict, interference_emails: set) -> Tuple[bool, list]:
    """Scan sender outbox to ensure no emails were sent to interference addresses."""
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
    """Prefer text/plain; fallback to text/html with tags removed."""
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