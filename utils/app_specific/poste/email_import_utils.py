import asyncio
from pathlib import Path
from typing import Optional, Any

from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError
from utils.app_specific.poste.local_email_manager import LocalEmailManager


def clear_all_email_folders(emails_config_file: str):
    """
    Clear all emails in INBOX, Drafts, and Sent folders.

    Args:
        emails_config_file: Path to the email configuration file
    """
    print(f"Using email config file: {emails_config_file}")

    # Initialize the email manager
    email_manager = LocalEmailManager(emails_config_file, verbose=True)

    # List available mailboxes first
    available_mailboxes = email_manager.list_mailboxes()

    print(f"Will clear the following folders: {available_mailboxes}")

    for folder in available_mailboxes:
        try:
            print(f"Clearing folder {folder} ...")
            email_manager.clear_all_emails(mailbox=folder)
            print(f"✅ Folder {folder} cleared successfully")
        except Exception as e:
            print(f"⚠️ Error clearing folder {folder}: {e}")

    print("📧 All email folders cleared")


async def import_emails_via_mcp(backup_file: str, local_token_key_session: Any,
                               description: str = "", folder: str = "INBOX") -> bool:
    """
    Import emails to the specified account using the MCP emails server.

    Args:
        backup_file: Path to the email backup file
        local_token_key_session: Session object containing email configuration
        description: Description of the operation
        folder: The mailbox folder to import into, default is INBOX

    Returns:
        bool: Whether the import was successful
    """
    print(f"Importing emails via MCP emails server {description}...")

    # Use the agent_workspace from the task config
    agent_workspace = "./"  # MCP requires a workspace path

    # Create MCP server manager
    mcp_manager = MCPServerManager(agent_workspace=agent_workspace, local_token_key_session=local_token_key_session)
    emails_server = mcp_manager.servers['emails']

    async with emails_server as server:
        try:
            # Use the import_emails tool to import the email backup
            result = await call_tool_with_retry(
                server,
                "import_emails",
                {
                    "import_path": backup_file,
                    "folder": folder
                }
            )

            if result.content:
                print(f"✅ Email import succeeded {description}: {result.content[0].text}")
                return True
            else:
                print(f"❌ Email import failed {description}: No content returned")
                return False

        except ToolCallError as e:
            print(f"❌ Email import failed {description}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unknown error occurred during email import {description}: {e}")
            return False


def setup_email_environment(local_token_key_session: Any, task_backup_file: Optional[str] = None,
                           interference_backup_file: Optional[str] = None) -> bool:
    """
    Set up the email environment, including clearing mailboxes and importing emails.

    Args:
        local_token_key_session: Session object containing email configuration
        task_backup_file: Path to the task-related email backup file (optional)
        interference_backup_file: Path to the interference email backup file (optional)

    Returns:
        bool: Whether the setup was successful
    """
    # Get the email config file path
    emails_config_file = local_token_key_session.emails_config_file

    # Step 0: Clear mailboxes
    print("=" * 60)
    print("Step 0: Clear email folders")
    print("=" * 60)
    clear_all_email_folders(emails_config_file)

    success = True

    # 1. Import task-related emails (if provided)
    if task_backup_file:
        if Path(task_backup_file).exists():
            print("\n" + "=" * 60)
            print("Step 1: Import task-related emails")
            print("=" * 60)
            success1 = asyncio.run(import_emails_via_mcp(task_backup_file, local_token_key_session, "(Task Emails)"))
            if not success1:
                print("\n❌ Task email import failed!")
                success = False
        else:
            print(f"\n❌ Task email backup file not found: {task_backup_file}")
            success = False

    # 2. Import interference emails (if provided)
    if interference_backup_file and Path(interference_backup_file).exists():
        print("\n" + "=" * 60)
        print("Step 2: Import interference emails")
        print("=" * 60)
        success2 = asyncio.run(import_emails_via_mcp(interference_backup_file, local_token_key_session, "(Interference Emails)"))

        if not success2:
            print("\n⚠️ Interference email import failed, but continuing...")
        else:
            print("✅ Interference email import succeeded")
    elif interference_backup_file:
        print(f"\n⚠️ Interference email file not found: {interference_backup_file}")

    if success:
        print("\n" + "=" * 60)
        print("✅ Email import completed! Initial email state has been set up!")
        print("=" * 60)

    return success