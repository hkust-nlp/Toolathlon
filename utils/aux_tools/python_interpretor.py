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
import io
import shutil
import tempfile
from pathlib import Path

# 保存原始的文件操作函数
_original_open = builtins.open
_original_io_open = io.open
_original_os_open = os.open
_original_os_listdir = os.listdir
_original_os_walk = os.walk
_original_os_path_exists = os.path.exists
_original_os_stat = os.stat
_original_os_remove = os.remove
_original_os_rename = os.rename
_original_os_makedirs = os.makedirs
_original_os_rmdir = os.rmdir
_original_os_unlink = os.unlink
_original_os_chmod = os.chmod
_original_os_chown = os.chown if hasattr(os, 'chown') else None
_original_os_link = os.link if hasattr(os, 'link') else None
_original_os_symlink = os.symlink if hasattr(os, 'symlink') else None
_original_os_readlink = os.readlink if hasattr(os, 'readlink') else None
_original_os_access = os.access
_original_os_utime = os.utime
_original_os_truncate = os.truncate if hasattr(os, 'truncate') else None

# shutil模块
_original_shutil_copy = shutil.copy
_original_shutil_copy2 = shutil.copy2
_original_shutil_copyfile = shutil.copyfile
_original_shutil_copytree = shutil.copytree
_original_shutil_move = shutil.move
_original_shutil_rmtree = shutil.rmtree

# pathlib模块
_original_path_open = Path.open
_original_path_read_text = Path.read_text
_original_path_write_text = Path.write_text
_original_path_read_bytes = Path.read_bytes
_original_path_write_bytes = Path.write_bytes
_original_path_unlink = Path.unlink
_original_path_rmdir = Path.rmdir

# 临时文件
_original_tempfile_mkstemp = tempfile.mkstemp
_original_tempfile_mkdtemp = tempfile.mkdtemp
_original_tempfile_TemporaryFile = tempfile.TemporaryFile
_original_tempfile_NamedTemporaryFile = tempfile.NamedTemporaryFile
_original_tempfile_TemporaryDirectory = tempfile.TemporaryDirectory

# 允许的目录
ALLOWED_BASE = r"{allowed_base}"
ALLOWED_BASE_TMP = os.path.join(ALLOWED_BASE, '.tmp')

def is_path_allowed(path):
    """检查路径是否在允许的目录内"""
    if path is None:
        return False
    try:
        # 处理 Path 对象
        if isinstance(path, Path):
            path = str(path)
        abs_path = os.path.abspath(path)
        allowed_abs = os.path.abspath(ALLOWED_BASE)
        return abs_path.startswith(allowed_abs + os.sep) or abs_path == allowed_abs
    except:
        return False

# 文件打开操作
def secure_open(path, mode='r', *args, **kwargs):
    """安全的open函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_open(path, mode, *args, **kwargs)

def secure_io_open(path, mode='r', *args, **kwargs):
    """安全的io.open函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_io_open(path, mode, *args, **kwargs)

def secure_os_open(path, flags, mode=0o777, *, dir_fd=None):
    """安全的os.open函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_open(path, flags, mode, dir_fd=dir_fd)

# 目录操作
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

def secure_makedirs(name, mode=0o777, exist_ok=False):
    """安全的os.makedirs函数"""
    if not is_path_allowed(name):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_makedirs(name, mode, exist_ok)

def secure_rmdir(path, *, dir_fd=None):
    """安全的os.rmdir函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_rmdir(path, dir_fd=dir_fd)

# 文件状态和属性
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

def secure_access(path, mode, *, dir_fd=None, effective_ids=False, follow_symlinks=True):
    """安全的os.access函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_access(path, mode, dir_fd=dir_fd, effective_ids=effective_ids, follow_symlinks=follow_symlinks)

# 文件删除操作
def secure_remove(path, *, dir_fd=None):
    """安全的os.remove函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_remove(path, dir_fd=dir_fd)

def secure_unlink(path, *, dir_fd=None):
    """安全的os.unlink函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_unlink(path, dir_fd=dir_fd)

# 文件重命名和移动
def secure_rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
    """安全的os.rename函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

