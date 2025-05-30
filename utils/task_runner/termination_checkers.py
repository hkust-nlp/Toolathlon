from typing import List, Dict

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
        for tool in recent_tools:
            if tool['function']['name'] in agent_stop_tools:
                return True
    else:
        raise ValueError("The `check_target` in termination_checker should only be `user` or `agent`!")

    return False