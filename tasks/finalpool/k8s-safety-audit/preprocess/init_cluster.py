import asyncio
from utils.general.helper import run_command

if __name__=="__main__":
    print("Starting the preprocess script, constructing the cluster...")
    asyncio.run(run_command(
                f"bash tasks/ruige/k8s-safety-audit/preprocess/init.sh", debug=True,show_output=True))
    print("Cluster constructed")