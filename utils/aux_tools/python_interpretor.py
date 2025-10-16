import json
import os
import subprocess
import uuid
import sys
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper


async def on_python_execute_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    try:
        # Parse parameters
        params = json.loads(params_str)
        code = params.get("code", "")
        filename = params.get("filename", f"{uuid.uuid4()}.py")
        timeout = params.get("timeout", 30)  # Default 30 seconds
        
        # Ensure timeout is not greater than 120 seconds
        if timeout > 120:
            timeout = 120
        
        # Ensure file name ends with .py
        if not filename.endswith(".py"):
            filename += ".py"
        
        # Get working directory
        agent_workspace = context.context.get('_agent_workspace', '.')
        agent_workspace = os.path.abspath(agent_workspace)
        
        # Create .python_tmp directory
        tmp_dir = os.path.join(agent_workspace, '.python_tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        
        # Create Python file
        file_path = os.path.join(tmp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Record start time
        import time
        start_time = time.time()
        
        # Execute Python file
        cmd = f"uv run --directory {agent_workspace} ./.python_tmp/{filename}"
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return f"=== EXECUTION TIMEOUT ===\nExecution timed out after {timeout} seconds\nExecution time: {execution_time:.3f} seconds"
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Build output
        output_parts = []
        
        # Add standard output
        if result.stdout:
            output_parts.append("=== STDOUT ===")
            output_parts.append(result.stdout.rstrip())
        
        # Add standard error
        if result.stderr:
            output_parts.append("=== STDERR ===")
            output_parts.append(result.stderr.rstrip())
        
        # Add execution information
        output_parts.append("=== EXECUTION INFO ===")
        output_parts.append(f"Return code: {result.returncode}")
        output_parts.append(f"Execution time: {execution_time:.3f} seconds")
        output_parts.append(f"Timeout limit: {timeout} seconds")
        
        # If there is no output
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
            },
            "timeout": {
                "type": "number",
                "maximum": 120,
                "default": 30,
                "description": "Maximum execution time in seconds. Cannot exceed 120 seconds. If a value greater than 120 is provided, it will be automatically limited to 120 seconds. Default is 30 seconds."
            }
        },
        "required": ["code"]
    },
    on_invoke_tool=on_python_execute_tool_invoke
)