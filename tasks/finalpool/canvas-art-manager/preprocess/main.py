import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from argparse import ArgumentParser

import imaplib
import email

import requests
import sys
import tarfile

# Import Canvas utility components
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from utils.app_specific.canvas import CanvasAPI

def delete_course_schedule_notifications(imap_server, imap_port, email_user=None, email_pass=None, mailbox="INBOX"):
    """
    检查收件邮箱中是否包含主题为'Course Schedule Notification'的邮件，有的话全部删除。

    :param imap_server: IMAP服务器地址
    :param imap_port: IMAP服务器端口（通常为993）
    :param email_user: 邮箱用户名
    :param email_pass: 邮箱密码
    :param mailbox: 要操作的邮箱文件夹，默认INBOX
    """
    try:
        # 连接到IMAP服务器
        mail = imaplib.IMAP4(imap_server, imap_port)
        # mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_user, email_pass)
        mail.select(mailbox)

        # 搜索主题为指定内容的邮件
        typ, data = mail.search(None, '(SUBJECT "Course Schedule Notification")')
        if typ != 'OK':
            print("搜索邮件失败")
            mail.logout()
            return

        msg_ids = data[0].split()
        if not msg_ids:
            print("没有找到主题为'Course Schedule Notification'的邮件。")
            mail.logout()
            return

        print(f"找到{len(msg_ids)}封待删除邮件。正在删除...")

        for msg_id in msg_ids:
            mail.store(msg_id, '+FLAGS', '\\Deleted')

        mail.expunge()
        print("删除完成。")
        mail.logout()
    except Exception as e:
        print(f"删除邮件时发生错误: {e}")

def send_email(to_email, subject, body, from_email, smtp_server, smtp_port, attachments=None, use_auth=False, smtp_user=None, smtp_pass=None):
    # 创建一个带附件的邮件对象
    msg = MIMEMultipart()
    msg['From'] = Header(from_email)
    msg['To'] = Header(to_email)
    msg['Subject'] = Header(subject, 'utf-8')

    # 邮件正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 添加附件
    if attachments:
        for file_path in attachments:
            if not os.path.isfile(file_path):
                print(f"Attachment {file_path} does not exist, skipping.")
                continue
            filename = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                mime = MIMEBase('application', 'octet-stream')
                mime.set_payload(f.read())
                encoders.encode_base64(mime)
                mime.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(mime)

    try:
        print(f"连接到SMTP服务器: {smtp_server}:{smtp_port} (非SSL模式)")
        # 明确使用非SSL连接
        server = smtplib.SMTP(smtp_server, smtp_port)

        # 设置调试级别（可选，用于查看详细的SMTP通信）
        # server.set_debuglevel(1)

        # 不启用STARTTLS，保持纯文本连接
        # server.starttls()  # 注释掉，确保不使用SSL/TLS

        # 只有在需要认证时才登录
        if use_auth and smtp_user and smtp_pass:
            print("使用SMTP认证登录")
            server.login(smtp_user, smtp_pass)
        else:
            print("SMTP连接已建立 (无认证模式)")

        # 发送邮件
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        print("Email sent successfully.")

    except Exception as e:
        print("Failed to send email:", e)

def parse_course_schedule_md(md_path):
    """
    解析course_schedule.md，返回课程名-上课时间的列表
    """
    courses = []
    if not os.path.isfile(md_path):
        print(f"课程表文件不存在: {md_path}")
        return courses
    with open(md_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("|---"):
                continue
            if line.startswith("|") and line.count("|") >= 4:
                # | Course Name | Instructor | Class Time | Admin |
                parts = [x.strip() for x in line.split("|")[1:-1]]
                if len(parts) >= 3:
                    course_name = parts[0]
                    class_time = parts[2]
                    full_name = f"{course_name}-{class_time}"
                    courses.append(full_name)
    return courses

# 管理员身份批量删除其他老师的课程
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--canvas_url", required=False, help="Canvas服务器URL, 例如 http://localhost:18080")
    parser.add_argument("--canvas_token", required=False, help="Canvas管理员Token")
    args = parser.parse_args()
    
    # 如果指定了agent_workspace，则进行文件解压缩
    if args.agent_workspace:
        # 确保agent workspace存在
        os.makedirs(args.agent_workspace, exist_ok=True)
        dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
        
        # 解压缩
        try:
            with tarfile.open(dst_tar_path, 'r:gz') as tar:
                print(f"正在解压缩到: {args.agent_workspace}")
                # Use the filter parameter to avoid deprecation warning in Python 3.14+
                tar.extractall(path=args.agent_workspace, filter='data')
                print("解压缩完成")
        except Exception as e:
            print(f"解压缩失败: {e}")
            sys.exit(1)
        
        # 删除压缩文件
        try:
            os.remove(dst_tar_path)
            print(f"已删除原始压缩文件: {dst_tar_path}")
        except Exception as e:
            print(f"删除压缩文件失败: {e}")
        
        print("预处理完成 - Canvas教学资源文件已准备就绪")

    # 执行邮件和Canvas操作（这些是预处理的主要任务）

    imap_server = "localhost"
    imap_port = 1143

    to_email = "mcpcanvasadmin3@mcp.com"  # 收件人邮箱
    subject = "Course Schedule Notification"
    body = """Dear Academic Administrators,
I hope this email finds you well. I am writing to inform you that the new academic course schedule for the coming academic year has been finalized and is now ready for your review and implementation.
XXX University
"""
    from_email = "coxw@mcp.com"  # 发件人邮箱
    smtp_server = "localhost"       # SMTP服务器地址
    smtp_port = 1587                # SMTP端口

    delete_course_schedule_notifications(imap_server, imap_port, to_email, "mcpcanvasadminpass3")

    # 添加附件路径列表
    attachments = [os.path.join(os.path.dirname(__file__), "course_schedule.md")]

    # 非认证模式调用（不传递用户名和密码）
    send_email(to_email, subject, body, from_email, smtp_server, smtp_port, attachments)

    # ========== Canvas课程删除操作（管理员身份，删除的课程老师不是管理员自身） ==========
    canvas_url = args.canvas_url or os.environ.get("CANVAS_URL") or "http://localhost:10001"
    from pathlib import Path
    parent_dir = Path(__file__).parent.parent
    sys.path.append(str(parent_dir))
    from token_key_session import all_token_key_session
    canvas_token = all_token_key_session.canvas_api_token
    course_md_path = os.path.join(os.path.dirname(__file__), "course_schedule.md")
    course_names = parse_course_schedule_md(course_md_path)
    all_canvas_tokens = all_token_key_session.all_canvas_teacher_tokens

    for canvas_token in all_canvas_tokens:
        if not course_names:
            print("未找到任何课程需要删除。")
        else:
            print(f"待删除课程名列表（管理员操作，删除的课程老师不是管理员自身）: {course_names}")
            
            # 使用Canvas utility组件
            canvas_api = CanvasAPI(canvas_url, canvas_token)
            all_canvas_courses = canvas_api.list_courses()
            
            # 课程名到id映射
            name2id = {c["name"]: c["id"] for c in all_canvas_courses}
            deleted_any = False
            for cname in course_names:
                if cname in name2id:
                    print(f"管理员身份：Canvas中存在课程: {cname}（该课程的老师不是管理员自身），准备删除...")
                    
                    # 使用Canvas utility组件删除课程
                    success = canvas_api.delete_course(name2id[cname], event='delete')
                    if success:
                        deleted_any = True
                else:
                    print(f"教师身份：Canvas中未找到课程: {cname}，跳过。")
            if not deleted_any:
                print("没有需要删除的Canvas课程（管理员操作）。")
