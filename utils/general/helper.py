import json
import os
from tqdm import tqdm
from pprint import pprint
import datetime
import re
import pandas as pd
import random
import ast
import sys
import numpy as np
import sympy as sp
import subprocess
from typing import List
from termcolor import colored
import pickle
import os
import shutil
import asyncio

import json
import os
import fcntl
import time
import errno

from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from utils.api_model.model_provider import model_provider_mapping
from utils.data_structures.agent_config import AgentConfig
from utils.data_structures.user_config import UserConfig
from configs.global_configs import global_configs
from agents import ModelProvider

from pathlib import Path
from typing import Union



BASIC_TYPES = [int, float, str, bool, None, list, dict, set, tuple]

def elegant_show(something, level=0, sid=0, full=False, max_list=None):
    # str,float,int
    # all print in this call should add level*4 spaces
    prefix = "\t" * level

    if isinstance(something, (str, float, int)) or something is None:
        if isinstance(something, str):
            # if '\n' in something:
            #     something = '\n'+something
            # add prefix whenever go to a new line in this string
            something = something.replace("\n", f"\n{prefix}")
        print(prefix, f"\033[1;35mElement: \033[0m", something)
    elif isinstance(something, list) or isinstance(something, tuple):
        # take a random example, and length
        # sid = 0
        if len(something) == 0:
            print(
                prefix,
                f"\033[1;33mLen: \033[0m{len(something)} \t\033[1;33m& No elements! \033[0m",
            )
        elif not full or len(something) == 1:
            print(
                prefix,
                f"\033[1;33mLen: \033[0m{len(something)} \t\033[1;33m& first element ...\033[0m",
            )
            elegant_show(something[sid], level + 1, sid, full, max_list)
        else:
            print(
                prefix,
                f"\033[1;33mLen: \033[0m{len(something)} \t\033[1;33m& Elements ...\033[0m",
            )
            end = min(len(something) - 1,max_list) if max_list is not None else len(something) - 1
            for i in range(end):
                elegant_show(something[i], level + 1, sid, full, max_list)
                print(
                    prefix + "\t", f"\033[1;33m-------------------------------\033[0m"
                )
            elegant_show(something[-1], level + 1, sid, full, max_list)

    elif isinstance(something, dict):
        for k, v in something.items():
            print(prefix, f"\033[1;34mKey: \033[0m{k} \033[1;34m...\033[0m")
            elegant_show(v, level + 1, sid, full, max_list)
    else:
        print(prefix, f"\033[1;31mError @ Type: \033[0m{type(something)}")
        # raise NotImplementedError

def show(messages):
    for item in messages:
        if 'content' in item:
            content = item['content']
        elif 'text' in item:
            content = item['text']
        else:
            raise ValueError
        if item['role']=='user':
            color = "red"
        elif item['role']=='system':
            color = "green"
        elif item['role']=='assistant':
            color = "blue"
        elif item['role']=='tool':
            color = "yellow"
        else:
            raise ValueError
        new_item = {k:v for k,v in item.items() if k  not in ['role','text','content','tokens','logprobs']}
        if content == "": content = "[[[[[[[[[[[[[[[Empty content]]]]]]]]]]]]]]]"
        print(f"|||{new_item}|||\n"+colored(content,color))
 
def read_jsonl(jsonl_file_path):
    s = []
    with open(jsonl_file_path, "r") as f:
        lines = f.readlines()
    for line in lines:
        linex = line.strip()
        if linex == "":
            continue
        s.append(json.loads(linex))
    return s

def load_jsonl_yield(path):
    with open(path) as f:
        for row, line in enumerate(f):
            try:
                line = json.loads(line)
                yield line
            except:
                pass

def read_json(json_file_path):
    with open(json_file_path, "r") as f:
        return json.load(f)

def read_parquet(parquet_file_path):
    dt = pd.read_parquet(parquet_file_path)
    # convert it into a list of dict
    return dt.to_dict(orient="records")

def read_pkl(pkl_file_path):
    with open(pkl_file_path, "rb") as f:
        return pickle.load(f)

def read_all(file_path):
    if file_path.endswith(".jsonl"):
        return read_jsonl(file_path)
    elif file_path.endswith(".json"):
        return read_json(file_path)
    elif file_path.endswith(".parquet"):
        return read_parquet(file_path)
    elif file_path.endswith(".pkl"):
        return read_pkl(file_path)
    else:
        with open(file_path, "r") as f:
            return f.read()

