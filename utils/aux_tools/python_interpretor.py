import json
import os
import subprocess
import uuid
import sys
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper


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
        
        
        # 创建 Python 文件
        file_path = os.path.join(tmp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 执行 Python 文件
        cmd = f"uv run --directory {agent_workspace} ./.python_tmp/{filename}"
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
    description='Execute Python code directly under the agent workspace, and returns stdout, stderr, return code, and execution time in a structured format.',
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