import asyncio
from pathlib import Path
from utils.general.helper import run_command

if __name__=="__main__":
    print("Starting the preprocess script, constructing the cluster...")
    init_script = Path(__file__).parent / "init.sh"
    asyncio.run(run_command(
                f"bash {str(init_script)}", debug=True,show_output=True))
    print("Cluster constructed")