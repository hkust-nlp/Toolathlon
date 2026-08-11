import sys
import os
from argparse import ArgumentParser
import json
import random
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import asyncio
from pathlib import Path

# Add utils to path
sys.path.append(os.path.dirname(__file__))

from utils.general.helper import read_json, print_color
from configs.token_key_session import all_token_key_session as global_token_key_session
from utils.app_specific.github.api import (
    github_get_login, github_delete_repo,
    github_create_user_repo, github_get_repo
)
from utils.app_specific.github.git_ops import git_mirror_clone, git_mirror_push
from utils.app_specific.poste.local_email_manager import LocalEmailManager

file_path = os.path.abspath(__file__)
EMAILS_CONFIG_FILE = os.path.join(os.path.dirname(file_path), "..", "emails_config.json")

RECEIVER_EMAIL_ADDR = read_json(EMAILS_CONFIG_FILE)['email']
GITHUB_TOKEN = global_token_key_session.github_token
READONLY = False
FORKING_LIST = [
    # (source repo, fork_default_branch_only)
    ("Toolathlon-Archive/My-Homepage", True),
    ("Toolathlon-Archive/optimizing-llms-contextual-reasoning", True),
    ("Toolathlon-Archive/llm-adaptive-learning", True),
    ("Toolathlon-Archive/ipsum-lorem-all-you-need", True),
    ("Toolathlon-Archive/enhancing-llms", True),
]

def to_importable_emails_format(legacy_emails, receiver_email: str, today_file_path: str):
    """
    Convert legacy format emails to an importable format.

    Rules:
    - Sender address: always <noreply@mcp.com>, display name is the original sender_name
    - The last email's time equals the time in today_file_path; if it's only a date, time is set to 18:00:00 UTC
    - For previous emails, each one's time (going backward) is randomly 4-8 hours earlier than the next
    - All recipients are receiver_email
    - message_id is in the format <email{email_id}@mcp.com>
    - Only one of body_text or body_html is filled, based on content type; the other is an empty string
    - Attachments is always an empty list
    """
    today_text = None
    try:
        with open(today_file_path, "r", encoding="utf-8") as f:
            today_text = f.read().strip()
    except Exception:
        today_text = None

    base_dt = None
    if today_text:
        try:
            base_dt = datetime.fromisoformat(today_text)
            if base_dt.tzinfo is None:
                base_dt = base_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                # Only date
                y, m, d = [int(x) for x in today_text.split("-")]
                base_dt = datetime(y, m, d, 18, 0, 0, tzinfo=timezone.utc)
            except Exception:
                base_dt = None
    if base_dt is None:
        base_dt = datetime.now(timezone.utc)

    random.seed(42)

    total = len(legacy_emails)
    # Build timestamps list: start from the last and go backwards
    timestamps = [None] * total
    if total > 0:
        timestamps[-1] = base_dt
        for i in range(total - 2, -1, -1):
            delta_hours = random.randint(4, 8)
            timestamps[i] = timestamps[i + 1] - timedelta(hours=delta_hours)

    def detect_is_html(content: str) -> bool:
        if not isinstance(content, str):
            return False
        lower = content.lower()
        return ("<html" in lower) or ("<body" in lower) or ("<p" in lower) or ("<div" in lower)

    emails_out = []
    for idx, item in enumerate(legacy_emails, start=1):
        email_id = str(idx)
        sender_name = item.get("sender_name", "")
        subject = item.get("subject", "")
        content = item.get("content", "")
        content_type = item.get("content_type", "auto")

        is_html = (content_type == "html") or (content_type == "auto" and detect_is_html(content))
        body_text = "" if is_html else content
        body_html = content if is_html else ""

        dt = timestamps[idx - 1] if total > 0 else base_dt
        rfc2822_date = format_datetime(dt)

        emails_out.append({
            "email_id": email_id,
            "subject": subject,
            "from_addr": f"{sender_name} <noreply@mcp.com>",
            "to_addr": receiver_email,
            "cc_addr": None,
            "bcc_addr": None,
            "date": rfc2822_date,
            "message_id": f"<email{email_id}@mcp.com>",
            "body_text": body_text,
            "body_html": body_html,
            "attachments": []
        })

    export = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "total_emails": total,
        "emails": emails_out
    }
    return export

async def import_emails_via_mcp(backup_file: str):
    """
    Import emails using the MCP emails server.
    """
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

    print(f"Importing emails using the MCP emails server...")

    agent_workspace = "./"
    mcp_manager = MCPServerManager(agent_workspace=agent_workspace, local_token_key_session={"emails_config_file": EMAILS_CONFIG_FILE})
    emails_server = mcp_manager.servers['emails']

    async with emails_server as server:
        try:
            result = await call_tool_with_retry(
                server,
                "import_emails",
                {
                    "import_path": backup_file,
                    "folder": "INBOX"
                }
            )

            if result.content and not getattr(result, "isError", False):
                print(f"✅ Email import process completed: {result.content[0].text}")
                return True
            else:
                error_text = result.content[0].text if result.content else "no return content"
                print(f"❌ Email import process failed: {error_text}")
                return False

        except ToolCallError as e:
            print(f"❌ Email import process failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Email import process failed: unknown error {e}")
            return False

