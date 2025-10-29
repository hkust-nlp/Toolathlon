from argparse import ArgumentParser
import json
from copy import deepcopy
import os


# create ./vis_traj/trajs if not exists
if not os.path.exists("./vis_traj/trajs"):
    os.makedirs("./vis_traj/trajs")

def convert_format(input_path, output_file):
    res = {}

    with open(f"{input_path}/eval_res.json", "r") as f:
        is_pass = json.load(f)["pass"]
        res["pass"] = is_pass

    with open(f"{input_path}/traj_log.json", "r") as f:
        data = json.load(f)
        try:
            msgs = data["messages"]
        except:
            raise ValueError(f"Failed to load messages from {input_path}/traj_log.json")
        msg_copies = []
        for msg in msgs:
            msg_copy = deepcopy(msg)
            if msg["role"] == "tool":
                content = msg["content"]
            elif msg["role"] == "user":
                content = msg["content"]
            elif msg["role"] == "assistant":
                content = msg["content"]
                if content is not None:
                    msg_copy["content"] = content
                if "tool_calls" in msg:
                    for i, tool_call in enumerate(msg["tool_calls"]):
                        arguments = tool_call["function"]["arguments"]
                        if tool_call["function"]["name"] == "local-python-execute":
                            if arguments == "":
                                msg_copy["tool_calls"][i]["function"]["arguments"] = arguments
                            else:
                                msg_copy["tool_calls"][i]["function"]["arguments"] = arguments
            msg_copies.append(msg_copy)
            res["messages"] = msg_copies

        with open(f"vis_traj/trajs/{output_file}", "w") as f:
            json.dump(res, f)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--input_path", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=True)
    args = parser.parse_args()
    convert_format(args.input_path, args.output_file)