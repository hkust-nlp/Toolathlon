from typing import List, Dict

from utils.openai_agents_monkey_patch.tool_name_aliases import to_model_tool_name


def default_termination_checker(content: str, 
                                recent_tools: List[Dict], 
                                check_target: str = "user",
                                user_stop_phrases: List[str] = [],
                                agent_stop_tools: List[str] = [],):
    if check_target == "user":
        for stop_phrase in user_stop_phrases:
            if stop_phrase in content:
                return True
    elif check_target == "agent":
        canonical_stop_tools = {
            to_model_tool_name(tool_name) for tool_name in agent_stop_tools
        }
        for tool in recent_tools:
            if to_model_tool_name(tool['function']['name']) in canonical_stop_tools:
                return True
    else:
        raise ValueError("The `check_target` in termination_checker should only be `user` or `agent`!")

    return False
