#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考试通知邮件发送脚本
通过Poste.io的SMTP/IMAP服务发送考试通知邮件
"""

import smtplib
import imaplib
import json
import logging
import time
import ssl
import email
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
            self.logger.error(f"邮件模板加载失败: {e}")
            raise
    
    def format_email_content(self, template: str) -> str:
        """格式化邮件内容"""
        try:
            # 获取配置信息
            sender_account = self.config['sender_account']
            recipient = self.config['recipient']
            exam_info = self.config['email_content']['exam_info']
            
            # 替换模板变量
            content = template.format(
                rrecipient_name=recipient['name'],
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