def write_jsonl(data, jsonl_file_path, mode="w"):
    # data is a list, each of the item is json-serilizable
    assert isinstance(data, list)
    if len(data) == 0:
        return
    if not os.path.exists(os.path.dirname(jsonl_file_path)):
        os.makedirs(os.path.dirname(jsonl_file_path))
    with open(jsonl_file_path, mode) as f:
        for item in data:
            f.write(json.dumps(item) + "\n")


def write_json(data, json_file_path, mode="w", timeout=10):
    """
    Thread/process safe JSON write function
    
    Args:
        data: dict or list, must be JSON serializable
        json_file_path: JSON file path
        mode: File open mode, default "w"
        timeout: Timeout for acquiring the lock (seconds)
    """
    assert isinstance(data, dict) or isinstance(data, list)
    
    # Ensure the directory exists
    dir_path = os.path.dirname(json_file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    
    start_time = time.time()
    
    while True:
        try:
            with open(json_file_path, mode) as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    # Write JSON data
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Ensure data is written to disk
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                break
                
        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EACCES:
                raise
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Failed to acquire file lock within {timeout} seconds: {json_file_path}")
            # Sleep for a short time and retry
            time.sleep(0.01)

def write_all(data, file_path, mode="w"):
    if file_path.endswith(".jsonl"):
        write_jsonl(data, file_path, mode)
    elif file_path.endswith(".json"):
        write_json(data, file_path, mode)
    else:
        with open(file_path, mode) as f:
            f.write(data)

def print_color(text, color="yellow", end='\n'):
    """
    Print the given text in the specified color.
    
    Args:
    text (str): The text to be printed.
    color (str): The color to use. Supported colors are:
                 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
    end (str): String appended after the last value, default a newline.
    """
    color_codes = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
    }
    
    reset_code = '\033[0m'
    
    if color.lower() not in color_codes:
        print(f"Unsupported color: {color}. Using default.", end='')
        print(text, end=end)
    else:
        color_code = color_codes[color.lower()]
        print(f"{color_code}{text}{reset_code}", end=end)

