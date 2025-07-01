import asyncio
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass, field

from utils.general.base_models import Message, MessageRole, CostReport
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from utils.data_structures.user_config import UserConfig

import random

logger = logging.getLogger(__name__)

@dataclass
class UserRuntimeConfig:
    """用户配置"""
    global_config: UserConfig

    starting_system_prompt: str
    user_id: Optional[str] = None
    max_history: int = 50

    metadata: Optional[Dict[str, Any]] = None
    track_costs: bool = True  # 是否追踪成本

@dataclass
class UserCostTracker:
    """用户成本追踪器"""
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cost_history: List[CostReport] = field(default_factory=list)
    cost_by_model: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def add_cost_report(self, report: CostReport):
        """添加成本报告"""
        self.total_cost += report.total_cost
        self.total_input_tokens += report.input_tokens
        self.total_output_tokens += report.output_tokens
        self.cost_history.append(report)
        
        # 按模型统计
        model = report.model
        if model not in self.cost_by_model:
            self.cost_by_model[model] = {
                "cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "count": 0
            }
        
        self.cost_by_model[model]["cost"] += report.total_cost
        self.cost_by_model[model]["input_tokens"] += report.input_tokens
        self.cost_by_model[model]["output_tokens"] += report.output_tokens
        self.cost_by_model[model]["count"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取成本摘要"""
        return {
            "total_cost": round(self.total_cost,4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_requests": len(self.cost_history),
            "average_cost_per_request": self.total_cost / len(self.cost_history) if self.cost_history else 0,
            "by_model": self.cost_by_model
        }

class User:
    """LLM 模拟的用户类，带成本追踪"""
    
    def __init__(
        self, 
        client: AsyncOpenAIClientWithRetry,
        user_config: UserRuntimeConfig
    ):
        """
        初始化用户
        
        Args:
            client: 外部传入的 OpenAI 客户端，用于共享并发控制
            user_config: 用户配置
        """
        self.client = client
        self.config = user_config
        self.user_id = user_config.user_id or self._generate_user_id()
        
        # 初始化对话历史
        self.conversation_history: List[Message] = []
        
        # 添加系统提示
        if self.config.starting_system_prompt:
            self._add_system_prompt(self.config.starting_system_prompt)
            logger.info(f"Created user {self.user_id} with system prompt: {self.config.starting_system_prompt[:50]}...")
        
        # 用户状态
        self.is_initialized = False
        self.interaction_count = 0
        self.total_tokens_used = 0
        self.created_at = datetime.now()
        self.last_interaction_at = None
        
        # 成本追踪
        self.cost_tracker = UserCostTracker() if self.config.track_costs else None
        
        
    
    def _generate_user_id(self) -> str:
        """生成用户ID"""
        import uuid
        return f"user_{uuid.uuid4().hex[:8]}"
    
    def _add_system_prompt(self, prompt: str):
        """添加系统提示到对话历史"""
        system_message = Message.system(
            content=prompt,
            metadata={
                "user_id": self.user_id,
            }
        )
        self.conversation_history.append(system_message)
    
    def _add_to_history(self, message: Message):
        """添加消息到对话历史，并管理历史长度"""
        message.update_metadata({
            "user_id": self.user_id,
            "interaction_count": self.interaction_count
        })
        
        self.conversation_history.append(message)
        
        # 保持系统消息并限制历史长度
        if len(self.conversation_history) > self.config.max_history:
            # 保留第一条系统消息
            system_messages = [msg for msg in self.conversation_history if msg.role == MessageRole.SYSTEM]
            other_messages = [msg for msg in self.conversation_history if msg.role != MessageRole.SYSTEM]
            
            # 保留系统消息和最近的消息
            keep_count = self.config.max_history - len(system_messages)
            self.conversation_history = system_messages + other_messages[-keep_count:]
    
    def receive_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        接收外部消息并添加到对话历史
        
        Args:
            content: 消息内容
            metadata: 可选的元数据
        """
        user_message = Message.user(
            content=content,
            metadata=metadata or {}
        )
        
        self._add_to_history(user_message)
        logger.debug(f"User {self.user_id} received message: {content[:50]}...")
    
    def initialize_conversation(self) -> None:
        """
        初始化对话
        如果当前只有系统提示，添加一个初始用户消息
        """
        # 检查是否只有系统消息
        non_system_messages = [msg for msg in self.conversation_history if msg.role != MessageRole.SYSTEM]
        
        if not non_system_messages and not self.is_initialized:
            initial_message = Message.user(
                content=random.choice(["Hi, what can I help you today?",
                                       "您好，请问有什么我可以帮助您的吗？"]),
                metadata={
                    "message_type": "initialization",
                    "auto_generated": True
                }
            )
            
            self._add_to_history(initial_message)
            self.is_initialized = True
            logger.info(f"User {self.user_id} initialized with greeting message")
    
    async def interact(self, **kwargs) -> str:
        """
        基于当前对话历史生成响应
        
        Args:
            **kwargs: 传递给 chat_completion 的额外参数
        
        Returns:
            生成的响应内容
        """
        # 确保对话已初始化
        if not self.is_initialized and len(self.conversation_history) <= 1:
            self.initialize_conversation()
        
        # 准备消息列表
        messages = self._prepare_messages_for_api()
        
        # 合并配置参数
        request_params = {
            "temperature": self.config.global_config.generation.temperature,
            "max_tokens": self.config.global_config.generation.max_tokens,
            "top_p": self.config.global_config.generation.top_p,
        }
        if self.config.global_config.model.short_name:
            request_params["model"] = self.config.global_config.model.short_name
        
        # 覆盖任何传入的参数
        request_params.update(kwargs)
        
        # 如果需要追踪成本，强制返回成本信息
        if self.config.track_costs and self.cost_tracker is not None:
            request_params["return_cost"] = True
        
        try:
            # 调用 API
            self.last_interaction_at = datetime.now()
            
            if request_params.get("return_cost", False):
                response, cost_report = await self.client.chat_completion(
                    messages,
                    **request_params
                )
                # 更新成本追踪
                if cost_report and self.cost_tracker:
                    self.cost_tracker.add_cost_report(cost_report)
                    self.total_tokens_used += cost_report.input_tokens + cost_report.output_tokens
                    
                    logger.debug(
                        f"User {self.user_id} interaction cost: "
                        f"${cost_report.total_cost:.4f} "
                        f"(in: {cost_report.input_tokens}, out: {cost_report.output_tokens})"
                    )
            else:
                response = await self.client.chat_completion(
                    messages,
                    **request_params
                )
            
            # 创建助手消息并添加到历史
            assistant_message = Message.assistant(
                content=response,
                metadata={
                    "generation_params": request_params,
                    "generated_at": datetime.now().isoformat()
                }
            )
            
            self._add_to_history(assistant_message)
            self.interaction_count += 1
            
            logger.info(
                f"User {self.user_id} completed interaction #{self.interaction_count}"
                + (f" (total cost: ${self.get_total_cost():.4f})" if self.cost_tracker else "")
            )
            
            return response
            
        except Exception as e:
            logger.error(f"User {self.user_id} interaction failed: {e}")
            raise
    
    def _prepare_messages_for_api(self) -> List[Dict[str, Any]]:
        """准备用于 API 调用的消息列表"""
        return [msg.to_api_dict() for msg in self.conversation_history]
    
    def get_total_cost(self) -> float:
        """获取总成本"""
        return self.cost_tracker.total_cost if self.cost_tracker else 0.0
    
    def get_cost_summary(self, detailed=False) -> Dict[str, Any]:
        """获取详细的成本摘要"""
        if not self.cost_tracker:
            return {
                "tracking_enabled": False,
                "total_cost": 0.0,
                "message": "Cost tracking is disabled for this user"
            }
        
        summary = self.cost_tracker.get_summary()
        if not detailed:
            summary.pop("average_cost_per_request")
            summary.pop("by_model")
            return summary
        
        summary["tracking_enabled"] = True
        summary["user_id"] = self.user_id
        summary["interaction_count"] = self.interaction_count
        
        # 添加每次交互的平均成本
        if self.interaction_count > 0:
            summary["average_cost_per_interaction"] = self.cost_tracker.total_cost / self.interaction_count
        
        return summary
    
    def get_cost_history(self) -> List[CostReport]:
        """获取成本历史记录"""
        return self.cost_tracker.cost_history if self.cost_tracker else []
    
    def clear_history(self, keep_system: bool = True) -> None:
        """
        清除对话历史
        
        Args:
            keep_system: 是否保留系统消息
        """
        if keep_system:
            self.conversation_history = [
                msg for msg in self.conversation_history 
                if msg.role == MessageRole.SYSTEM
            ]
        else:
            self.conversation_history = []
        
        self.is_initialized = False
        self.interaction_count = 0
        logger.info(f"User {self.user_id} history cleared (keep_system={keep_system})")
    
    def get_conversation_history(self) -> List[Message]:
        """获取完整的对话历史"""
        return self.conversation_history.copy()
    
    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        return self.conversation_history[-1] if self.conversation_history else None
    
    def get_last_user_message(self) -> Optional[Message]:
        """获取最后一条用户消息"""
        for msg in reversed(self.conversation_history):
            if msg.role == MessageRole.USER:
                return msg
        return None
    
    def get_last_assistant_message(self) -> Optional[Message]:
        """获取最后一条助手消息"""
        for msg in reversed(self.conversation_history):
            if msg.role == MessageRole.ASSISTANT:
                return msg
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息（包含成本）"""
        message_counts = {
            "system": 0,
            "user": 0,
            "assistant": 0,
            "total": len(self.conversation_history)
        }
        
        for msg in self.conversation_history:
            message_counts[msg.role.value] += 1
        
        stats = {
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_interaction_at": self.last_interaction_at.isoformat() if self.last_interaction_at else None,
            "interaction_count": self.interaction_count,
            "total_tokens_used": self.total_tokens_used,
            "message_counts": message_counts,
            "is_initialized": self.is_initialized,
            "config": {
                "max_history": self.config.max_history,
                "temperature": self.config.global_config.generation.temperature,
                "model": self.config.global_config.model.short_name,
                "track_costs": self.config.track_costs
            }
        }
        
        # 添加成本信息
        if self.cost_tracker:
            stats["cost_summary"] = self.get_cost_summary()
        
        return stats

    def get_state(self) -> Dict:
        """获取当前状态用于保存"""
        return {
            'conversation_history': self.conversation_history.copy(),
            # 添加其他需要保存的状态
        }
    
    def set_state(self, state: Dict) -> None:
        """从保存的状态恢复"""
        self.conversation_history = state.get('conversation_history', [])
        # 恢复其他状态

    def export_conversation(self, format: str = "json", include_costs: bool = True) -> Union[str, List[Dict[str, Any]]]:
        """
        导出对话历史
        
        Args:
            format: 导出格式，支持 'json' 或 'list'
            include_costs: 是否包含成本信息
        
        Returns:
            导出的对话数据
        """
        if format == "list":
            return self._prepare_messages_for_api()
        
        elif format == "json":
            import json
            export_data = {
                "user_id": self.user_id,
                "created_at": self.created_at.isoformat(),
                "interaction_count": self.interaction_count,
                "config": {
                    "starting_system_prompt": self.config.starting_system_prompt,
                    "temperature": self.config.global_config.generation.temperature,
                    "model": self.config.global_config.model.short_name,
                    "track_costs": self.config.track_costs
                },
                "messages": self._prepare_messages_for_api()
            }
            
            # 添加成本信息
            if include_costs and self.cost_tracker:
                export_data["cost_summary"] = self.get_cost_summary()
                export_data["cost_history"] = [
                    report.model_dump() for report in self.cost_tracker.cost_history
                ]
            
            return json.dumps(export_data, ensure_ascii=False, indent=2)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def __repr__(self) -> str:
        cost_str = f", cost=${self.get_total_cost():.4f}" if self.cost_tracker else ""
        return (f"User(id={self.user_id}, "
                f"interactions={self.interaction_count}, "
                f"messages={len(self.conversation_history)}"
                f"{cost_str})")
    
    def __str__(self) -> str:
        cost_str = f" (${self.get_total_cost():.4f})" if self.cost_tracker else ""
        return f"User {self.user_id}{cost_str}"

# 成本分析工具
class CostAnalyzer:
    """分析用户群体的成本"""
    
    def __init__(self, users: List[User]):
        self.users = users
    
    def get_total_cost(self) -> float:
        """获取所有用户的总成本"""
        return sum(user.get_total_cost() for user in self.users)
    
    def get_cost_by_user(self) -> Dict[str, float]:
        """获取每个用户的成本"""
        return {user.user_id: user.get_total_cost() for user in self.users}
    
    def get_cost_by_model(self) -> Dict[str, Dict[str, Any]]:
        """按模型汇总成本"""
        model_costs = {}
        
        for user in self.users:
            if user.cost_tracker:
                for model, stats in user.cost_tracker.cost_by_model.items():
                    if model not in model_costs:
                        model_costs[model] = {
                            "total_cost": 0,
                            "total_input_tokens": 0,
                            "total_output_tokens": 0,
                            "request_count": 0,
                            "user_count": 0
                        }
                    
                    model_costs[model]["total_cost"] += stats["cost"]
                    model_costs[model]["total_input_tokens"] += stats["input_tokens"]
                    model_costs[model]["total_output_tokens"] += stats["output_tokens"]
                    model_costs[model]["request_count"] += stats["count"]
                    model_costs[model]["user_count"] += 1
        
        return model_costs
    
    def get_top_spenders(self, n: int = 10) -> List[Tuple[str, float]]:
        """获取花费最多的用户"""
        user_costs = [(user.user_id, user.get_total_cost()) for user in self.users]
        user_costs.sort(key=lambda x: x[1], reverse=True)
        return user_costs[:n]
    
    def get_cost_statistics(self) -> Dict[str, Any]:
        """获取成本统计信息"""
        costs = [user.get_total_cost() for user in self.users]
        
        if not costs:
            return {
                "user_count": 0,
                "total_cost": 0,
                "average_cost": 0,
                "min_cost": 0,
                "max_cost": 0,
                "median_cost": 0
            }
        
        import statistics
        
        return {
            "user_count": len(costs),
            "total_cost": sum(costs),
            "average_cost": statistics.mean(costs),
            "min_cost": min(costs),
            "max_cost": max(costs),
            "median_cost": statistics.median(costs),
            "std_dev": statistics.stdev(costs) if len(costs) > 1 else 0
        }
    
    def generate_cost_report(self, output_file: Optional[str] = None) -> str:
        """生成成本报告"""
        report = []
        report.append("=== User Cost Analysis Report ===\n")
        
        # 总体统计
        stats = self.get_cost_statistics()
        report.append("Overall Statistics:")
        report.append(f"  Total Users: {stats['user_count']}")
        report.append(f"  Total Cost: ${stats['total_cost']:.4f}")
        report.append(f"  Average Cost per User: ${stats['average_cost']:.4f}")
        report.append(f"  Cost Range: ${stats['min_cost']:.4f} - ${stats['max_cost']:.4f}")
        report.append(f"  Median Cost: ${stats['median_cost']:.4f}")
        report.append(f"  Standard Deviation: ${stats['std_dev']:.4f}")
        report.append("")
        
        # 按模型统计
        model_costs = self.get_cost_by_model()
        if model_costs:
            report.append("Cost by Model:")
            for model, stats in model_costs.items():
                report.append(f"  {model}:")
                report.append(f"    Total Cost: ${stats['total_cost']:.4f}")
                report.append(f"    Requests: {stats['request_count']}")
                report.append(f"    Users: {stats['user_count']}")
                report.append(f"    Avg Cost per Request: ${stats['total_cost']/stats['request_count']:.4f}")
            report.append("")
        
        # Top花费用户
        top_spenders = self.get_top_spenders(5)
        report.append("Top 5 Spenders:")
        for user_id, cost in top_spenders:
            report.append(f"  {user_id}: ${cost:.4f}")
        report.append("")
        
        # 详细用户列表
        report.append("Detailed User Costs:")
        for user in sorted(self.users, key=lambda u: u.get_total_cost(), reverse=True):
            summary = user.get_cost_summary()
            if summary.get("tracking_enabled"):
                report.append(f"  {user.user_id}:")
                report.append(f"    Total Cost: ${summary['total_cost']:.4f}")
                report.append(f"    Interactions: {user.interaction_count}")
                report.append(f"    Avg per Interaction: ${summary.get('average_cost_per_interaction', 0):.4f}")
                report.append(f"    Total Tokens: {summary['total_input_tokens'] + summary['total_output_tokens']}")
        
        report_text = "\n".join(report)
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"Cost report saved to {output_file}")
        
        return report_text


# 用户池管理器
class UserPool:
    """管理多个用户的池"""
    
    def __init__(self, client: AsyncOpenAIClientWithRetry):
        self.client = client
        self.users: Dict[str, User] = {}
        self._lock = asyncio.Lock()
    
    async def create_user(self, user_config: UserRuntimeConfig) -> User:
        """创建新用户"""
        user = User(self.client, user_config)
        
        async with self._lock:
            self.users[user.user_id] = user
        
        return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        async with self._lock:
            return self.users.get(user_id)
    
    async def remove_user(self, user_id: str) -> bool:
        """移除用户"""
        async with self._lock:
            if user_id in self.users:
                del self.users[user_id]
                return True
            return False
    
    async def create_users_batch(self, configs: List[UserRuntimeConfig]) -> List[User]:
        """批量创建用户"""
        users = []
        for config in configs:
            user = await self.create_user(config)
            users.append(user)
        return users
    
    async def interact_all_users(self, **kwargs) -> Dict[str, str]:
        """让所有用户进行一轮交互"""
        results = {}
        
        # 获取所有用户
        async with self._lock:
            user_list = list(self.users.values())
        
        # 并发交互
        tasks = []
        for user in user_list:
            task = asyncio.create_task(user.interact(**kwargs))
            tasks.append((user.user_id, task))
        
        # 收集结果
        for user_id, task in tasks:
            try:
                response = await task
                results[user_id] = response
            except Exception as e:
                logger.error(f"User {user_id} interaction failed: {e}")
                results[user_id] = f"Error: {str(e)}"
        
        return results
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有用户的统计信息"""
        stats = {}
        for user_id, user in self.users.items():
            stats[user_id] = user.get_statistics()
        return stats
    
    async def broadcast_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """向所有用户广播消息"""
        async with self._lock:
            for user in self.users.values():
                user.receive_message(content, metadata)

# 用户行为模拟器
class UserBehaviorSimulator:
    """模拟真实用户行为"""
    
    def __init__(self, user: User):
        self.user = user
        self.behavior_patterns = {
            "active": {"min_delay": 0.5, "max_delay": 2.0, "response_probability": 0.9},
            "moderate": {"min_delay": 2.0, "max_delay": 5.0, "response_probability": 0.7},
            "passive": {"min_delay": 5.0, "max_delay": 10.0, "response_probability": 0.5},
        }
        self.current_behavior = "moderate"
    
    def set_behavior(self, behavior_type: str):
        """设置行为模式"""
        if behavior_type in self.behavior_patterns:
            self.current_behavior = behavior_type
        else:
            raise ValueError(f"Unknown behavior type: {behavior_type}")
    
    async def simulate_interaction(self, incoming_message: str) -> Optional[str]:
        """模拟用户交互，包括延迟和可能不响应"""
        import random
        
        pattern = self.behavior_patterns[self.current_behavior]
        
        # 模拟思考时间
        think_time = random.uniform(pattern["min_delay"], pattern["max_delay"])
        await asyncio.sleep(think_time)
        
        # 决定是否响应
        if random.random() > pattern["response_probability"]:
            logger.info(f"User {self.user.user_id} chose not to respond")
            return None
        
        # 接收消息并生成响应
        self.user.receive_message(incoming_message)
        response = await self.user.interact()
        
        return response
    
    async def simulate_conversation_flow(
        self, 
        messages: List[str], 
        response_handler: Optional[callable] = None
    ) -> List[Tuple[str, Optional[str]]]:
        """模拟整个对话流程"""
        results = []
        
        for message in messages:
            response = await self.simulate_interaction(message)
            results.append((message, response))
            
            if response_handler and response:
                await response_handler(message, response)
        
        return results

# 扩展的用户池管理器，带成本追踪
class UserPoolWithCostTracking(UserPool):
    """带成本追踪的用户池管理器"""
    
    def __init__(self, client: AsyncOpenAIClientWithRetry):
        super().__init__(client)
        self.cost_analyzer = None
    
    def get_cost_analyzer(self) -> CostAnalyzer:
        """获取成本分析器"""
        users = list(self.users.values())
        return CostAnalyzer(users)
    
    def get_total_pool_cost(self) -> float:
        """获取整个用户池的总成本"""
        return sum(user.get_total_cost() for user in self.users.values())
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """获取用户池的成本摘要"""
        analyzer = self.get_cost_analyzer()
        return {
            "pool_stats": analyzer.get_cost_statistics(),
            "by_model": analyzer.get_cost_by_model(),
            "top_spenders": analyzer.get_top_spenders(10)
        }
    
    async def monitor_costs(self, threshold: float, callback: callable):
        """监控成本，当超过阈值时触发回调"""
        while True:
            total_cost = self.get_total_pool_cost()
            if total_cost > threshold:
                await callback(total_cost, self.get_cost_summary())
                break
            await asyncio.sleep(1)  # 每秒检查一次


if __name__ == "__main__":
    pass