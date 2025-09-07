#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考试通知邮件发送脚本
通过Poste.io的SMTP/IMAP服务发送考试通知邮件

新功能：干扰邮件注入
====================
为了模拟真实的邮箱环境，现在可以在考试通知邮件前后注入一些无关的干扰邮件。

干扰邮件类型（25种）：
📦 购物电商：Amazon, eBay, Target, Etsy
🎬 娱乐媒体：Netflix, YouTube, Spotify, TikTok
👥 社交网络：LinkedIn, Facebook, Instagram, Twitter
💰 金融银行：Chase Bank, PayPal, Wells Fargo
🍕 外卖配送：Uber Eats, DoorDash, Grubhub
✈️ 旅行住宿：Booking.com, Airbnb, Delta Airlines
📰 新闻资讯：The New York Times, Medium
🎯 团购优惠：Groupon, LivingSocial
💬 社区论坛：Reddit, Stack Overflow
💪 健康健身：MyFitnessPal, Headspace
🎮 游戏娱乐：Steam, Twitch

邮件数量和时间分布：
- 考试邮件前：随机注入6-12封邮件，时间分布在考试邮件前0.5-5天
- 考试邮件后：随机注入4-8封邮件，时间分布在考试邮件后1-48小时
- 总计：10-20封干扰邮件 + 1封考试通知邮件

使用方法：
```python
# 推荐用法：清除收件箱 + 干扰邮件（模拟真实环境）
inject_exam_emails_from_config('config.json', clear_inbox=True, add_distractions=True)

# 只注入考试邮件，无干扰
inject_exam_emails_from_config('config.json', clear_inbox=True, add_distractions=False)
```

测试模式：
```bash
python send_exam_notification_smtp.py --test
```

运行效果示例：
```
📋 模式: 清除收件箱后注入新邮件
🎭 干扰模式: 启用 - 将添加无关邮件增加真实性

🎭 步骤1: 注入干扰邮件（考试通知前）...
📮 正在注入 9 封干扰邮件（考试通知前）...
  ✅ Amazon: Your order has been shipped! Track your package... (11-27 09:15)
  ✅ Chase Bank: Account Alert: Large purchase detected... (11-28 14:32)
  ✅ Netflix: New shows added to your list - Watch now!... (11-29 11:45)
  ✅ MyFitnessPal: Weekly progress: You're on track! 💪... (11-29 19:20)
  ✅ Instagram: Your Story highlights got 50+ views! 📸... (11-30 08:30)
  ✅ Steam: Weekend Deal: 75% off indie games! 🎮... (11-30 16:45)
  ✅ Booking.com: Price drop alert! Save $45 on your Tokyo tri... (11-30 22:10)
  ✅ Target: Weekend sale: Up to 50% off home essentials... (12-01 06:22)
  ✅ PayPal: You've received $25.00 from Mom... (12-01 07:55)

📧 步骤2: 注入考试通知邮件...
✅ 邮件注入成功！

🎭 步骤3: 注入干扰邮件（考试通知后）...
📮 正在注入 6 封干扰邮件（考试通知后）...
  ✅ DoorDash: Your order from Thai Garden is on the way! 🚗... (12-01 12:30)
  ✅ Facebook: You have 3 friend requests and 8 notification... (12-01 15:45)
  ✅ YouTube: Your video got 1,000 views! 🎉... (12-01 20:15)
  ✅ Reddit: Trending posts you might have missed... (12-02 08:30)
  ✅ LinkedIn: Someone viewed your profile... (12-02 14:20)
  ✅ Twitch: Your favorite streamer is live! 🔴... (12-02 19:45)

🎭 已添加干扰邮件以模拟真实邮箱环境
```

总计邮件数：15封干扰邮件 + 1封考试通知 = 16封邮件
"""

import smtplib
import imaplib
import json
import logging
import time
import ssl
import email
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class ExamNotificationSender:
    """考试通知邮件发送器"""
    
    def __init__(self, config_file: str):
        """
        初始化邮件发送器
        :param config_file: 配置文件路径
        """
        # 先创建logger，再加载配置
        self.logger = logging.getLogger('ExamNotificationSender')
        self.setup_logging()
        self.config = self._load_config(config_file)
        self.smtp_connection = None
        self.imap_connection = None
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info("配置文件加载成功")
            return config
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")
    
    def get_recipient_credentials(self) -> Dict[str, str]:
        """获取收件人的邮箱凭据"""
        try:
            # 直接从配置中获取收件人信息
            recipient = self.config['recipient']
            
            # 检查是否包含密码信息
            if 'password' in recipient:
                credentials = {
                    'email': recipient['email'],
                    'password': recipient['password']
                }
                self.logger.info(f"成功获取收件人凭据: {recipient['email']}")
                return credentials
            else:
                self.logger.warning("收件人配置中缺少密码信息")
                return None
            
        except Exception as e:
            self.logger.error(f"获取收件人凭据失败: {e}")
            return None
    
    def setup_logging(self):
        """设置日志系统"""
        # 使用默认配置初始化日志系统
        log_file = 'email_send.log'
        log_level = logging.INFO
        
        # 配置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置logger
        self.logger.setLevel(log_level)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("日志系统初始化完成")
    
    def connect_smtp(self) -> bool:
        """连接SMTP服务器"""
        try:
            server_config = self.config['server_config']
            self.logger.info(f"正在连接SMTP服务器: {server_config['smtp_server']}:{server_config['smtp_port']}")
            
            # 创建SMTP连接
            self.smtp_connection = smtplib.SMTP(
                server_config['smtp_server'],
                server_config['smtp_port'],
                timeout=server_config.get('timeout', 30)
            )
            
            # 设置调试级别
            self.smtp_connection.set_debuglevel(1)
            
            # 发送EHLO命令
            self.smtp_connection.ehlo()
            
            # 检查是否支持STARTTLS
            if self.smtp_connection.has_extn('STARTTLS'):
                self.logger.info("服务器支持STARTTLS，正在启用...")
                self.smtp_connection.starttls()
                self.smtp_connection.ehlo()
                self.logger.info("STARTTLS启用成功")
            else:
                self.logger.info("服务器不支持STARTTLS")
            
            self.logger.info("SMTP服务器连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP服务器连接失败: {e}")
            return False
    
    def authenticate_smtp(self) -> bool:
        """SMTP服务器认证"""
        try:
            sender_account = self.config['sender_account']
            self.logger.info(f"正在认证SMTP账户: {sender_account['email']}")
            
            # 检查服务器是否支持AUTH
            if not self.smtp_connection.has_extn('AUTH'):
                self.logger.warning("服务器不支持AUTH扩展，尝试直接发送邮件...")
                return True  # 如果服务器不需要认证，直接返回成功
            
            # 执行SMTP认证
            self.smtp_connection.login(
                sender_account['email'],
                sender_account['password']
            )
            
            self.logger.info("SMTP认证成功")
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP认证失败: {e}")
            # 如果认证失败，尝试不认证发送
            self.logger.info("尝试不认证发送邮件...")
            return True
    
    def load_email_template(self) -> str:
        """加载邮件模板"""
        try:
            template_file = self.config['email_content']['template_file']
            template_path = Path(__file__).parent.parent / 'files' / template_file
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            self.logger.info("邮件模板加载成功")
            return template
        except Exception as e:
            self.logger.error(f"加载邮件模板失败: {e}")
            # 返回默认模板
            default_template = """Dear {recipient_name},

