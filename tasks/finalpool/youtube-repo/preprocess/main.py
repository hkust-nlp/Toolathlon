from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
