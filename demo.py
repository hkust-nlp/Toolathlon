from typing import Any
import os, platform
from agents import (
    Agent,
    RunConfig,
    Runner,
    ModelSettings, ToolCallItem, MessageOutputItem, ToolCallOutputItem, RunContextWrapper,
    AgentHooks, RunHooks, TContext, Tool
)
from openai import AsyncOpenAI
import asyncio
import json, jsonlines
import uuid
import datetime
from local_tools.tool_bash import tool_bash
from local_tools.tool_search import tool_search
from utils.tool_servers import MCPServerManager
from utils.model_provider import model_provider, models

from utils.helper import *

import shutil

from configs.global_configs import global_configs

# 自定义JSON编码器，用于处理将Python中的布尔值转换为小写的'true'和'false'形式输出
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()  # 将布尔值转换为小写的'true'或'false'字符串
        return super().default(o)


model_name = "gpt-4.1-mini"

all_tools = []


class AgentLifecycle(AgentHooks):
    def __init__(self):
        super().__init__()
    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        print("AgentLifecycle | on_start")
        pass
    async def on_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print("AgentLifecycle | on_end")
        pass

class RunLifecycle(RunHooks):
    def __init__(self):
        super().__init__()
    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        print('>>on_agent_start')
    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        print('>>on_agent_end')
    async def on_tool_start(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        tool: Tool,
    ) -> None:
        pass
        print('>>调用工具', tool.name)
    async def on_tool_end(
        self,
        context: RunContextWrapper[TContext],
        agent: Agent[TContext],
        tool: Tool,
        result: str,
    ) -> None:
        pass
        print('>>收到工具执行结果', tool.name)

def generate_sp(context: RunContextWrapper, agent: Agent):
    return "这是一个假SP"

# TODO: how to evaluate the status of a task
async def eval_agent(dump_line):
    # config = 任务配置
    # messages = 任务过程中的所有responses， tool calls 和 tool returns
    """
    单任务评估
    预期可能会被检查的内容：
        - user response ： 检查用户端的所有输出
        - response ： 检查llm的所有输出
        - tool calls ： 检查llm的所有tool calls
        - tool outputs ： 检查所有tool outputs
        ====== 对以下内容的检查需要从config再启动 ======
        - local status ： 检查特定工作目录下的文件（比如保存了一些东西，修改了一些东西etc）
        - remote status ： 手动调用MCP server检查remote status是否正常修改 [不知道是否可能]
    利用上述内容来完成对任务执行成功与否的判断
    """
    config = dump_line['config']
    messages = dump_line['messages']
    ...
    eval_results = {"pass":False}
    return eval_results

async def initialze(config):
    print("初始化工作区")
    agent_workspace = config.agent_workspace
    if os.path.exists(agent_workspace):
        print("reset/remove workspace to initialize")
        shutil.rmtree(agent_workspace)
    os.makedirs(agent_workspace)
    # TODO: prepare the needed files under this workspace
    ...
    flag = True # indicate whether it is initialized properly
    return flag
        

