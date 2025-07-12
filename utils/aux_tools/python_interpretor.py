import json
import os
import subprocess
import uuid
import sys
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper

# 安全包装器代码模板
SANDBOX_WRAPPER = '''
import os
import sys
import builtins

# 保存原始的文件操作函数
_original_open = builtins.open
_original_os_open = os.open
_original_os_listdir = os.listdir
_original_os_walk = os.walk
_original_os_path_exists = os.path.exists
_original_os_stat = os.stat
_original_os_remove = os.remove
_original_os_rename = os.rename
_original_os_makedirs = os.makedirs

# 允许的目录
ALLOWED_BASE = r"{allowed_base}"

def is_path_allowed(path):
    """检查路径是否在允许的目录内"""
    try:
        abs_path = os.path.abspath(path)
        allowed_abs = os.path.abspath(ALLOWED_BASE)
        return abs_path.startswith(allowed_abs + os.sep) or abs_path == allowed_abs
    except:
        return False

def secure_open(path, mode='r', *args, **kwargs):
    """安全的open函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_open(path, mode, *args, **kwargs)

def secure_os_open(path, flags, mode=0o777, *, dir_fd=None):
    """安全的os.open函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_open(path, flags, mode, dir_fd=dir_fd)

def secure_listdir(path='.'):
    """安全的os.listdir函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_listdir(path)

def secure_walk(top, topdown=True, onerror=None, followlinks=False):
    """安全的os.walk函数"""
    if not is_path_allowed(top):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_walk(top, topdown, onerror, followlinks)

def secure_exists(path):
    """安全的os.path.exists函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_path_exists(path)

def secure_stat(path, *, dir_fd=None, follow_symlinks=True):
    """安全的os.stat函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

def secure_remove(path, *, dir_fd=None):
    """安全的os.remove函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_remove(path, dir_fd=dir_fd)

def secure_rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
    """安全的os.rename函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

def secure_makedirs(name, mode=0o777, exist_ok=False):
    """安全的os.makedirs函数"""
    if not is_path_allowed(name):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_makedirs(name, mode, exist_ok)

# 替换内置函数
builtins.open = secure_open
os.open = secure_os_open
os.listdir = secure_listdir
os.walk = secure_walk
os.path.exists = secure_exists
os.stat = secure_stat
os.remove = secure_remove
os.rename = secure_rename
os.makedirs = secure_makedirs

# 禁用一些危险的模块导入
def secure_import(name, *args, **kwargs):
    dangerous_modules = ['subprocess', 'socket', 'requests', 'urllib', 'http']
    if any(name.startswith(mod) for mod in dangerous_modules):
        raise ImportError(f"Import of module '{{name}}' is not allowed for security reasons")
    return _original_import(name, *args, **kwargs)

_original_import = builtins.__import__
builtins.__import__ = secure_import

# 用户代码开始
os.chdir(ALLOWED_BASE)  # 设置工作目录为允许的目录

{user_code}
'''

async def on_python_execute_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    try:
        # 解析参数
        params = json.loads(params_str)
        code = params.get("code", "")
        filename = params.get("filename", f"{uuid.uuid4()}.py")
        
        # 确保文件名以 .py 结尾
        if not filename.endswith(".py"):
            filename += ".py"
        
        # 获取工作目录
        agent_workspace = context.context.get('_agent_workspace', '.')
        agent_workspace = os.path.abspath(agent_workspace)
        
        # 创建 .python_tmp 目录
        tmp_dir = os.path.join(agent_workspace, '.python_tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        # 将用户代码包装在安全沙箱中
        wrapped_code = SANDBOX_WRAPPER.format(
            allowed_base=agent_workspace,
            user_code=code
        )
        
        # 创建 Python 文件
        file_path = os.path.join(tmp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(wrapped_code)
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 执行 Python 文件
        cmd = f"uv run --directory {tmp_dir} {filename}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 构建输出
        output_parts = []
        
        # 添加标准输出
        if result.stdout:
            output_parts.append("=== STDOUT ===")
            output_parts.append(result.stdout.rstrip())
        
        # 添加标准错误
        if result.stderr:
            output_parts.append("=== STDERR ===")
            output_parts.append(result.stderr.rstrip())
        
        # 添加执行信息
        output_parts.append("=== EXECUTION INFO ===")
        output_parts.append(f"Return code: {result.returncode}")
        output_parts.append(f"Execution time: {execution_time:.3f} seconds")
        
        # 如果没有任何输出
        if not result.stdout and not result.stderr:
            output_parts.insert(0, "No console output produced.")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"Error executing Python code: {str(e)}"

tool_python_execute = FunctionTool(
    name='local-python-execute',
    description='Execute Python code in a sandboxed environment (file access limited to agent workspace). Returns stdout, stderr, return code, and execution time in a structured format.',
    params_json_schema={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute (can be directly pasted into a .py file)"
            },
            "filename": {
                "type": "string",
                "description": "Filename for the Python file (including .py extension). If not provided, a random UUID will be used."
            }
        },
        "required": ["code"]
    },
    on_invoke_tool=on_python_execute_tool_invoke
)