import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep
import sys
import os
import json
from typing import Dict, List, Union

# Add current directory to sys.path for local module imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from clean_local_emails import clean_multiple_accounts

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Sending emails to build initial state.")
    
    # First, clean all relevant email accounts (including student mailboxes)
    print("Cleaning local mailboxes (including student accounts)...")
    # Use the clean_local_emails module logic: read from emails_all_config.json and clean in batch
    
    config_path = os.path.abspath(os.path.join(current_dir, '..', 'emails_all_config.json'))
    with open(config_path, 'r', encoding='utf-8') as f:
        accounts_to_clean: Union[Dict[str, str], List[Dict[str, str]]] = json.load(f)
    
    clean_success = clean_multiple_accounts(accounts_to_clean)
    if not clean_success:
        print("⚠️ Not all mailboxes cleaned successfully, but continuing with email sending.")
    else:
        print("✅ Mailbox cleaning completed.")

    # Read single receiver config
    receiver_config_path = os.path.abspath(os.path.join(current_dir, '..', 'emails_config.json'))
    with open(receiver_config_path, 'r', encoding='utf-8') as f:
        receiver_config: Dict[str, str] = json.load(f)
    receiver = receiver_config["email"]

    # Paths for emails data and placeholders
    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"

    # Path to local send_email.py module
    send_email_path = Path(__file__).parent / "send_email.py"

    print(f"🚀 Begin sending emails...")
    print(f"   Receiver: {receiver}")
    print(f"   Email data file: {email_jsonl_file}")
    print(f"   Placeholder file: {placeholder_file_path}")

    # Load emails data
    emails_data: List[dict] = []
    with open(email_jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                emails_data.append(json.loads(line))
            except Exception:
                continue

    def _normalize_name(name: str) -> str:
        import re
        n = name or ""
        n = re.sub(r"[._-]+", " ", n)
        n = re.sub(r"\d+", "", n)
        n = re.sub(r"[^A-Za-z\s]", "", n)
        n = re.sub(r"\s+", " ", n).strip().lower()
        return n

    total_senders = len(accounts_to_clean)
    success_count = 0
    skipped_same_addr = 0
    no_match_count = 0

    temp_dir = (Path(__file__).parent / ".." / "temp_send").resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)

    for idx, account in enumerate(accounts_to_clean, 1):
        sender_email = account.get("email")
        sender_password = account.get("password", "")
        sender_display = account.get("name", sender_email)

        # Skip if sender and receiver are the same
        if sender_email == receiver:
            print(f"\n↪️  [{idx}/{total_senders}] Skipped: sender and receiver are the same -> {sender_email}")
            skipped_same_addr += 1
            continue

        candidates = set()
        candidates.add(_normalize_name(sender_display))
        local_part = (sender_email.split('@', 1)[0] if sender_email else "")
        candidates.add(_normalize_name(local_part))

        # Find matching email item for this account
        match_item = None
        for item in emails_data:
            sender_name_in_mail = item.get('sender_name')
            if _normalize_name(sender_name_in_mail) in candidates:
                match_item = item
                break

        if not match_item:
            print(f"\n⚠️  [{idx}/{total_senders}] No matching content found for sender account={sender_email}")
            no_match_count += 1
            continue

        # Write to a temp jsonl containing only the matched email
        tmp_jsonl = temp_dir / f"{sender_email.replace('@','_at_').replace('.', '_')}.jsonl"
        with open(tmp_jsonl, 'w', encoding='utf-8') as tf:
            tf.write(json.dumps(match_item, ensure_ascii=False) + "\n")

        print(f"\n➡️  [{idx}/{total_senders}] Sending from {sender_email} ({sender_display}) to {receiver}")
        try:
            asyncio.run(run_command(
                f"timeout 60s uv run {send_email_path} -s {sender_email} "
                f"-p '{sender_password}' "
                f"-r {receiver} "
                f"-j {tmp_jsonl} "
                f"--delay 0.2 "
                f"--placeholder {placeholder_file_path} "
                f"--no-confirm",
                debug=True,
                show_output=True
            ))
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to send: sender={sender_email}, error={e}")

    # Summary result output
    print(
        f"Summary: success={success_count > 0 and (success_count + no_match_count + skipped_same_addr) == total_senders}, "
        f"Accounts sent={success_count}/{total_senders}, skipped same address={skipped_same_addr}, no match={no_match_count}, receiver={receiver}"
    )

    # Wait a bit to ensure all emails are received
    print("Waiting 10s for all emails to be received...")
    sleep(10)

    print("Finished building initial state by sending emails!")