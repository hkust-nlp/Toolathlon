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
import subprocess
import json
import asyncio

# Import Canvas utility components
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from utils.app_specific.canvas import CanvasAPI

def run_command(command, description="", check=True, shell=True):
    """Run a command and handle output"""
    print(f"🔧 {description}")
    print(f"   Command: {command}")

    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stdout:
            print(f"   Stdout: {e.stdout}")
        if e.stderr:
            print(f"   Stderr: {e.stderr}")
        if check:
            raise
        return e


def clear_inbox(imap_server, imap_port, email_user=None, email_pass=None, mailbox="INBOX"):
    """
    清空整个收件箱。

    :param imap_server: IMAP服务器地址
    :param imap_port: IMAP服务器端口（通常为993）
    :param email_user: 邮箱用户名
    :param email_pass: 邮箱密码
    :param mailbox: 要操作的邮箱文件夹，默认INBOX
    """
    try:
        # Add the utils path for import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent
        finalpool_dir = task_dir.parent
        tasks_dir = finalpool_dir.parent
        mcpbench_root = tasks_dir.parent
        utils_dir = mcpbench_root / "utils"

        sys.path.insert(0, str(utils_dir))
        from app_specific.poste.ops import clear_folder

        # Prepare IMAP configuration for clear_folder function
        imap_config = {
            "email": email_user,
            "password": email_pass,
            "imap_server": imap_server,
            "imap_port": imap_port,
            "use_ssl": False,  # Canvas Art Manager uses non-SSL
            "use_starttls": False
        }

        print(f"🔧 Clearing inbox for: {email_user}")

        # Clear the INBOX folder
        clear_folder(mailbox, imap_config)

        print("✅ Inbox clearing completed successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to clear inbox: {e}")
        print("💡 Continuing with preprocessing anyway...")
        return False

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
                    full_name = course_name
                    courses.append(full_name)
    return courses