async def run_agent(config, res_log_file) -> None:
    """
    单任务执行
    config需要包括的内容：
        - needed_mcp_servers = 该任务需要连接哪些mcp server [目前先保持静态，即连接的mcp列表在任务执行中不会改变]
        - instruction = 该任务的system prompt
        - id = 唯一识别序列号
        - meta = 其他信息
    """
    global all_tools

    # 初始化工作区
    await initialze(config)

    # 创建并启动mcp服务器
    mcp_manager = MCPServerManager(agent_workspace=config.agent_workspace)
    # 连接到该任务需要的mcp servers
    await mcp_manager.connect_servers(config.needed_mcp_servers)

    # hooks initialize
    agent_hooks = AgentLifecycle()
    run_hooks = RunLifecycle()
    agent = None

    try:
        print(">>初始化agent loop")
        # agent initialize
        agent = Agent(
            name="Assistant",
            instructions=generate_sp,
            model=model_provider.get_model(models[model_name]),
            mcp_servers=[*mcp_manager.get_all_connected_servers()], # 指定mcp servers
            tools=[], # TODO：是否要提供非mcp的tools ... my personal view is that we need some basic operations like cmd execution, but we can also use a mcp server to do that
            hooks=agent_hooks,
            model_settings=ModelSettings( # TODO: fix here
                temperature=1.0,
                top_p=1.0,
                max_tokens=4096,
                tool_choice="auto",
                parallel_tool_calls=True, # 禁止并行调用， TODO: 先禁止并行调用，不过不确定对于非gpt模型管不管用
            ),
        )

        print(f">>可用工具列表")
        mcp_tools = await agent.get_all_tools()
        for tool in mcp_tools:
            print(f"[{tool.name}]", tool.description)
            all_tools.append({"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.params_json_schema}})
    except Exception as e:
        print(e)
        print(">>初始化错误")


    # interac_loop
    logs = []
    logs_to_record = []
    # TODO: 这里现在还需要用户来扮演，理想情况下应该是单轮/固定多轮/LLM扮演下的多轮（这里需要再起一个user llm provider）
    try:
        while True:
            user_query = input("user:").strip()
            if user_query == 'quit':
                break

            logs.append({"role": "user", "content": user_query})
            logs_to_record.append({"role": "user", "content": user_query})

            result = await Runner.run(
                starting_agent=agent,
                input=logs,
                run_config=RunConfig(
                    model_provider=model_provider,
                ),
                hooks=run_hooks,
                max_turns=40,
            )

            print(f"assistant: {result.final_output}")
            logs.extend([item.to_input_item() for item in result.new_items])


            item_index = 0
            while item_index < len(result.new_items):
                current_item = result.new_items[item_index]
                # 1. MessageOutputItem
                if isinstance(current_item, MessageOutputItem):
                    if item_index == len(result.new_items) - 1:
                        # 如果MessageOutput是最后一条消息，则为assistant的最终回复
                        '''
                        TODO: https://platform.openai.com/docs/guides/text?api-mode=responses,
                        观察['content'][0]['text']是否有其他数据结构
                        '''
                        logs_to_record.append({"role": "assistant", "content": current_item.to_input_item()['content'][0]['text']})
                        item_index += 1
                    else:
                        # 如果MessageOutput不是最后一条消息，其必然调用工具（即content和tool_call同时输出的形式）
                        # 找出同批次并行调用的tools，从下一条开始
                        tool_calls = []
                        for i in range(item_index+1, len(result.new_items)):
                            if not isinstance(result.new_items[i], ToolCallItem):
                                break
                            tool_calls.append({"id": result.new_items[i].to_input_item()['call_id'], "type": "function", "function": {"name": result.new_items[i].to_input_item()["name"], "arguments": result.new_items[i].to_input_item()["arguments"]}})
                        logs_to_record.append({"role": "assistant", "content": current_item.to_input_item()['content'][0]['text'], "tool_calls": tool_calls})
                        item_index += (1 + len(tool_calls))

                # 2. ToolCallItem
                elif isinstance(current_item, ToolCallItem):
                    # 不带content的tool_call调用，找出同批次并行调用的tools，包括自己
                    tool_calls = []
                    for i in range(item_index, len(result.new_items)):
                        if not isinstance(result.new_items[i], ToolCallItem):
                            break
                        tool_calls.append({"id": result.new_items[i].to_input_item()['call_id'], "type": "function", "function": {"name": result.new_items[i].to_input_item()["name"], "arguments": result.new_items[i].to_input_item()["arguments"]}})
                    logs_to_record.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
                    item_index += len(tool_calls)

                # 3. ToolCallOutputItem
                elif isinstance(current_item, ToolCallOutputItem):
                    # tool执行结果，每一条正常输出（role = tool）
                    logs_to_record.append({"role": "tool", "content": current_item.to_input_item()["output"], "tool_call_id": current_item.to_input_item()["call_id"]})
                    item_index += 1

    except Exception as e:
        print(123, e)

    finally:
        with open(res_log_file, 'a', encoding='utf-8') as f:
            result = {'config':config,
                      'request_id': str(uuid.uuid4()), 
                      'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                      'tool_calls': {'tools': all_tools, 'tool_choice': 'auto'}, 
                      'messages': []}
            for msg in logs_to_record:
                result['messages'].append(msg)

            # 使用自定义的JSON编码器将字典转换为字符串，确保布尔值输出为小写的true或false形式
            json_output = json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder)
            f.write(json_output + '\n')
        await mcp_manager.disconnect_servers()

async def main():
    # in the main part, we set an example of solving one task and evaling one task
    from addict import Dict
    os_info = platform.platform()
    if "Linux" in os_info: # 若在服务器上，加proxy
        os.environ['http_proxy'] = global_configs['proxy']
        os.environ['https_proxy'] = global_configs['proxy']

    # 未来一段时间打算骑自行车从广州出发到北京，帮我规划一下行程，要求兼顾路程、住宿和游玩的地方，并且注意一下适合骑行的天气，最后查询一些旅游网站，优化这个行程方案。
    log_file = "./storage/slack/slack_xxx_00001/log.jsonl"

    config = Dict(needed_mcp_servers = ['slack','filesystem'],
                      instruction="你是Slack机器人",
                      id="slack_xxx_00001",
                      meta={},
                      agent_workspace="./storage/slack/slack_xxx_00001/workspace"
                      )

    await run_agent(config=config, res_log_file=log_file)

    sample_dump_line = read_all(log_file)[-1]

    eval_res = await eval_agent(sample_dump_line)

    print(eval_res)


if __name__ == "__main__":
    asyncio.run(main())
    


    



