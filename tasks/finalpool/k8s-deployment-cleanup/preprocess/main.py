import os
import asyncio
from utils.general.helper import run_command
from argparse import ArgumentParser
from utils.general.helper import read_json,print_color
from utils.app_specific.poste.ops import clear_folder

involved_emails_file = os.path.join(os.path.dirname(__file__), "..", "files", "involved_emails.json")
print('file path: ', involved_emails_file)

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Starting the preprocess script for k8s deployment cleanup task...")
    print("Constructing the cluster with old deployments in dev-* namespaces...")
    
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "k8s_deployment_cleanup.sh")
    asyncio.run(run_command(
                f"bash {script_path} start {args.agent_workspace}", debug=True, show_output=True))
    
    print_color("Cluster constructed with old deployments ready for cleanup","green")
    
    # exit(0)

    # we also need to clear some folders for the emails
    involved_emails = read_json(involved_emails_file)
    for role in involved_emails:
        for email_address, config in involved_emails[role].items():
            full_config = {"email": email_address, **config}
            clear_folder("INBOX",full_config)
            clear_folder("Sent",full_config)
    
    print_color("Emails cleared for all involved email accounts!","green")

    print_color("Preprocess done!","green")