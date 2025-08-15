from argparse import ArgumentParser
import asyncio

from .check_local import check_local
from utils.general.helper import read_json  




if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    args = parser.parse_args()

    res_log = read_json(args.res_log_file)
    
    
    # check local
    local_pass, local_error = check_local(args.agent_workspace, args.groundtruth_workspace)
    if not local_pass:
        print("local check failed: ", local_error)
        exit(1)
    
    
    print("Pass all tests!")