This is a notification about your upcoming exam:

Course: {course_name}
Date: {exam_date}
Time: {exam_time}
Location: {exam_location}
Type: {exam_type}
Duration: {duration}

Please arrive 15 minutes before the exam time.

Best regards,
Course Instructor"""
            return default_template
    
    def format_email_content(self, template: str) -> str:
        """格式化邮件内容"""
        try:
            # 获取配置信息
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            exam_info = self.config['email_content']['exam_info']
            
            # 替换模板变量
            content = template.format(
                recipient_name=recipient['name'],
                course_name=exam_info['course_name'],
                exam_type=exam_info['exam_type'],
                exam_date=exam_info['exam_date'],
                exam_time=exam_info['exam_time'],
                duration=exam_info['duration'],
                exam_location=exam_info['exam_location'],
                sender_email=sender_account['email'],
                sender_name=sender_account['name'],
                send_time=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            self.logger.info("邮件内容格式化完成")
            return content
            
        except Exception as e:
            self.logger.error(f"邮件内容格式化失败: {e}")
            raise
    
    def send_email(self, content: str) -> bool:
        """发送邮件"""
        try:
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            subject = self.config['email_content']['subject']
            
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = f"{sender_account['name']} <{sender_account['email']}>"
            msg['To'] = f"{recipient['name']} <{recipient['email']}>"
            msg['Subject'] = subject
            
            # 添加邮件正文
            text_part = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # 发送邮件
            self.logger.info(f"正在发送邮件给: {recipient['email']}")
            self.smtp_connection.send_message(msg)
            
            self.logger.info("邮件发送成功")
            return True
            
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")
            return False
    
    def connect_imap(self) -> bool:
        """连接IMAP服务器"""
        try:
            server_config = self.config['server_config']
            self.logger.info(f"正在连接IMAP服务器: {server_config['imap_server']}:{server_config['imap_port']}")
            
            # 创建IMAP连接
            if server_config.get('use_ssl', False):
                self.imap_connection = imaplib.IMAP4_SSL(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            else:
                self.imap_connection = imaplib.IMAP4(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            
            self.logger.info("IMAP服务器连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"IMAP服务器连接失败: {e}")
            return False
    
    def authenticate_imap(self) -> bool:
        """IMAP服务器认证"""
        try:
            sender_account = self.config['sender_account']
            self.logger.info(f"正在认证IMAP账户: {sender_account['email']}")
            
            # 执行IMAP认证
            self.imap_connection.login(
                sender_account['email'],
                sender_account['password']
            )
            
            self.logger.info("IMAP认证成功")
            return True
            
        except Exception as e:
            self.logger.error(f"IMAP认证失败: {e}")
            return False
    
    def delete_recipient_inbox_emails(self) -> bool:
        """删除收件人收件箱中的所有邮件"""
        try:
            # 获取收件人凭据
            recipient_credentials = self.get_recipient_credentials()
            if not recipient_credentials:
                self.logger.warning("无法获取收件人凭据，跳过删除操作")
                return False
            
            # 使用收件人凭据连接IMAP服务器
            server_config = self.config['server_config']
            self.logger.info(f"正在连接收件人IMAP服务器: {server_config['imap_server']}:{server_config['imap_port']}")
            
            # 创建新的IMAP连接（使用收件人凭据）
            if server_config.get('use_ssl', False):
                recipient_imap = imaplib.IMAP4_SSL(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            else:
                recipient_imap = imaplib.IMAP4(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            
            # 使用收件人凭据认证
            recipient_imap.login(
                recipient_credentials['email'],
                recipient_credentials['password']
            )
            
            self.logger.info("收件人IMAP连接成功")
            
            # 选择收件箱
            recipient_imap.select('INBOX')
            
            # 搜索所有邮件
            _, message_numbers = recipient_imap.search(None, 'ALL')
            
            if message_numbers[0]:
                # 获取所有邮件编号
                email_nums = message_numbers[0].split()
                total_emails = len(email_nums)
                
                if total_emails > 0:
                    self.logger.info(f"找到 {total_emails} 封邮件，开始删除...")
                    
                    # 删除所有邮件
                    for email_num in email_nums:
                        recipient_imap.store(email_num, '+FLAGS', '\\Deleted')
                    
                    # 永久删除标记的邮件
                    recipient_imap.expunge()
                    
                    self.logger.info(f"成功删除收件箱中的 {total_emails} 封邮件")
                else:
                    self.logger.info("收件箱中没有邮件需要删除")
            else:
                self.logger.info("收件箱中没有邮件")
            
            # 关闭收件人IMAP连接
            recipient_imap.close()
            recipient_imap.logout()
            
            return True
            
        except Exception as e:
            self.logger.error(f"删除收件人收件箱邮件失败: {e}")
            return False
    
    def verify_email_sent(self) -> bool:
        """验证邮件是否发送成功"""
        try:
            self.logger.info("正在验证邮件发送状态...")
            
            # 选择发件箱
            self.imap_connection.select('Sent')
            
            # 搜索最近的邮件
            search_criteria = f'TO "{self.config["recipient"]["email"]}"'
            _, message_numbers = self.imap_connection.search(None, search_criteria)
            
            if message_numbers[0]:
                # 获取最新的邮件
                latest_email_num = message_numbers[0].split()[-1]
                _, msg_data = self.imap_connection.fetch(latest_email_num, '(RFC822)')
                
                # 解析邮件内容
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # 检查邮件主题
                subject = email_message.get('Subject', '')
                expected_subject = self.config['email_content']['subject']
                
                if expected_subject in subject:
                    self.logger.info("邮件发送验证成功")
                    return True
                else:
                    self.logger.warning(f"邮件主题不匹配: 期望 '{expected_subject}', 实际 '{subject}'")
                    return False
            else:
                self.logger.warning("未找到发送给目标收件人的邮件")
                return False
                
        except Exception as e:
            self.logger.error(f"邮件验证失败: {e}")
            return False
    
    def cleanup(self):
        """清理连接"""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                self.logger.info("SMTP连接已关闭")
            
            if self.imap_connection:
                self.imap_connection.close()
                self.imap_connection.logout()
                self.logger.info("IMAP连接已关闭")
                
        except Exception as e:
            self.logger.error(f"清理连接时出错: {e}")
    
    def send_exam_notification(self) -> bool:
        """发送考试通知邮件的主流程"""
        try:
            self.logger.info("开始发送考试通知邮件...")
            
            # 1. 连接SMTP服务器
            if not self.connect_smtp():
                return False
            
            # 2. SMTP认证
            if not self.authenticate_smtp():
                return False
            
            # 3. 删除收件人收件箱中的所有邮件
            self.logger.info("开始删除收件人收件箱邮件...")
            delete_success = self.delete_recipient_inbox_emails()
            if delete_success:
                self.logger.info("收件人收件箱邮件删除完成")
            else:
                self.logger.warning("收件人收件箱邮件删除失败，但继续执行邮件发送")
            
            # 4. 加载和格式化邮件模板
            template = self.load_email_template()
            content = self.format_email_content(template)
            
            # 5. 发送邮件
            if not self.send_email(content):
                return False
            
            # 邮件发送成功
            self.logger.info("🎉 考试通知邮件发送成功！")
            print("✅ 邮件发送成功！")
            print(f"📧 发件人: {self.config['sender_account']['email']}")
            print(f"📧 收件人: {self.config['recipient']['email']}")
            print(f"📝 主题: {self.config['email_content']['subject']}")
            print(f"📅 考试时间: {self.config['email_content']['exam_info']['exam_date']} {self.config['email_content']['exam_info']['exam_time']}")
            print(f"📍 考试地点: {self.config['email_content']['exam_info']['exam_location']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"发送考试通知邮件时发生错误: {e}")
            print(f"❌ 邮件发送失败: {e}")
            return False
        
        finally:
            self.cleanup()

def main():
    """主函数"""
    try:
        # 配置文件路径
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        # 创建邮件发送器
        sender = ExamNotificationSender(str(config_file))
        
        # 发送考试通知邮件
        success = sender.send_exam_notification()
        
        if success:
            print("\n🎯 考试通知邮件处理完成！")
        else:
            print("\n💥 考试通知邮件处理失败！")
            exit(1)
            
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        exit(1)

if __name__ == "__main__":
    main()

class ExamNotificationInjector:
    """考试通知邮件直接注入器 - 直接将邮件注入到收件箱，支持自定义时间戳"""
    
    def __init__(self, config_file: str):
        """
        初始化邮件注入器
        :param config_file: 配置文件路径
        """
        self.logger = logging.getLogger('ExamNotificationInjector')
        self.setup_logging()
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info("配置文件加载成功")
            return config
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")
    
    def setup_logging(self):
        """设置日志"""
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def load_email_template(self) -> str:
        """加载邮件模板"""
        try:
            template_file = self.config['email_content']['template_file']
            template_path = Path(__file__).parent.parent / 'files' / template_file
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            self.logger.info("邮件模板加载成功")
            return template
        except Exception as e:
            self.logger.error(f"加载邮件模板失败: {e}")
            # 返回默认模板
            return """Dear {recipient_name},

