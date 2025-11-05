from dataclasses import dataclass, field
import importlib.util
from typing import List, Dict, Optional, Union
from pathlib import Path
from datetime import datetime

from utils.general.helper import path_to_module, read_json
import os

@dataclass
class SystemPrompts:
    """System prompt messages."""
    agent: Union[str, Dict]
    user: Union[str, Dict]
    
    @classmethod
    def build(cls, task_dir: str, cn_mode: bool=False):
        if cn_mode:
            agent_sp_path = Path("tasks") / task_dir / "docs" / "agent_system_prompt_cn.md"
            user_sp_path = Path("tasks") / task_dir / "docs" / "user_system_prompt_cn.md"
        else:
            agent_sp_path = Path("tasks") / task_dir / "docs" / "agent_system_prompt.md"
            user_sp_path = Path("tasks") / task_dir / "docs" / "user_system_prompt.md"
        if agent_sp_path.exists():
            with open(agent_sp_path, 'r', encoding='utf-8') as f:
                agent_sp = f.read()
        else:
            agent_sp = None
        if user_sp_path.exists():
            with open(user_sp_path, 'r', encoding='utf-8') as f:
                user_sp = f.read()
        else:
            user_sp = None
        return cls(agent=agent_sp, user=user_sp)

    def apply(self, agent_workspace: str, 
              task_str: str,
              time: str,
              single_turn_mode: bool=False,
              cn_mode: bool=False):

        if self.agent is not None:
            self.agent = self.agent.replace("!!<<<<||||current_working_dir||||>>>>!!", os.getcwd())
            self.agent = self.agent.replace("!!<<<<||||workspace_dir||||>>>>!!", os.path.abspath(agent_workspace))
            self.agent = self.agent.replace("!!<<<<||||workspace_dir_rela||||>>>>!!", os.path.relpath(agent_workspace))
            self.agent = self.agent.replace("!!<<<<||||time||||>>>>!!", time)
            if single_turn_mode:
                if not cn_mode:
                    self.agent += "\nPlease complete the given task independently. Do not seek confirmation or additional feedback from the user. You should handle all situations on your own, as the user will not provide any further information."
                else:
                    self.agent += "\nPlease complete the given task independently. Do not seek confirmation or additional feedback from the user. You should handle all situations on your own, as the user will not provide any further information."
        if self.user is not None:
            self.user = self.user.replace("!!<<<<||||task_description||||>>>>!!", task_str)
        return self

@dataclass
class Initialization:
    """Initialization configuration."""
    workspace: str
    process_command: str

    @classmethod
    def build(cls, task_dir: str, cn_mode: bool=False):
        workspace_path = Path("tasks") / task_dir / "initial_workspace"
        process_command_path = Path("tasks") / task_dir / "preprocess" / "main.py"

        # If cn_mode and these paths exist, overwrite them
        if cn_mode:
            if (Path("tasks") / task_dir / "initial_workspace_cn").exists():
                workspace_path = Path("tasks") / task_dir / "initial_workspace_cn"
            if (Path("tasks") / task_dir / "preprocess" / "main_cn.py").exists():
                process_command_path = Path("tasks") / task_dir / "preprocess" / "main_cn.py"

        if process_command_path.exists():
            process_command = f"uv run -m {path_to_module(process_command_path)}"
        else:
            process_command = None
        if workspace_path.exists():
            workspace = str(workspace_path)
        else:
            workspace = None
        return cls(workspace=workspace, process_command=process_command)

@dataclass
class Evaluation:
    """Evaluation configuration."""
    groundtruth_workspace: str
    evaluation_command: str

    @classmethod
    def build(cls, task_dir: str, cn_mode: bool=False):
        groundtruth_workspace_path = Path("tasks") / task_dir / "groundtruth_workspace"
        evaluation_command_path = Path("tasks") / task_dir / "evaluation" / "main.py"

        # If cn_mode and these paths exist, overwrite them
        if cn_mode:
            if (Path("tasks") / task_dir / "groundtruth_workspace_cn").exists():
                groundtruth_workspace_path = Path("tasks") / task_dir / "groundtruth_workspace_cn"
            if (Path("tasks") / task_dir / "evaluation" / "main_cn.py").exists():
                evaluation_command_path = Path("tasks") / task_dir / "evaluation" / "main_cn.py"

        if evaluation_command_path.exists():
            evaluation_command = f"uv run -m {path_to_module(evaluation_command_path)}"
        else:
            evaluation_command = None
        if groundtruth_workspace_path.exists():
            groundtruth_workspace = str(groundtruth_workspace_path)
        else:
            groundtruth_workspace = None
        return cls(groundtruth_workspace=groundtruth_workspace, evaluation_command=evaluation_command)

