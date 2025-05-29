from typing import Any
import os, platform
from agents import (
    Agent,
    RunConfig,
    Usage,
    Runner,
    ModelSettings, ToolCallItem, MessageOutputItem, ToolCallOutputItem, RunContextWrapper,
    AgentHooks, RunHooks, TContext, Tool
)
import asyncio
import json
import uuid
import datetime
from utils.mcp.tool_servers import MCPServerManager
from utils.api_model.model_provider import API_MAPPINGS, model_provider_mapping, calculate_cost
import shutil
from configs.global_configs import global_configs
import traceback
from utils.general.helper import copy_folder_contents, read_json, run_command, specifical_inialize_for_mcp
from enum import Enum

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from addict import Dict

from utils.roles.user import User, UserConfig
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry

class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

async def get_user_input():
    session = PromptSession()
    with patch_stdout():
        user_query = await session.prompt_async("user: ")
    return user_query.strip()

# 自定义JSON编码器，用于处理将Python中的布尔值转换为小写的'true'和'false'形式输出
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()  # 将布尔值转换为小写的'true'或'false'字符串
        return super().default(o)

class AgentLifecycle(AgentHooks):
    def __init__(self):
        super().__init__()
    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        pass
    async def on_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
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
    task_config = Dict(dump_line['config'])
    task_status = dump_line['status']

    if task_status != TaskStatus.SUCCESS.value:
        return {"pass": False, "failure": "task_not_successfully_executed"}

    # thing we need to do evaluate
    res_log_file = task_config.log_file
    agent_workspace = task_config.agent_workspace
    groundtruth_workspace = task_config.groundtruth_workspace
    check_local_state_command = task_config.check_local_state_command
    check_log_command = task_config.check_log_command

    # check log
    if check_log_command is not None:
        try:
            args = f"--res_log_file {res_log_file}"
            command = f"{check_log_command} {args}"
            await run_command(command)
        except:
            return {"pass":False, "failure": "fail_to_pass_log_check"}
        
    # check status
    if check_local_state_command is not None:
        try:
            args = f"--agent_workspace {agent_workspace} --groundtruth_workspace {groundtruth_workspace}"
            command = f"{check_local_state_command} {args}"
            await run_command(command)
        except:
            return {"pass":False, "failure": "fail_to_pass_local_state_check"}

    eval_results = {"pass":True}
    return eval_results

async def initialze(task_config, show_traceback=False):
    print(f"Starting to initialize workspace for {task_config.id} ...")
    
    log_file = task_config.log_file
    agent_workspace = task_config.agent_workspace
    initial_state_workspace = task_config.initial_workspace

    try:
        # remove existing ones
        if os.path.exists(agent_workspace):
            print("Reset/Remove an exitsing agent workspace.")
            shutil.rmtree(agent_workspace)

        if os.path.exists(log_file):
            print("Reset/Remove an exitsing log file.")
            os.remove(log_file)
        
        # copy the initial state (files)
        await copy_folder_contents(initial_state_workspace, agent_workspace)

        # do some preprocessing if needed
        if task_config.initial_process_command is not None:
            args = f"--agent_workspace {task_config.agent_workspace}"
            command = f"{task_config.initial_process_command} {args}"
            await run_command(command)
            
        # other specific operations for mcp servers
        await specifical_inialize_for_mcp(task_config)

    except Exception as e:
        print("Workspace initialization failed, reason : ", e)
        if show_traceback:
            traceback.print_exc()
        return False

    print(f"Successfully initialize workspace for {task_config.id}!")
    return True

