from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from pathlib import Path

@dataclass
class SystemPrompts:
    """系统提示信息"""
    agent: str
    user: str

@dataclass
class Initialization:
    """初始化配置"""
    workspace: str
    process_command: str

@dataclass
class Evaluation:
    """评估配置"""
    groundtruth_workspace: str
    local_state_command: str
    log_command: str

@dataclass
class StopConditions:
    """评估配置"""
    user_phrases: List[str] = None
    tool_names: List[str] = None

@dataclass
class TaskConfig:
    """任务配置"""
    # 基本信息
    id: str
    needed_mcp_servers: List[str]
    task_root: str
    system_prompts: SystemPrompts
    initialization: Initialization
    evaluation: Evaluation
    stop: StopConditions
    log_file: Optional[str] = None
    agent_workspace: Optional[str] = None
    max_turns: int = None
    meta: Dict = field(default_factory=dict)

    agent_short_name: str = None
    global_task_config: Dict = None
    
    def __post_init__(self):
        """在初始化后自动设置默认值"""
        # 使用 Path 对象处理路径
        task_root_path = Path(self.task_root)
        
        # 规范化 task_root（保持字符串格式以保持向后兼容）
        self.task_root = str(task_root_path)

        # 从global task config载入dump_path并更新task_root_path, 方便多次测量前后互不影响
        if self.global_task_config is not None and "dump_path" in self.global_task_config:
            # 把modelname拼在global_task_config.dump_path后面
            global_dump_path = self.global_task_config['dump_path']
            if global_dump_path.endswith(self.agent_short_name) or global_dump_path.endswith(self.agent_short_name+'/'):
                pass
            else:
                global_dump_path = Path(global_dump_path)/Path(self.agent_short_name)
            self.task_root = str(global_dump_path / task_root_path)
            task_root_path = Path(self.task_root)
        
        # 如果没有指定 log_file，自动生成
        if self.log_file is None:
            self.log_file = str(task_root_path / "log.json")
        
        # 如果没有指定 agent_workspace，自动生成
        if self.agent_workspace is None:
            self.agent_workspace = str(task_root_path / "workspace")

        # 设置一些默认的停止条件
        if self.stop.tool_names is None:
            self.stop.tool_names = []
        
        if self.stop.user_phrases is None:
            self.stop.user_phrases = ["#### STOP"]

        if self.global_task_config is not None and "max_turns" in self.global_task_config:
            self.max_turns = self.global_task_config['max_turns']
    
    # 使用 Path 对象的属性方法
    @property
    def task_root_path(self) -> Path:
        """返回任务根目录的Path对象"""
        return Path(self.task_root)
    
    @property
    def log_file_path(self) -> Path:
        """返回日志文件的Path对象"""
        return Path(self.log_file)
    
    @property
    def agent_workspace_path(self) -> Path:
        """返回agent工作区的Path对象"""
        return Path(self.agent_workspace)
    
    @classmethod
    def from_dict(cls, 
                  data: dict, 
                  agent_short_name: str = None,
                  global_task_config: dict = None) -> 'TaskConfig':
        """从字典创建TaskConfig实例"""
        return cls(
            id=data['id'],
            needed_mcp_servers=data['needed_mcp_servers'],
            task_root=data['task_root'],
            system_prompts=SystemPrompts(**data['system_prompts']),
            initialization=Initialization(**data['initialization']),
            evaluation=Evaluation(**data['evaluation']),
            log_file=data.get('log_file'),
            agent_workspace=data.get('agent_workspace'),
            stop=StopConditions(**data.get('stop',{})),
            max_turns=data.get("max_turns"),
            meta=data.get('meta', {}),
            agent_short_name = agent_short_name,
            global_task_config=global_task_config,
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'needed_mcp_servers': self.needed_mcp_servers,
            'task_root': self.task_root,
            'log_file': self.log_file,
            'agent_workspace': self.agent_workspace,
            'system_prompts': {
                'agent': self.system_prompts.agent,
                'user': self.system_prompts.user
            },
            'initialization': {
                'workspace': self.initialization.workspace,
                'process_command': self.initialization.process_command
            },
            'stop': {
                'user_phrases':self.stop.user_phrases,
                'tool_names':self.stop.tool_names,
            },
            'evaluation': {
                'groundtruth_workspace': self.evaluation.groundtruth_workspace,
                'local_state_command': self.evaluation.local_state_command,
                'log_command': self.evaluation.log_command
            },
            'meta': self.meta
        }

    def ensure_directories(self):
        """确保所有必要的目录存在"""
        # 创建任务根目录
        self.task_root_path.mkdir(parents=True, exist_ok=True)
        
        # 创建工作区目录
        self.agent_workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 确保日志文件的父目录存在
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def clean_workspace(self):
        """清理工作区（谨慎使用）"""
        import shutil
        if self.agent_workspace_path.exists():
            shutil.rmtree(self.agent_workspace_path)
        self.agent_workspace_path.mkdir(parents=True, exist_ok=True)

