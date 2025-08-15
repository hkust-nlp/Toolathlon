import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    args = parser.parse_args()

    print("发邮件以构建初始状态")
    # 先清理gmail和calendar
    # 然后发邮件
    print("清理gmail和calendar")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('clean_gmail_calendar')} --credentials_file {args.credentials_file}"
                ,debug=True,show_output=True))

    # 使用MCP服务器发送邮件，不再需要账户配置
    receiver = "test@example.com"  # 这里需要根据实际情况配置收件人

    # 邮件文件路径
    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"

    # 使用新的MCP邮件发送脚本
    asyncio.run(run_command(
                f"uv run -m {get_module_path('mcp_send_email')} "
                f"-r {receiver} "
                f"-j {email_jsonl_file} "
                f"--placeholder {placeholder_file_path} "
                f"--delay 2.0 "
                f"--no-confirm"
                ,debug=True,show_output=True))
    
    # 等待直到所有邮件都已收到
    print("等待10s以便邮件接收完成...")
    sleep(10)
    
    print("已通过MCP服务器发送邮件构建初始状态！")