This is a notification about your upcoming exam:

Course: {course_name}
Date: {exam_date}
Time: {exam_time}
Location: {exam_location}
Type: {exam_type}
Duration: {duration}

Please arrive 15 minutes before the exam time.

Best regards,
Course Instructor"""
    
    def format_email_content(self, template: str) -> str:
        """格式化邮件内容"""
        try:
            exam_info = self.config['email_content']['exam_info']
            recipient = self.config['recipient']
            
            content = template.format(
                recipient_name=recipient['name'],
                course_name=exam_info['course_name'],
                exam_type=exam_info['exam_type'],
                exam_date=exam_info['exam_date'],
                exam_time=exam_info['exam_time'],
                duration=exam_info['duration'],
                exam_location=exam_info['exam_location'],
                sender_email=self.config['sender_account']['email'],
                sender_name=self.config['sender_account']['name'],
                send_time=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            self.logger.info("邮件内容格式化成功")
            return content
        except Exception as e:
            self.logger.error(f"格式化邮件内容失败: {e}")
            raise
    
    def inject_email_to_imap(self, content: str, custom_timestamp: Optional[float] = None) -> bool:
        """
        直接将邮件注入到IMAP服务器收件箱
        :param content: 邮件内容
        :param custom_timestamp: 自定义时间戳 (Unix timestamp)，如果为None则使用当前时间
        """
        try:
            # 获取配置
            server_config = self.config['server_config']
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            subject = self.config['email_content']['subject']
            
            # 连接到IMAP服务器
            if server_config.get("use_ssl"):
                imap = imaplib.IMAP4_SSL(server_config["imap_server"], server_config["imap_port"])
            else:
                imap = imaplib.IMAP4(server_config["imap_server"], server_config["imap_port"])
            
            if server_config.get("use_starttls"):
                imap.starttls()
            
            # 使用收件人凭据登录
            imap.login(recipient['email'], recipient['password'])
            self.logger.info(f"✅ Connected to IMAP server as {recipient['email']}")
            
            # 选择收件箱
            imap.select("INBOX")
            
            # 创建邮件消息
            msg = MIMEMultipart()
            msg['From'] = f"{sender_account['name']} <{sender_account['email']}>"
            msg['To'] = f"{recipient['name']} <{recipient['email']}>"
            msg['Subject'] = subject
            
            # 设置时间戳
            if custom_timestamp:
                from email.utils import formatdate
                msg['Date'] = formatdate(custom_timestamp)
                self.logger.info(f"使用自定义时间戳: {formatdate(custom_timestamp)}")
            else:
                from email.utils import formatdate
                msg['Date'] = formatdate()
                self.logger.info("使用当前时间戳")
            
            # 添加邮件正文
            text_part = MIMEText(content, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # 将邮件注入到收件箱
            email_string = msg.as_string()
            imap.append("INBOX", None, None, email_string.encode('utf-8'))
            
            # 关闭连接
            imap.close()
            imap.logout()
            
            self.logger.info("✅ 邮件成功注入到收件箱")
            return True
            
        except Exception as e:
            self.logger.error(f"邮件注入失败: {e}")
            return False
    
    def delete_recipient_inbox_emails(self) -> bool:
        """删除收件人收件箱中的所有邮件"""
        try:
            # 获取收件人凭据
            recipient = self.config['recipient']
            server_config = self.config['server_config']
            
            self.logger.info(f"正在连接收件人IMAP服务器: {server_config['imap_server']}:{server_config['imap_port']}")
            
            # 创建新的IMAP连接（使用收件人凭据）
            if server_config.get('use_ssl', False):
                recipient_imap = imaplib.IMAP4_SSL(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            else:
                recipient_imap = imaplib.IMAP4(
                    server_config['imap_server'],
                    server_config['imap_port']
                )
            
            # 使用收件人凭据认证
            recipient_imap.login(
                recipient['email'],
                recipient['password']
            )
            
            self.logger.info("收件人IMAP连接成功")
            print("🗑️ 正在清除收件箱中的所有邮件...")
            
            # 选择收件箱
            recipient_imap.select('INBOX')
            
            # 搜索所有邮件
            _, message_numbers = recipient_imap.search(None, 'ALL')
            
            if message_numbers[0]:
                # 获取所有邮件编号
                email_nums = message_numbers[0].split()
                total_emails = len(email_nums)
                
                if total_emails > 0:
                    self.logger.info(f"找到 {total_emails} 封邮件，开始删除...")
                    print(f"📧 找到 {total_emails} 封邮件，正在删除...")
                    
                    # 删除所有邮件
                    for email_num in email_nums:
                        recipient_imap.store(email_num, '+FLAGS', '\\Deleted')
                    
                    # 永久删除标记的邮件
                    recipient_imap.expunge()
                    
                    self.logger.info(f"成功删除收件箱中的 {total_emails} 封邮件")
                    print(f"✅ 成功删除收件箱中的 {total_emails} 封邮件")
                else:
                    self.logger.info("收件箱中没有邮件需要删除")
                    print("📭 收件箱中没有邮件需要删除")
            else:
                self.logger.info("收件箱中没有邮件")
                print("📭 收件箱中没有邮件")
            
            # 关闭收件人IMAP连接
            recipient_imap.close()
            recipient_imap.logout()
            
            return True
            
        except Exception as e:
            self.logger.error(f"删除收件人收件箱邮件失败: {e}")
            print(f"❌ 删除收件箱邮件失败: {e}")
            return False

    def generate_distraction_emails(self) -> list:
        """生成干扰邮件模板"""
        distraction_emails = [
            # ===== 购物电商 =====
            {
                "from_name": "Amazon",
                "from_email": "no-reply@amazon.com",
                "subject": "Your order has been shipped! Track your package",
                "content": """Dear Customer,

