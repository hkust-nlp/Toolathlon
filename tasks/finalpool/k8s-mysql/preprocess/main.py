import asyncio
from utils.general.helper import run_command
from argparse import ArgumentParser
from pathlib import Path

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("Starting the preprocess script, constructing the cluster...")
    script_path = Path(__file__).parent / "init.sh"
    asyncio.run(run_command(
                f"bash {script_path}", debug=True,show_output=True))
    print("Cluster constructed")

    print("Initialization complete")