@dataclass
class StopConditions:
    """Stop conditions configuration."""
    user_phrases: List[str] = None
    tool_names: List[str] = None

    @classmethod
    def build(cls, stop_conditions: Dict):
        if stop_conditions is None:
            stop_conditions = {}
        if "user_phrases" in stop_conditions:
            user_phrases = stop_conditions["user_phrases"]
        else:
            user_phrases = ["#### STOP"]
        if "tool_names" in stop_conditions:
            tool_names = stop_conditions["tool_names"]
        else:
            tool_names = ['local-claim_done']
        return cls(user_phrases=user_phrases, tool_names=tool_names)

@dataclass
class TaskConfig:
    """Task configuration."""
    # Basic information
    task_dir: str  # Relative path under tasks/
    id: str = None
    needed_mcp_servers: List[str] = None
    needed_local_tools: List[str] = None
    task_root: str = None
    task_str: str = None
    system_prompts: SystemPrompts = None
    initialization: Initialization = None
    evaluation: Evaluation = None
    stop: StopConditions = None
    log_file: Optional[str] = None
    agent_workspace: Optional[str] = None
    max_turns: int = None
    max_steps_under_single_turn_mode: int = None
    single_turn_mode: bool = False
    cn_mode: bool = False
    meta: Dict = field(default_factory=dict)
    launch_time: str = None

    agent_short_name: str = None
    global_task_config: Dict = None

    local_token_key_session: Dict = None

    def __post_init__(self):
        """Automatically set default values after initialization."""
        assert self.task_dir is not None, "task_dir is required"
        assert len(Path(self.task_dir).parts) == 2, "task_dir must be a relative path under tasks/ with format 'split/task_name'"

        if self.task_root is None:
            self.task_root = self.task_dir
        
        if self.id is None:
            self.id = '-'.join(Path(self.task_dir).parts)

        prefix = ''
        if self.cn_mode:
            prefix = 'Chinese-'
        if self.single_turn_mode:
            prefix += 'SingleUserTurn-'

        # Add SingleUserTurn- or Chinese- prefixes to the last level of task_root, e.g., xx/yy becomes xx/SingleUserTurn-yy
        task_root_parts = Path(self.task_root).parts
        if len(task_root_parts) >= 1:
            last_part = task_root_parts[-1]
            new_last_part = f"{prefix}{last_part}"
            new_parts = list(task_root_parts[:-1]) + [new_last_part]
            self.task_root = str(Path(*new_parts))

        task_root_path = Path(self.task_root)
        self.task_root = str(task_root_path)

        if self.task_str is None:
            if self.cn_mode:
                task_str_path = Path("tasks") / self.task_dir / "docs" / "task_cn.md"
            else:
                task_str_path = Path("tasks") / self.task_dir / "docs" / "task.md"
            with open(task_str_path, 'r', encoding='utf-8') as f:
                self.task_str = f.read()

        # Update dump_path from global_task_config to task_root_path for isolation on repeated runs
        if self.global_task_config is not None and "dump_path" in self.global_task_config:
            global_dump_path = self.global_task_config['dump_path']
            if global_dump_path.endswith(self.agent_short_name.replace('/', '_')) or global_dump_path.endswith(self.agent_short_name.replace('/', '_') + '/'):
                pass
            else:
                global_dump_path = Path(global_dump_path) / Path(self.agent_short_name.replace('/', '_'))
            self.task_root = str(global_dump_path / task_root_path)
            task_root_path = Path(self.task_root)

        if (
            self.global_task_config is not None
            and self.global_task_config.get('direct_to_dumps', False)
            and "dump_path" in self.global_task_config
        ):
            self.task_root = self.global_task_config['dump_path']
            task_root_path = Path(self.task_root)

        # Ensure absolute path for task_root
        self.task_root = os.path.abspath(self.task_root)

        # Automatically generate log_file if not specified
        if self.log_file is None:
            self.log_file = str(task_root_path / "traj_log.json")
        self.log_file = os.path.abspath(self.log_file)

        # Automatically generate agent_workspace if not specified
        if self.agent_workspace is None:
            self.agent_workspace = str(task_root_path / "workspace")
        self.agent_workspace = os.path.abspath(self.agent_workspace)

        # Not sure if this will contradict with the legacy resume mechanism
        eval_res_filepath = str(task_root_path / "eval_res.json")
        if os.path.exists(eval_res_filepath):
            os.remove(eval_res_filepath)

        if self.global_task_config is not None and "max_turns" in self.global_task_config:
            self.max_turns = self.global_task_config['max_turns']

        if self.global_task_config is not None and "max_steps_under_single_turn_mode" in self.global_task_config:
            self.max_steps_under_single_turn_mode = self.global_task_config['max_steps_under_single_turn_mode']

        self.system_prompts.apply(
            self.agent_workspace,
            self.task_str,
            self.launch_time,
            self.single_turn_mode,
            self.cn_mode
        )

        # if self.local_token_key_session is None:
        #     # Dynamically load the module if necessary

    def load_local_token_key_session(self) -> None:
        token_key_session_path = str(Path("tasks") / self.task_dir / "token_key_session.py")

        if Path(token_key_session_path).exists():
            spec = importlib.util.spec_from_file_location("token_key_session", token_key_session_path)
            token_key_session_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(token_key_session_module)
            # Get all_token_key_session variable
            self.local_token_key_session = token_key_session_module.all_token_key_session

    # Use Path object property accessors
    @property
    def task_root_path(self) -> Path:
        """Return Path object of task root directory."""
        return Path(self.task_root)
    
    @property
    def log_file_path(self) -> Path:
        """Return Path object of log file."""
        return Path(self.log_file)
    
    @property
    def agent_workspace_path(self) -> Path:
        """Return Path object of agent workspace directory."""
        return Path(self.agent_workspace)
    
    @classmethod
    def from_dict(cls, task_config_dict: dict) -> 'TaskConfig':
        # Reconstruct from a dict produced by to_dict
        # Note evaluation, system_prompts, initialization, stop are None and need to be constructed
        task_config_dict['evaluation'] = Evaluation(**task_config_dict['evaluation'])
        task_config_dict['system_prompts'] = SystemPrompts(**task_config_dict['system_prompts'])
        task_config_dict['initialization'] = Initialization(**task_config_dict['initialization'])
        task_config_dict['stop'] = StopConditions(**task_config_dict['stop'])
        return cls(**task_config_dict)

    @classmethod
    def build(
        cls,
        task_dir: str,
        agent_short_name: str = None,
        global_task_config: dict = None,
        single_turn_mode: bool = False,
        cn_mode: bool = False
    ) -> 'TaskConfig':
        """Build TaskConfig instance from a dictionary."""
        task_config_dict = read_json(Path("tasks") / task_dir / "task_config.json")
        return cls(
            task_dir=task_dir,
            needed_mcp_servers=task_config_dict['needed_mcp_servers'],
            needed_local_tools=task_config_dict['needed_local_tools'],
            max_turns=task_config_dict.get("max_turns"),
            meta=task_config_dict.get('meta', {}),
            agent_short_name=agent_short_name,
            global_task_config=global_task_config,
            stop=StopConditions.build(task_config_dict.get('stop')),
            system_prompts=SystemPrompts.build(task_dir, cn_mode),
            initialization=Initialization.build(task_dir, cn_mode),
            evaluation=Evaluation.build(task_dir, cn_mode),
            single_turn_mode=single_turn_mode,
            cn_mode=cn_mode,
            # The following timestamp contains year, month, day, time, and weekday
            launch_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'task_dir': self.task_dir,
            'id': self.id,
            'needed_mcp_servers': self.needed_mcp_servers,
            'needed_local_tools': self.needed_local_tools,
            'task_root': self.task_root,
            'task_str': self.task_str,
            'log_file': self.log_file,
            'agent_workspace': self.agent_workspace,
            'launch_time': self.launch_time,
            'max_turns': self.max_turns,
            'max_steps_under_single_turn_mode': self.max_steps_under_single_turn_mode,
            'single_turn_mode': self.single_turn_mode,
            'cn_mode': self.cn_mode,
            'system_prompts': {
                'agent': self.system_prompts.agent,
                'user': self.system_prompts.user
            },
            'initialization': {
                'workspace': self.initialization.workspace,
                'process_command': self.initialization.process_command
            },
            'stop': {
                'user_phrases': self.stop.user_phrases,
                'tool_names': self.stop.tool_names,
            },
            'evaluation': {
                'groundtruth_workspace': self.evaluation.groundtruth_workspace,
                'evaluation_command': self.evaluation.evaluation_command
            },
            'meta': self.meta,
            'local_token_key_session': self.local_token_key_session
        }

    def ensure_directories(self):
        """Ensure all necessary directories exist."""
        # Create task root directory
        self.task_root_path.mkdir(parents=True, exist_ok=True)

        # Create agent workspace directory
        self.agent_workspace_path.mkdir(parents=True, exist_ok=True)

        # Ensure parent directory of log file exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def clean_workspace(self):
        """Clean the agent workspace (use with caution)."""
        import shutil
        if self.agent_workspace_path.exists():
            shutil.rmtree(self.agent_workspace_path)
        self.agent_workspace_path.mkdir(parents=True, exist_ok=True)

# Example usage
if __name__ == "__main__":
    pass