Good news! Your recent order has been shipped and is on its way to you.

Order Details:
- Order Number: #123-4567890-1234567
- Shipping Carrier: UPS
- Tracking Number: 1Z999AA1234567890
- Estimated Delivery: 2-3 business days

You can track your package using the tracking number above on the carrier's website.

Thank you for choosing Amazon!

Best regards,
Amazon Customer Service Team"""
            },
            {
                "from_name": "eBay",
                "from_email": "ebay@ebay.com",
                "subject": "You've been outbid! Act fast to win this item",
                "content": """Hi,

Someone has placed a higher bid on the item you're watching:

Item: Vintage Leather Jacket - Size M
Current bid: $45.00
Your maximum bid: $40.00
Time left: 2 hours 34 minutes

Don't let this item slip away! Place a higher bid now to stay in the lead.

Happy bidding!
eBay Team"""
            },
            {
                "from_name": "Target",
                "from_email": "target@target.com",
                "subject": "Weekend sale: Up to 50% off home essentials",
                "content": """Don't miss out on these amazing deals!

This Weekend Only:
🏠 Home & Garden: Up to 50% off
👕 Clothing: Buy 2, get 1 free
🧴 Beauty products: 30% off select items
🍯 Grocery essentials: $5 off $50+

Plus, free shipping on orders over $35!
Sale ends Sunday at midnight.

Shop now - Target"""
            },
            {
                "from_name": "Etsy",
                "from_email": "transaction@etsy.com",
                "subject": "Your Etsy order is ready for pickup!",
                "content": """Great news!

Your order from ArtisanCraftsStudio is ready for pickup.

Order #ET789456123
- Handmade ceramic mug set (2 pieces)
- Custom name engraving
- Total: $34.95

Pickup available at the seller's studio or choose shipping.
Leave a review after pickup to help other buyers!

Thanks for supporting small businesses,
Etsy Team"""
            },

            # ===== 娱乐媒体 =====
            {
                "from_name": "Netflix",
                "from_email": "info@netflix.com", 
                "subject": "New shows added to your list - Watch now!",
                "content": """Hi there,

We've added some new shows and movies that we think you'll love!

New This Week:
🎬 The Crown - Season 6 (Drama)
🎭 Comedy Special: Dave Chappelle
🎯 True Crime: The Vanishing 
🚀 Sci-Fi Series: Space Force Returns

Don't forget to check out your personalized recommendations.

Happy watching!
The Netflix Team"""
            },
            {
                "from_name": "YouTube",
                "from_email": "noreply@youtube.com",
                "subject": "Your video got 1,000 views! 🎉",
                "content": """Congratulations!

Your video "How to Make Perfect Coffee at Home" just reached 1,000 views!

Video Stats:
📊 1,047 views
👍 89 likes  
💬 23 comments
⏱️ Average watch time: 3:42

Keep creating amazing content. Your subscribers love it!

YouTube Creator Team"""
            },
            {
                "from_name": "Spotify",
                "from_email": "noreply@spotify.com",
                "subject": "Your Weekly Music Discovery is ready!",
                "content": """Hey Music Lover!

Your personalized playlist is ready with 30 new songs picked just for you.

This Week's Highlights:
🎵 Trending Pop hits
🎸 Indie rock discoveries  
🎤 Hip-hop favorites
🎹 Chill electronic vibes

Plus, check out your 2024 listening stats - you've discovered 847 new artists this year!

Start listening now and discover your next favorite song.

Keep the music playing,
Spotify"""
            },
            {
                "from_name": "TikTok",
                "from_email": "no-reply@tiktok.com",
                "subject": "Your video is trending! 🔥",
                "content": """Amazing news!

Your TikTok video is taking off:

📱 "Quick morning routine hack"
👀 25.3K views in 24 hours
❤️ 3.2K likes
🔄 892 shares
💭 156 comments

Your content is resonating with viewers! Keep up the great work.

TikTok Creator Fund Team"""
            },

            # ===== 社交网络 =====
            {
                "from_name": "LinkedIn",
                "from_email": "notifications@linkedin.com",
                "subject": "Someone viewed your profile",
                "content": """Hi,

