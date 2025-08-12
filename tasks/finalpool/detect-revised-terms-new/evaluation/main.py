from argparse import ArgumentParser
import asyncio

from .check_content import check_content
from utils.general.helper import read_json  


if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--launch_time", nargs='*', required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()

    res_log = read_json(args.res_log_file)
    
    # check content
    try:
        Pass, Error = check_content(args.agent_workspace, args.groundtruth_workspace)
        if not Pass:
            print("content check failed: ", Error)
            exit(1)
    except Exception as e:
        print("content check error: ", e)
        exit(1)
    
    print("Pass all tests!")