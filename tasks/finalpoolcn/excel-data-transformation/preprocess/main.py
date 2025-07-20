from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()

    # 需要复制到agent工作空间的文件
    to_copy_files = ["Household_Appliances.xlsx"]
    
    for filename in to_copy_files:
        fullfilepath = os.path.join(args.agent_workspace, filename)
        # 暂时不进行多次复制，保持原始文件
        # copy_multiple_times(file_path=fullfilepath, times=1) 