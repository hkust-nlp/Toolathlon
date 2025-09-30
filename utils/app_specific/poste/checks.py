#!/usr/bin/env python3

from typing import Dict, List, Tuple
import email
import imaplib

from .ops import _connect_imap, _close_imap_safely, decode_email_subject, _decode_mime_words


def find_sent_emails(sender_config: Dict) -> List[dict]:
    imap = None
    results: List[dict] = []
    try:
        imap = _connect_imap(sender_config)
        status, _ = imap.select('Sent')
        if status != 'OK':
            return []
        status, nums = imap.search(None, 'ALL')
        if status != 'OK' or not nums or not nums[0]:
            return []
        for num in nums[0].split():
            s, data = imap.fetch(num, '(RFC822)')
            if s != 'OK' or not data or not data[0]:
                continue
            msg = email.message_from_bytes(data[0][1])
            results.append({
                'id': num.decode() if isinstance(num, bytes) else str(num),
                'subject': _decode_mime_words(msg.get('Subject', '')),
                'subject_lower': decode_email_subject(msg.get('Subject', '')),
                'to': (msg.get('To') or '').lower(),
                'cc': (msg.get('Cc') or '').lower(),
            })
        return results
    finally:
        _close_imap_safely(imap)


def assert_no_email_sent_to(sender_config: Dict, target_email: str) -> Tuple[bool, List[dict]]:
    emails = find_sent_emails(sender_config)
    target = (target_email or '').lower()
    hits = [m for m in emails if target in m.get('to','') or target in m.get('cc','')]
    return (len(hits) == 0), hits


def count_sent_with_subject_and_cc(sender_config: Dict, target_email: str, subject_prefix: str, cc_email: str) -> int:
    emails = find_sent_emails(sender_config)
    target = (target_email or '').lower()
    cc = (cc_email or '').lower()
    prefix = subject_prefix.lower()
    return sum(1 for m in emails if (target in m.get('to','') and cc in m.get('cc','') and m.get('subject','').startswith(prefix)))


def count_any_sent_to_or_cc(sender_config: Dict, target_email: str) -> int:
    emails = find_sent_emails(sender_config)
    target = (target_email or '').lower()
    return sum(1 for m in emails if (target in m.get('to','') or target in m.get('cc','')))


def verify_emails_sent_to_recipients(sender_config: Dict, expected_recipients: List[str],
                                   content_extractor=None, content_validator=None) -> Tuple[bool, Dict]:
    """
    验证是否向预期收件人列表精确发送了邮件

    Args:
        sender_config: 发件人邮箱配置
        expected_recipients: 预期收件人邮箱列表
        content_extractor: 可选的邮件内容提取函数 (email_body -> extracted_content)
        content_validator: 可选的内容验证函数 (extracted_content -> bool)

    Returns:
        Tuple[bool, Dict]: (是否通过验证, 详细结果字典)
    """
    from .ops import _extract_text_from_message
    import re

    imap = None
    try:
        imap = _connect_imap(sender_config)
        status, _ = imap.select('Sent')
        if status != 'OK':
            return False, {"error": "无法访问已发送文件夹"}

        status, nums = imap.search(None, 'ALL')
        if status != 'OK':
            return False, {"error": "无法搜索邮件"}

        if not nums or not nums[0]:
            return False, {"error": "已发送邮件为空", "found_recipients": [], "expected_recipients": expected_recipients}

        # 统计实际发送的收件人
        found_recipients = set()
        extracted_contents = []

        expected_set = {email.lower() for email in expected_recipients}

        for num in nums[0].split():
            try:
                s, data = imap.fetch(num, '(RFC822)')
                if s != 'OK' or not data or not data[0]:
                    continue

                msg = email.message_from_bytes(data[0][1])

                # 获取所有收件人
                to_field = (msg.get('To') or '').lower()
                cc_field = (msg.get('Cc') or '').lower()
                bcc_field = (msg.get('Bcc') or '').lower()
                all_recipients_text = f"{to_field},{cc_field},{bcc_field}"

                # 检查哪些预期收件人在此邮件中
                email_recipients = set()
                for expected_email in expected_recipients:
                    if expected_email.lower() in all_recipients_text:
                        found_recipients.add(expected_email.lower())
                        email_recipients.add(expected_email.lower())

                # 如果有内容提取和验证需求，且此邮件包含预期收件人
                if email_recipients and (content_extractor or content_validator):
                    email_body = _extract_text_from_message(msg)

                    if content_extractor:
                        extracted = content_extractor(email_body)
                        extracted_contents.extend(extracted if isinstance(extracted, list) else [extracted])

                    if content_validator and not content_validator(email_body):
                        return False, {
                            "error": "邮件内容验证失败",
                            "recipients_in_email": list(email_recipients),
                            "email_body_preview": email_body[:200]
                        }

            except Exception as e:
                continue

        # 计算结果
        expected_lower = {email.lower() for email in expected_recipients}
        missing_recipients = expected_lower - found_recipients
        extra_recipients = found_recipients - expected_lower

        result = {
            "expected_count": len(expected_recipients),
            "found_count": len(found_recipients),
            "missing_recipients": list(missing_recipients),
            "extra_recipients": list(extra_recipients),
            "found_recipients": list(found_recipients),
            "expected_recipients": expected_recipients
        }

        if extracted_contents:
            result["extracted_contents"] = extracted_contents

        # 判断是否通过
        if missing_recipients or extra_recipients:
            if missing_recipients and extra_recipients:
                result["error"] = f"既有缺少的收件人({len(missing_recipients)}个)，又有额外的收件人({len(extra_recipients)}个)"
            elif missing_recipients:
                result["error"] = f"缺少 {len(missing_recipients)} 个预期收件人"
            else:
                result["error"] = f"发送给了 {len(extra_recipients)} 个额外收件人"
            return False, result

        return True, result

    except Exception as e:
        return False, {"error": f"邮件验证出错: {e}"}
    finally:
        _close_imap_safely(imap)


def extract_url_patterns_from_email(email_body: str, url_patterns: List[str]) -> List[str]:
    """
    从邮件正文中提取匹配指定模式的URL

    Args:
        email_body: 邮件正文
        url_patterns: URL正则表达式模式列表

    Returns:
        List[str]: 匹配的URL列表
    """
    import re

    found_urls = []
    for pattern in url_patterns:
        matches = re.findall(pattern, email_body, re.IGNORECASE)
        for match in matches:
            # 处理元组匹配结果
            if isinstance(match, tuple):
                url = next((m for m in match if m), "")
            else:
                url = match

            # 清理URL末尾的特殊字符
            url = re.sub(r'[^\w\-\.:/]$', '', url)
            if url and url not in found_urls:
                found_urls.append(url)

    return found_urls

