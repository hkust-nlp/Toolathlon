import sys
import os
from pathlib import Path
from argparse import ArgumentParser
import asyncio

# Add the task directory to sys.path to access token_key_session
sys.path.insert(0, str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session
from utils.app_specific.poste.email_import_utils import clear_all_email_folders
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

async def clear_google_calendar():
    """
    Clear all events from Google Calendar.
    """
    print("\n" + "=" * 60)
    print("Clearing all Google Calendar events")
    print("=" * 60)

    try:
        # Initialize MCP Server Manager
        print("🔧 Initializing MCP Server Manager...")
        mcp_manager = MCPServerManager(agent_workspace="./", local_token_key_session=all_token_key_session, debug=True)

        # Connect to Google Calendar server
        print("🔗 Connecting to Google Calendar server...")
        await mcp_manager.connect_servers(['google_calendar'])

        if not mcp_manager.is_server_connected('google_calendar'):
            print("❌ Failed to connect to Google Calendar server")
            return False

        google_calendar_server = mcp_manager.connected_servers['google_calendar']
        print("✅ Successfully connected to Google Calendar server")

        async with mcp_manager:
            # List all existing events
            print("🔍 Retrieving all existing events...")

            list_result = await call_tool_with_retry(
                google_calendar_server,
                "list_events",
                {
                    "timeMin": "2020-01-01T00:00:00Z",  # far in the past
                    "timeMax": "2030-12-31T23:59:59Z",  # far in the future
                    "maxResults": 2500  # high limit to get all events
                }
            )

            # Extract events from CallToolResult
            existing_events = []
            if hasattr(list_result, 'content') and list_result.content:
                # Get the first TextContent object
                text_content = list_result.content[0]
                if hasattr(text_content, 'text'):
                    import json
                    events_text = text_content.text

                    # Text starts with "Found X events:" followed by JSON
                    if "Found" in events_text and "[" in events_text:
                        json_start = events_text.find("[")
                        json_part = events_text[json_start:]
                        existing_events = json.loads(json_part)
                    else:
                        existing_events = []

            print(f"📋 Found {len(existing_events)} events to delete.")

            # Delete each event
            deleted_count = 0
            for event in existing_events:
                try:
                    # Each event should be a dict
                    event_id = event.get('id')
                    event_title = event.get('summary', 'Untitled')

                    if event_id:
                        await call_tool_with_retry(
                            google_calendar_server,
                            "delete_event",
                            {"eventId": event_id}
                        )
                        deleted_count += 1
                        print(f"   ✅ Deleted: {event_title}")

                except Exception as e:
                    event_title = event.get('summary', 'Unknown') if isinstance(event, dict) else 'Unknown'
                    print(f"   ⚠️ Failed to delete event '{event_title}': {e}")
                    continue

            print(f"🗑️ Successfully deleted {deleted_count} existing events")
            print("📅 Google Calendar cleanup complete")
            return True

    except Exception as e:
        print(f"❌ Error occurred during Google Calendar cleanup: {e}")
        return False

async def import_emails_via_mcp(backup_file: str):
    """
    Import emails using the MCP emails server.
    """
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

    print(f"Importing emails via MCP emails server...")

    agent_workspace = "./"
    mcp_manager = MCPServerManager(agent_workspace=agent_workspace, local_token_key_session=all_token_key_session)
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

            if result.content:
                print(f"✅ Email import successful: {result.content[0].text}")
                return True
            else:
                print(f"❌ Email import failed: no content returned")
                return False

        except ToolCallError as e:
            print(f"❌ Email import failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unknown error during email import: {e}")
            return False

if __name__=="__main__":
    import asyncio

    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Building initial state using local Poste email server and Google Calendar...")

    async def main_async():
        # Step 0: Clear emails
        print("=" * 60)
        print("Clearing all email folders")
        print("=" * 60)
        clear_all_email_folders(all_token_key_session.emails_config_file)

        # Step 1: Clear Google Calendar
        print("=" * 60)
        print("Clearing Google Calendar")
        print("=" * 60)
        calendar_success = await clear_google_calendar()
        if not calendar_success:
            print("⚠️ Failed to clear Google Calendar, but proceeding...")

        # Step 2: Import the converted email backup
        backup_file = Path(__file__).parent / ".." / "files" / "emails_backup.json"

        if not backup_file.exists():
            print(f"❌ Email backup file does not exist: {backup_file}")
            print("Please run convert_emails.py first to generate the email backup file")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("Importing emails into local email system")
        print("=" * 60)
        success = await import_emails_via_mcp(str(backup_file))

        if not success:
            print("\n❌ Email import failed!")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("✅ Local email and calendar environment setup complete!")
        print("=" * 60)

    asyncio.run(main_async())