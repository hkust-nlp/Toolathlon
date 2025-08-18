import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep
import sys

# 添加当前目录到路径以便导入本地模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from clean_local_emails import clean_multiple_accounts

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # 本地邮箱配置
    local_email_receiver_config = {
        "email": "virginia_diaz@mcp.com",
        "password": "virginia_85W", 
        "name": "NLP Course Assistant",
        "imap_server": "localhost", 
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587, 
        "use_ssl": False,
        "use_starttls": False,
        "use_auth": False  # 本地服务器无需认证
    }

    local_email_config = {
        "email": "mcooper@mcp.com",
        "password": "maria_89vHV7", 
        "name": "NLP Course Student",
        "imap_server": "localhost", 
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587, 
        "use_ssl": False,
        "use_starttls": False,
        "use_auth": False  # 本地服务器无需认证
    }

    # 学生邮箱配置 - 朱晓钟
    local_email_config_zxz = {
        "email": "bennettb47@mcp.com",
        "password": "bennett$b549", 
        "name": "朱晓钟",
        "imap_server": "localhost", 
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587, 
        "use_ssl": False,
        "use_starttls": False,
        "use_auth": False
    }

    # 学生邮箱配置 - 韦杨珂
    local_email_config_wyk = {
        "email": "gortiz78@mcp.com",
        "password": "ortiz$g114yW", 
        "name": "韦杨珂",
        "imap_server": "localhost", 
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587, 
        "use_ssl": False,
        "use_starttls": False,
        "use_auth": False
    }

    print("发邮件以构建初始状态")
    
    # 首先清理所有相关的邮箱账户（包括学生邮箱）
    print("清理本地邮箱（包括学生邮箱）")
    accounts_to_clean = [
        local_email_receiver_config, 
        local_email_config,
        local_email_config_zxz,  # 朱晓钟的邮箱
        local_email_config_wyk   # 韦杨珂的邮箱
    ]
    
    clean_success = clean_multiple_accounts(accounts_to_clean)
    if not clean_success:
        print("⚠️ 邮箱清理未完全成功，但继续执行邮件发送")
    else:
        print("✅ 邮箱清理完成")

    # 发送方使用 mcooper@mcp.com，接收方使用 virginia_diaz@mcp.com
    sender_email = local_email_config["email"]  # mcooper@mcp.com
    sender_password = local_email_config["password"]
    receiver = local_email_receiver_config["email"]  # virginia_diaz@mcp.com
    
    print(f"📧 邮件发送配置:")
    print(f"   发送方: {sender_email} ({local_email_config['name']})")
    print(f"   接收方: {receiver} ({local_email_receiver_config['name']})")

    # 邮件数据文件路径
    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"

    # 使用本地send_email.py模块
    send_email_path = Path(__file__).parent / "send_email.py"
    
    print(f"🚀 开始发送邮件...")
    print(f"   邮件数据: {email_jsonl_file}")
    print(f"   占位符: {placeholder_file_path}")
    
    asyncio.run(run_command(
                f"uv run {send_email_path} -s {sender_email} "
                f"-p '{sender_password}' "
                f"-r {receiver} "
                f"-j {email_jsonl_file} "
                f"--delay 2.0 "
                f"--placeholder {placeholder_file_path} "
                # f"--quiet "
                f"--no-confirm"
                ,debug=True,show_output=True))
    
    # 等待直到所有邮件都已收到
    print("等待10s以便邮件接收完成...")
    sleep(10)

    
    print("已通过发送邮件构建初始状态！")