# 使用示例
if __name__ == "__main__":
    # 原始数据
    config_data = {
        "id": "dev_filesystem_001",
        "needed_mcp_servers": ["filesystem"],
        "task_root": "./dumps/dev/filesystem_001/",
        "system_prompts": {
            "agent": "you are a smart agent to deal with issues about filesystem",
            "user": "你是一位正在与agent对话的用户，你这次交互的主要目标任务是管理个人工作区（如列出文件）并追踪一周的财务支出..."
        },
        "initialization": {
            "workspace": "./initial_states/dev/filesystem_001/workspace",
            "process_command": "python -m initial_states.dev.filesystem_001.preprocess",
        },
        "evaluation": {
            "groundtruth_workspace": "./groundtruth/dev/filesystem_001/workspace",
            "local_state_command": "python -m groundtruth.dev.filesystem_001.check_local",
            "log_command": "python -m groundtruth.dev.filesystem_001.check_log"
        },
        "meta": {}
    }
    
    # 示例1：使用字典初始化
    task_config1 = TaskConfig(config_data)
    print("示例1 - 完整配置：")
    print(f"  Task ID: {task_config1.id}")
    print(f"  Task root: {task_config1.task_root}")
    print(f"  Log file: {task_config1.log_file}")
    print(f"  Agent workspace: {task_config1.agent_workspace}")
    
    # 示例2：不提供 log_file 和 agent_workspace，测试自动生成
    config_data2 = {
        "id": "dev_filesystem_002",
        "needed_mcp_servers": ["filesystem"],
        "task_root": "./dumps/dev/filesystem_002",  # 注意：没有结尾的斜杠
        "system_prompts": {
            "agent": "you are a smart agent",
            "user": "you are a user"
        },
        "initialization": {
            "workspace": "./initial_states/dev/filesystem_002/workspace",
            "process_command": "python -m initial_states.dev.filesystem_002.preprocess",
        },
        "evaluation": {
            "groundtruth_workspace": "./groundtruth/dev/filesystem_002/workspace",
            "local_state_command": "python -m groundtruth.dev.filesystem_002.check_local",
            "log_command": "python -m groundtruth.dev.filesystem_002.check_log"
        }
    }
    
    task_config2 = TaskConfig(config_data2)
    print("\n示例2 - 自动生成路径：")
    print(f"  Task ID: {task_config2.id}")
    print(f"  Task root: {task_config2.task_root}")
    print(f"  Log file: {task_config2.log_file}")
    print(f"  Agent workspace: {task_config2.agent_workspace}")
    
    # 示例3：测试不同的路径格式
    print("\n示例3 - 测试路径处理：")
    test_paths = [
        "./dumps/dev/test1/",
        "./dumps/dev/test2",
        "dumps\\dev\\test3",  # Windows 风格
        "./dumps/./dev/../dev/test4/",  # 带有相对路径
    ]
    
    for i, path in enumerate(test_paths):
        config = {
            "id": f"test_{i}",
            "needed_mcp_servers": ["filesystem"],
            "task_root": path,
            "system_prompts": {"agent": "agent", "user": "user"},
            "initialization": {"workspace": "./ws", "process_command": "cmd"},
            "evaluation": {
                "groundtruth_workspace": "./gt",
                "local_state_command": "cmd1",
                "log_command": "cmd2"
            }
        }
        task = TaskConfig(config)
        print(f"  原始路径: {path}")
        print(f"  规范化后: {task.task_root}")
        print(f"  日志文件: {task.log_file}")
        print()
    
    # 示例4：使用 Path 对象的便利功能
    print("示例4 - Path 对象功能：")
    task = TaskConfig(config_data)
    print(f"  任务根目录是否存在: {task.task_root_path.exists()}")
    print(f"  日志文件父目录: {task.log_file_path.parent}")
    print(f"  工作区绝对路径: {task.agent_workspace_path.absolute()}")
    
    # 可以调用 ensure_directories 来创建所有必要的目录
    # task.ensure_directories()
    
    # 示例5：正常的关键字参数初始化仍然支持
    print("\n示例5 - 关键字参数初始化：")
    task_config3 = TaskConfig(
        id="manual_test",
        needed_mcp_servers=["filesystem"],
        task_root="./manual_test/",
        system_prompts=SystemPrompts(agent="test agent", user="test user"),
        initialization=Initialization(
            workspace="./manual_workspace",
            process_command="echo 'hello'"
        ),
        evaluation=Evaluation(
            groundtruth_workspace="./manual_gt",
            local_state_command="python check.py",
            log_command="python log.py"
        ),
        meta={"version": "1.0"}
    )
    print(f"  ID: {task_config3.id}")
    print(f"  Meta: {task_config3.meta}")