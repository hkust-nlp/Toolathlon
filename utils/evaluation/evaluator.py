from typing import Dict, Any, List, Optional
from utils.roles.task_agent import TaskStatus
from utils.data_structures.task_config import TaskConfig
from utils.general.helper import run_command, read_json, write_json
import logging
import os

class TaskEvaluator:
    """任务评估器"""
    
    @staticmethod
    async def evaluate_one(dump_line: Dict[str, Any]) -> Dict[str, Any]:
        """
        单任务评估
        预期可能会被检查的内容：
            - user response：检查用户端的所有输出
            - response：检查llm的所有输出
            - tool calls：检查llm的所有tool calls
            - tool outputs：检查所有tool outputs
            ====== 对以下内容的检查需要从config再启动 ======
            - local status：检查特定工作目录下的文件（比如保存了一些东西，修改了一些东西etc）
            - remote status：手动调用MCP server检查remote status是否正常修改 [不知道是否可能]
        利用上述内容来完成对任务执行成功与否的判断
        """
        task_config = TaskConfig.from_dict(dump_line['config'])
        task_status = dump_line['status']
        # 准备评估所需的信息
        res_log_file = task_config.log_file
        agent_workspace = task_config.agent_workspace
        groundtruth_workspace = task_config.evaluation.groundtruth_workspace
        eval_command = task_config.evaluation.evaluation_command
        launch_time = task_config.launch_time
        print(f"launch time in eval is {launch_time}")

        # 评估所有内容
        if eval_command is not None:
            # try:
            args = f"--res_log_file {res_log_file} --agent_workspace {agent_workspace} --groundtruth_workspace {groundtruth_workspace} --launch_time \"{launch_time}\""
            command = f"{eval_command} {args}"
            output, error, returncode = await run_command(command,debug=True)
            print("== Evaluation STDOUT ==")
            print(output)
            print("== Evaluation STDERR ==")
            print(error)
            if returncode != 0:
                return {
                    "pass": False, 
                    "failure": output,
                }

        if task_status != TaskStatus.SUCCESS.value:
            return {
                "pass": True, 
                # 原因是模型可能前面已经做对，但花了一些时间在检查，导致超过轮数限制了
                "details": f"Task status: {task_status}, but all evaluation checks passed, so we consider it passed"
            }
        else:
            return {
                "pass": True,
                "details": "All evaluation checks passed, and task status is success"
            }
    
    @staticmethod
    async def evaluate_from_log_file(log_file_path: str, allow_resume: bool = False) -> Dict[str, Any]:
        """从日志文件评估任务"""
        try:            
            if not os.path.exists(log_file_path):
                return {
                    "pass": False,
                    "failure": "log_file_not_found",
                    "details": f"Log file not found: {log_file_path}"
                }
            # if allow_resume AND we can load pre exist eval res, we just load it
            eval_file_path = os.path.join(os.path.dirname(log_file_path),"eval_res.json")
            if allow_resume and os.path.exists(eval_file_path):
                eval_res = read_json(eval_file_path)
                return eval_res
            # otherwise, we do real eval and store the eval result
            dump_line = read_json(log_file_path)
            eval_res = await TaskEvaluator.evaluate_one(dump_line)
            write_json(eval_res, eval_file_path)
            return eval_res
            
        except Exception as e:
            logging.error(f"Error evaluating from log file {log_file_path}: {e}")
            return {
                "pass": False,
                "failure": "evaluation_error",
                "details": str(e)
            }
    
    @staticmethod
    async def batch_evaluate(run_results: List[Dict[str, Any]], allow_resume: bool=False) -> List[Dict[str, Any]]:
        """批量评估任务结果"""
        eval_results = []
        
        for run_result in run_results:
            eval_result = {
                "task_config_path": run_result["task_config_path"],
                "task_id": run_result.get("task_id", "unknown"),
            }
            
            if not run_result.get("success", False):
                eval_result["evaluation"] = {
                    "pass": False,
                    "failure": "task_execution_failed",
                    "details": run_result.get("error", "Unknown error")
                }
            else:
                log_file = run_result.get("log_file")
                if log_file:
                    eval_result["evaluation"] = await TaskEvaluator.evaluate_from_log_file(log_file, allow_resume = allow_resume)
                else:
                    eval_result["evaluation"] = {
                        "pass": False,
                        "failure": "no_log_file",
                        "details": "No log file generated"
                    }
            
            eval_result["pass"] = eval_result["evaluation"]["pass"]
            eval_results.append(eval_result)
        
        return eval_results