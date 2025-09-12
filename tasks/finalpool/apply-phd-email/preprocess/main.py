import sys
import os
import tarfile
import asyncio
from argparse import ArgumentParser
from pathlib import Path

from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError

sys.path.insert(0, str(Path(__file__).parent.parent))  # 添加任务目录到路径
from token_key_session import all_token_key_session

async def import_emails_via_mcp(backup_file: str, description: str = ""):
    """
    使用MCP emails server导入邮件到任务指定的邮箱账号
    """
    print(f"使用MCP emails server导入邮件{description}...")
    
    # 使用任务配置的agent_workspace
    agent_workspace = "./"  # MCP需要一个workspace路径
    
    # 创建MCP服务器管理器
    mcp_manager = MCPServerManager(agent_workspace=agent_workspace)
    emails_server = mcp_manager.servers['emails']
    
    async with emails_server as server:
        try:
            # 使用import_emails工具导入邮件备份
            result = await call_tool_with_retry(
                server, 
                "import_emails",
                {
                    "import_path": backup_file,
                    "folder": "INBOX"  # 导入到收件箱
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

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    # 首先处理文件解压缩（如果agent_workspace被指定）
    if args.agent_workspace:
        # 确保agent workspace存在
        os.makedirs(args.agent_workspace, exist_ok=True)
        dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
        
        # 解压缩文件
        try:
            with tarfile.open(dst_tar_path, 'r:gz') as tar:
                print(f"正在解压缩申请文件到: {args.agent_workspace}")
                # Use the filter parameter to avoid deprecation warning in Python 3.14+
                tar.extractall(path=args.agent_workspace, filter='data')
                print("解压缩完成")
        except Exception as e:
            print(f"解压缩失败: {e}")
            # 继续执行，因为可能文件已经存在或者不需要解压缩
        
        # 删除压缩文件
        try:
            os.remove(dst_tar_path)
            print(f"已删除原始压缩文件: {dst_tar_path}")
        except Exception as e:
            print(f"删除压缩文件失败: {e}")

    print("Preprocessing...")
    print("使用MCP邮件导入模式")
    
    # 获取邮件配置文件路径（用于配置MCP server）
    emails_config_file = all_token_key_session.emails_config_file
    print(f"使用邮件配置文件: {emails_config_file}")
    
    # 1. 导入任务相关的邮件（从任务files目录）
    task_backup_file = Path(__file__).parent / ".." / "files" / "emails_backup.json"
    if not task_backup_file.exists():
        print("❌ 未找到任务邮件备份文件，请先运行转换脚本生成emails_backup.json")
        sys.exit(1)
    
    print("=" * 60)
    print("第一步：导入任务相关邮件")
    print("=" * 60)
    success1 = asyncio.run(import_emails_via_mcp(str(task_backup_file), "（任务邮件）"))
    
    if not success1:
        print("\n❌ 任务邮件导入失败！")
        sys.exit(1)
    
    # 2. 导入干扰邮件（从development/examples目录）
    interference_backup_file = Path(__file__).parent.parent.parent.parent.parent / "development" / "examples" / "emails" / "corrected_email_backup.json"
    if interference_backup_file.exists():
        print("\n" + "=" * 60)
        print("第二步：导入干扰邮件")
        print("=" * 60)
        success2 = asyncio.run(import_emails_via_mcp(str(interference_backup_file), "（干扰邮件）"))
        
        if not success2:
            print("\n⚠️ 干扰邮件导入失败，但继续执行...")
        else:
            print("✅ 干扰邮件导入成功")
    else:
        print(f"\n⚠️ 未找到干扰邮件文件: {interference_backup_file}")
    
    print("\n" + "=" * 60)
    print("✅ 邮件导入完成！已构建初始邮件状态！")
    print("=" * 60)