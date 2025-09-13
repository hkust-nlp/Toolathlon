import re
import imaplib
import email
from typing import Dict, List, Tuple
from .ops import _connect_imap, _close_imap_safely, extract_email_body, decode_email_subject


def check_expense_claim_emails_in_sent(
    sender_config: Dict,
    claim_ids: List[str],
    expected_subject_type: str,
    expected_recipients: List[str],
    expected_cc: List[str] = None
) -> Tuple[bool, Dict]:
    """
    Check sender's Sent folder for expense claim emails.
    
    Args:
        sender_config: IMAP config for sender account
        claim_ids: List of claim IDs (EXP format) to search for
        expected_subject_type: "Review Required" or "Over-Cap Notice"
        expected_recipients: List of TO recipient emails  
        expected_cc: Optional list of CC recipient emails
        
    Returns:
        (success, details): Whether expected emails were found and details
    """
    imap = None
    found_emails = []
    
    try:
        imap = _connect_imap(sender_config)
        
        # Select Sent folder
        status, _ = imap.select('Sent')
        if status != 'OK':
            return False, {"error": "Could not select Sent folder"}
        
        # Search all messages
        status, message_numbers = imap.search(None, 'ALL')
        if status != 'OK':
            return False, {"error": "Search failed in Sent folder"}
        
        all_messages = message_numbers[0].split()
        
        # Determine expected subject
        if "Review Required" in expected_subject_type:
            expected_subject_key = "Expense Claim Review Required"
        else:
            expected_subject_key = "Expense Over-Cap Notice"
        
        for num in reversed(all_messages):  # Check newest first
            try:
                status, message_data = imap.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue
                    
                email_message = email.message_from_bytes(message_data[0][1])
                subject = decode_email_subject(email_message.get('Subject', ''))
                to_field = email_message.get('To', '').lower()
                cc_field = email_message.get('Cc', '').lower()
                body = extract_email_body(email_message)
                
                # Check if subject matches
                if expected_subject_key not in subject:
                    continue
                
                # Check recipients (TO field)
                to_match = any(recipient.lower() in to_field for recipient in expected_recipients)
                if not to_match:
                    continue
                
                # Check CC if specified
                if expected_cc:
                    cc_match = any(cc_recipient.lower() in cc_field for cc_recipient in expected_cc)
                    if not cc_match:
                        continue
                
                # Search for claim IDs (EXP pattern) in body
                claim_pattern = r'EXP\d{7,}'
                found_claim_matches = re.findall(claim_pattern, body, re.IGNORECASE)
                
                if found_claim_matches:
                    found_emails.append({
                        'subject': subject,
                        'to': to_field,
                        'cc': cc_field,
                        'claim_ids_found': list(set(found_claim_matches)),
                        'body_excerpt': body[:200],
                        'message_id': num.decode() if isinstance(num, bytes) else str(num)
                    })
                    
            except Exception as e:
                continue
        
    except Exception as e:
        return False, {"error": f"IMAP error: {str(e)}"}
    finally:
        _close_imap_safely(imap)
    
    # Analyze results
    all_found_claims = set()
    for email_info in found_emails:
        all_found_claims.update(email_info['claim_ids_found'])
    
    expected_claims = set(claim_ids)
    missing_claims = expected_claims - all_found_claims
    
    success = len(missing_claims) == 0
    
    details = {
        'expected_claims': list(expected_claims),
        'found_claims': list(all_found_claims),
        'missing_claims': list(missing_claims),
        'found_emails': found_emails,
        'total_emails_found': len(found_emails),
        'success': success
    }
    
    return success, details