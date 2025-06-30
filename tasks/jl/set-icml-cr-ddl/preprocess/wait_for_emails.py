import json
import time
import argparse
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def load_emails_from_jsonl(file_path):
    """从JSONL文件加载邮件数据，返回邮件列表"""
    emails = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                try:
                    email_data = json.loads(line)
                    emails.append(email_data)
                except json.JSONDecodeError as e:
                    print(f"⚠️  第 {line_num} 行JSON解析错误: {e}")
                    continue
        return emails
    except FileNotFoundError:
        print(f"❌ 文件未找到: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}")
        sys.exit(1)


def get_gmail_service(credentials_file):
    """获取Gmail服务"""
    # 加载凭证
    with open(credentials_file, 'r') as f:
        cred_data = json.load(f)
    
    creds = Credentials(
        token=cred_data.get('token'),
        refresh_token=cred_data.get('refresh_token'),
        token_uri=cred_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=cred_data.get('client_id'),
        client_secret=cred_data.get('client_secret')
    )
    
    # 刷新 token
    if creds.expired:
        print("正在刷新访问令牌...")
        creds.refresh(Request())
    
    # 构建 Gmail 服务
    return build('gmail', 'v1', credentials=creds)


def count_recent_emails(gmail_service, sender_email, minutes=10):
    """统计最近几分钟内来自指定发件人的邮件数量"""
    try:
        # 构建查询条件：来自指定发件人且在最近几分钟内
        query = f"from:{sender_email} newer_than:{minutes}m"
        
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100
        ).execute()
        
        messages = results.get('messages', [])
        return len(messages)
        
    except HttpError as e:
        print(f"❌ Gmail API 错误: {e}")
        return 0


def wait_for_emails(credentials_file, email_jsonl_file, max_wait_minutes=30, check_interval=10):
    """
    等待所有邮件都收到
    
    :param credentials_file: Gmail凭证文件路径
    :param email_jsonl_file: 邮件JSONL文件路径
    :param max_wait_minutes: 最大等待时间（分钟）
    :param check_interval: 检查间隔（秒）
    """
    print("=" * 60)
    print("等待邮件接收完成")
    print("=" * 60)
    
    # 加载邮件数据
    print("正在加载邮件数据...")
    emails = load_emails_from_jsonl(email_jsonl_file)
    expected_count = len(emails)
    print(f"期望接收 {expected_count} 封邮件")
    
    # 获取发件人邮箱（从第一封邮件中提取）
    if not emails:
        print("❌ 没有邮件数据")
        return False
    
    # 从邮件数据中提取发件人邮箱
    # 这里假设发件人邮箱是固定的，从配置中获取
    from configs.google_accounts import account_info
    sender_email = account_info.aux_google_account_1.email
    print(f"发件人邮箱: {sender_email}")
    
    # 获取Gmail服务
    gmail_service = get_gmail_service(credentials_file)
    
    # 获取用户信息
    try:
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f"收件人邮箱: {profile.get('emailAddress')}")
    except HttpError as e:
        print(f"❌ 无法获取用户信息: {e}")
        return False
    
    print("\n开始等待邮件接收...")
    print(f"检查间隔: {check_interval} 秒")
    print(f"最大等待时间: {max_wait_minutes} 分钟")
    print("-" * 60)
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while True:
        # 检查当前时间是否超过最大等待时间
        elapsed_time = time.time() - start_time
        if elapsed_time > max_wait_seconds:
            print(f"\n❌ 等待超时！已等待 {max_wait_minutes} 分钟")
            return False
        
        # 统计最近10分钟内的邮件数量
        recent_count = count_recent_emails(gmail_service, sender_email, minutes=10)
        
        # 显示进度
        elapsed_minutes = int(elapsed_time / 60)
        elapsed_seconds = int(elapsed_time % 60)
        print(f"[{elapsed_minutes:02d}:{elapsed_seconds:02d}] 已收到 {recent_count}/{expected_count} 封邮件")
        
        # 检查是否所有邮件都已收到
        if recent_count >= expected_count:
            print(f"\n✅ 所有邮件都已收到！")
            print(f"   期望: {expected_count} 封")
            print(f"   实际: {recent_count} 封")
            print(f"   耗时: {elapsed_minutes} 分 {elapsed_seconds} 秒")
            return True
        
        # 等待下次检查
        time.sleep(check_interval)


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='等待Gmail邮件接收完成',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--credentials_file',
        required=True,
        help='Gmail凭证文件路径'
    )
    
    parser.add_argument(
        '--email_jsonl_file',
        required=True,
        help='邮件JSONL文件路径'
    )
    
    parser.add_argument(
        '--max_wait_minutes',
        type=int,
        default=30,
        help='最大等待时间（分钟，默认: 30）'
    )
    
    parser.add_argument(
        '--check_interval',
        type=int,
        default=10,
        help='检查间隔（秒，默认: 10）'
    )
    
    return parser


def main():
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 等待邮件接收
    success = wait_for_emails(
        credentials_file=args.credentials_file,
        email_jsonl_file=args.email_jsonl_file,
        max_wait_minutes=args.max_wait_minutes,
        check_interval=args.check_interval
    )
    
    if not success:
        print("\n❌ 邮件接收等待失败")
        sys.exit(1)
    
    print("\n✅ 邮件接收等待完成！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        sys.exit(1) 