def timer(func):
    def format_time(time_delta):
        hours, remainder = divmod(time_delta.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    def wrapper(*args, **kwargs):
        start_time = datetime.datetime.now()
        print("Start time: ", start_time.strftime("%Y-%m-%d %H:%M:%S"))
        result = func(*args, **kwargs)
        end_time = datetime.datetime.now()
        print("End time: ", end_time.strftime("%Y-%m-%d %H:%M:%S"))
        elapsed_time = end_time - start_time
        print("Execution time: ", format_time(elapsed_time))
        return result
    return wrapper

def reorganize_jsonl(jsonl_file, w_blank=True):
    # We assume all lines in this file has an index field
    dt = read_all(jsonl_file)
    # Sort the lines in dt based on the index field
    dt = sorted(dt, key=lambda x: int(x['index']))
    
    # If w_blank is True, we insert a blank {} into positions where the index is missed
    if w_blank:
        last_idx = int(dt[-1]['index'])
        new_dt = []
        current_index = 0
        
        for item in dt:
            item_index = int(item['index'])
            while current_index < item_index:
                new_dt.append({})
                current_index += 1
            new_dt.append(item)
            current_index += 1
        
        dt = new_dt

    return dt

def extract_param(command, param_name):
    # Use regex to match the value after the parameter --param_name
    pattern = f"--{param_name} (\\S+)"
    match = re.search(pattern, command)
    
    if match:
        return match.group(1)  # Return the matched parameter value
    else:
        return None  # Return None if not found
    
def check_obj_size(obj,size):
    # check if the size of `obj` <= size, unit is Byte
    return sys.getsizeof(obj) <= size

def normalize_value(v):
    max_float_precision = 2
    "Recursively convert values to strings if not a built-in type"
    if type(v) in BASIC_TYPES:
        if isinstance(v, dict):
            return {k: normalize_value(v) for k, v in v.items()}
        elif isinstance(v, list):
            return [normalize_value(v) for v in v]
        elif isinstance(v, set):
            return {normalize_value(v) for v in v}
        elif isinstance(v, tuple):
            return tuple(normalize_value(v) for v in v)
        elif isinstance(v, float):
            return round(v, max_float_precision)
        else:
            return v
    elif isinstance(v, complex):
        # keep the max_float_precision for complex number
        return str(
            round(v.real, max_float_precision)
            + round(v.imag, max_float_precision) * 1j
        )
    elif isinstance(v, np.ndarray):
        return repr(v)
    elif isinstance(v, sp.Expr):
        # For float numbers in sympy, keep the max_float_precision
        def format_floats(expr):
            if expr.is_number and expr.is_Float:
                return round(expr, 2)  # Round to 2 decimal places
            elif expr.is_Atom:
                return expr
            else:
                return expr.func(*map(format_floats, expr.args))

        formatted_expr = format_floats(v)
        return str(formatted_expr)
    else:
        return str(v)

def build_messages(prompt, response = None, system_message = None):
    messages = []
    if system_message is not None:
        messages.append({"role":"system","content":system_message})
    messages.append({"role":"user","content":prompt})
    if response is not None:
        messages.append({"role":"assistant","content":response})
    return messages

def get_total_items_with_wc(filename):
    result = subprocess.run(['wc', '-l', filename], stdout=subprocess.PIPE, text=True)
    total_lines = int(result.stdout.split()[0])  # The output of wc is: number of lines filename, so only take the first part
    return total_lines

async def copy_folder_contents(source_folder, target_folder, debug=False):
    """
    Copy all contents of source folder A to target folder B
    
    Args:
        source_folder: Source folder path (A)
        target_folder: Target folder path (B)
    """

    # If target folder does not exist, create it
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        if debug:
            print(f"Target directory `{target_folder}` has been created!")

    # If source folder is None, it means no local initialization is needed
    if source_folder is None:
        print("Source directory is None, not need to copy & paste.")
        return

    # Check if source folder exists
    if not os.path.exists(source_folder):
        raise FileNotFoundError(f"Error: Source directory `{source_folder}` does not exist!")
    
    # Check if source path is a directory
    if not os.path.isdir(source_folder):
        raise NotADirectoryError(f"Error: `{source_folder}` is not a directory!")
    
    # Iterate through all contents of source folder
    for item in os.listdir(source_folder):
        source_path = os.path.join(source_folder, item)
        target_path = os.path.join(target_folder, item)
        
        try:
            if os.path.isdir(source_path):
                # If it is a folder, recursively copy
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)
            else:
                # If it is a file, copy directly
                shutil.copy2(source_path, target_path)
        except Exception as e:
            print(f"Error in copying `{item}` : {str(e)}")
    
    if debug:
        print(f"Copy done! `{source_folder}` -> `{target_folder}`")

async def run_command(command, debug=False, show_output=False):
    """
    Asynchronously execute command and return output
    
    Args:
        command: The command string to execute
        debug: Whether to print debug information
        show_output: Whether to print the output of the command
        
    Returns:
        tuple: (stdout, stderr, return_code)
    """

    # Get current working directory
    current_dir = os.path.abspath(os.getcwd())
    print_color(f"Current working directory to run command: {current_dir}","cyan")

    # Create subprocess
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    if debug:
        print_color(f"Executing command : {command}","cyan")

    # Wait for command execution to complete
    stdout, stderr = await process.communicate()
    
    # Decode output
    stdout_decoded = stdout.decode()
    stderr_decoded = stderr.decode()
    
    # if process.returncode != 0:
    #     raise RuntimeError(f"Failed in executing the command: {stderr_decoded}")
    
    if debug:
        print_color("Successfully executed!","green")
    
    # If output is needed to be shown
    if show_output and stdout_decoded:
        print(f"Command output:\n{stdout_decoded}")
    
    # Return output and return code, so that the caller can further process
    return stdout_decoded, stderr_decoded, process.returncode

async def specifical_inialize_for_mcp(task_config):
    if "arxiv_local" in task_config.needed_mcp_servers:
        cache_dir = os.path.join(task_config.agent_workspace,"arxiv_local_storage")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        assert os.path.exists(cache_dir)
        print("[arxiv_local] arxiv local cache dir has been established")
    if "memory" in task_config.needed_mcp_servers:
        cache_dir = os.path.join(task_config.agent_workspace,"memory")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        assert os.path.exists(cache_dir)
        print("[memory] memory cache dir has been established")
    if "xmind" in task_config.needed_mcp_servers:
        cache_dir = os.path.join(task_config.agent_workspace,"xmind")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        assert os.path.exists(cache_dir)
        print("[xmind] xmind cache dir has been established")
    if "playwright" in task_config.needed_mcp_servers:
        cache_dir = os.path.join(task_config.agent_workspace,".playwright_output")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        assert os.path.exists(cache_dir)
        print("[playwright] playwright file output dir has been established")