async def delete_all_courses_via_mcp(target_course_names):
    """
    Delete specified courses using MCP canvas server

    This function will:
    1. Connect to canvas MCP server
    2. List all courses in the account
    3. Delete only the courses whose names match target_course_names

    :param target_course_names: List of course names to delete (required).
    """
    print(f"🗑️ Starting to delete {len(target_course_names)} specified courses via Canvas MCP...")

    try:
        # Add the utils path for MCPServerManager import
        script_dir = Path(__file__).parent
        task_dir = script_dir.parent  # canvas-art-manager
        finalpool_dir = task_dir.parent  # finalpool
        tasks_dir = finalpool_dir.parent  # tasks
        mcpbench_root = tasks_dir.parent  # mcpbench_dev

        sys.path.insert(0, str(mcpbench_root))
        from utils.mcp.tool_servers import MCPServerManager

        print(f"🚀 Attempting to connect to Canvas MCP server...")

        # Load local token_key_session from task directory
        local_token_key_session = None
        token_key_session_path = task_dir / "token_key_session.py"

        if token_key_session_path.exists():
            print(f"🔑 Loading task-specific token configuration from {token_key_session_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("token_key_session", token_key_session_path)
            token_key_session_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(token_key_session_module)
            local_token_key_session = token_key_session_module.all_token_key_session
        else:
            print("⚠️  No task-specific token configuration found, using global defaults")

        # Set up temporary workspace
        workspace = script_dir / "temp_workspace"
        workspace.mkdir(exist_ok=True)

        # Initialize MCP Server Manager with local token configuration
        server_manager = MCPServerManager(
            agent_workspace=str(workspace),
            config_dir=str(mcpbench_root / "configs" / "mcp_servers"),
            debug=False,
            local_token_key_session=local_token_key_session
        )

        # Connect to canvas server specifically
        await server_manager.connect_servers(["canvas"])
        connected_names = server_manager.get_connected_server_names()

        if "canvas" not in connected_names:
            print("❌ Failed to connect to canvas MCP server")
            return False

        print(f"✅ Connected to canvas MCP server")

        canvas_server = server_manager.connected_servers["canvas"]

        # First, try to get all courses from account (admin view)
        print("🔍 Fetching all courses from account...")
        try:
            account_courses_result = await canvas_server.call_tool("canvas_list_account_courses", {"account_id": 1})
            courses = []

            # Parse the result to extract courses
            if hasattr(account_courses_result, 'content'):
                for content in account_courses_result.content:
                    if hasattr(content, 'text'):
                        try:
                            courses = json.loads(content.text)
                        except:
                            print(f"Could not parse account courses: {content.text}")

            # If account courses didn't work, try user courses
            if not courses:
                print("🔍 Trying to fetch user courses...")
                user_courses_result = await canvas_server.call_tool("canvas_list_courses", {})
                if hasattr(user_courses_result, 'content'):
                    for content in user_courses_result.content:
                        if hasattr(content, 'text'):
                            try:
                                courses = json.loads(content.text)
                            except:
                                print(f"Could not parse user courses: {content.text}")

        except Exception as e:
            print(f"❌ Error fetching courses: {e}")
            courses = []

        if not courses:
            print("⚠️  No courses found to delete")
            await server_manager.disconnect_servers()
            return True

        print(f"📚 Found {len(courses)} total courses")
        print(f"🎯 Target courses to delete: {target_course_names}")

        # Filter courses to only include target courses
        courses_to_delete = []
        for course in courses:
            course_name = course.get('name', f'Course {course.get("id")}')
            if course_name in target_course_names:
                courses_to_delete.append(course)
                print(f"📚 Found target course to delete: {course_name}")
            else:
                print(f"⏩ Skipping course: {course_name} (not in target list)")

        if not courses_to_delete:
            print("⚠️  No matching courses found to delete")
            await server_manager.disconnect_servers()
            return True

        print(f"📚 Will delete {len(courses_to_delete)} courses")

        # Delete each course
        deleted_count = 0
        failed_count = 0

        for course in courses_to_delete:
            course_id = course.get('id')
            course_name = course.get('name', f'Course {course_id}')

            print(f"🗑️ Deleting course {course_id}: {course_name}")

            try:
                delete_result = await canvas_server.call_tool("canvas_delete_course", {"course_id": course_id})

                # Check if deletion was successful
                success = False
                if hasattr(delete_result, 'content'):
                    for content in delete_result.content:
                        if hasattr(content, 'text'):
                            print(f"   📄 {content.text}")
                            if "deleted" in content.text.lower() or "concluded" in content.text.lower():
                                success = True
                        else:
                            print(f"   📄 {content}")

                if success:
                    print(f"   ✅ Successfully deleted course {course_id}")
                    deleted_count += 1
                else:
                    print(f"   ⚠️ Deletion status unclear for course {course_id}")
                    deleted_count += 1  # Assume success if no error

            except Exception as e:
                print(f"   ❌ Failed to delete course {course_id}: {e}")
                failed_count += 1

        # Cleanup
        await server_manager.disconnect_servers()

        print(f"\n📊 Deletion Summary:")
        print(f"   ✅ Successfully deleted: {deleted_count} courses")
        print(f"   ❌ Failed to delete: {failed_count} courses")
        print(f"   📚 Total processed: {len(courses)} courses")

        if failed_count == 0:
            print("✅ All courses deleted successfully")
            return True
        else:
            print(f"⚠️ {failed_count} courses failed to delete")
            return False

    except ImportError as ie:
        print(f"❌ Could not import MCP utilities: {ie}")
        return False
    except Exception as e:
        print(f"❌ Error during course deletion: {e}")
        import traceback
        traceback.print_exc()
        return False

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

    # 清空整个收件箱
    clear_inbox(
        imap_server=imap_server,
        imap_port=imap_port,
        email_user=to_email,
        email_pass="mcpcanvasadminpass3"
    )

    # 生成邮件并导入到收件箱
    try:
        print("📧 Generating inbox emails...")
        # 运行generate_inbox.py
        generate_script = os.path.join(os.path.dirname(__file__), "generate_inbox.py")
        result = run_command(
            f"python {generate_script}",
            "Generating inbox with course notifications and fake emails"
        )
        print("✅ Email generation completed")

        print("📨 Importing emails to MCP server...")
        # 运行import_emails.py
        import_script = os.path.join(os.path.dirname(__file__), "import_emails.py")
        result = run_command(
            f"python {import_script} --target-folder INBOX --preserve-folders",
            "Importing emails to MCP server",
            check=False  # Don't fail if import has issues
        )

        if result and hasattr(result, 'returncode') and result.returncode == 0:
            print("✅ Email import completed successfully")
        else:
            print("⚠️ Email import completed with warnings")

    except Exception as e:
        print(f"❌ Error in email generation/import: {e}")
        print("💡 Continuing with preprocessing anyway...")

    # ========== Canvas课程删除操作（使用MCP方法） ==========
    print("🗑️ Starting Canvas course cleanup using MCP...")

    # 获取需要删除的课程列表
    course_schedule_path = os.path.join(os.path.dirname(__file__), "course_schedule.md")
    target_courses = parse_course_schedule_md(course_schedule_path)

    if not target_courses:
        print(f"❌ Error: No courses found in course_schedule.md at {course_schedule_path}")
        print("Cannot proceed with course deletion without a valid course schedule.")
        sys.exit(1)

    print(f"📋 Found {len(target_courses)} courses to delete from course_schedule.md:")
    for course in target_courses:
        print(f"   - {course}")

    try:
        # Run the MCP deletion function with target courses
        success = asyncio.run(delete_all_courses_via_mcp(target_courses))
        if success:
            print("✅ MCP course deletion completed successfully")
        else:
            print("⚠️ MCP course deletion completed with some issues")
    except Exception as e:
        print(f"❌ Error during MCP course deletion: {e}")
        import traceback
        traceback.print_exc()