A professional in your network recently viewed your LinkedIn profile.

Profile Views This Week: 5
- 2 from your industry
- 1 from a recruiter 
- 2 from your extended network

Keep your profile updated to make a great impression!

Grow your professional network:
- Connect with colleagues
- Share industry insights
- Engage with posts

Best regards,
LinkedIn Team"""
            },
            {
                "from_name": "Facebook",
                "from_email": "notification@facebookmail.com",
                "subject": "You have 3 friend requests and 8 notifications",
                "content": """What's happening on Facebook

👥 Friend Requests (3):
• Sarah Johnson (2 mutual friends)
• Mike Chen (1 mutual friend)  
• Emma Rodriguez (5 mutual friends)

🔔 Recent Activity:
• John liked your photo
• 5 people commented on your post
• Lisa shared your article
• You have 3 event invitations

Don't miss out on what your friends are sharing!

The Facebook Team"""
            },
            {
                "from_name": "Instagram",
                "from_email": "no-reply@mail.instagram.com",
                "subject": "Your Story highlights got 50+ views! 📸",
                "content": """Your content is performing great!

Story Highlights Performance:
📊 "Travel Memories" - 67 views
🍕 "Food Adventures" - 52 views
🐕 "Pet Photos" - 89 views

Recent Activity:
• @alex_photo liked 3 of your posts
• @sarah_travels started following you
• 12 people viewed your latest story

Keep sharing those amazing moments!

Instagram Team"""
            },
            {
                "from_name": "Twitter",
                "from_email": "info@twitter.com",
                "subject": "Your tweet is getting attention! 🐦",
                "content": """Tweet Performance Update

Your recent tweet about coffee brewing tips:

📈 2.1K impressions
🔄 45 retweets
❤️ 178 likes
💬 23 replies

Top reply: "This actually works! Thanks for the tip 🙌"

Your engagement is up 67% this week. Keep the conversations going!

Twitter Team"""
            },

            # ===== 金融银行 =====
            {
                "from_name": "Chase Bank",
                "from_email": "alerts@chase.com",
                "subject": "Account Alert: Large purchase detected",
                "content": """Security Notice

We detected a large purchase on your Chase account:

Transaction Details:
• Amount: $847.32
• Merchant: Best Buy Electronics
• Date: Today, 2:34 PM
• Location: Downtown Mall

If this was you, no action needed.
If this wasn't you, please contact us immediately at 1-800-CHASE-24.

Your security is our priority.
Chase Fraud Protection Team"""
            },
            {
                "from_name": "PayPal",
                "from_email": "service@paypal.com",
                "subject": "You've received $25.00 from Mom",
                "content": """You've got money!

Payment Details:
From: Linda Smith (Mom)
Amount: $25.00
Note: "Coffee money for this week ☕"

The money is now available in your PayPal balance.
You can transfer it to your bank account or use it for your next purchase.

Thanks for using PayPal!
PayPal Team"""
            },
            {
                "from_name": "Wells Fargo",
                "from_email": "wellsfargo@wellsfargo.com",
                "subject": "Monthly statement is ready",
                "content": """Your statement is now available

Wells Fargo Checking Account
Statement Period: Nov 1 - Nov 30, 2024

Account Summary:
• Beginning Balance: $2,847.63
• Total Deposits: $3,200.00
• Total Withdrawals: $2,156.84
• Ending Balance: $3,890.79

View your complete statement online or in the Wells Fargo mobile app.

Wells Fargo Customer Service"""
            },

            # ===== 外卖配送 =====
            {
                "from_name": "Uber Eats",
                "from_email": "orders@ubereats.com",
                "subject": "20% off your next order - Limited time!",
                "content": """Hungry? We've got you covered! 🍕

Get 20% off your next Uber Eats order with code: SAVE20

Valid on orders over $25 from participating restaurants.

Popular near you:
🍔 Joe's Burger Joint (4.8★)
🍜 Dragon Noodle House (4.9★) 
🥗 Fresh Garden Cafe (4.7★)
🍕 Tony's Pizza Palace (4.6★)

Offer expires in 48 hours - Order now!

Bon appétit,
Uber Eats Team"""
            },
            {
                "from_name": "DoorDash",
                "from_email": "no-reply@doordash.com",
                "subject": "Your order from Thai Garden is on the way! 🚗",
                "content": """Great news! Your order is on the way.

Order Details:
• Pad Thai with chicken
• Spring rolls (4 pieces)  
• Thai iced tea
• Total: $28.47

Your Dasher Mike is 8 minutes away.
Track your order in real-time in the app.

Enjoy your meal!
DoorDash Team"""
            },
            {
                "from_name": "Grubhub",
                "from_email": "orders@grubhub.com",
                "subject": "Free delivery weekend! Order from 50+ restaurants",
                "content": """Free delivery all weekend long! 🚚

No delivery fees on orders from participating restaurants:

🌮 Mexican: Taco Bell, Chipotle, Local Taqueria
🍝 Italian: Papa John's, Local Pasta House
🍗 American: KFC, Five Guys, Local Grill
🍱 Asian: Panda Express, Local Sushi Bar

Minimum order $15. Offer valid Sat-Sun only.

Order now and save!
Grubhub Team"""
            },

            # ===== 旅行住宿 =====
            {
                "from_name": "Booking.com",
                "from_email": "customer.service@booking.com",
                "subject": "Price drop alert! Save $45 on your Tokyo trip",
                "content": """Good news! Prices dropped for your saved search.

Tokyo, Japan - Dec 15-22, 2024

Hotel Price Drops:
🏨 Tokyo Grand Hotel: Was $180/night → Now $135/night
🏨 Shibuya Business Hotel: Was $95/night → Now $78/night  
🏨 Asakusa Traditional Inn: Was $120/night → Now $89/night

Book now to lock in these lower prices!
Prices may go up again.

Happy travels,
Booking.com Team"""
            },
            {
                "from_name": "Airbnb",
                "from_email": "automated@airbnb.com",
                "subject": "Your host is excited to welcome you! 🏠",
                "content": """Your trip is coming up soon!

Booking Details:
📍 Cozy downtown apartment in Portland
📅 Check-in: Dec 8, 2024 (3:00 PM)
📅 Check-out: Dec 11, 2024 (11:00 AM)
🏠 Host: Jennifer

Check-in Instructions:
• Key lockbox code: 5847
• WiFi password: CoffeeCity2024
• Parking spot #12 in back lot

Your host says: "Welcome! There's fresh coffee and local restaurant recommendations on the counter."

