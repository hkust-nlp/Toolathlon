from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
from .clean_local_emails import clean_emails
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    try:
        args = parser.parse_args()
    except:
        pass

    # clean emails
    receiver_config={
        "email": "jjones@mcp.com",
        "password": "jessica1987%",
        "name": "Meeting Assignment Agent",
        "imap_server": "localhost",
        "imap_port": 1143,
        "smtp_server": "localhost",
        "smtp_port": 1587,
        "use_ssl": False,
        "use_starttls": False
    }
    clean_emails(receiver_config)
