import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re
import time
from argparse import ArgumentParser, RawTextHelpFormatter
from utils.mcp.tool_servers import MCPServerManager, call_tool_with_retry, ToolCallError


class MCPEmailSender:
    """使用MCP服务器发送邮件的类"""
    
    def __init__(self, verbose=True):
        """
        初始化MCP邮件发送器
        :param verbose: 是否打印详细信息
        """
        self.verbose = verbose
        self.server_manager = MCPServerManager()
    
    def _log(self, message, force=False):
        """打印日志信息"""
        if self.verbose or force:
            print(message)
    
    async def send_email(self, to_email, subject, content, content_type='plain'):
        """
        使用MCP服务器发送邮件
        :param to_email: 收件人邮箱
        :param subject: 邮件标题
        :param content: 邮件内容
        :param content_type: 内容类型 'plain' 或 'html'
        """
        try:
            # 准备邮件参数
            email_params = {
                'to': to_email,
                'subject': subject,
                'body': content if content_type == 'plain' else '',
                'html_body': content if content_type == 'html' else ''
            }
            
            # 移除空的html_body参数
            if not email_params['html_body']:
                del email_params['html_body']
            
            self._log(f"正在发送邮件...")
            self._log(f"   收件人：{to_email}")
            self._log(f"   主题：{subject}")
            self._log(f"   内容类型：{content_type}")
            
            # 使用MCP服务器发送邮件
            result = await call_tool_with_retry(
                server_name='emails',
                tool_name='send_email',
                arguments=email_params,
                max_retries=3,
                server_manager=self.server_manager
            )
            
            self._log("✅ 邮件发送成功！")
            self._log("-" * 50)
            return True
            
        except ToolCallError as e:
            error_msg = f"MCP邮件发送失败 - 主题: {subject}, 错误: {str(e)}"
            self._log(f"❌ {error_msg}", force=True)
            self._log("-" * 50)
            return False
        except Exception as e:
            error_msg = f"邮件发送异常 - 主题: {subject}, 错误: {str(e)}"
            self._log(f"❌ {error_msg}", force=True)
            self._log("-" * 50)
            return False
    
    async def send_batch_emails(self, to_email, email_list, delay=1):
        """
        批量发送邮件
        :param to_email: 收件人邮箱
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
            
            success = await self.send_email(
                to_email=to_email,
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
        
        self._log("\n批量发送完成！")
        self._log(f"成功: {success_count} 封，失败: {fail_count} 封")
        
        return success_count, fail_count, failed_emails


def format_email_with_personal_info(email_data, 
                                    placeholder_values, 
                                    today,
                                    verbose=True):
    """
    使用personal_info中的键值对格式化邮件数据
    占位符格式: <<<<||||key||||>>>>
    :param email_data: 原始邮件数据字典
    :param placeholder_values: 占位符值字典
    :param today: 今天的日期
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
                    pattern = r'<<<<\|\|\|\|([\w+-]+)\|\|\|\|>>>>'
                    matches = re.findall(pattern, value)
                    
                    formatted_value = value
                    for match in matches:
                        placeholder = f'<<<<||||{match}||||>>>>'
                        if match in placeholder_values:
                            replacement = str(placeholder_values[match])
                            formatted_value = formatted_value.replace(placeholder, replacement)
                        # 如果是日期或者年份
                        elif match == 'year' or match.startswith('today+') or match.startswith('today-'):
                            try:
                                if match == 'year':
                                    # 计算今天+30天后的年份
                                    today_date = datetime.fromisoformat(today)
                                    future_date = today_date + timedelta(days=30)
                                    replacement = str(future_date.year)
                                elif match.startswith('today+'):
                                    # 解析today+X格式，X是天数
                                    days_to_add = int(match[6:])  # 去掉'today+'前缀
                                    today_date = datetime.fromisoformat(today)
                                    future_date = today_date + timedelta(days=days_to_add)
                                    replacement = future_date.strftime('%Y-%m-%d')
                                elif match.startswith('today-'):
                                    # 解析today-X格式，X是天数
                                    days_to_subtract = int(match[6:])  # 去掉'today-'前缀
                                    today_date = datetime.fromisoformat(today)
                                    past_date = today_date - timedelta(days=days_to_subtract)
                                    replacement = past_date.strftime('%Y-%m-%d')
                                else:
                                    replacement = placeholder  # 保持原样
                                
                                formatted_value = formatted_value.replace(placeholder, replacement)
                            except (ValueError, TypeError) as e:
                                _log(f"⚠️  日期处理错误: {e}", force=True)
                                # 如果日期处理失败，保持原占位符
                                pass
                        else:
                            _log(f"⚠️  未找到placeholder_values中的键: {match}", force=True)
                    
                    formatted_email[key] = formatted_value
                    
                except Exception as e:
                    _log(f"⚠️  格式化字段 '{key}' 时出错: {e}", force=True)
                    # 如果格式化失败，保持原值
                    pass
        
        return formatted_email
        
    except Exception as e:
        _log(f"⚠️  格式化邮件数据时出错: {e}", force=True)
        return email_data


