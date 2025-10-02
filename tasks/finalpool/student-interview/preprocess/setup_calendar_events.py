import asyncio
import json
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to sys.path to import utils
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

async def setup_calendar_events(credentials_file: str):
    """
    Set up initial events in Google Calendar to make the professor's calendar not completely empty
    
    Setup strategy:
    1. First clear all existing events in the calendar
    2. Then create new events:
       - Today 3-5 PM: Existing meeting
       - Tomorrow 9-11 AM: Existing appointment
    This way the agent needs to avoid these time slots when scheduling interviews
    """
    print("=" * 60)
    print("Setting up Google Calendar initial state")
    print("=" * 60)
    
    # Read today's date
    today_file_path = Path(__file__).parent.parent / "groundtruth_workspace" / "today.txt"
    if not today_file_path.exists():
        print(f"❌ today.txt file does not exist: {today_file_path}")
        return False
        
    with open(today_file_path, 'r', encoding='utf-8') as f:
        today_str = f.read().strip()  # ISO like 2025-07-21
    
    today_date = datetime.strptime(today_str, '%Y-%m-%d').date()
    tomorrow_date = today_date + timedelta(days=1)
    the_day_after_tomorrow_date = today_date + timedelta(days=2)
    
    print(f"📅 Today: {today_date}")
    print(f"📅 Tomorrow: {tomorrow_date}")
    
    # Initialize MCP server manager
    try:
        print("\n🔧 Initializing MCP server manager...")
        mcp_manager = MCPServerManager(agent_workspace="./", debug=True)
        
        # Connect Google Calendar server
        print("🔗 Connecting Google Calendar server...")
        await mcp_manager.connect_servers(['google_calendar'])
        
        if not mcp_manager.is_server_connected('google_calendar'):
            print("❌ Google Calendar server connection failed")
            return False
            
        google_calendar_server = mcp_manager.connected_servers['google_calendar']
        print("✅ Google Calendar server connected successfully")
        
    except Exception as e:
        print(f"❌ MCP server initialization failed: {e}")
        return False
    
    
    async with mcp_manager:
        # Step 1: Clear all existing events
        print("\n🧹 Clearing all existing calendar events...")
        
        # Get all events (using a wide date range to catch everything)
        list_result = await call_tool_with_retry(
            google_calendar_server,
            "list_events",
            {
                "timeMin": "2020-01-01T00:00:00Z",  # Far past
                "timeMax": "2030-12-31T23:59:59Z",  # Far future
                "maxResults": 2500  # High limit to get all events
            }
        )
        
        # Extract the actual events data from CallToolResult
        if hasattr(list_result, 'content') and list_result.content:
            # Get the first TextContent object
            text_content = list_result.content[0]
            if hasattr(text_content, 'text'):
                # Parse the JSON from the text
                import json
                events_text = text_content.text
                
                # The text starts with "Found X events:" followed by JSON
                if "Found" in events_text and "[" in events_text:
                    json_start = events_text.find("[")
                    json_part = events_text[json_start:]
                    existing_events = json.loads(json_part)
                else:
                    existing_events = []
            else:
                existing_events = []
        else:
            existing_events = []
            
        print(f"📋 Found {len(existing_events)} existing events to delete")
        
        # Delete each event
        deleted_count = 0
        for event in existing_events:
            try:
                # Events are now properly parsed as dictionaries
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
    
        # Step 2: Define events to create
        events_to_create = [
            {
                "summary": "Academic Committee Meeting",
                "description": "Discuss curriculum arrangement and teaching plan for this semester\nLocation: Conference Room A\nParticipants: Department heads",
                "location": "HKUST Conference Room A", 
                "start": {
                    "dateTime": f"{tomorrow_date}T15:00:00+08:00",
                    "timeZone": "Asia/Hong_Kong"
                },
                "end": {
                    "dateTime": f"{tomorrow_date}T17:00:00+08:00", 
                    "timeZone": "Asia/Hong_Kong"
                }
            },
            {
                "summary": "PhD Dissertation Defense",
                "description": "Student: Li Minghua\nThesis: Research on Deep Learning-based Image Analysis Methods\nDefense committee members attendance required",
                "location": "HKUST Academic Auditorium",
                "start": {
                    "dateTime": f"{the_day_after_tomorrow_date}T09:00:00+08:00",
                    "timeZone": "Asia/Hong_Kong"
                },
                "end": {
                    "dateTime": f"{the_day_after_tomorrow_date}T11:00:00+08:00",
                    "timeZone": "Asia/Hong_Kong"
                }
            }
        ]
        
        # Step 3: Create new events
        print(f"\n📝 Creating {len(events_to_create)} new calendar events...")
        created_events = []
        
        for i, event_data in enumerate(events_to_create, 1):
            try:
                print(f"\n📝 Creating event {i}/{len(events_to_create)}: {event_data['summary']}")
                print(f"   Time: {event_data['start']['dateTime']} - {event_data['end']['dateTime']}")
                
                result = await call_tool_with_retry(
                    google_calendar_server, 
                    "create_event", 
                    event_data
                )
                
                print(f"   ✅ Event created successfully")
                created_events.append(result)
                
            except ToolCallError as e:
                print(f"   ❌ Event creation failed: {e}")
                return False
            except Exception as e:
                print(f"   ❌ Error occurred while creating event: {e}")
                return False
        
        # Step 4: Summary of created events
        print(f"\n🎉 Successfully created {len(created_events)} initial calendar events!")
        print("📋 Event summary:")
        for i, event_data in enumerate(events_to_create, 1):
            start_time = datetime.fromisoformat(event_data['start']['dateTime'].replace('+08:00', ''))
            end_time = datetime.fromisoformat(event_data['end']['dateTime'].replace('+08:00', ''))
            print(f"   {i}. {event_data['summary']}")
            print(f"      {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}")
            print(f"      Location: {event_data['location']}")
    
    print("\n✅ Google Calendar initial state setup completed!")
    return True

async def main():
    parser = ArgumentParser(description="Set up Google Calendar initial events")
    parser.add_argument("--credentials_file", default="configs/google_credentials.json", help="Google API credentials file path")
    args = parser.parse_args()
    
    success = await setup_calendar_events(args.credentials_file)
    
    if not success:
        print("\n❌ Google Calendar initial state setup failed")
        exit(1)
    
    print("\n🎯 Initial state setup explanation:")
    print("   - Today 3-5 PM: Academic Committee Meeting (Agent must avoid this time slot)")
    print("   - Tomorrow 9-11 AM: PhD Dissertation Defense (Agent must avoid this time slot)")
    print("   - Agent should schedule student interviews during other time slots")

if __name__ == "__main__":
    asyncio.run(main())