Have a great stay!
Airbnb Team"""
            },
            {
                "from_name": "Delta Airlines",
                "from_email": "noreply@delta.com",
                "subject": "Flight DL1284 - Check-in now available ✈️",
                "content": """You can now check in for your flight!

Flight Information:
✈️ DL1284: New York (JFK) → Los Angeles (LAX)
📅 Tomorrow, Dec 2, 2024
🕐 Departure: 8:30 AM
🕒 Arrival: 11:45 AM (local time)
💺 Seat: 12F (Window)

Check in now to:
• Select your seat preferences
• Add bags if needed
• Get your mobile boarding pass

Safe travels!
Delta Air Lines"""
            },

            # ===== 新闻资讯 =====
            {
                "from_name": "The New York Times",
                "from_email": "nyt@nytimes.com",
                "subject": "Morning Briefing: Today's top stories",
                "content": """Good morning! Here's what you need to know:

🌍 World News:
• Climate summit reaches breakthrough agreement
• Tech innovation drives economic growth
• Space mission discovers new planetary system

🏛️ Politics:
• Congressional budget talks continue
• New infrastructure projects announced
• International trade agreements updated

📊 Business:
• Stock markets hit record highs
• Consumer confidence rises
• Tech sector leads gains

☀️ Weather: Sunny, high 72°F

Read more at nytimes.com
The New York Times"""
            },
            {
                "from_name": "Medium",
                "from_email": "noreply@medium.com",
                "subject": "Top stories in Technology this week 📱",
                "content": """Your weekly digest from Medium

📱 Technology highlights:

Most Popular:
• "The Future of Remote Work: 5 Trends to Watch"
• "AI Tools That Actually Save Time (Not Hype)"
• "Building Better Apps: Lessons from 100 User Interviews"

Trending Topics:
#MachineLearning #RemoteWork #Productivity #StartupLife

Based on your reading history, you might also like:
• "From Burnout to Balance: A Developer's Journey"
• "Why Every Team Needs a Documentation Strategy"

Happy reading!
Medium Team"""
            },

            # ===== 团购优惠 =====
            {
                "from_name": "Groupon",
                "from_email": "deals@groupon.com",
                "subject": "Weekend Flash Sale - Up to 70% off activities!",
                "content": """Weekend Plans? We've got deals! ⚡

Flash Sale ends Sunday midnight:

🎯 Activities & Entertainment:
- Escape Rooms: $15 (reg. $45)
- Mini Golf: $8 (reg. $20) 
- Bowling: $12 (reg. $35)
- Movie Tickets: $7 (reg. $15)

🍽️ Dining Deals:
- Italian Restaurant: 50% off dinner
- Sushi Bar: $25 for $50 worth
- Steakhouse: 40% off weekend brunch

⚽ Fitness & Wellness:
- Yoga Classes: $20 for 5 sessions
- Massage Therapy: 60% off
- Rock Climbing: $18 (reg. $40)

Limited quantities - grab yours now!
Groupon Deals Team"""
            },
            {
                "from_name": "LivingSocial",
                "from_email": "deals@livingsocial.com",
                "subject": "Local adventure deals - 60% off outdoor activities",
                "content": """Adventure awaits! 🏞️

Limited-time outdoor deals in your area:

🚴 Bike Tours:
• City highlights tour: $25 (reg. $65)
• Wine country cycling: $45 (reg. $95)

🛶 Water Sports:
• Kayak rental (2 hours): $18 (reg. $40)
• Stand-up paddleboard lesson: $22 (reg. $50)

🏔️ Hiking & Nature:
• Guided nature walk: $12 (reg. $30)
• Rock climbing intro class: $35 (reg. $80)

Book by Sunday to secure these prices!

Get outside and explore,
LivingSocial Adventures"""
            },

            # ===== 社区论坛 =====
            {
                "from_name": "Reddit",
                "from_email": "noreply@reddit.com",
                "subject": "Trending posts you might have missed",
                "content": """What's happening on Reddit

Here are the top posts from communities you follow:

🔥 Hot Posts:
• r/funny: Cat accidentally orders 50 pizzas
• r/technology: New smartphone breaks durability records
• r/movies: Behind-the-scenes secrets from latest blockbuster
• r/gaming: Indie game becomes overnight sensation

💬 Active Discussions:
• What's the best life advice you've received?
• Share your most embarrassing moment
• What skill should everyone learn?

Jump back into the conversation!
Reddit Team"""
            },
            {
                "from_name": "Stack Overflow",
                "from_email": "noreply@stackoverflow.com",
                "subject": "Weekly digest: Top Python questions",
                "content": """This week in Python development

🐍 Top Questions:
• "How to optimize database queries in Django?"
• "Best practices for handling API rate limits"
• "Memory management in large dataset processing"
• "Testing async functions properly"

💡 Popular Answers:
• List comprehensions vs generator expressions
• When to use async/await in Python
• Docker setup for Python microservices

Keep coding and keep learning!
Stack Overflow Team"""
            },

            # ===== 健康健身 =====
            {
                "from_name": "MyFitnessPal",
                "from_email": "noreply@myfitnesspal.com",
                "subject": "Weekly progress: You're on track! 💪",
                "content": """Great work this week!

📊 Weekly Summary:
• Logged 6 out of 7 days
• Average calories: 1,847 (goal: 1,800)
• Protein goal met 5 days
• Water intake: 95% of goal

🏃 Activity:
• 4 workouts completed
• 23,456 steps total
• 2.1 lbs lost this month

Keep up the momentum! Small consistent changes lead to big results.

Your health journey team,
MyFitnessPal"""
            },
            {
                "from_name": "Headspace",
                "from_email": "hello@headspace.com",
                "subject": "3-minute meditation break? 🧘‍♀️",
                "content": """Take a moment for yourself

You've been working hard. How about a quick meditation break?

🧘 Suggested sessions:
• "Desk Stress Relief" (3 min)
• "Focus Boost" (5 min)  
• "Gratitude Pause" (3 min)
• "Energy Reset" (7 min)

Research shows even 3 minutes of mindfulness can:
✓ Reduce stress levels
✓ Improve focus
✓ Boost creativity

Ready to press pause?

Mindfully yours,
Headspace Team"""
            },

            # ===== 游戏娱乐 =====
            {
                "from_name": "Steam",
                "from_email": "noreply@steampowered.com",
                "subject": "Weekend Deal: 75% off indie games! 🎮",
                "content": """Steam Weekend Sale is here!

🎮 Featured Deals (up to 75% off):
• "Pixel Adventure Quest" - $4.99 (was $19.99)
• "Space Strategy Empire" - $7.49 (was $29.99)
• "Cozy Farming Simulator" - $3.74 (was $14.99)
• "Mystery Detective Story" - $5.99 (was $23.99)

