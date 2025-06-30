import os
from utils.general.helper import read_json

def check_local(agent_workspace: str, groundtruth_workspace: str):
    agent_needed_file = os.path.join(agent_workspace,"0519-0525_all_cost.json")
    groundtruth_needed_file = os.path.join(groundtruth_workspace,"0519-0525_all_cost.json")

    agent_generated_data = read_json(agent_needed_file)
    groundtruth_data = read_json(groundtruth_needed_file)

    for date, costs in groundtruth_data.items():
        for category, value in costs.items():
            if agent_generated_data[date][category] != value:
                return False, f"{date} {category} should be {value} but got {agent_generated_data[date][category]}"
    
    return True, None


    