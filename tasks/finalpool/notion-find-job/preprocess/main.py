import sys
import os
from argparse import ArgumentParser
import asyncio
# Add utils to path
sys.path.append(os.path.dirname(__file__))

from configs.token_key_session import all_token_key_session
# from utils.app_specific.notion_page_duplicator import NotionPageDuplicator
from utils.general.helper import run_command, print_color
from .clean_local_emails import clean_emails

NEEDED_SUBPAGE_NAME = "Job Finder"

async def main():
    parser = ArgumentParser(description="Example code for notion tasks preprocess")
    parser.add_argument("--agent_workspace", required=False, 
                       help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
    duplicated_page_id_file = os.path.join(task_root_path, "files", "duplicated_page_id.txt")
    # delete the old duplicated page id file
    if os.path.exists(duplicated_page_id_file):
        os.remove(duplicated_page_id_file)

    command = f"uv run -m utils.app_specific.notion.notion_remove_and_duplicate "
    command += f"--duplicated_page_id_file {duplicated_page_id_file} "
    command += f"--needed_subpage_name \"{NEEDED_SUBPAGE_NAME}\" "
    await run_command(command, debug=True, show_output=True)

    # example we do have a duplicated page id file, so we can use it to get the duplicated page id
    if not os.path.exists(duplicated_page_id_file):
        raise FileNotFoundError(f"Duplicated page id file {duplicated_page_id_file} not found")
    
    with open(duplicated_page_id_file, "r") as f:
        duplicated_page_id = f.read()
    print_color(f"Duplicated page id: {duplicated_page_id}. Process done!","green")

if __name__ == "__main__":
    asyncio.run(main())

    # Clean target recipient inboxes
    config = {
        "email": "laura.hall@mcp.com",
        "password": "laura2004%fA",
        "name": "Meeting Assignment Agent",
        "imap_server": "localhost",
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587,
        "use_ssl": False,
        "use_starttls": False
    }
    clean_emails(config)

    config = {
        "email": "janetr@mcp.com",
        "password": "Jrogers864D2",
        "name": "Meeting Assignment Agent",
        "imap_server": "localhost",
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587,
        "use_ssl": False,
        "use_starttls": False
    }
    clean_emails(config)
    
    # Clean all other emails from other_emails.txt
    other_emails_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "other_emails.txt")
    if os.path.exists(other_emails_file):
        print_color(f"Cleaning other emails from {other_emails_file}", "yellow")
        with open(other_emails_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and ";;" in line:
                    email_addr, password = line.split(";;", 1)
                    config = {
                        "email": email_addr.strip(),
                        "password": password.strip(),
                        "name": "Email Cleaner Agent",
                        "imap_server": "localhost",
                        "imap_port": 1143,
                        "smtp_server": "localhost",
                        "smtp_port": 1587,
                        "use_ssl": False,
                        "use_starttls": False
                    }
                    print_color(f"Cleaning inbox for {email_addr}", "blue")
                    clean_emails(config)
        print_color("All other emails cleaned successfully!", "green")
    else:
        print_color(f"Warning: {other_emails_file} not found", "red")
