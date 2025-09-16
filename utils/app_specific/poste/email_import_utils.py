import asyncio
from pathlib import Path
from typing import Optional, Any

from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError
from utils.app_specific.poste.local_email_manager import LocalEmailManager


def clear_all_email_folders(emails_config_file: str):
    """
    清理INBOX、Draft、Sent三个文件夹的邮件

    Args:
        emails_config_file: 邮件配置文件路径
    """
    print(f"使用邮件配置文件: {emails_config_file}")

    # 初始化邮件管理器
    email_manager = LocalEmailManager(emails_config_file, verbose=True)

    # 首先列出可用的邮箱文件夹
    try:
        available_mailboxes = email_manager.list_mailboxes()
    except Exception as e:
        print(f"⚠️ 无法获取邮箱文件夹列表: {e}")
        available_mailboxes = ['INBOX']

    # 需要清理的文件夹（只清理存在的文件夹）
    desired_folders = ['INBOX', 'Drafts', 'Sent']
    folders_to_clear = [folder for folder in desired_folders if folder in available_mailboxes]

    if not folders_to_clear:
        folders_to_clear = ['INBOX']  # 确保至少清理INBOX

    print(f"将清理以下文件夹: {folders_to_clear}")

    for folder in folders_to_clear:
        try:
            print(f"清理 {folder} 文件夹...")
            email_manager.clear_all_emails(mailbox=folder)
            print(f"✅ {folder} 文件夹清理完成")
        except Exception as e:
            print(f"⚠️ 清理 {folder} 文件夹时出错: {e}")

    print("📧 所有邮箱文件夹清理完成")


async def import_emails_via_mcp(backup_file: str, local_token_key_session: Any,
                               description: str = "", folder: str = "INBOX") -> bool:
    """
    使用MCP emails server导入邮件到任务指定的邮箱账号

    Args:
        backup_file: 邮件备份文件路径
        local_token_key_session: 包含邮件配置的会话对象
        description: 操作描述信息
        folder: 要导入到的邮箱文件夹，默认为INBOX

    Returns:
        bool: 是否导入成功
    """
    print(f"使用MCP emails server导入邮件{description}...")

    # 使用任务配置的agent_workspace
    agent_workspace = "./"  # MCP需要一个workspace路径

    # 创建MCP服务器管理器
    mcp_manager = MCPServerManager(agent_workspace=agent_workspace, local_token_key_session=local_token_key_session)
    emails_server = mcp_manager.servers['emails']

    async with emails_server as server:
        try:
            # 使用import_emails工具导入邮件备份
            result = await call_tool_with_retry(
                server,
                "import_emails",
                {
                    "import_path": backup_file,
                    "folder": folder
                }
            )

            if result.content:
                print(f"✅ 邮件导入成功{description}: {result.content[0].text}")
                return True
            else:
                print(f"❌ 邮件导入失败{description}: 无返回内容")
                return False

        except ToolCallError as e:
            print(f"❌ 邮件导入失败{description}: {e}")
            return False
        except Exception as e:
            print(f"❌ 邮件导入时发生未知错误{description}: {e}")
            return False


def setup_email_environment(local_token_key_session: Any, task_backup_file: Optional[str] = None,
                           interference_backup_file: Optional[str] = None) -> bool:
    """
    设置邮件环境，包括清理邮箱和导入邮件

    Args:
        local_token_key_session: 包含邮件配置的会话对象
        task_backup_file: 任务相关邮件备份文件路径（可选）
        interference_backup_file: 干扰邮件备份文件路径（可选）

    Returns:
        bool: 设置是否成功
    """
    # 获取邮件配置文件路径
    emails_config_file = local_token_key_session.emails_config_file

    # 步骤0：清理邮箱
    print("=" * 60)
    print("第零步：清理邮箱文件夹")
    print("=" * 60)
    clear_all_email_folders(emails_config_file)

    success = True

    # 1. 导入任务相关的邮件（如果提供）
    if task_backup_file:
        if Path(task_backup_file).exists():
            print("\n" + "=" * 60)
            print("第一步：导入任务相关邮件")
            print("=" * 60)
            success1 = asyncio.run(import_emails_via_mcp(task_backup_file, local_token_key_session, "（任务邮件）"))
            if not success1:
                print("\n❌ 任务邮件导入失败！")
                success = False
        else:
            print(f"\n❌ 未找到任务邮件备份文件: {task_backup_file}")
            success = False

    # 2. 导入干扰邮件（如果提供）
    if interference_backup_file and Path(interference_backup_file).exists():
        print("\n" + "=" * 60)
        print("第二步：导入干扰邮件")
        print("=" * 60)
        success2 = asyncio.run(import_emails_via_mcp(interference_backup_file, local_token_key_session, "（干扰邮件）"))

        if not success2:
            print("\n⚠️ 干扰邮件导入失败，但继续执行...")
        else:
            print("✅ 干扰邮件导入成功")
    elif interference_backup_file:
        print(f"\n⚠️ 未找到干扰邮件文件: {interference_backup_file}")

    if success:
        print("\n" + "=" * 60)
        print("✅ 邮件导入完成！已构建初始邮件状态！")
        print("=" * 60)

    return success