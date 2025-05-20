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
        if content == "": content = "[[[[[[[[[[[[[[[空content]]]]]]]]]]]]]]]"
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

def update_jsonl(line_num: int, jsonl_file_path:str, key_indicator=None, json_file_path="files/test.json", ) -> None:
    """
    读取给定的 JSON 文件，将其压缩成一行，并替换 JSONL 文件中指定行的内容。
    两者需要确保 `leetcode_id` 字段一致。
    
    Args:
        json_file_path (str): 要读取的 JSON 文件路径。
        line_num (int): JSONL 文件中的行号（从1开始）。
        jsonl_file_path (str): 要更新的 JSONL 文件路径。
        key_indicator (str): 用于检查 JSON 文件和 JSONL 文件中的记录是否匹配的字段。
    """
    # 读取 JSON 文件内容并压缩成一行
    try:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            new_json_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"读取 JSON 文件 {json_file_path} 出错: {e}")
        return

    # 压缩 JSON 数据
    new_json_str = json.dumps(new_json_data, separators=(',', ':'))

    # 读取 JSONL 文件
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as jsonl_file:
            lines = jsonl_file.readlines()
    except FileNotFoundError as e:
        print(f"读取 JSONL 文件 {jsonl_file_path} 出错: {e}")
        return

    # 检查指定行号是否超出范围
    if line_num < 1 or line_num > len(lines):
        print(f"错误：指定的行号 {line_num} 超出了 JSONL 文件的范围。")
        return

    # 获取 JSONL 文件中指定行并加载为 JSON 对象
    try:
        original_json = json.loads(lines[line_num - 1].strip())
    except json.JSONDecodeError as e:
        print(f"解析 JSONL 文件的第 {line_num} 行内容失败: {e}")
        return

    # 检查 `key_indicator` 是否匹配
    if key_indicator is not None:
        if original_json.get(key_indicator) != new_json_data.get(key_indicator):
            print(f"错误：JSON 文件和 JSONL 文件的 `{key_indicator}` 不匹配。")
            return

    # 更新 JSONL 文件中的指定行
    lines[line_num - 1] = new_json_str + '\n'

    # 将更新过的内容写回 JSONL 文件
    try:
        with open(jsonl_file_path, 'w', encoding='utf-8') as jsonl_file:
            jsonl_file.writelines(lines)
        print(f"已成功更新 JSONL 文件的第 {line_num} 行。")
    except IOError as e:
        print(f"写入 JSONL 文件 {jsonl_file_path} 时出错: {e}")

def update_json(key, txt_file_path="files/test.txt", json_file_path="files/test.json",) -> None:
    with open(txt_file_path, "r") as f:
        content = f.read()

    with open(json_file_path, "r") as f:
        data = json.load(f)
        data[key] = content

    with open(json_file_path, "w") as f:
        json.dump(data, f)

def write_json(data, json_file_path, mode="w"):
    # data is a dict, json-serilizable
    assert isinstance(data, dict) or isinstance(data, list)
    if not os.path.exists(os.path.dirname(json_file_path)):
        os.makedirs(os.path.dirname(json_file_path))
    with open(json_file_path, mode) as f:
        f.write(json.dumps(data))

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
        'white': '\033[97m'
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
        print("开始时间：", start_time.strftime("%Y-%m-%d %H:%M:%S"))
        result = func(*args, **kwargs)
        end_time = datetime.datetime.now()
        print("结束时间：", end_time.strftime("%Y-%m-%d %H:%M:%S"))
        elapsed_time = end_time - start_time
        print("执行时间：", format_time(elapsed_time))
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
    # 使用正则表达式匹配参数 --param_name 后面的值
    pattern = f"--{param_name} (\\S+)"
    match = re.search(pattern, command)
    
    if match:
        return match.group(1)  # 返回匹配的参数值
    else:
        return None  # 如果未找到，返回 None
    
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
    total_lines = int(result.stdout.split()[0])  # wc输出的形式是: 行数 文件名, 所以只取第一部分
    return total_lines

if __name__=="__main__":
    pass