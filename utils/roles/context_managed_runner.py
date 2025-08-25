# context_managed_runner.py (更新版)
import json
from typing import Dict, Any, List, Union, Optional
from datetime import datetime
from pathlib import Path

from agents import Runner, RunConfig, RunHooks, Agent, RunResult
from agents.run_context import RunContextWrapper
from agents.items import (
    RunItem, TResponseInputItem, MessageOutputItem, 
    ToolCallItem, ToolCallOutputItem, ItemHelpers
)
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
from utils.api_model.model_provider import ContextTooLongError

class ContextManagedRunner(Runner):
    """支持上下文管理和历史记录的 Runner"""
    
    # 默认历史文件存储路径
    DEFAULT_HISTORY_DIR = Path("conversation_histories")
    
    @classmethod
    async def run(
        cls,
        starting_agent: Agent,
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        max_turns: int = 10,
        hooks: RunHooks | None = None,
        run_config: RunConfig | None = None,
        previous_response_id: str | None = None,
        history_dir: Union[str, Path, None] = None,  # 新增参数
        session_id: Optional[str] = None,  # 允许指定session_id
    ) -> RunResult:
        """重写 run 方法，添加上下文管理功能
        
        Args:
            history_dir: 历史文件存储目录，如果为None则使用默认目录
            session_id: 指定的会话ID，如果为None则自动生成
            ... 其他参数同父类
        """
        
        # 处理历史目录
        if history_dir is None:
            history_dir = cls.DEFAULT_HISTORY_DIR
        else:
            history_dir = Path(history_dir)
        
        # 确保目录存在
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成或使用提供的会话 ID
        if session_id is None:
            session_id = cls._generate_session_id()
        
        # 创建包装后的 context
        if context is None:
            context = {}
        
        # 初始化上下文元数据，包含历史目录信息
        wrapped_context = cls._init_context_metadata(context, session_id, history_dir)
        
        # 记录初始输入到历史
        # 不用记录,会在user那里处理
        # cls._save_initial_input_to_history(session_id, input, history_dir)

        # 调用父类的 run 方法
        result = await super().run(
            starting_agent=starting_agent,
            input=input,
            context=wrapped_context,
            max_turns=max_turns,
            hooks=hooks,
            run_config=run_config,
            previous_response_id=previous_response_id,
        )
        
        return result

    @classmethod
    def run_sync(
        cls,
        starting_agent: Agent,
        input: str | list[TResponseInputItem],
        *,
        context: Any = None,
        max_turns: int = 10,
        hooks: RunHooks | None = None,
        run_config: RunConfig | None = None,
        previous_response_id: str | None = None,
        history_dir: Union[str, Path, None] = None,  # 新增参数
        session_id: Optional[str] = None,  # 允许指定session_id
    ) -> RunResult:
        """同步版本的run方法，支持历史记录"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            cls.run(
                starting_agent=starting_agent,
                input=input,
                context=context,
                max_turns=max_turns,
                hooks=hooks,
                run_config=run_config,
                previous_response_id=previous_response_id,
                history_dir=history_dir,
                session_id=session_id,
            )
        )

    @classmethod
    def _init_context_metadata(cls, context: Any, session_id: str, history_dir: Path) -> Any:
        """初始化或更新上下文元数据"""
        # 如果 context 是 None，创建新的
        if context is None:
            context = {}
        
        # 检查是否已经初始化过
        if "_context_meta" in context:
            # 已经初始化，不要覆盖
            return context
        
        # 首次初始化
        metadata = {
            "session_id": session_id,
            "history_dir": str(history_dir),
            "started_at": datetime.now().isoformat(),
            "current_turn": 0,
            "total_turns_ever": 0,
            "turns_in_current_sequence": 0,
            "mini_turns_in_current_sequence": 0,
            "boundary_in_current_sequence": [],
            "truncated_turns": 0,
            "truncation_history": []
        }
        
        context["_session_id"] = session_id
        context["_history_dir"] = str(history_dir)
        context["_context_meta"] = metadata
        context["_context_limit"] = context.get("_context_limit", 128000)
        
        return context

    @classmethod
    async def _run_single_turn(cls, **kwargs):
        # print('----IN-----')
        """重写单轮执行，添加历史保存和截断检查"""
        
        # 获取 context_wrapper
        context_wrapper = kwargs.get('context_wrapper')
        original_input = kwargs.get('original_input')
        generated_items = kwargs.get('generated_items', [])
        agent = kwargs.get('agent')

        # context_wrapper.context 才是我们的数据存储位置
        ctx = context_wrapper.context if context_wrapper and hasattr(context_wrapper, 'context') else {}

        # 设置当前模型的上下文窗口信息
        if ctx and ("_context_limit" not in ctx or ctx["_context_limit"] is None):
            model_name = agent.model.model
            from utils.api_model.model_provider import API_MAPPINGS
            
            context_limit_found = False
            for key, mapping in API_MAPPINGS.items():
                if model_name == key:
                    ctx["_context_limit"] = mapping.context_window
                    context_limit_found = True
                    break
                # 或者检查是否在 api_model 映射中
                elif 'api_model' in mapping:
                    for provider, api_model_name in mapping.api_model.items():
                        if model_name == api_model_name:
                            ctx["_context_limit"] = mapping.context_window
                            context_limit_found = True
                            break
                    if context_limit_found:
                        break
            
            # # 如果没找到，设置默认值
            # if not context_limit_found:
            #     ctx["_context_limit"] = 128000
        # print("模型名称", model_name, "上下文窗口", ctx["_context_limit"])

        # 获取历史目录
        history_dir = Path(ctx.get("_history_dir", cls.DEFAULT_HISTORY_DIR))
        
        # 记录执行前的项目数，以便识别新增项
        items_before = len(generated_items)

        # 更新轮次信息
        # 获取和更新元数据
        meta = ctx.get("_context_meta", {})
        if "turns_in_current_sequence" not in meta:
            meta["turns_in_current_sequence"] = 0

        meta["current_turn"] = meta.get("current_turn", 0) + 1
        meta["total_turns_ever"] = meta.get("total_turns_ever", 0) + 1
        meta["turns_in_current_sequence"] = meta.get("turns_in_current_sequence", 0) + 1


        # 调用父类方法执行实际的单轮
        try:
            result = await super()._run_single_turn(**kwargs)
        except ContextTooLongError as e:
            # 标记需要强制重置上下文，并记录已执行的步数
            ctx["_force_reset_context"] = {
                "reason": str(e),
                "token_count": getattr(e, 'token_count', None),
                "max_tokens": getattr(e, 'max_tokens', None),
                "timestamp": datetime.now().isoformat(),
                "executed_mini_turns": meta.get("mini_turns_in_current_sequence", 0),  # 已执行的mini turns
                "executed_turns": meta.get("turns_in_current_sequence", 0)  # 已执行的turns
            }
            # 重新抛出，让上层处理
            raise


        meta["boundary_in_current_sequence"].append((meta["mini_turns_in_current_sequence"], 
                                                     meta["mini_turns_in_current_sequence"]+len(result.new_step_items)))
        # print("len(meta['boundary_in_current_sequence'])", len(meta["boundary_in_current_sequence"]))
        # print("meta['turns_in_current_sequence']", meta["turns_in_current_sequence"])
        
        assert len(meta["boundary_in_current_sequence"]) == meta["turns_in_current_sequence"], (
            f"boundary_in_current_sequence 长度与 turns_in_current_sequence 不一致: {len(meta['boundary_in_current_sequence'])} != {meta['turns_in_current_sequence']}, 其中boundary_in_current_sequence: {meta['boundary_in_current_sequence']}"
        )
        meta["mini_turns_in_current_sequence"] += len(result.new_step_items)

        # 更新累积的 usage 信息到 context
        if hasattr(context_wrapper, 'usage'):
            ctx["_cumulative_usage"] = {
                "total_tokens": context_wrapper.usage.total_tokens,
                "input_tokens": context_wrapper.usage.input_tokens,
                "output_tokens": context_wrapper.usage.output_tokens,
                "requests": context_wrapper.usage.requests
            }

        # 保存新增的项目到历史
        session_id = ctx.get("_session_id")
        # print("session_id", session_id, "len(generated_items)", len(generated_items), "items_before", items_before)
        # if session_id and len(generated_items) > items_before:
            # new_items = generated_items[items_before:]
        cls._save_items_to_history(
            session_id=session_id,
            turn_number=meta.get("current_turn", 0),
            items=result.new_step_items,
            agent_name=agent.name if agent else "unknown",
            history_dir=history_dir
        )
        
        # 检查待处理的截断请求
        pending_truncate = ctx.get("_pending_truncate")
        # print("pending_truncate", pending_truncate)

        # 获取全序列 items, 类型为list[TResponseInputItem]
        all_seq_items = ItemHelpers.input_to_new_input_list(original_input)
        all_seq_items.extend([generated_item.to_input_item() for generated_item in generated_items])

        # TODO: 现在相当于我们扔掉了pre_step_items和new_step_items，直接用all_seq_items
        # 但是这样会导致我们无法知道哪些是pre_step_items，哪些是new_step_items
        # 所以需要一个更好的方法来处理这个问题
        if pending_truncate:
            cls._handle_truncation(
                original_input=original_input,
                pre_step_items=result.pre_step_items,
                new_step_items=result.new_step_items,
                truncate_params=pending_truncate,
                context_wrapper=context_wrapper
            )
            # 清除标记
            ctx["_pending_truncate"] = None
            
            # # 更新turn_result
            # result.original_input = original_input
            # result.pre_step_items = []
            # result.new_step_items = ctx["_truncated_items"]
        # else:
        #     result.original_input = []
        #     result.pre_step_items = []
        #     result.new_step_items = all_seq_items.copy()
        
        # # 更新统计信息
        # cls._update_context_stats(context_wrapper, generated_items)
        
        # print("result.next_step", result.next_step)
        # print('----OUT-----')
        
        return result
    
    @classmethod
    def _handle_truncation(
        cls,
        original_input: List[TResponseInputItem],
        pre_step_items: List[RunItem],
        new_step_items: List[RunItem],
        truncate_params: Dict[str, Any],
        context_wrapper: RunContextWrapper
    ):
        """处理截断请求"""
        method = truncate_params.get("method")
        value = truncate_params.get("value")
        preserve_system = truncate_params.get("preserve_system", True)
        
        ctx = context_wrapper.context if context_wrapper else {}
        meta = ctx.get("_context_meta", {})
        
        # 找到所有轮次的边界
        turn_boundaries = ctx["_context_meta"]["boundary_in_current_sequence"]
        total_turns = len(turn_boundaries)
        
        # 验证轮次数量与 turns_in_current_sequence 的一致性
        current_turns_in_sequence = meta.get("turns_in_current_sequence", 0)
        assert total_turns == current_turns_in_sequence, (
            f"轮次边界数量 ({total_turns}) 与 turns_in_current_sequence ({current_turns_in_sequence}) 不一致"
        )
        
        if total_turns == 0:
            return  # 没有可截断的内容
        
        # 根据不同策略执行截断
        keep_turns = total_turns  # 默认保留所有
        
        if method == "keep_recent_turns":
            keep_turns = min(int(value), total_turns)
        elif method == "keep_recent_percent":
            keep_turns = max(1, int(total_turns * value / 100))
        elif method == "delete_first_turns":
            keep_turns = max(1, total_turns - int(value))
        elif method == "delete_first_percent":
            delete_turns = int(total_turns * value / 100)
            keep_turns = max(1, total_turns - delete_turns)
        
        # 执行截断
        if keep_turns < total_turns:
            print("keep_turns < total_turns, 执行截断")
            
            # 计算需要删除的轮次数量
            delete_turns = total_turns - keep_turns
            
            # 从前到后删除，按照 original_input -> pre_step_items -> new_step_items 的顺序
            deleted_items_count = cls._truncate_sequential_lists(
                original_input, pre_step_items, new_step_items, 
                turn_boundaries, delete_turns, preserve_system
            )
            
            if deleted_items_count > 0:
                meta["turns_in_current_sequence"] = keep_turns
                meta["truncated_turns"] = meta.get("truncated_turns", 0) + delete_turns
                meta["truncation_history"].append({
                    "at_turn": meta["current_turn"],
                    "method": method,
                    "value": value,
                    "deleted_items": deleted_items_count,
                    "deleted_turns": delete_turns,
                    "timestamp": datetime.now().isoformat()
                })
                ctx["_context_truncated"] = True
                
                # 更新 mini_turns_in_current_sequence
                meta["mini_turns_in_current_sequence"] = len(original_input) + len(pre_step_items) + len(new_step_items)
                
                # 更新边界信息，需要减去删除的项目数量
                meta["boundary_in_current_sequence"] = [
                    (start - deleted_items_count, end - deleted_items_count)
                    for start, end in turn_boundaries[-keep_turns:]
                ]
    
    @classmethod
    def _find_turn_boundaries(cls, items: List[TResponseInputItem]) -> List[tuple[int, int]]:
        """找到每轮对话的边界 [(start_idx, end_idx), ...]
        
        轮次定义：user 或 assistant 消息开始新的一轮，tools 跟随其对应的 assistant
        """
        boundaries = []
        # TODO: implement this
        
        return boundaries
    
    @classmethod
    def _truncate_sequential_lists(
        cls,
        original_input: List[TResponseInputItem],
        pre_step_items: List[RunItem],
        new_step_items: List[RunItem],
        boundaries: List[tuple[int, int]],
        delete_turns: int,
        preserve_system: bool
    ) -> int:
        """按照顺序截断三个列表，从前到后删除指定轮次的项目"""
        if delete_turns <= 0:
            return 0
        
        # 计算要删除的起始位置
        delete_from_boundary = boundaries[delete_turns - 1]
        delete_from_idx = delete_from_boundary[1]
        
        # 简单地从前往后删除
        deleted_count = 0
        
        # 先删除 original_input
        if delete_from_idx <= len(original_input):
            # 删除 original_input 中的项目
            original_input[:] = original_input[delete_from_idx:]
            deleted_count = delete_from_idx
        else:
            # original_input 全部删除
            deleted_count = len(original_input)
            original_input.clear()
            # 继续删除 pre_step_items
            remaining_delete = delete_from_idx - deleted_count
            if remaining_delete <= len(pre_step_items):
                pre_step_items[:] = pre_step_items[remaining_delete:]
                deleted_count += remaining_delete
            else:
                # pre_step_items 全部删除
                deleted_count += len(pre_step_items)
                pre_step_items.clear()
                # 继续删除 new_step_items
                remaining_delete = delete_from_idx - deleted_count
                if remaining_delete <= len(new_step_items):
                    new_step_items[:] = new_step_items[remaining_delete:]
                    deleted_count += remaining_delete
                else:
                    # new_step_items 全部删除
                    new_step_items.clear()
                    deleted_count = delete_from_idx
        
        return deleted_count
    
    @classmethod
    def _create_truncation_notice(cls, method: str, value: Any, deleted_items: int, deleted_turns: int) -> MessageOutputItem:
        """创建截断通知的系统消息"""
        content = f"[上下文管理] 由于token限制，已使用 {method}({value}) 策略进行截断。删除了 {deleted_items} 条消息（约 {deleted_turns} 轮对话）。"
        
        # 创建一个系统消息
        raw_message = ResponseOutputMessage(
            id="system_truncation",
            content=[ResponseOutputText(
                text=content,
                type="output_text",
                annotations=[]
            )],
            role="system",
            type="message",
            status="completed"
        )
        
        # 需要一个 agent，这里我们用一个占位符
        # 实际使用时可能需要从 context 获取当前 agent
        from agents import Agent
        placeholder_agent = Agent(name="system", model="gpt-4")
        
        return MessageOutputItem(
            agent=placeholder_agent,
            raw_item=raw_message
        )
    
    @classmethod
    def _save_items_to_history(
        cls,
        session_id: str,
        turn_number: int,
        items: List[RunItem],
        agent_name: str,
        history_dir: Path
    ):
        """保存项目到历史文件"""
        history_path = history_dir / f"{session_id}_history.jsonl"
        # 保证目录存在
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        # print("进入_save_items_to_history")
        with open(history_path, 'a', encoding='utf-8') as f:
            for step_idx, item in enumerate(items):
                # print("保存item")
                record = {
                    "in_turn_steps": step_idx,  # 在当前轮次中的步骤顺序
                    "turn": turn_number,
                    "timestamp": datetime.now().isoformat(),
                    "agent": agent_name,
                    "item_type": item.type,
                    "raw_content": item.raw_item.model_dump() if hasattr(item.raw_item, 'model_dump') else item.raw_item
                }
                
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    @classmethod
    def _save_initial_input_to_history(cls, 
                                       session_id: str, 
                                       input: Union[str, List[TResponseInputItem]], 
                                       history_dir: Path,
                                       turn_number: int = 0):
        """保存初始输入到历史"""
        history_path = history_dir / f"{session_id}_history.jsonl"
        # 保证目录存在
        history_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查是否已经有初始输入记录
        if history_path.exists():
            with open(history_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if record.get("type") == "initial_input":
                            return  # 已经存在，不重复写入
                    except json.JSONDecodeError:
                        continue

        with open(history_path, 'a', encoding='utf-8') as f:
            record = {
                "in_turn_steps": 0,  # 初始输入总是第一步
                "turn": turn_number,
                "timestamp": datetime.now().isoformat(),
                "type": "initial_input",
                "content": input if isinstance(input, str) else [item.model_dump() for item in input]
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')


    @classmethod
    def _save_user_input_to_history(cls, session_id: str, user_input: Union[str, TResponseInputItem], history_dir: Path, turn_number: int):
        """保存用户输入到历史"""
        history_path = Path(history_dir) / f"{session_id}_history.jsonl"
        # 保证目录存在
        history_path.parent.mkdir(parents=True, exist_ok=True)

        with open(history_path, 'a', encoding='utf-8') as f:
            record = {
                "in_turn_steps": 0,  # 用户输入在当前轮次中是第一步
                "turn": turn_number,
                "timestamp": datetime.now().isoformat(),
                "type": "user_input",
                "content": user_input if isinstance(user_input, str) else [item.model_dump() for item in user_input]
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    @classmethod
    def _generate_session_id(cls) -> str:
        """生成唯一的会话 ID"""
        from uuid import uuid4
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"


    @classmethod
    def get_formatted_history(cls, history_dir: Union[str, Path], session_id: str) -> List[Dict[str, Any]]:
        """获取格式化的历史记录，用于保存到日志
        
        Returns:
            格式化后的消息列表，适合保存到日志文件
        """
        history_file = Path(history_dir) / f"{session_id}_history.jsonl"
        
        if not history_file.exists():
            return []
        
        formatted_messages = []
        
        # 按轮次和步骤顺序读取所有记录
        records = []
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        # 按轮次和步骤排序
        records.sort(key=lambda x: (x.get("turn", 0), x.get("in_turn_steps", 0)))
        
        # 处理每个轮次的记录
        current_turn = -1
        current_turn_records = []
        
        for record in records:
            # 跳过初始输入记录
            if record.get("type") == "initial_input":
                continue
                
            turn = record.get("turn", 0)
            
            # 如果轮次变化，处理上一轮次的记录
            if turn != current_turn and current_turn_records:
                formatted_messages.extend(cls._process_turn_records(current_turn_records))
                current_turn_records = []
            
            current_turn = turn
            current_turn_records.append(record)
        
        # 处理最后一轮次的记录
        if current_turn_records:
            formatted_messages.extend(cls._process_turn_records(current_turn_records))
        
        return formatted_messages
    
    @classmethod
    def _process_turn_records(cls, records: List[Dict]) -> List[Dict]:
        """处理单个轮次的记录，返回格式化的消息列表"""
        formatted_messages = []
        item_index = 0
        
        while item_index < len(records):
            current_record = records[item_index]
            
            if current_record.get("type") == "user_input":
                # 用户输入
                content = current_record.get("content", "")
                if isinstance(content, list):
                    # 如果是列表格式，提取文本内容
                    content_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            content_parts.append(item.get("text", ""))
                    content = " ".join(content_parts)
                
                formatted_messages.append({
                    "role": "user",
                    "content": content
                })
                item_index += 1
                
            elif current_record.get("item_type") == "message_output_item":
                raw_content = current_record.get("raw_content", {})
                role = "unknown"
                content = ""
                
                if isinstance(raw_content, dict):
                    role = raw_content.get("role", "unknown")
                    # 提取文本内容
                    content_parts = []
                    for content_item in raw_content.get("content", []):
                        if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                            content_parts.append(content_item.get("text", ""))
                    content = " ".join(content_parts)
                
                if role == "system" and "上下文管理" in content:
                    # 跳过上下文管理的系统消息
                    item_index += 1
                    continue
                
                # 检查是否是最后一条消息（没有后续的工具调用）
                if item_index == len(records) - 1:
                    # 最后一条消息，为assistant的最终回复
                    formatted_messages.append({
                        "role": role,
                        "content": content
                    })
                    item_index += 1
                else:
                    # 不是最后一条消息，检查是否有工具调用
                    tool_calls = []
                    next_index = item_index + 1
                    
                    # 收集后续的工具调用
                    while next_index < len(records) and records[next_index].get("item_type") == "tool_call_item":
                        tool_record = records[next_index]
                        raw_content = tool_record.get("raw_content", {})
                        tool_call = {
                            "id": raw_content.get("call_id", "unknown") if isinstance(raw_content, dict) else "unknown",
                            "type": "function",
                            "function": {
                                "name": raw_content.get("name", "unknown") if isinstance(raw_content, dict) else "unknown",
                                "arguments": raw_content.get("arguments", "{}") if isinstance(raw_content, dict) else "{}"
                            }
                        }
                        tool_calls.append(tool_call)
                        next_index += 1
                    
                    if tool_calls:
                        # 有工具调用的assistant消息
                        formatted_messages.append({
                            "role": role,
                            "content": content,
                            "tool_calls": tool_calls
                        })
                        item_index = next_index
                    else:
                        # 没有工具调用的普通消息
                        formatted_messages.append({
                            "role": role,
                            "content": content
                        })
                        item_index += 1
                        
            elif current_record.get("item_type") == "tool_call_item":
                # 不带content的tool_call调用
                tool_calls = []
                next_index = item_index
                
                # 收集连续的工具调用
                while next_index < len(records) and records[next_index].get("item_type") == "tool_call_item":
                    tool_record = records[next_index]
                    raw_content = tool_record.get("raw_content", {})
                    tool_call = {
                        "id": raw_content.get("call_id", "unknown") if isinstance(raw_content, dict) else "unknown",
                        "type": "function",
                        "function": {
                            "name": raw_content.get("name", "unknown") if isinstance(raw_content, dict) else "unknown",
                            "arguments": raw_content.get("arguments", "{}") if isinstance(raw_content, dict) else "{}"
                        }
                    }
                    tool_calls.append(tool_call)
                    next_index += 1
                
                # 创建没有content的assistant消息
                formatted_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls
                })
                item_index = next_index
                
            elif current_record.get("item_type") == "tool_call_output_item":
                # tool执行结果
                raw_content = current_record.get("raw_content", {})
                formatted_messages.append({
                    "role": "tool",
                    "content": raw_content.get("output", "") if isinstance(raw_content, dict) else "",
                    "tool_call_id": raw_content.get("call_id", "unknown") if isinstance(raw_content, dict) else "unknown"
                })
                item_index += 1
                
            else:
                # 其他类型的记录，跳过
                item_index += 1
        
        return formatted_messages

    @classmethod
    def get_recent_turns_summary(cls, history_dir: Union[str, Path], session_id: str, num_turns: int = 5) -> str:
        """获取最近N轮交互的简化摘要，用于上下文重置时的临时记忆
        
        Args:
            history_dir: 历史文件目录
            session_id: 会话ID
            num_turns: 要获取的轮次数量
            
        Returns:
            格式化的历史摘要字符串
        """
        history_file = Path(history_dir) / f"{session_id}_history.jsonl"
        
        if not history_file.exists():
            return "No history"
        
        # 读取并按轮次整理记录
        records = []
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue
        
        # 按轮次和步骤排序
        records.sort(key=lambda x: (x.get("turn", 0), x.get("in_turn_steps", 0)))
        
        # 按轮次分组
        turns_data = {}
        for record in records:
            turn_num = record.get("turn", 0)
            if turn_num not in turns_data:
                turns_data[turn_num] = []
            turns_data[turn_num].append(record)
        
        # 获取最近的轮次
        recent_turn_nums = sorted(turns_data.keys())[-num_turns:] if len(turns_data) > num_turns else sorted(turns_data.keys())
        
        if not recent_turn_nums:
            return "No recent turns"
        
        summary_lines = []
        summary_lines.append(f"=== Overview of recent {len(recent_turn_nums)} turns of interaction history ===")
        
        for turn_num in recent_turn_nums:
            turn_records = turns_data[turn_num]
            summary_lines.append(f"\nTurn#{turn_num}:")
            
            for record in turn_records:
                if record.get("type") == "user_input":
                    # 用户输入
                    content = record.get("content", "")
                    if isinstance(content, list):
                        # 处理列表格式的内容
                        content_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                content_parts.append(item.get("text", ""))
                        content = " ".join(content_parts)
                    
                    formatted_content = cls._format_multiline_content(content, max_length=500)
                    summary_lines.append(f"  User:")
                    summary_lines.append(f"    {formatted_content}")
                    
                elif record.get("item_type") == "message_output_item":
                    # Agent响应
                    raw_content = record.get("raw_content", {})
                    role = raw_content.get("role", "unknown")
                    
                    if role == "assistant":
                        # 提取文本内容
                        content_parts = []
                        for content_item in raw_content.get("content", []):
                            if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                content_parts.append(content_item.get("text", ""))
                        content = " ".join(content_parts)
                        
                        if content.strip():  # 只有非空内容才显示
                            formatted_content = cls._format_multiline_content(content, max_length=500)
                            summary_lines.append(f"  Assistant:")
                            summary_lines.append(f"    {formatted_content}")
                
                elif record.get("item_type") == "tool_call_item":
                    # 工具调用
                    raw_content = record.get("raw_content", {})
                    if isinstance(raw_content, dict):
                        tool_name = raw_content.get("name", "unknown")
                        call_id = raw_content.get("call_id", "unknown")
                        arguments = raw_content.get("arguments", "{}")
                        
                        # 格式化参数（处理多行内容）
                        formatted_args = cls._format_multiline_content(arguments, max_length=300)
                        summary_lines.append(f"  Tool Call: {tool_name}")
                        summary_lines.append(f"    ID: {call_id}")
                        summary_lines.append(f"    Args: {formatted_args}")
                    else:
                        summary_lines.append(f"  Tool Call: unknown")
                    
                elif record.get("item_type") == "tool_call_output_item":
                    # 工具执行结果
                    raw_content = record.get("raw_content", {})
                    if isinstance(raw_content, dict):
                        call_id = raw_content.get("call_id", "unknown")
                        output = raw_content.get("output", "")
                        if output.strip():
                            formatted_output = cls._format_multiline_content(output, max_length=400)
                            summary_lines.append(f"  Tool Result (ID: {call_id}):")
                            summary_lines.append(f"    {formatted_output}")
                    else:
                        summary_lines.append(f"  Tool Result: unknown")
        
        summary_lines.append("\nNote: This is a simplified overview. Please use the history record search tool to view the complete content and search infomation in it.")
        return "\n".join(summary_lines)
    
    @classmethod
    def _format_multiline_content(cls, content: str, max_length: int = 500) -> str:
        """格式化多行内容，处理换行符和长度限制
        
        Args:
            content: 原始内容
            max_length: 最大长度限制
            
        Returns:
            格式化后的内容字符串
        """
        if not content:
            return "[No content]"
        
        content = content.strip()
        
        # 如果内容不长，直接返回（保持原有的换行）
        if len(content) <= max_length:
            # 将换行符替换为换行加缩进，保持格式
            lines = content.split('\n')
            if len(lines) <= 1:
                return content
            else:
                # 多行内容，每行添加适当缩进
                formatted_lines = [lines[0]]  # 第一行不需要额外缩进
                for line in lines[1:]:
                    formatted_lines.append(f"    {line}")
                return '\n'.join(formatted_lines)
        
        # 内容过长，需要截断
        # 先尝试按行截断
        lines = content.split('\n')
        if len(lines) > 1:
            # 多行内容，逐行累积直到超过限制
            accumulated = []
            current_length = 0
            
            for line in lines:
                if current_length + len(line) + 1 <= max_length - 20:  # 留出省略号和提示的空间
                    accumulated.append(line)
                    current_length += len(line) + 1  # +1 for newline
                else:
                    break
            
            if accumulated:
                result_lines = [accumulated[0]]
                for line in accumulated[1:]:
                    result_lines.append(f"    {line}")
                
                if len(accumulated) < len(lines):
                    result_lines.append(f"    ... (truncated, total {len(lines)} lines, {len(content)} chars)")
                
                return '\n'.join(result_lines)
        
        # 单行内容或多行截断失败，使用原有的截断逻辑
        half_length = (max_length - 20) // 2  # 留出省略号和提示的空间
        truncated = content[:half_length] + " ... " + content[-half_length:]
        return f"{truncated}\n    (truncated from {len(content)} chars)"

    @classmethod
    def _format_content_with_truncation(cls, content: str, max_length: int = 500) -> str:
        """格式化内容，超过限制时进行截断
        
        Args:
            content: 原始内容
            max_length: 最大长度限制
            
        Returns:
            格式化后的内容字符串
        """
        if not content:
            return "[No content]"
        
        content = content.strip()
        if len(content) <= max_length:
            return content
        
        # 截断逻辑：前250字符 + ... + 后250字符
        half_length = (max_length - 5) // 2  # 减去 " ... " 的5个字符
        truncated = content[:half_length] + " ... " + content[-half_length:]
        return f"(actual length: {len(content)} chars, truncated to {max_length} chars) {truncated} "

    @classmethod
    def get_session_stats(cls, history_dir: Union[str, Path], session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        history_file = Path(history_dir) / f"{session_id}_history.jsonl"
        
        if not history_file.exists():
            return {}
        
        stats = {
            "total_turns": 0,
            "total_messages": 0,
            "tool_calls": 0,
            "truncations": 0,
            "user_input_turns": 0,
            "assistant_turns": 0, # 一次返回+执行其中所有工具为一个assistant轮
        }
        
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    stats["total_messages"] += 1
                    
                    if record.get("type") == "user_input":
                        stats["user_input_turns"] += 1
                    if record.get("item_type") == "message_output_item":
                        pass
                    elif record.get("item_type") == "tool_call_item":
                        stats["tool_calls"] += 1
                        
                except json.JSONDecodeError:
                    continue
            # stats["total_turns"] 为最后一个line的 "turn" 字段 + 1
            stats["total_turns"] = record.get("turn", 0)+1 # 包括用户输入,并考虑从0计数的问题
            stats["assistant_turns"] = record.get("turn", 0)+1 - stats["user_input_turns"]
            
        
        return stats