import imaplib
import smtplib
import json
import email
import time
import re
from email import policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple


class EmailSendError(Exception):
    """邮件发送错误"""
    pass


class LocalEmailManager:
    """本地邮件管理器，集成发送和接收功能"""
    
    def __init__(self, config_file: str, verbose: bool = True):
        """
        初始化本地邮箱管理器
        
        Args:
            config_file: 配置文件路径
            verbose: 是否打印详细信息
        """
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # 基本配置
        self.email = self.config['email']
        self.password = self.config.get('password') or ""  # 允许空密码（本地免认证）
        self.name = self.config.get('name') or self.email
        self.verbose = verbose

        # IMAP 配置
        self.imap_server = self.config['imap_server']
        self.imap_port = int(self.config['imap_port'])

        # SMTP 配置
        self.smtp_server = self.config['smtp_server']
        self.smtp_port = int(self.config['smtp_port'])

        # 连接选项
        self.use_ssl = self.config.get('use_ssl', False)
        self.use_starttls = self.config.get('use_starttls', False)

    def _log(self, message: str, force: bool = False):
        """打印日志信息"""
        if self.verbose or force:
            print(message)

    # ========================================
    # IMAP 相关功能
    # ========================================
    
    def connect_imap(self) -> imaplib.IMAP4:
        """连接 IMAP 服务器并登录（必要时）"""
        if self.use_ssl:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        else:
            mail = imaplib.IMAP4(self.imap_server, self.imap_port)

        try:
            mail.login(self.email, self.password)
        except imaplib.IMAP4.error as e:
            raise RuntimeError(f"IMAP 登录失败：{e}")
        return mail

    def clear_all_emails(self, mailbox: str = 'INBOX') -> None:
        """清空某个邮箱（默认 INBOX）"""
        mail = self.connect_imap()
        try:
            typ, _ = mail.select(mailbox)
            if typ != 'OK':
                raise RuntimeError(f"无法选择邮箱 {mailbox}")

            typ, data = mail.search(None, 'ALL')
            if typ != 'OK':
                raise RuntimeError("搜索邮件失败")

            ids = data[0].split()
            if not ids:
                self._log("ℹ️ 收件箱已为空，无需清理。")
            else:
                for num in ids:
                    mail.store(num, '+FLAGS', r'(\Deleted)')
                mail.expunge()
                self._log("✅ 已清空邮箱中的所有邮件")
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()

    def get_all_emails(self, mailbox: str = 'INBOX') -> List[Dict[str, str]]:
        """获取邮箱中的所有邮件（主题/发件人/日期/正文）"""
        mail = self.connect_imap()
        emails = []
        try:
            typ, _ = mail.select(mailbox)
            if typ != 'OK':
                raise RuntimeError(f"无法选择邮箱 {mailbox}")

            typ, data = mail.search(None, 'ALL')
            if typ != 'OK':
                raise RuntimeError("搜索邮件失败")

            ids = data[0].split()
            if not ids:
                return []

            for num in ids:
                typ, msg_data = mail.fetch(num, '(RFC822)')
                if typ != 'OK' or not msg_data or not msg_data[0]:
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email, policy=policy.default)

                emails.append({
                    'subject': msg['Subject'],
                    'from': msg['From'],
                    'date': msg['Date'],
                    'body': self._extract_body(msg),
                })
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()
        return emails

    def count_recent_emails(self, sender_email: Optional[str] = None, 
                          minutes: int = 20, mailbox: str = 'INBOX') -> int:
        """统计最近几分钟内的邮件数量，可指定发件人"""
        mail = self.connect_imap()
        try:
            typ, _ = mail.select(mailbox)
            if typ != 'OK':
                raise RuntimeError(f"无法选择邮箱 {mailbox}")

            # 计算时间范围
            since_time = datetime.now() - timedelta(minutes=minutes)
            since_date = since_time.strftime('%d-%b-%Y')
            
            # 构建搜索条件
            if sender_email:
                search_criteria = f'(SINCE "{since_date}" FROM "{sender_email}")'
            else:
                search_criteria = f'SINCE "{since_date}"'

            typ, data = mail.search(None, search_criteria)
            if typ != 'OK':
                self._log(f"搜索邮件失败，条件：{search_criteria}")
                return 0

            ids = data[0].split()
            return len(ids)

        except Exception as e:
            self._log(f"统计邮件时出错：{e}")
            return 0
        finally:
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()

    def wait_for_emails(self, expected_count: int, sender_email: Optional[str] = None, 
                       max_wait_minutes: int = 30, check_interval: int = 10) -> bool:
        """
        等待指定数量的邮件到达
        
        Args:
            expected_count: 期望收到的邮件数量
            sender_email: 可选，指定发件人邮箱
            max_wait_minutes: 最大等待时间（分钟）
            check_interval: 检查间隔（秒）
            
        Returns:
            bool: 是否成功收到所有邮件
        """
        self._log("=" * 60)
        self._log("等待邮件接收完成")
        self._log("=" * 60)
        self._log(f"期望接收 {expected_count} 封邮件")
        if sender_email:
            self._log(f"发件人邮箱: {sender_email}")
        
        self._log("\n开始等待邮件接收...")
        self._log(f"检查间隔: {check_interval} 秒")
        self._log(f"最大等待时间: {max_wait_minutes} 分钟")
        self._log("-" * 60)

        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60

        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_seconds:
                self._log(f"\n❌ 等待超时！已等待 {max_wait_minutes} 分钟")
                return False

            # 统计最近邮件数量
            recent_count = self.count_recent_emails(sender_email, minutes=max_wait_minutes)

            # 显示进度
            elapsed_minutes = int(elapsed_time / 60)
            elapsed_seconds = int(elapsed_time % 60)
            self._log(f"[{elapsed_minutes:02d}:{elapsed_seconds:02d}] 已收到 {recent_count}/{expected_count} 封邮件")

            # 检查是否所有邮件都已收到
            if recent_count >= expected_count:
                self._log(f"\n✅ 所有邮件都已收到！")
                self._log(f"   期望: {expected_count} 封")
                self._log(f"   实际: {recent_count} 封")
                self._log(f"   耗时: {elapsed_minutes} 分 {elapsed_seconds} 秒")
                return True

            time.sleep(check_interval)

    # ========================================
    # SMTP 相关功能
    # ========================================
    
    def send_email(self, to_email: str, subject: str, content: str, 
                   content_type: str = 'html', sender_name: Optional[str] = None) -> bool:
        """
        发送邮件到本地 SMTP
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件标题
            content: 邮件内容
            content_type: 内容类型 'plain' 或 'html'
            sender_name: 发件人显示名称，默认使用配置中的名称
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建邮件
            msg = MIMEMultipart()
            display_name = sender_name or self.name
            msg['From'] = formataddr((display_name, self.email))
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(content, _subtype=content_type, _charset='utf-8'))

            # 建立 SMTP 连接
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
                server.ehlo()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                server.ehlo_or_helo_if_needed()

                # STARTTLS：仅在配置打开时尝试
                if self.use_starttls:
                    if 'starttls' in getattr(server, 'esmtp_features', {}):
                        server.starttls()
                        server.ehlo()
                    else:
                        self._log("ℹ️ 服务器不支持 STARTTLS，按明文继续。")

            # 登录：仅在服务器宣称支持 AUTH 时尝试
            esmtp_features = getattr(server, 'esmtp_features', {})
            if 'auth' in esmtp_features and self.password:
                try:
                    server.login(self.email, self.password)
                except smtplib.SMTPNotSupportedError:
                    self._log("ℹ️ 服务器不支持 AUTH，跳过登录。")
                except smtplib.SMTPException as e:
                    self._log(f"ℹ️ SMTP 登录失败（将尝试无认证发送）：{e}")

            # 发送
            server.send_message(msg)
            server.quit()
            self._log(f"✅ 邮件发送成功: {subject}")
            self._log(f"   发件人：{display_name}")
            self._log(f"   收件人：{to_email}")
            self._log("-" * 50)
            return True

        except Exception as e:
            self._log(f"❌ 邮件发送失败: {e}", force=True)
            self._log(f"   发件人: {sender_name or self.name}")
            self._log(f"   主题: {subject}")
            self._log("-" * 50)
            return False

    def send_batch_emails(self, receiver_email: str, email_list: List[Dict[str, Any]], 
                         delay: float = 1) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        批量发送邮件
        
        Args:
            receiver_email: 收件人邮箱
            email_list: 邮件列表，每个元素是一个字典
            delay: 每封邮件之间的延迟（秒）
            
        Returns:
            Tuple[成功数量, 失败数量, 失败的邮件列表]
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
                content = email_data['content']
                if ('<html>' in content.lower() or '<body>' in content.lower() or 
                    '<p>' in content or '<div>' in content):
                    content_type = 'html'
                else:
                    content_type = 'plain'

            success = self.send_email(
                to_email=receiver_email,
                subject=email_data['subject'],
                content=email_data['content'],
                content_type=content_type,
                sender_name=email_data['sender_name']
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

    # ========================================
    # 数据处理相关功能
    # ========================================
    
    def format_email_with_placeholders(self, email_data: Dict[str, Any], 
                                     placeholder_values: Dict[str, str], 
                                     today: str) -> Dict[str, Any]:
        """
        使用占位符格式化邮件数据
        占位符格式: <<<<||||key||||>>>>
        
        Args:
            email_data: 原始邮件数据字典
            placeholder_values: 占位符键值对
            today: 今天的日期（ISO格式）
            
        Returns:
            格式化后的邮件数据字典
        """
        formatted_email = email_data.copy()

        try:
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
                            elif match == 'year' or match.startswith('today+') or match.startswith('today-'):
                                try:
                                    if match == 'year':
                                        today_date = datetime.fromisoformat(today)
                                        future_date = today_date + timedelta(days=30)
                                        replacement = str(future_date.year)
                                    elif match.startswith('today+'):
                                        days_to_add = int(match[6:])  # 去掉'today+'前缀
                                        today_date = datetime.fromisoformat(today)
                                        future_date = today_date + timedelta(days=days_to_add)
                                        replacement = future_date.strftime('%Y-%m-%d')
                                    elif match.startswith('today-'):
                                        days_to_subtract = int(match[6:])  # 去掉'today-'前缀
                                        today_date = datetime.fromisoformat(today)
                                        past_date = today_date - timedelta(days=days_to_subtract)
                                        replacement = past_date.strftime('%Y-%m-%d')
                                    else:
                                        replacement = placeholder

                                    formatted_value = formatted_value.replace(placeholder, replacement)
                                except (ValueError, TypeError) as e:
                                    self._log(f"⚠️ 日期处理错误: {e}", force=True)
                            else:
                                self._log(f"⚠️ 未找到占位符的键: {match}", force=True)

                        formatted_email[key] = formatted_value

                    except Exception as e:
                        self._log(f"⚠️ 格式化字段 '{key}' 时出错: {e}", force=True)

            return formatted_email

        except Exception as e:
            self._log(f"⚠️ 格式化邮件数据时出错: {e}", force=True)
            return email_data

    def load_emails_from_jsonl(self, file_path: str, placeholder_file_path: str = None, 
                              save_today_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        从JSONL文件加载邮件数据
        
        Args:
            file_path: JSONL文件路径
            placeholder_file_path: 占位符文件路径
            save_today_to: 保存today时间的文件路径
            
        Returns:
            邮件列表
        """
        emails = []
        placeholder_values = {}
        
        if placeholder_file_path:
            with open(placeholder_file_path, 'r', encoding='utf-8') as f:
                placeholder_values = json.load(f)

        # 获取今天的日期
        today = datetime.now().strftime('%Y-%m-%d')

        # 保存today时间到指定文件
        if save_today_to:
            today_path = Path(save_today_to)
            today_path.parent.mkdir(parents=True, exist_ok=True)
            with open(today_path, 'w', encoding='utf-8') as f:
                f.write(today)
            self._log(f"✅ 已保存today时间到: {today_path}")

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
                            self._log(f"⚠️ 第 {line_num} 行缺少必需字段: {missing_fields}", force=True)
                            continue

                        # 设置默认内容类型
                        if 'content_type' not in email_data:
                            email_data['content_type'] = 'auto'

                        # 使用占位符格式化邮件数据
                        if placeholder_values:
                            formatted_email = self.format_email_with_placeholders(
                                email_data, placeholder_values, today)
                            emails.append(formatted_email)
                        else:
                            emails.append(email_data)

                    except json.JSONDecodeError as e:
                        self._log(f"⚠️ 第 {line_num} 行JSON解析错误: {e}", force=True)
                        continue

            self._log(f"✅ 成功加载 {len(emails)} 封邮件")
            return emails

        except FileNotFoundError:
            self._log(f"❌ 文件未找到: {file_path}", force=True)
            raise
        except Exception as e:
            self._log(f"❌ 读取文件时出错: {e}", force=True)
            raise

    # ========================================
    # Helper 方法
    # ========================================
    
    def _extract_body(self, msg: email.message.EmailMessage) -> str:
        """
        优先返回 text/plain；若无则退回 text/html；都无则返回空串。
        遍历 multipart 时跳过附件。
        """
        if msg.is_multipart():
            plain_text = None
            html_text = None
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = (part.get('Content-Disposition') or '').lower()
                if 'attachment' in disp:
                    continue
                if ctype == 'text/plain' and plain_text is None:
                    plain_text = self._safe_decode(part)
                elif ctype == 'text/html' and html_text is None:
                    html_text = self._safe_decode(part)
            return plain_text if plain_text is not None else (html_text or "")
        else:
            ctype = msg.get_content_type()
            if ctype in ('text/plain', 'text/html'):
                return self._safe_decode(msg)
            return ""

    def _safe_decode(self, part: email.message.Message) -> str:
        """按声明字符集解码，默认 utf-8，出错用替换策略"""
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ""
            charset = part.get_content_charset() or 'utf-8'
            return payload.decode(charset, errors='replace')
        except Exception:
            try:
                return payload.decode('utf-8', errors='replace')
            except Exception:
                return ""