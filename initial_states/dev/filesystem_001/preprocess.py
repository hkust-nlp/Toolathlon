from utils.data_processing.process_ops import copy_multiple_times
from argparse import ArgumentParser
import os

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()

    to_copy_files = ["0519-0525_cost_food.csv",
                     "0519-0525_spent_others.md",]
    
    for filename in to_copy_files:
        fullfilepath = os.path.join(args.agent_workspace,filename)
        copy_multiple_times(file_path=fullfilepath,times=1)

# 你能帮我展示一下我的工作区下都有哪些文件吗

# 好的，我想知道我从5.19开始这一周花了多少钱，你能把每天的花费写到一个工作区下的json文件吗，格式是这样 {"0519":{"food":xx,"traffic":xx,"others":xx,"total":xx},...}

# 我忘了说了。文件名应该是 0519-0526_all_cost

# 很好，我能知道一下我这周每一类的总开支是多少吗，以及我总共花了多少钱