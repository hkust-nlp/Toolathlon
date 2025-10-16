# stdio_servers/bash_server.py
# -*- coding: utf-8 -*-
import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
from time import sleep

async def on_sleep_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    seconds = params.get("seconds", 1)
    sleep(seconds)
    return f"has slept {seconds} seconds, wake up!"

tool_sleep = FunctionTool(
    name='local-sleep',
    description='use this tool to sleep for a while',
    params_json_schema={
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "description": 'the number of seconds to sleep',
            },
        },
        "required": ["seconds"]
    },
    on_invoke_tool=on_sleep_tool_invoke
)

async def on_done_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    return "you have claimed the task is done!"

tool_done = FunctionTool(
    name='local-claim_done',
    description='claim the task is done',
    params_json_schema={
        "type": "object",
        "properties": {
        },
    },
    on_invoke_tool=on_done_tool_invoke
)

if __name__ == "__main__":
    pass
