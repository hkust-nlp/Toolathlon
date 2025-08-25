import asyncio
import sys
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep

from utils.local_email import LocalEmailManager

sys.path.insert(0, str(Path(__file__).parent.parent))  # 添加任务目录到路径
from token_key_session import all_token_key_session

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    

    print("Preprocessing...")

    print("发邮件以构建初始状态")
    
    # 获取邮件配置文件路径
    emails_config_file = all_token_key_session.emails_config_file
    print(f"使用邮件配置文件: {emails_config_file}")
    
    # 初始化本地邮件管理器
    email_manager = LocalEmailManager(emails_config_file, verbose=True)
    
    # 清理邮箱
    print("清理邮箱")
    email_manager.clear_all_emails()
    
    # 邮件文件路径
    email_jsonl_file = Path(__file__).parent / ".." / "files" / "emails.jsonl"
    placeholder_file_path = Path(__file__).parent / ".." / "files" / "placeholder_values.json"
    
    # 保存今天时间的文件路径
    today_file_path = Path(__file__).parent / ".." / "groundtruth_workspace" / "today.txt"
    
    # 加载邮件数据
    print("正在加载邮件数据...")
    emails = email_manager.load_emails_from_jsonl(
        str(email_jsonl_file), 
        str(placeholder_file_path),
        str(today_file_path)
    )
    
    if not emails:
        print("❌ 没有有效的邮件数据")
        sys.exit(1)
    
    # 批量发送邮件
    print(f"开始发送 {len(emails)} 封邮件...")
    success_count, fail_count, failed_emails = email_manager.send_batch_emails(
        receiver_email=email_manager.email,  # 发送给自己
        email_list=emails,
        delay=2.0
    )
    
    # 显示发送结果
    if fail_count > 0:
        print(f"\n❌ 有 {fail_count} 封邮件发送失败:")
        for failed in failed_emails:
            print(f"  - 第 {failed['index']} 封: {failed['sender_name']} - {failed['subject']}")
        sys.exit(1)
    
    print(f"\n✅ 成功发送 {success_count} 封邮件")
    
    # 等待邮件接收完成
    print("等待10s以便邮件接收完成...")
    sleep(10)
    
    print("验证所有邮件都已收到...")
    success = email_manager.wait_for_emails(
        expected_count=len(emails),
        sender_email=None,  # 不限制发件人
        max_wait_minutes=1,
        check_interval=5
    )
    
    if not success:
        print("\n❌ 邮件接收等待失败")
        sys.exit(1)
    
    print("\n✅ 已通过发送邮件构建初始状态！")
    
    # 打印所有邮件的发件人和主题以供调试
    # print("\n=== 调试信息：所有邮件的发件人和主题 ===")
    # for i, email in enumerate(emails, 1):
    #     sender = email.get('sender_name', 'Unknown Sender')
    #     subject = email.get('subject', 'No Subject')
    #     print(f"{i:2d}. 发件人: {sender} | 主题: {subject}")
    # print("=" * 50)

    print("初始化 GitHub 仓库...")
    github_token = all_token_key_session.github_token
    asyncio.run(run_command(
                f"uv run -m {get_module_path('init_github_repo')} --github_token {github_token}"
                ,debug=True,show_output=True))
    print("GitHub 仓库初始化完成")