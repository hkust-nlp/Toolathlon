import asyncio
import sys
from argparse import ArgumentParser
from pathlib import Path
from utils.general.helper import run_command, get_module_path
from time import sleep

from utils.app_specific.poste.local_email_manager import LocalEmailManager

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
    
    # 接收方邮件配置文件路径（用于评测清理）
    receiver_config_file = Path(__file__).parent / ".." / "files" / "receiver_config.json"
    
    # 初始化本地邮件管理器
    email_manager = LocalEmailManager(emails_config_file, verbose=True)
    
    # 清理邮箱（包括发送方和接收方）
    print("清理发送方邮箱...")
    email_manager.clear_all_emails()
    
    print("清理接收方邮箱...")
    receiver_email_manager = LocalEmailManager(str(receiver_config_file), verbose=True)
    receiver_email_manager.clear_all_emails()
    
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