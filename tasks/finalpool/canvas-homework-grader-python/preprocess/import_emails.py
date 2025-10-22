#!/usr/bin/env python3
"""
Import generated inbox emails to MCP email server using the emails MCP import_emails tool
"""

import json
import sys
import asyncio
import os
from pathlib import Path
from argparse import ArgumentParser


def load_generated_inbox(inbox_path):
    """Load the generated inbox JSON file"""
    try:
        with open(inbox_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded inbox with {data['total_emails']} emails")
        print(f"📅 Export date: {data['export_date']}")
        return data
    except Exception as e:
        print(f"❌ Error loading inbox file: {e}")
        return None


def validate_inbox_structure(inbox_data):
    """Validate that the inbox has the expected structure"""
    required_fields = ['export_date', 'total_emails', 'emails']
    
    for field in required_fields:
        if field not in inbox_data:
            print(f"❌ Missing required field: {field}")
            return False
    
    if not isinstance(inbox_data['emails'], list):
        print(f"❌ 'emails' should be a list")
        return False
    
    # Check first email structure
    if inbox_data['emails']:
        email = inbox_data['emails'][0]
        required_email_fields = ['email_id', 'subject', 'from_addr', 'to_addr', 'date', 'body_text', 'body_html']
        
        for field in required_email_fields:
            if field not in email:
                print(f"⚠️  Email missing field: {field}")
    
    print("✅ Inbox structure validation passed")
    return True


async def import_emails_via_mcp(inbox_path, target_folder="INBOX", preserve_folders=True):
    """
    Import emails using MCP emails server import_emails tool
    
    Args:
        inbox_path: Path to the generated_inbox.json file
        target_folder: Target folder name (default: "INBOX") 
        preserve_folders: Whether to preserve folder structure (default: True)
    """
    print(f"📧 Importing emails from: {inbox_path}")
    
    try:
        # Add the utils path for MCPServerManager import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent  # canvas-homework-grader-python
        finalpool_dir = task_dir.parent  # finalpool
        tasks_dir = finalpool_dir.parent  # tasks
        toolathlon_root = tasks_dir.parent  # toolathlon
        
        sys.path.insert(0, str(toolathlon_root))
        from utils.mcp.tool_servers import MCPServerManager
        
        print(f"🚀 Attempting to import emails via MCP server...")
        
        # Load local token_key_session from task directory
        local_token_key_session = None
        token_key_session_path = task_dir / "token_key_session.py"
        
        if token_key_session_path.exists():
            print(f"🔑 Loading task-specific token configuration from {token_key_session_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("token_key_session", token_key_session_path)
            token_key_session_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(token_key_session_module)
            local_token_key_session = token_key_session_module.all_token_key_session
        else:
            print("⚠️  No task-specific token configuration found, using global defaults")
        
        # Set up temporary workspace
        workspace = script_dir / "temp_workspace"
        workspace.mkdir(exist_ok=True)
        
        # Initialize MCP Server Manager with local token configuration
        server_manager = MCPServerManager(
            agent_workspace=str(workspace),
            config_dir=str(toolathlon_root / "configs" / "mcp_servers"),
            debug=False,
            local_token_key_session=local_token_key_session  # This is the key part!
        )
        
        # Connect to emails server specifically
        await server_manager.connect_servers(["emails"])
        connected_names = server_manager.get_connected_server_names()
        
        if "emails" not in connected_names:
            print("❌ Failed to connect to emails MCP server")
            return False
        
        print(f"✅ Connected to emails MCP server")
        
        # Call the import_emails tool
        emails_server = server_manager.connected_servers["emails"]
        
        args = {
            "import_path": str(inbox_path),
            "target_folder": target_folder,
            "preserve_folders": preserve_folders
        }
        
        print(f"🔄 Calling import_emails with args: {args}")
        result = await emails_server.call_tool("import_emails", args)
        
        # Process the result
        success = False
        if hasattr(result, 'content'):
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)
                    if "successfully imported" in content.text.lower() or "import completed" in content.text.lower():
                        success = True
                else:
                    print(content)
        elif isinstance(result, dict):
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if result.get('success') or 'imported' in str(result).lower():
                success = True
        else:
            print(result)
            if 'success' in str(result).lower():
                success = True
        
        # Cleanup
        await server_manager.disconnect_servers()
        
        if success:
            print("✅ MCP import completed successfully")
            return True
        else:
            print("❌ MCP import may have failed or returned unclear result")
            return False
            
    except ImportError as ie:
        print(f"❌ Could not import MCP utilities: {ie}")
        return False
    except Exception as e:
        print(f"❌ Error during MCP import: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_inbox_summary(inbox_data):
    """Show a summary of the inbox contents"""
    print("\n📊 Inbox Summary:")
    print("=" * 50)
    
    emails = inbox_data['emails']
    
    # Count by folder
    folder_counts = {}
    for email in emails:
        folder = email.get('folder', 'INBOX')
        folder_counts[folder] = folder_counts.get(folder, 0) + 1
    
    print(f"📧 Total emails: {len(emails)}")
    print(f"📁 Folders:")
    for folder, count in folder_counts.items():
        print(f"   - {folder}: {count} emails")
    
    # Show homework submissions only
    homework_emails = []
    for email in emails:
        subject = email.get('subject', '')
        if any(keyword in subject for keyword in ['Homework', 'HW2', 'homework']):
            homework_emails.append(email)
    
    if homework_emails:
        print(f"\n📝 Found {len(homework_emails)} homework submissions:")
        for email in homework_emails:
            email_id = email.get('email_id', 'N/A')
            subject = email.get('subject', 'No subject')
            from_addr = email.get('from_addr', 'Unknown sender')
            print(f"   ID {email_id}: {subject} - {from_addr}")


async def main():
    """Main async function"""
    parser = ArgumentParser(description="Import generated inbox to MCP email server")
    parser.add_argument("--inbox-path", 
                       default=None,
                       help="Path to generated_inbox.json file")
    parser.add_argument("--target-folder", 
                       default="INBOX",
                       help="Target folder for imported emails (default: INBOX)")
    parser.add_argument("--preserve-folders", 
                       action="store_true",
                       default=True,
                       help="Preserve original folder structure (default: True)")
    parser.add_argument("--no-preserve-folders", 
                       action="store_false",
                       dest="preserve_folders",
                       help="Don't preserve folder structure, put all in target folder")
    parser.add_argument("--show-summary-only", 
                       action="store_true",
                       help="Only show inbox summary, don't import")
    
    args = parser.parse_args()
    
    # Determine inbox path
    if args.inbox_path:
        inbox_path = Path(args.inbox_path)
    else:
        # Default to generated_inbox.json in the files directory
        base_dir = Path(__file__).parent.parent
        inbox_path = base_dir / "files" / "generated_inbox.json"
    
    if not inbox_path.exists():
        print(f"❌ Inbox file not found: {inbox_path}")
        sys.exit(1)
    
    print("📧 Email Import Tool for Canvas Homework Grader")
    print("=" * 60)
    
    # Load and validate inbox
    inbox_data = load_generated_inbox(inbox_path)
    if not inbox_data:
        sys.exit(1)
    
    if not validate_inbox_structure(inbox_data):
        sys.exit(1)
    
    # Show summary only if requested
    if args.show_summary_only:
        show_inbox_summary(inbox_data)
        return
    
    # Import emails
    print(f"🚀 Starting email import...")
    success = await import_emails_via_mcp(
        inbox_path=inbox_path,
        target_folder=args.target_folder,
        preserve_folders=args.preserve_folders
    )
    
    if success:
        print("✅ Email import process completed!")
        sys.exit(0)
    else:
        print("❌ Email import failed")
        print("\n🔧 Manual MCP Tool Call Required:")
        print(f"   Tool: import_emails (from emails MCP server)")
        print(f"   Arguments:")
        print(f"     - import_path: \"{inbox_path}\"")
        print(f"     - target_folder: \"{args.target_folder}\"")
        print(f"     - preserve_folders: {args.preserve_folders}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())