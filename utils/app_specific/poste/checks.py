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