# 文件权限和属性修改
def secure_chmod(path, mode, *, dir_fd=None, follow_symlinks=True):
    """安全的os.chmod函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_chmod(path, mode, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

def secure_chown(path, uid, gid, *, dir_fd=None, follow_symlinks=True):
    """安全的os.chown函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_chown(path, uid, gid, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

def secure_utime(path, times=None, *, ns=None, dir_fd=None, follow_symlinks=True):
    """安全的os.utime函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_utime(path, times, ns=ns, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

def secure_truncate(path, length):
    """安全的os.truncate函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_truncate(path, length)

# 链接操作
def secure_link(src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
    """安全的os.link函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_link(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks)

def secure_symlink(src, dst, target_is_directory=False, *, dir_fd=None):
    """安全的os.symlink函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_symlink(src, dst, target_is_directory, dir_fd=dir_fd)

def secure_readlink(path, *, dir_fd=None):
    """安全的os.readlink函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_os_readlink(path, dir_fd=dir_fd)

# shutil安全包装
def secure_shutil_copy(src, dst, *, follow_symlinks=True):
    """安全的shutil.copy函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_shutil_copy(src, dst, follow_symlinks=follow_symlinks)

def secure_shutil_copy2(src, dst, *, follow_symlinks=True):
    """安全的shutil.copy2函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_shutil_copy2(src, dst, follow_symlinks=follow_symlinks)

def secure_shutil_copyfile(src, dst, *, follow_symlinks=True):
    """安全的shutil.copyfile函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_shutil_copyfile(src, dst, follow_symlinks=follow_symlinks)

def secure_shutil_copytree(src, dst, **kwargs):
    """安全的shutil.copytree函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_shutil_copytree(src, dst, **kwargs)

def secure_shutil_move(src, dst, **kwargs):
    """安全的shutil.move函数"""
    if not is_path_allowed(src) or not is_path_allowed(dst):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_shutil_move(src, dst, **kwargs)

def secure_shutil_rmtree(path, **kwargs):
    """安全的shutil.rmtree函数"""
    if not is_path_allowed(path):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_shutil_rmtree(path, **kwargs)

# pathlib安全包装
def secure_path_open(self, mode='r', **kwargs):
    """安全的Path.open方法"""
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    return _original_open(str(self), mode, **kwargs)

def secure_path_read_text(self, encoding=None, errors=None):
    """安全的Path.read_text方法"""
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    with self.open('r', encoding=encoding, errors=errors) as f:
        return f.read()

def secure_path_write_text(self, data, encoding=None, errors=None, newline=None):
    """安全的Path.write_text方法"""
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    with self.open('w', encoding=encoding, errors=errors, newline=newline) as f:
        return f.write(data)

def secure_path_read_bytes(self):
    """安全的Path.read_bytes方法"""
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    with self.open('rb') as f:
        return f.read()

def secure_path_write_bytes(self, data):
    """安全的Path.write_bytes方法"""
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    with self.open('wb') as f:
        return f.write(data)

def secure_path_unlink(self, missing_ok=False):
    """安全的Path.unlink方法""" 
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    try:
        _original_os_unlink(str(self))
    except FileNotFoundError:
        if not missing_ok:
            raise

def secure_path_rmdir(self):
    """安全的Path.rmdir方法"""
    if not is_path_allowed(str(self)):
        raise PermissionError(f"Access denied: Cannot access files outside of {{ALLOWED_BASE}}")
    _original_os_rmdir(str(self))

# 临时文件安全包装
def secure_tempfile_mkstemp(suffix=None, prefix=None, dir=None, text=False):
    """安全的tempfile.mkstemp"""
    if dir and not is_path_allowed(dir):
        raise PermissionError(f"Access denied: Cannot create temp files outside of {{ALLOWED_BASE}}")
    # 如果没指定目录，使用允许的目录
    if not dir:
        dir = ALLOWED_BASE_TMP
    return _original_tempfile_mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)

def secure_tempfile_mkdtemp(suffix=None, prefix=None, dir=None):
    """安全的tempfile.mkdtemp"""
    if dir and not is_path_allowed(dir):
        raise PermissionError(f"Access denied: Cannot create temp directory outside of {{ALLOWED_BASE}}")
    # 如果没指定目录，使用允许的目录
    if not dir:
        dir = ALLOWED_BASE_TMP
    return _original_tempfile_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

def secure_tempfile_TemporaryFile(mode='w+b', buffering=-1, encoding=None, 
                                  newline=None, suffix=None, prefix=None, 
                                  dir=None, *, errors=None):
    """安全的tempfile.TemporaryFile"""
    if dir and not is_path_allowed(dir):
        raise PermissionError(f"Access denied: Cannot create temp files outside of {{ALLOWED_BASE}}")
    if not dir:
        dir = ALLOWED_BASE_TMP
    return _original_tempfile_TemporaryFile(mode, buffering, encoding, newline, 
                                            suffix, prefix, dir, errors=errors)

def secure_tempfile_NamedTemporaryFile(mode='w+b', buffering=-1, encoding=None,
                                      newline=None, suffix=None, prefix=None,
                                      dir=None, delete=True, *, errors=None):
    """安全的tempfile.NamedTemporaryFile"""
    if dir and not is_path_allowed(dir):
        raise PermissionError(f"Access denied: Cannot create temp files outside of {{ALLOWED_BASE}}")
    if not dir:
        dir = ALLOWED_BASE_TMP
    return _original_tempfile_NamedTemporaryFile(mode, buffering, encoding, newline,
                                                 suffix, prefix, dir, delete, errors=errors)

class secure_tempfile_TemporaryDirectory:
    """安全的tempfile.TemporaryDirectory"""
    def __init__(self, suffix=None, prefix=None, dir=None):
        if dir and not is_path_allowed(dir):
            raise PermissionError(f"Access denied: Cannot create temp directory outside of {{ALLOWED_BASE}}")
        if not dir:
            dir = ALLOWED_BASE_TMP
        self._wrapped = _original_tempfile_TemporaryDirectory(suffix=suffix, prefix=prefix, dir=dir)
    
    def __enter__(self):
        return self._wrapped.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._wrapped.__exit__(exc_type, exc_val, exc_tb)
    
    @property
    def name(self):
        return self._wrapped.name
    
    def cleanup(self):
        return self._wrapped.cleanup()

# 替换内置函数
builtins.open = secure_open
io.open = secure_io_open
os.open = secure_os_open
os.listdir = secure_listdir
os.walk = secure_walk
os.path.exists = secure_exists
os.stat = secure_stat
os.remove = secure_remove
os.unlink = secure_unlink
os.rename = secure_rename
os.makedirs = secure_makedirs
os.rmdir = secure_rmdir
os.chmod = secure_chmod
if _original_os_chown:
    os.chown = secure_chown
if _original_os_link:
    os.link = secure_link
if _original_os_symlink:
    os.symlink = secure_symlink
if _original_os_readlink:
    os.readlink = secure_readlink
os.access = secure_access
os.utime = secure_utime
if _original_os_truncate:
    os.truncate = secure_truncate

# 替换shutil函数
shutil.copy = secure_shutil_copy
shutil.copy2 = secure_shutil_copy2
shutil.copyfile = secure_shutil_copyfile
shutil.copytree = secure_shutil_copytree
shutil.move = secure_shutil_move
shutil.rmtree = secure_shutil_rmtree

# 替换pathlib方法
Path.open = secure_path_open
Path.read_text = secure_path_read_text
Path.write_text = secure_path_write_text
Path.read_bytes = secure_path_read_bytes
Path.write_bytes = secure_path_write_bytes
Path.unlink = secure_path_unlink
Path.rmdir = secure_path_rmdir

# 替换tempfile函数
tempfile.mkstemp = secure_tempfile_mkstemp
tempfile.mkdtemp = secure_tempfile_mkdtemp
tempfile.TemporaryFile = secure_tempfile_TemporaryFile
tempfile.NamedTemporaryFile = secure_tempfile_NamedTemporaryFile
tempfile.TemporaryDirectory = secure_tempfile_TemporaryDirectory

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