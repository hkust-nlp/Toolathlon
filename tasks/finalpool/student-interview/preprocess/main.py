import asyncio
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    from configs.google_accounts import account_info
    # from configs.personal_info import personal_info

    print("发邮件以构建初始状态")
    # 先清理gmail和calendar
    # 然后发邮件
    print("清理gmail和calendar")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('clean_gmail_calendar')} --credentials_file {args.credentials_file}"
                ,debug=True,show_output=True))

    sender_email = account_info.aux_google_account_1.email
    sender_app_password = account_info.aux_google_account_1.app_password
    receiver = account_info.main_google_account.email

    # TODO: now hardcoded here
    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"

    asyncio.run(run_command(
                f"uv run -m {get_module_path('send_email')} -s {sender_email} "
                f"-p '{sender_app_password}' "
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
    
    # 设置Google Calendar初始状态
    print("\n设置Google Calendar初始状态...")
    asyncio.run(run_command(
                f"uv run -m {get_module_path('setup_calendar_events')} --credentials_file {args.credentials_file}"
                ,debug=True,show_output=True))
    
    # asyncio.run(run_command(
    #             f"uv run -m {get_module_path('wait_for_emails')} "
    #             f"--credentials_file {args.credentials_file} "
    #             f"--email_jsonl_file {email_jsonl_file} "
    #             f"--max_wait_minutes 5 "
    #             f"--check_interval 5"
    #             ,debug=True,show_output=True))
    
    print("已完成初始状态构建！")
    print("✅ Gmail: 5封学生简历邮件已发送")
    print("✅ Google Calendar: 2个初始事件已创建")
    print("   - 今天15:00-17:00: 学术委员会会议") 
    print("   - 明天09:00-11:00: 博士生论文答辩")
    print("🎯 Agent需要避开这些时间段来安排面试")