import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time
from email import policy
from email.utils import formataddr
import argparse
import json
import sys
from pathlib import Path
import re

from configs.personal_info import personal_info

class EmailSendError(Exception):
    """邮件发送错误"""
    pass

class GmailSender:
    def __init__(self, sender_email, app_password, verbose=True):
        """
        初始化Gmail发送器
        :param sender_email: 你的Gmail邮箱地址
        :param app_password: Gmail应用专用密码（16位）
        :param verbose: 是否打印详细信息
        """
        self.sender_email = sender_email
        self.app_password = app_password
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.verbose = verbose
    
    def _log(self, message, force=False):
        """打印日志信息"""
        if self.verbose or force:
            print(message)
    
    def send_email(self, receiver_email, sender_name, subject, content, content_type='plain'):
        """
        发送邮件
        :param receiver_email: 收件人邮箱
        :param sender_name: 发件人显示名称
        :param subject: 邮件标题
        :param content: 邮件内容
        :param content_type: 内容类型 'plain' 或 'html'
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            
            # 设置发件人（包含自定义名称）
            msg['From'] = formataddr((sender_name, self.sender_email))
            msg['To'] = receiver_email
            msg['Subject'] = subject
            
            # 添加邮件正文
            msg.attach(MIMEText(content, content_type, 'utf-8'))
            
            # 连接Gmail服务器
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # 启用TLS加密
            server.login(self.sender_email, self.app_password)
            
            # 发送邮件
            server.send_message(msg)
            server.quit()
            
            self._log(f"✅ 邮件发送成功！")
            self._log(f"   发件人：{sender_name}")
            self._log(f"   收件人：{receiver_email}")
            self._log(f"   主题：{subject}")
            self._log("-" * 50)
            
            return True
            
        except Exception as e:
            error_msg = f"邮件发送失败 - 发件人: {sender_name}, 主题: {subject}, 错误: {str(e)}"
            self._log(f"❌ {error_msg}", force=True)
            self._log("-" * 50)
            return False
    
    def send_batch_emails(self, receiver_email, email_list, delay=1):
        """
        批量发送邮件
        :param receiver_email: 收件人邮箱
        :param email_list: 邮件列表，每个元素是一个字典
        :param delay: 每封邮件之间的延迟（秒）
        :return: (success_count, fail_count, failed_emails)
        """
        self._log(f"开始批量发送 {len(email_list)} 封邮件...\n")
        
        success_count = 0
        fail_count = 0
        failed_emails = []
        
        for i, email_data in enumerate(email_list, 1):
            self._log(f"正在发送第 {i}/{len(email_list)} 封邮件...")
            
            # 自动检测内容类型
            content_type = email_data.get('content_type', 'plain')
            if content_type == 'auto':
                # 简单检测是否包含HTML标签
                content = email_data['content']
                if '<html>' in content.lower() or '<body>' in content.lower() or '<p>' in content or '<div>' in content:
                    content_type = 'html'
                else:
                    content_type = 'plain'
            
            success = self.send_email(
                receiver_email=receiver_email,
                sender_name=email_data['sender_name'],
                subject=email_data['subject'],
                content=email_data['content'],
                content_type=content_type
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                failed_emails.append({
                    'index': i,
                    'sender_name': email_data['sender_name'],
                    'subject': email_data['subject']
                })
            
            if i < len(email_list):
                self._log(f"等待 {delay} 秒后发送下一封邮件...\n")
                time.sleep(delay)
        
        self._log(f"\n批量发送完成！")
        self._log(f"成功: {success_count} 封，失败: {fail_count} 封")
        
        return success_count, fail_count, failed_emails

def format_email_with_personal_info(email_data, verbose=True):
    """
    使用personal_info中的键值对格式化邮件数据
    占位符格式: <<<<||||key||||>>>>
    :param email_data: 原始邮件数据字典
    :param verbose: 是否打印详细信息
    :return: 格式化后的邮件数据字典
    """
    def _log(message, force=False):
        if verbose or force:
            print(message)
    
    formatted_email = email_data.copy()
    
    try:
        # 格式化每个字符串字段
        for key, value in formatted_email.items():
            if isinstance(value, str):
                try:
                    # 查找所有占位符 <<<<||||key||||>>>>
                    pattern = r'<<<<\|\|\|\|(\w+)\|\|\|\|>>>>'
                    matches = re.findall(pattern, value)
                    
                    formatted_value = value
                    for match in matches:
                        placeholder = f'<<<<||||{match}||||>>>>'
                        if match in personal_info:
                            replacement = str(personal_info[match])
                            formatted_value = formatted_value.replace(placeholder, replacement)
                            _log(f"替换占位符: {placeholder} -> {replacement}")
                        else:
                            _log(f"⚠️  未找到personal_info中的键: {match}", force=True)
                    
                    formatted_email[key] = formatted_value
                    
                except Exception as e:
                    _log(f"⚠️  格式化字段 '{key}' 时出错: {e}", force=True)
                    # 如果格式化失败，保持原值
                    pass
        
        return formatted_email
        
    except Exception as e:
        _log(f"⚠️  格式化邮件数据时出错: {e}", force=True)
        return email_data

def load_emails_from_jsonl(file_path, verbose=True):
    """
    从JSONL文件加载邮件数据
    :param file_path: JSONL文件路径
    :param verbose: 是否打印详细信息
    :return: 邮件列表
    """
    def _log(message, force=False):
        if verbose or force:
            print(message)
    
    emails = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                try:
                    email_data = json.loads(line)
                    
                    # 验证必需字段
                    required_fields = ['sender_name', 'subject', 'content']
                    missing_fields = [field for field in required_fields if field not in email_data]
                    
                    if missing_fields:
                        _log(f"⚠️  第 {line_num} 行缺少必需字段: {missing_fields}", force=True)
                        continue
                    
                    # 如果没有指定content_type，设为auto以自动检测
                    if 'content_type' not in email_data:
                        email_data['content_type'] = 'auto'
                    
                    # 使用personal_info格式化邮件数据
                    formatted_email = format_email_with_personal_info(email_data, verbose=verbose)
                    emails.append(formatted_email)
                    
                except json.JSONDecodeError as e:
                    _log(f"⚠️  第 {line_num} 行JSON解析错误: {e}", force=True)
                    continue
                    
        _log(f"✅ 成功加载 {len(emails)} 封邮件")
        return emails
        
    except FileNotFoundError:
        print(f"❌ 文件未找到: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}")
        sys.exit(1)

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='Gmail批量邮件发送工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python gmail_sender.py --sender your@gmail.com --password "your_app_password" --receiver target@example.com --jsonl emails.jsonl

JSONL文件格式示例:
  {"sender_name": "张三", "subject": "测试邮件", "content": "这是邮件内容"}
  {"sender_name": "李四", "subject": "HTML邮件", "content": "<h1>HTML标题</h1><p>内容</p>", "content_type": "html"}
  
占位符格式:
  使用 <<<<||||key||||>>>> 作为占位符，其中key是personal_info中的键名
  例如: "Hello <<<<||||name||||>>>>, your email is <<<<||||email||||>>>>"
        '''
    )
    
    parser.add_argument(
        '--sender', '-s',
        required=True,
        help='发件人Gmail邮箱地址'
    )
    
    parser.add_argument(
        '--password', '-p',
        required=True,
        help='Gmail应用专用密码（16位）'
    )
    
    parser.add_argument(
        '--receiver', '-r',
        required=True,
        help='收件人邮箱地址'
    )
    
    parser.add_argument(
        '--jsonl', '-j',
        required=True,
        help='包含邮件内容的JSONL文件路径'
    )
    
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=2.0,
        help='每封邮件之间的延迟秒数（默认: 2秒）'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只检查JSONL文件，不实际发送邮件'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='安静模式，只在出错时打印信息'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='不需要确认，直接发送'
    )
    
    return parser

def main():
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 设置verbose模式
    verbose = not args.quiet
    
    # 打印配置信息
    if verbose:
        print("=" * 60)
        print("Gmail批量邮件发送工具")
        print("=" * 60)
        print(f"发件人邮箱: {args.sender}")
        print(f"收件人邮箱: {args.receiver}")
        print(f"邮件数据文件: {args.jsonl}")
        print(f"发送延迟: {args.delay} 秒")
        print("=" * 60)
        print()
    
    # 加载邮件数据
    if verbose:
        print("正在加载邮件数据...")
    emails = load_emails_from_jsonl(args.jsonl, verbose=verbose)
    
    if not emails:
        print("❌ 没有有效的邮件数据")
        sys.exit(1)
    
    # 如果是dry-run模式，只显示邮件预览
    if args.dry_run:
        if verbose:
            print("\n🔍 Dry-run模式 - 邮件预览:\n")
            for i, email in enumerate(emails, 1):
                print(f"邮件 {i}:")
                print(f"  发件人名称: {email['sender_name']}")
                print(f"  主题: {email['subject']}")
                print(f"  内容类型: {email.get('content_type', 'auto')}")
                print(f"  内容预览: {email['content'][:100]}{'...' if len(email['content']) > 100 else ''}")
                print("-" * 40)
            print(f"\n总计: {len(emails)} 封邮件")
        else:
            print(f"Dry-run: {len(emails)} emails loaded")
        return
    
    # 确认发送
    if not args.no_confirm:
        if verbose:
            print(f"\n准备发送 {len(emails)} 封邮件到 {args.receiver}")
        confirm = input("是否继续？(y/n): ")
        if confirm.lower() != 'y':
            if verbose:
                print("已取消发送")
            sys.exit(0)
    
    # 创建发送器并发送邮件
    if verbose:
        print("\n开始发送邮件...\n")
    
    sender = GmailSender(args.sender, args.password, verbose=verbose)
    success_count, fail_count, failed_emails = sender.send_batch_emails(
        receiver_email=args.receiver,
        email_list=emails,
        delay=args.delay
    )
    
    # 显示最终结果
    if verbose:
        print("\n" + "=" * 60)
        print("发送完成！")
        print(f"成功: {success_count} 封")
        print(f"失败: {fail_count} 封")
        print("=" * 60)
    else:
        # 安静模式下只打印简单结果
        print(f"完成: 成功 {success_count}/{len(emails)}")
    
    # 如果有失败的邮件，打印详情并抛出异常
    if fail_count > 0:
        print(f"\n❌ 有 {fail_count} 封邮件发送失败:")
        for failed in failed_emails:
            print(f"  - 第 {failed['index']} 封: {failed['sender_name']} - {failed['subject']}")
        
        # 抛出异常使程序返回非0状态码
        raise EmailSendError(f"{fail_count} 封邮件发送失败")

if __name__ == "__main__":
    try:
        main()
    except EmailSendError as e:
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        sys.exit(1)