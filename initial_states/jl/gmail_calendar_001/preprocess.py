import asyncio
from argparse import ArgumentParser
from utils.general.helper import run_command

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--credentials_file",default="configs/credentials.json")
    args = parser.parse_args()

    from configs.google_accounts import account_info
    from configs.personal_info import personal_info

    print("发邮件以构建初始状态")
    asyncio.run(run_command(
                f"uv run -m initial_states.jl.gmail_calendar_001.clean_gmail_calendar --credentials_file {args.credentials_file}"
                ,debug=True,show_output=True))

    sender_email = account_info.aux_google_account_1.email
    sender_app_password = account_info.aux_google_account_1.app_password
    receiver = account_info.main_google_account.email

    # TODO: now hardcoded here
    email_jsonl_file = "initial_states/jl/gmail_calendar_001/emails.jsonl"

    asyncio.run(run_command(
                f"uv run -m initial_states.jl.gmail_calendar_001.send_email -s {sender_email} "
                f"-p '{sender_app_password}' "
                f"-r {receiver} "
                f"-j {email_jsonl_file} "
                f"--delay 1.0 "
                # f"--quiet "
                f"--no-confirm"
                ,debug=True,show_output=True))
    print("已通过发送邮件构建初始状态！")