def build_user_client(user_config: UserConfig) -> AsyncOpenAIClientWithRetry:
    """Build user client"""
    return AsyncOpenAIClientWithRetry(
        api_key=global_configs.aihubmix_key,
        base_url="https://aihubmix.com/v1",
        provider=user_config.model.provider,
    )

def build_agent_model_provider(agent_config: AgentConfig, override_provider: str = None) -> ModelProvider:
    """Build agent model provider"""
    return model_provider_mapping[agent_config.model.provider if override_provider is None else override_provider]()

def setup_proxy(use_proxy: bool = False) -> None:
    """Set proxy"""
    if use_proxy:
        import os
        os.environ['http_proxy'] = global_configs.proxy
        os.environ['https_proxy'] = global_configs.proxy
        print("Proxy enabled")

def path_to_module(path: Union[str, Path]) -> str:
    """Convert file path to module format
    
    Examples:
    - 'xx/yy/zz.py' -> 'xx.yy.zz'
    - 'xx\\yy\\zz.py' -> 'xx.yy.zz'
    - './xx/yy/zz.py' -> 'xx.yy.zz'
    - '../xx/yy/zz.py' -> '..xx.yy.zz'
    """
    p = Path(path)
    
    # Get path without suffix
    if p.suffix == '.py':
        p = p.with_suffix('')
    
    # Join path parts with dots
    parts = p.parts
    
    # Filter out current directory marker '.'
    parts = [part for part in parts if part != '.']
    
    return '.'.join(parts)

def get_module_path(replace_last: str = None) -> str:
    """
    Get the package path (relative to the current working directory) connected with dots, optionally replace the last level.
    - replace_last: If specified, replace the last level (usually the file name) with the value
    """
    import inspect
    # Get call stack, find the first py file that is not helper.py
    stack = inspect.stack()
    target_file = None
    for frame in stack:
        fname = frame.filename
        if not fname.endswith("helper.py") and fname.endswith(".py"):
            target_file = os.path.abspath(fname)
            break
    if target_file is None:
        raise RuntimeError("Cannot automatically infer target file path")
    
    # Use current working directory as root directory
    cwd = os.getcwd()
    # Calculate relative path
    relative_path = os.path.relpath(target_file, cwd)
    module_path = os.path.splitext(relative_path)[0].replace(os.sep, ".")
    
    if replace_last is not None:
        parts = module_path.split('.')
        parts[-1] = replace_last
        module_path = '.'.join(parts)
    
    return module_path

def normalize_str(xstring):
    # remove punctuation and whitespace and lowercase
    return re.sub(r'[^\w]', '', xstring).lower().strip()

def compare_iso_time(agent_time, groundtruth_time,date_only=False):
    # given both date in iso format, compare if they are the same
    agent_time = datetime.datetime.fromisoformat(agent_time)
    groundtruth_time = datetime.datetime.fromisoformat(groundtruth_time)
    if date_only: # we only compare the date part
        agent_time = agent_time.date()
        groundtruth_time = groundtruth_time.date()
    return agent_time == groundtruth_time


async def fork_repo(source_repo, target_repo, fork_default_branch_only, readonly=False):
    command = f"uv run -m utils.app_specific.github.github_delete_and_refork "
    command += f"--source_repo_name {source_repo} "
    command += f"--target_repo_name {target_repo}"
    if fork_default_branch_only:
        command += " --default_branch_only"
    if readonly:
        command += " --read_only"
    await run_command(command, debug=True, show_output=True)
    print_color(f"Forked repo {source_repo} to {target_repo} successfully","green")

async def forked_repo_to_independent(repo_name,tmp_dir,private):
    command = f"uv run -m utils.app_specific.github.github_fork_to_independent "
    command += f"--repo_name {repo_name} "
    command += f"--tmp_dir \"{tmp_dir}\""
    if private:
        command += " --private"
    await run_command(command, debug=True, show_output=True)
    print_color(f"Forked repo {repo_name} to independent repo successfully","green")

if __name__=="__main__":
    pass