⭐ Highly Rated:
• All games 85%+ positive reviews
• Perfect for weekend gaming sessions
• Support independent developers

Sale ends Monday at 10 AM PST.

Happy gaming!
Steam Team"""
            },
            {
                "from_name": "Twitch",
                "from_email": "no-reply@twitch.tv",
                "subject": "Your favorite streamer is live! 🔴",
                "content": """GameMaster_Pro is now live!

🎮 Currently Playing: "Cyberpunk Adventure Redux"
👥 1,247 viewers watching
⏱️ Stream started 23 minutes ago

Recent highlights:
• Epic boss battle victory
• Viewer challenge accepted
• New speedrun attempt starting

Don't miss the action! Join the chat and be part of the community.

See you in the stream!
Twitch Notifications"""
            }
        ]
        return distraction_emails

    def inject_distraction_email(self, email_template: dict, timestamp: float) -> bool:
        """注入单个干扰邮件"""
        try:
            # 获取配置
            server_config = self.config['server_config']
            recipient = self.config['recipient']
            
            # 连接到IMAP服务器
            if server_config.get("use_ssl"):
                imap = imaplib.IMAP4_SSL(server_config["imap_server"], server_config["imap_port"])
            else:
                imap = imaplib.IMAP4(server_config["imap_server"], server_config["imap_port"])
            
            if server_config.get("use_starttls"):
                imap.starttls()
            
            # 使用收件人凭据登录
            imap.login(recipient['email'], recipient['password'])
            
            # 选择收件箱
            imap.select("INBOX")
            
            # 创建邮件消息
            msg = MIMEMultipart()
            msg['From'] = f"{email_template['from_name']} <{email_template['from_email']}>"
            msg['To'] = f"{recipient['name']} <{recipient['email']}>"
            msg['Subject'] = email_template['subject']
            
            # 设置时间戳
            from email.utils import formatdate
            msg['Date'] = formatdate(timestamp)
            
            # 添加邮件正文
            text_part = MIMEText(email_template['content'], 'plain', 'utf-8')
            msg.attach(text_part)
            
            # 将邮件注入到收件箱
            email_string = msg.as_string()
            imap.append("INBOX", None, None, email_string.encode('utf-8'))
            
            # 关闭连接
            imap.close()
            imap.logout()
            
            return True
            
        except Exception as e:
            self.logger.error(f"注入干扰邮件失败: {e}")
            return False

    def inject_exam_notification(self, custom_timestamp: Optional[float] = None, clear_inbox: bool = False, add_distractions: bool = True) -> bool:
        """
        注入考试通知邮件到收件箱
        :param custom_timestamp: 自定义时间戳 (Unix timestamp)
        :param clear_inbox: 是否在注入前清除收件箱中的所有邮件
        :param add_distractions: 是否添加干扰邮件
        """
        try:
            self.logger.info("开始注入考试通知邮件...")
            
            # 0. 如果启用清除选项，先清除收件箱
            if clear_inbox:
                print("\n🗑️ 步骤0: 清除收件箱邮件...")
                delete_success = self.delete_recipient_inbox_emails()
                if delete_success:
                    print("✅ 收件箱邮件清除完成")
                    self.logger.info("收件箱邮件清除完成")
                else:
                    print("⚠️ 收件箱邮件清除失败，但继续执行邮件注入")
                    self.logger.warning("收件箱邮件清除失败，但继续执行邮件注入")
            
            # 确定考试邮件的时间戳
            if custom_timestamp:
                exam_timestamp = custom_timestamp
            else:
                exam_timestamp = time.time()
            
            # 1. 注入干扰邮件（考试邮件之前）
            if add_distractions:
                print("\n🎭 步骤1: 注入干扰邮件（考试通知前）...")
                self.inject_distraction_emails_before(exam_timestamp)
            
            # 2. 加载和格式化考试邮件模板
            print("\n📧 步骤2: 注入考试通知邮件...")
            template = self.load_email_template()
            content = self.format_email_content(template)
            
            # 3. 注入考试邮件
            if not self.inject_email_to_imap(content, exam_timestamp):
                return False
            
            # 4. 注入干扰邮件（考试邮件之后）
            if add_distractions:
                print("\n🎭 步骤3: 注入干扰邮件（考试通知后）...")
                self.inject_distraction_emails_after(exam_timestamp)
            
            # 邮件注入成功
            self.logger.info("🎉 考试通知邮件注入成功！")
            print("\n✅ 邮件注入成功！")
            print(f"📧 发件人: {self.config['sender_account']['email']}")
            print(f"📧 收件人: {self.config['recipient']['email']}")
            print(f"📝 主题: {self.config['email_content']['subject']}")
            print(f"📅 考试时间: {self.config['email_content']['exam_info']['exam_date']} {self.config['email_content']['exam_info']['exam_time']}")
            print(f"📍 考试地点: {self.config['email_content']['exam_info']['exam_location']}")
            
            if custom_timestamp:
                from datetime import datetime
                dt = datetime.fromtimestamp(custom_timestamp)
                print(f"⏰ 邮件时间戳: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if add_distractions:
                print("🎭 已添加干扰邮件以模拟真实邮箱环境")
            
            return True
            
        except Exception as e:
            self.logger.error(f"注入考试通知邮件时发生错误: {e}")
            print(f"❌ 邮件注入失败: {e}")
            return False

    def inject_distraction_emails_before(self, exam_timestamp: float):
        """在考试邮件之前注入干扰邮件"""
        try:
            distraction_emails = self.generate_distraction_emails()
            
            # 在考试邮件前1-5天注入6-12封干扰邮件，增加数量使邮箱更加混乱
            num_emails = random.randint(6, 12)
            selected_emails = random.sample(distraction_emails, min(num_emails, len(distraction_emails)))
            
            print(f"📮 正在注入 {len(selected_emails)} 封干扰邮件（考试通知前）...")
            
            for i, email_template in enumerate(selected_emails):
                # 在考试邮件前0.5-5天的随机时间，扩大时间范围
                days_before = random.uniform(0.5, 5.0)  # 0.5-5天前
                hours_offset = random.uniform(0, 24)    # 再加上0-24小时的随机偏移
                total_seconds_before = (days_before * 24 * 3600) + (hours_offset * 3600)
                
                distraction_timestamp = exam_timestamp - total_seconds_before
                
                success = self.inject_distraction_email(email_template, distraction_timestamp)
                if success:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(distraction_timestamp)
                    print(f"  ✅ {email_template['from_name']}: {email_template['subject'][:50]}... ({dt.strftime('%m-%d %H:%M')})")
                else:
                    print(f"  ❌ 失败: {email_template['from_name']}")
                
                # 添加小延迟避免服务器压力
                time.sleep(0.3)
                
        except Exception as e:
            self.logger.error(f"注入考试前干扰邮件失败: {e}")
            print("⚠️ 部分干扰邮件注入失败，但继续执行")

    def inject_distraction_emails_after(self, exam_timestamp: float):
        """在考试邮件之后注入干扰邮件"""
        try:
            distraction_emails = self.generate_distraction_emails()
            
            # 在考试邮件后几小时到2天内注入4-8封干扰邮件，增加数量
            num_emails = random.randint(4, 8)
            # 选择不同的邮件，避免与之前选择的重复
            remaining_emails = [e for e in distraction_emails]
            random.shuffle(remaining_emails)  # 打乱顺序确保多样性
            selected_emails = remaining_emails[:min(num_emails, len(remaining_emails))]
            
            print(f"📮 正在注入 {len(selected_emails)} 封干扰邮件（考试通知后）...")
            
            for i, email_template in enumerate(selected_emails):
                # 在考试邮件后1小时到2天的随机时间，扩大时间范围
                hours_after = random.uniform(1, 48)     # 1-48小时后（2天）
                minutes_offset = random.uniform(0, 60)  # 再加上0-60分钟的随机偏移
                total_seconds_after = (hours_after * 3600) + (minutes_offset * 60)
                
                distraction_timestamp = exam_timestamp + total_seconds_after
                
                success = self.inject_distraction_email(email_template, distraction_timestamp)
                if success:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(distraction_timestamp)
                    print(f"  ✅ {email_template['from_name']}: {email_template['subject'][:50]}... ({dt.strftime('%m-%d %H:%M')})")
                else:
                    print(f"  ❌ 失败: {email_template['from_name']}")
                
                # 添加小延迟避免服务器压力
                time.sleep(0.3)
                
        except Exception as e:
            self.logger.error(f"注入考试后干扰邮件失败: {e}")
            print("⚠️ 部分干扰邮件注入失败，但继续执行")


def inject_exam_emails_from_config(config_file_path: str, custom_timestamp: Optional[float] = None, clear_inbox: bool = False, add_distractions: bool = True):
    """
    一键从email_config.json导入考试通知邮件
    :param config_file_path: email_config.json文件路径
    :param custom_timestamp: 自定义时间戳 (Unix timestamp)，如果为None则使用当前时间
    :param clear_inbox: 是否在注入前清除收件箱中的所有邮件
                       - True: 清除收件箱后再注入新邮件（推荐用于测试环境）
                       - False: 直接注入新邮件，保留现有邮件
    :param add_distractions: 是否添加干扰邮件
                           - True: 在考试通知前后添加无关邮件，模拟真实邮箱环境
                           - False: 只注入考试通知邮件
    
    使用示例:
    # 清除收件箱后注入邮件，包含干扰邮件（推荐）
    inject_exam_emails_from_config('config.json', clear_inbox=True, add_distractions=True)
    
    # 保留现有邮件，只注入考试通知邮件
    inject_exam_emails_from_config('config.json', clear_inbox=False, add_distractions=False)
    """
    try:
        print("开始一键导入考试通知邮件...")
        if clear_inbox:
            print("📋 模式: 清除收件箱后注入新邮件")
        else:
            print("📋 模式: 保留现有邮件，直接注入新邮件")
            
        if add_distractions:
            print("🎭 干扰模式: 启用 - 将添加无关邮件增加真实性")
        else:
            print("🎯 干扰模式: 关闭 - 只注入考试通知邮件")
        
        # 创建邮件注入器
        injector = ExamNotificationInjector(config_file_path)
        
        # 注入考试通知邮件
        success = injector.inject_exam_notification(custom_timestamp, clear_inbox, add_distractions)
        
        if success:
            print("\n🎯 考试通知邮件导入完成！")
            return True
        else:
            print("\n💥 考试通知邮件导入失败！")
            return False
            
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        return False


def main_inject():
    """主函数 - 邮件注入模式"""
    try:
        # 配置文件路径
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        # 示例：使用自定义时间戳（这里设置为2024年12月1日 10:00:00）
        from datetime import datetime
        custom_time = datetime(2024, 12, 1, 10, 0, 0)
        custom_timestamp = custom_time.timestamp()
        
        print(f"📅 设置邮件时间为: {custom_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 一键导入邮件 - 启用清除收件箱选项和干扰邮件
        success = inject_exam_emails_from_config(str(config_file), custom_timestamp, clear_inbox=True, add_distractions=True)
        
        if not success:
            exit(1)
            
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        exit(1)

def test_inject_with_options():
    """测试函数 - 演示不同的邮件注入选项"""
    try:
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        print("=" * 60)
        print("📧 邮件注入功能测试")
        print("=" * 60)
        
        while True:
            print("\n请选择操作:")
            print("1. 清除收件箱后注入邮件 + 干扰邮件 (推荐)")
            print("2. 清除收件箱后注入邮件 (无干扰)")
            print("3. 直接注入邮件 + 干扰邮件 (保留现有邮件)")
            print("4. 直接注入邮件 (保留现有邮件，无干扰)")
            print("5. 只清除收件箱 (不注入邮件)")
            print("6. 退出")
            
            choice = input("\n请输入选项 (1-6): ").strip()
            
            if choice == '1':
                print("\n🗑️+🎭 选择: 清除收件箱后注入邮件 + 干扰邮件")
                inject_exam_emails_from_config(str(config_file), clear_inbox=True, add_distractions=True)
            
            elif choice == '2':
                print("\n🗑️ 选择: 清除收件箱后注入邮件 (无干扰)")
                inject_exam_emails_from_config(str(config_file), clear_inbox=True, add_distractions=False)
            
            elif choice == '3':
                print("\n📧+🎭 选择: 直接注入邮件 + 干扰邮件")
                inject_exam_emails_from_config(str(config_file), clear_inbox=False, add_distractions=True)
                
            elif choice == '4':
                print("\n📧 选择: 直接注入邮件 (无干扰)")
                inject_exam_emails_from_config(str(config_file), clear_inbox=False, add_distractions=False)
            
            elif choice == '5':
                print("\n🗑️ 选择: 只清除收件箱")
                injector = ExamNotificationInjector(str(config_file))
                injector.delete_recipient_inbox_emails()
            
            elif choice == '6':
                print("\n👋 退出测试")
                break
            
            else:
                print("\n❌ 无效选项，请重新选择")
    
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    # 如果直接运行此文件，启动测试模式
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_inject_with_options()
    else:
        main()