async def prepare_one_repo(source_repo, target_repo_name, fork_default_branch_only, readonly):
    """
    Prepare a repository by creating an independent copy (not a fork).
    Directly mirror clone from source and create as independent repo.
    """
    import time
    import shutil

    github_user = github_get_login(GITHUB_TOKEN)
    target_repo_full = f"{github_user}/{target_repo_name}"

    print(f"Preparing {source_repo} → {target_repo_full}...")

    # Check if target repo exists, delete it if so
    try:
        if github_get_repo(GITHUB_TOKEN, github_user, target_repo_name):
            print(f"Target repo {target_repo_full} exists, deleting it...")
            github_delete_repo(GITHUB_TOKEN, github_user, target_repo_name)
            time.sleep(2)
    except RuntimeError as e:
        # 404 means repo doesn't exist, which is fine
        if "404" not in str(e):
            raise

    # Mirror clone source repo directly
    tmpdir = Path(os.path.dirname(__file__)) / ".." / "tmp" / target_repo_name
    tmpdir.mkdir(parents=True, exist_ok=True)
    local_mirror_dir = tmpdir / f"{target_repo_name}.git"

    print(f"Mirror cloning {source_repo}...")
    await git_mirror_clone(GITHUB_TOKEN, source_repo, str(local_mirror_dir))

    # Create new independent repo
    print(f"Creating new independent repo {target_repo_full}...")
    github_create_user_repo(GITHUB_TOKEN, target_repo_name, private=False)

    # Push mirror to new repo
    print(f"Pushing mirror to {target_repo_full}...")
    await git_mirror_push(GITHUB_TOKEN, str(local_mirror_dir), target_repo_full)

    # Cleanup
    shutil.rmtree(tmpdir)
    print(f"✓ Completed {target_repo_full}")

async def process_emails():
    # Initialize the local email manager
    email_manager = LocalEmailManager(EMAILS_CONFIG_FILE, verbose=True)
    
    # Clear mailboxes
    print("Mailbox clearing...")
    email_manager.clear_all_emails('INBOX')
    email_manager.clear_all_emails('Sent')

    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"
    
    # Path to file storing today's date
    today_file_path = Path(__file__).parent / ".." / "groundtruth_workspace" / "today.txt"
    
    # Load email data
    print("Loading emails...")
    legacy_format_emails = email_manager.load_emails_from_jsonl(
        str(email_jsonl_file), 
        str(placeholder_file_path),
        str(today_file_path)
    )

    # The emails variable is [{"sender_name","subject","content","content_type"}] from oldest to newest

    # The desired format:
    # - All senders are <noreply@mcp.com>
    # - The last email's send time should be the time in today_file_path, and its 'email_id' should be the largest = len(emails)
    # - Earlier emails are offset backwards by a random 4-8 hours each
    # - All recipients are RECEIVER_EMAIL_ADDR
    # - message_id is <email{email_id}@mcp.com>
    # - If type is html, fill body_html, else it's ""; vice versa for text
    # The final variable is importable_format_emails, saved to importable_emails_file_path

    """
    {
      "export_date": "2025-09-15T19:01:19.793374",
      "total_emails": 18,
      "emails": [
        {
          "email_id": "1",
          "subject": "[COML 2025] Camera-ready instructions for accepted papers",
          "from_addr": "COML 2025 <noreply@mcp.com>",
          "to_addr": "jsmith@mcp.com",
          "cc_addr": null,
          "bcc_addr": null,
          "date": "Wed, 10 Sep 2025 18:31:19 +0000",
          "message_id": "<email1@mcp.com>",
          "body_text": "...",
          "body_html": "...",
          "is_read": false,
          "is_important": false,
          "folder": "INBOX",
          "attachments": []
        },
        ...
      ]
    }
    """

    importable_format_emails = to_importable_emails_format(
        legacy_emails=legacy_format_emails,
        receiver_email=RECEIVER_EMAIL_ADDR,
        today_file_path=str(today_file_path)
    )

    importable_emails_file_path = Path(__file__).parent / ".." / "files" / "importable_emails.json"
    importable_emails_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(importable_emails_file_path, "w", encoding="utf-8") as f:
        json.dump(importable_format_emails, f, ensure_ascii=False, indent=2)
    print_color(f"Saved importable emails to {importable_emails_file_path}", "green")

    return importable_emails_file_path

async def main():
    parser = ArgumentParser(description="Preprocessing tool for email and repo setup tasks")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Run multiple fork_repo && form2independent in parallel using async
    # Parse new target_repo names from source_repo automatically

    real_forking_list = []
    for source_repo, fork_default_branch_only in FORKING_LIST:
        target_repo = source_repo.split("/")[1]
        real_forking_list.append((source_repo, target_repo, fork_default_branch_only, READONLY))

    # tasks = [prepare_one_repo(source_repo, target_repo, fork_default_branch_only, readonly) for source_repo, target_repo, fork_default_branch_only, readonly in real_forking_list]
    # await asyncio.gather(*tasks)
    # NOTE: we temporarily change it to serial execution to avoid the issue of too many concurrent requests to the GitHub API.
    for source_repo, target_repo, fork_default_branch_only, readonly in real_forking_list:
        await prepare_one_repo(source_repo, target_repo, fork_default_branch_only, readonly)

    print_color("Forking and becoming independent for all repos successfully!","green")

    importable_emails_file_path = await process_emails()

    import_ok = await import_emails_via_mcp(importable_emails_file_path)
    if not import_ok:
        print_color("Email import failed, preprocessing cannot continue.", "red")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

