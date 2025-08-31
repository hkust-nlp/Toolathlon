from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False)
    args = parser.parse_args()

    to_copy_files = ["0519-0525_cost_food.csv",
                     "0519-0525_spent_others.md",]
    
    for filename in to_copy_files:
        fullfilepath = os.path.join(args.agent_workspace,filename)
        copy_multiple_times(file_path=fullfilepath,times=1)