def load_emails_from_jsonl(file_path, placeholder_file_path, verbose=True):
    """
    从JSONL文件加载邮件数据
    :param file_path: JSONL文件路径
    :param placeholder_file_path: 占位符文件路径
    :param verbose: 是否打印详细信息
    :return: 邮件列表
    """
    def _log(message, force=False):
        if verbose or force:
            print(message)
    
    emails = []
    placeholder_values = {}
    with open(placeholder_file_path, 'r', encoding='utf-8') as f:
        placeholder_values = json.load(f)

    # 获取今天的日期，格式为ISO格式 (YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 保存today时间到文件，用于后续eval
    # 相对于当前文件的位置：../groundtruth_workspace/today.txt
    script_dir = Path(__file__).parent.parent
    today_file_path = script_dir / 'groundtruth_workspace' / 'today.txt'
    with open(today_file_path, 'w', encoding='utf-8') as f:
        f.write(today)
    _log(f"✅ 已保存today时间到: {today_file_path}")

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
                    
                    # 使用placeholder_values格式化邮件数据
                    formatted_email = format_email_with_personal_info(email_data, placeholder_values, today, verbose=verbose)
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
    parser = ArgumentParser(
        description='MCP邮件批量发送工具',
        formatter_class=RawTextHelpFormatter,
        epilog='''
示例:
  python mcp_send_email.py --receiver target@example.com --jsonl emails.jsonl --placeholder placeholder.json

JSONL文件格式示例:
  {"sender_name": "张三", "subject": "测试邮件", "content": "这是邮件内容"}
  {"sender_name": "李四", "subject": "HTML邮件", "content": "<h1>HTML标题</h1><p>内容</p>", "content_type": "html"}
        '''
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
        '--placeholder', '-pl',
        required=True,
        help='包含占位符的JSON文件路径'
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


async def main():
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 设置verbose模式
    verbose = not args.quiet
    
    # 打印配置信息
    if verbose:
        print("=" * 60)
        print("MCP邮件批量发送工具")
        print("=" * 60)
        print(f"收件人邮箱: {args.receiver}")
        print(f"邮件数据文件: {args.jsonl}")
        print(f"占位符文件: {args.placeholder}")
        print(f"发送延迟: {args.delay} 秒")
        print("=" * 60)
        print()
    
    # 加载邮件数据
    if verbose:
        print("正在加载邮件数据...")
    
    emails = load_emails_from_jsonl(args.jsonl, args.placeholder, verbose=verbose)

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
    
    sender = MCPEmailSender(verbose=verbose)
    success_count, fail_count, failed_emails = await sender.send_batch_emails(
        to_email=args.receiver,
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
        raise Exception(f"{fail_count} 封邮件发送失败")


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        sys.exit(1)