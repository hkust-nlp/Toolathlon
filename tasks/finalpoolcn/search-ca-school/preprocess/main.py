from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()

    to_copy_files = ["cs_masters_funding_LA_500miles_2025.json",
                     "cs_masters_funding_LA_500miles_2025.md",]
    
    for filename in to_copy_files:
        fullfilepath = os.path.join(args.agent_workspace,filename)
        copy_multiple_times(file_path=fullfilepath,times=1)