async def run_agent(task_config, 
                    model_config, 
                    user_client,
                    user_config, 
                    mcp_config_path) -> None:
    """
    单任务执行
    config需要包括的内容：
        - needed_mcp_servers = 该任务需要连接哪些mcp server [目前先保持静态，即连接的mcp列表在任务执行中不会改变]
        - instruction = 该任务的system prompt
        - id = 唯一识别序列号
        - meta = 其他信息
    """
    all_tools = []

    # 初始化工作区
    await initialze(task_config)

    # 设置log file
    res_log_file = os.path.join(task_config.task_root,"log.json")
    task_config.agent_workspace = os.path.join(task_config.task_root,"workspace")

    # 创建并启动mcp服务器
    mcp_manager = MCPServerManager(agent_workspace=task_config.agent_workspace,
                                   config_dir=mcp_config_path)
    # 连接到该任务需要的mcp servers
    await mcp_manager.connect_servers(task_config.needed_mcp_servers)

    # hooks initialize
    agent_hooks = AgentLifecycle()
    run_hooks = RunLifecycle()
    agent = None

    # 启动agent
    try:
        print(">>初始化agent loop")
        # agent initialize
        agent = Agent(
            name="Assistant",
            instructions=task_config.system_prompt_instructions,
            model=model_config.provider.get_model(model_config.model_real_name),
            mcp_servers=[*mcp_manager.get_all_connected_servers()], # 指定mcp servers
            tools=[],
            hooks=agent_hooks,
            model_settings=ModelSettings(
                temperature=model_config.temperature,
                top_p=model_config.top_p,
                max_tokens=model_config.max_tokens,
                tool_choice=model_config.tool_choice,
                parallel_tool_calls=model_config.parallel_tool_calls,
            ),
        )
        usage = Usage()
       
        mcp_tools = await agent.get_all_tools()
        print(f">>可用工具列表 (x{len(mcp_tools)})")
        for tool in mcp_tools:
            print(f"[{tool.name}]", tool.description)
            all_tools.append({"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.params_json_schema}})
    except Exception as e:
        print(e)
        print(">>初始化错误")

    # 启动user
    try:
        real_user_config = UserConfig(
            starting_system_prompt=task_config.user_system_prompt_setting,
            temperature=user_config.temperature,
            top_p=user_config.top_p,
            model = user_config.model_short_name,
            max_tokens = user_config.max_tokens,
        )
        user_simulator = User(client = user_client,
                        user_config=real_user_config)
        user_simulator.initialize_conversation()
    except Exception as e:
        print(e)
        print(">>模拟用户启动错误")


    # interac_loop
    logs = []
    logs_to_record = []
    # TODO: 这里现在还需要用户来扮演，理想情况下应该是单轮/固定多轮/LLM扮演下的多轮（这里需要再起一个user llm provider）
    try:
        while True:
            user_query = await user_simulator.interact()

            print(f"user: {user_query}")

            logs.append({"role": "user", "content": user_query})
            logs_to_record.append({"role": "user", "content": user_query})

            if '#### STOP' in user_query:
                break

            result = await Runner.run(
                starting_agent=agent,
                input=logs,
                run_config=RunConfig(
                    model_provider=model_config.provider,
                ),
                hooks=run_hooks,
                max_turns=model_config.max_inner_turns,
            )

            for raw_response in result.raw_responses:
                usage.add(raw_response.usage)

            print(f"assistant: {result.final_output}")
            logs.extend([item.to_input_item() for item in result.new_items])

            user_simulator.receive_message(result.final_output)

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
        task_status = TaskStatus.SUCCESS
    except Exception as e:
        traceback.print_exc()
        print("Error when interacting with agent - ", e)
        task_status = TaskStatus.FAILED

    finally:
        user_cost = user_simulator.get_cost_summary()
        print("===模拟用户的开销如下===")
        for k,v in user_cost.items():
            print(f"{k} : {v}")
        print("===Agent的开销如下===")
        _, _, total_cost = calculate_cost(model_config.model_short_name,
                                          usage.input_tokens,
                                          usage.output_tokens)
        agent_cost = {
            "total_cost": total_cost,
            "total_input_tokens" : usage.input_tokens,
            "total_output_tokens" : usage.output_tokens,
            "total_requests":usage.requests,
        }
        for k,v in agent_cost.items():
            print(f"{k} : {v}")

        with open(res_log_file, "w", encoding='utf-8') as f:
            result = {'config':task_config,
                      'request_id': str(uuid.uuid4()), 
                      'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                      'tool_calls': {'tools': all_tools, 'tool_choice': 'auto'}, 
                      "status": task_status.value,
                      'messages': []}
            for msg in logs_to_record:
                result['messages'].append(msg)

            # 使用自定义的JSON编码器将字典转换为字符串，确保布尔值输出为小写的true或false形式
            json_output = json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder)
            f.write(json_output)
        await mcp_manager.disconnect_servers()

async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--with_proxy", action="store_true")
    parser.add_argument("--model_short_name", default="gpt-4.1-mini")
    parser.add_argument("--user_model_short_name", default="gpt-4.1")
    parser.add_argument("--model_provider_name", default="aihubmix")
    parser.add_argument("--task_config", default="tasks/dev/filesystem_001/task_config.json")
    parser.add_argument("--mcp_config_path", default="configs/mcp_servers")
    args = parser.parse_args()
    
    if args.with_proxy:
        os.environ['http_proxy'] = global_configs.proxy
        os.environ['https_proxy'] = global_configs.proxy

    model_provider = model_provider_mapping[args.model_provider_name]()
    model_real_name = API_MAPPINGS[args.model_short_name].api_model[args.model_provider_name]

    model_config = Dict(# model related
                        model_short_name=args.model_short_name,
                        model_real_name=model_real_name,
                        provider=model_provider,
                        # generation related
                        temperature=0.0,
                        top_p=1.0,
                        max_tokens=4096,
                        # tool call related
                        tool_choice="auto",
                        parallel_tool_calls=False,
                        max_inner_turns=20,
                        )

    user_config = Dict(
        model_short_name = args.user_model_short_name,
        model_provider_name = args.model_provider_name,
        top_p=1.0,
        temperature=0.7,
        max_tokens=1024,
    )

    task_config = Dict(read_json(args.task_config))

    user_client = AsyncOpenAIClientWithRetry(
        api_key = global_configs.non_ds_key,
        base_url = global_configs.base_url_non_ds,
        provider = user_config.model_provider_name,
    )

    await run_agent(task_config=task_config,
                    model_config=model_config,
                    user_client=user_client,
                    user_config = user_config,
                    mcp_config_path=args.mcp_config_path)

    log_file = task_config.log_file

    dump_line = read_json(log_file)

    eval_res = await eval_agent(dump_line)

    print(eval_res)

if __name__ == "__main__":
    asyncio.run(main())
    


    



