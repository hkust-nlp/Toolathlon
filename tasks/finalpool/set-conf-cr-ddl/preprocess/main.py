import sys
import os
from pathlib import Path
from argparse import ArgumentParser
import asyncio

# 添加任务目录到路径以访问token_key_session
sys.path.insert(0, str(Path(__file__).parent.parent))
from token_key_session import all_token_key_session
from utils.app_specific.poste.email_import_utils import clear_all_email_folders
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

async def clear_google_calendar():
    """
    清理Google Calendar中的所有事件
    """
    print("\n" + "=" * 60)
    print("清理Google Calendar事件")
    print("=" * 60)

    try:
        # 初始化MCP服务器管理器
        print("🔧 初始化MCP服务器管理器...")
        mcp_manager = MCPServerManager(agent_workspace="./", local_token_key_session=all_token_key_session, debug=True)

        # 连接Google Calendar服务器
        print("🔗 连接Google Calendar服务器...")
        await mcp_manager.connect_servers(['google_calendar'])

        if not mcp_manager.is_server_connected('google_calendar'):
            print("❌ Google Calendar服务器连接失败")
            return False

        google_calendar_server = mcp_manager.connected_servers['google_calendar']
        print("✅ Google Calendar服务器连接成功")

        async with mcp_manager:
            # 获取所有现有事件
            print("🔍 获取所有现有事件...")

            list_result = await call_tool_with_retry(
                google_calendar_server,
                "list_events",
                {
                    "timeMin": "2020-01-01T00:00:00Z",  # 远在过去
                    "timeMax": "2030-12-31T23:59:59Z",  # 远在未来
                    "maxResults": 2500  # 高限制以获取所有事件
                }
            )

            # 从CallToolResult中提取实际事件数据
            existing_events = []
            if hasattr(list_result, 'content') and list_result.content:
                # 获取第一个TextContent对象
                text_content = list_result.content[0]
                if hasattr(text_content, 'text'):
                    # 从text中解析JSON
                    import json
                    events_text = text_content.text

                    # 文本以"Found X events:"开始，后跟JSON
                    if "Found" in events_text and "[" in events_text:
                        json_start = events_text.find("[")
                        json_part = events_text[json_start:]
                        existing_events = json.loads(json_part)
                    else:
                        existing_events = []

            print(f"📋 找到 {len(existing_events)} 个现有事件需要删除")

            # 删除每个事件
            deleted_count = 0
            for event in existing_events:
                try:
                    # 事件现在正确解析为字典
                    event_id = event.get('id')
                    event_title = event.get('summary', 'Untitled')

                    if event_id:
                        await call_tool_with_retry(
                            google_calendar_server,
                            "delete_event",
                            {"eventId": event_id}
                        )
                        deleted_count += 1
                        print(f"   ✅ 已删除: {event_title}")

                except Exception as e:
                    event_title = event.get('summary', 'Unknown') if isinstance(event, dict) else 'Unknown'
                    print(f"   ⚠️ 删除事件 '{event_title}' 失败: {e}")
                    continue

            print(f"🗑️ 成功删除 {deleted_count} 个现有事件")
            print("📅 Google Calendar清理完成")
            return True

    except Exception as e:
        print(f"❌ Google Calendar清理过程中出错: {e}")
        return False

async def import_emails_via_mcp(backup_file: str):
    """
    使用MCP emails server导入邮件
    """
    from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

    print(f"使用MCP emails server导入邮件...")

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
                print(f"✅ 邮件导入成功: {result.content[0].text}")
                return True
            else:
                print(f"❌ 邮件导入失败: 无返回内容")
                return False

        except ToolCallError as e:
            print(f"❌ 邮件导入失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 邮件导入时发生未知错误: {e}")
            return False

if __name__=="__main__":
    import asyncio

    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("使用本地Poste邮件服务器和Google Calendar构建初始状态...")

    async def main_async():
        # 步骤0：清理邮箱
        print("=" * 60)
        print("清理邮箱文件夹")
        print("=" * 60)
        clear_all_email_folders(all_token_key_session.emails_config_file)

        # 步骤1：清理Google Calendar
        print("=" * 60)
        print("清理Google Calendar")
        print("=" * 60)
        calendar_success = await clear_google_calendar()
        if not calendar_success:
            print("⚠️ Google Calendar清理失败，但继续执行")

        # 步骤2：导入已转换的邮件备份
        backup_file = Path(__file__).parent / ".." / "files" / "emails_backup.json"

        if not backup_file.exists():
            print(f"❌ 邮件备份文件不存在: {backup_file}")
            print("请先运行 convert_emails.py 生成邮件备份文件")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("导入邮件到本地邮箱")
        print("=" * 60)
        success = await import_emails_via_mcp(str(backup_file))

        if not success:
            print("\n❌ 邮件导入失败！")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("✅ 本地邮件和日历环境构建完成！")
        print("=" * 60)

    asyncio.run(main_async())