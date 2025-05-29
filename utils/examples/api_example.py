import asyncio
import time
from configs.global_configs import global_configs
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from utils.conversation.conversation_manager import ConversationManager
from utils.misc.tool_manager import ToolManager
from utils.api_model.concurrency_manager import PriorityRequestQueue, RateLimiter
from utils.logging.logging_utils import LogAnalyzer, LogMonitor
from utils.api_model.api_utils import batch_process_with_progress
import json

# 使用示例
async def basic_example():
    """基础使用示例"""
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
    )
    
    async with client:
        # 简单请求
        response = await client.chat_completion([
            {"role": "user", "content": "你好，请介绍一下自己"}
        ])
        print(f"响应: {response}")
        
        # 获取成本信息
        response, cost_report = await client.chat_completion(
            [{"role": "user", "content": "解释量子计算"}],
            return_cost=True
        )
        print(f"响应: {response}")
        print(f"成本: ${cost_report.total_cost:.4f}")

async def example_with_logging():
    """带日志记录的使用示例"""
    # 创建带日志记录的客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/openai_requests.log",  # 指定日志文件
        enable_console_log=True  # 同时输出到控制台
    )
    
    # 创建对话管理器
    conversation_manager = ConversationManager(max_history=10)
    conversation_manager.set_client(client)
    
    async with client:
        # 示例1：单个请求
        response = await client.chat_completion([
            {"role": "system", "content": "你是一个有用的助手"},
            {"role": "user", "content": "请解释什么是机器学习"}
        ])
        print(f"响应: {response}\n")
        
        # 示例2：并发请求
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                client.chat_completion([
                    {"role": "user", "content": f"问题 {i}: 生成一个随机数"}
                ])
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 示例3：使用对话管理器
        conv_id = "test_conversation"
        
        # 第一轮对话
        response1 = await conversation_manager.generate_response(
            conv_id,
            "你好，我想了解Python",
            system_prompt="你是一个Python编程专家"
        )
        print(f"助手响应1: {response1}\n")
        
        # 第二轮对话（会包含历史）
        response2 = await conversation_manager.generate_response(
            conv_id,
            "能详细说说装饰器吗？"
        )
        print(f"助手响应2: {response2}\n")
    
    # 分析日志
    print("\n=== 日志分析 ===")
    analyzer = LogAnalyzer("./logs/openai_requests.log")
    stats = analyzer.get_statistics()
    
    print(f"总请求数: {stats['total_requests']}")
    print(f"成功率: {stats['success_rate']:.2%}")
    print(f"平均响应时间: {stats['average_duration_ms']:.2f}ms")
    print(f"总成本: ${stats['total_cost']:.4f}")
    print(f"总Token使用: 输入={stats['total_tokens']['input']}, 输出={stats['total_tokens']['output']}")
    print(f"模型使用统计: {stats['requests_by_model']}")
    
    # 导出到CSV
    analyzer.export_to_csv("./logs/request_analysis.csv")
    print("\n日志已导出到 request_analysis.csv")

async def advanced_example():
    """高级使用示例"""
    
    # 1. 设置全局并发限制
    AsyncOpenAIClientWithRetry.set_global_concurrency(50)
    
    # 2. 创建带并发控制和日志的客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        global_concurrency=50,  # 全局最多50个并发
        use_model_concurrency=True,  # 使用模型特定的并发限制
        log_file="./logs/advanced_openai_requests.log"
    )
    
    # 3. 创建优先级队列
    priority_queue = PriorityRequestQueue(client)
    
    # 4. 结果收集器
    results = {}
    
    async def handle_result(request_id, result, error):
        """处理结果的回调"""
        if error:
            results[request_id] = f"Error: {error}"
        else:
            results[request_id] = result
    
    async with client:
        # 启动队列处理
        await priority_queue.start(num_workers=10)
        
        try:
            # 添加不同优先级的请求
            high_priority_tasks = []
            for i in range(5):
                req_id = await priority_queue.add_request(
                    [{"role": "user", "content": f"高优先级请求 {i}"}],
                    priority=0,  # 最高优先级
                    callback=handle_result
                )
                high_priority_tasks.append(req_id)
            
            normal_priority_tasks = []
            for i in range(10):
                req_id = await priority_queue.add_request(
                    [{"role": "user", "content": f"普通优先级请求 {i}"}],
                    priority=1,
                    callback=handle_result
                )
                normal_priority_tasks.append(req_id)
            
            low_priority_tasks = []
            for i in range(20):
                req_id = await priority_queue.add_request(
                    [{"role": "user", "content": f"低优先级请求 {i}"}],
                    priority=2,
                    callback=handle_result
                )
                low_priority_tasks.append(req_id)
            
            # 等待所有任务完成
            while len(results) < 35:
                await asyncio.sleep(0.1)
            
            # 统计处理顺序
            print("请求处理统计:")
            print(f"高优先级完成: {sum(1 for t in high_priority_tasks if t in results)}/5")
            print(f"普通优先级完成: {sum(1 for t in normal_priority_tasks if t in results)}/10")
            print(f"低优先级完成: {sum(1 for t in low_priority_tasks if t in results)}/20")
            
        finally:
            # 停止队列
            await priority_queue.stop()
    
    # 打印成本统计
    print("\n成本统计:")
    summary = client.get_cost_summary()
    print(f"总成本: ${summary['total_cost']:.4f}")
    print(f"总请求数: {summary['request_count']}")
    print(f"总输入Token: {summary['total_input_tokens']}")
    print(f"总输出Token: {summary['total_output_tokens']}")
    
    print("\n按模型统计:")
    for model, stats in summary['by_model'].items():
        print(f"  {model}:")
        print(f"    请求数: {stats['count']}")
        print(f"    成本: ${stats['cost']:.4f}")
        print(f"    输入Token: {stats['input_tokens']}")
        print(f"    输出Token: {stats['output_tokens']}")

async def batch_processing_example():
    """批量处理示例"""
    
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/batch_requests.log"
    )
    
    # 准备批量任务
    tasks = []
    for i in range(100):
        tasks.append({
            'messages': [
                {"role": "user", "content": f"为产品 {i} 生成一个创意描述"}
            ],
            'kwargs': {
                'temperature': 0.8,
                'max_tokens': 100
            }
        })
    
    # 进度回调
    async def progress_callback(completed, total):
        print(f"进度: {completed}/{total} ({completed/total*100:.1f}%)")
    
    async with client:
        print("开始批量处理...")
        results = await batch_process_with_progress(
            client,
            tasks,
            batch_size=10,
            progress_callback=progress_callback
        )
        
        print(f"\n完成! 成功处理 {len([r for r in results if r])} 个请求")
        
        # 显示成本
        summary = client.get_cost_summary()
        print(f"总成本: ${summary['total_cost']:.4f}")

async def monitor_example():
    """日志监控示例"""
    
    # 创建日志监控器
    def on_log_update(new_content):
        """处理新的日志内容"""
        lines = new_content.strip().split('\n')
        for line in lines:
            if line and not line.startswith('-') and not line.startswith('='):
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'REQUEST':
                        print(f"[监控] 新请求 #{entry['request_index']}: {entry['model']}")
                    elif entry.get('type') == 'RESPONSE':
                        print(f"[监控] 响应 #{entry['request_index']}: {entry.get('duration_ms', 0):.1f}ms")
                    elif entry.get('type') == 'ERROR':
                        print(f"[监控] 错误 #{entry['request_index']}: {entry['error_message']}")
                except:
                    pass
    
    # 启动监控
    monitor = LogMonitor("./logs/openai_requests.log", on_log_update)
    monitor.start()
    
    # 创建客户端并发送请求
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/openai_requests.log"
    )
    
    async with client:
        # 发送一些请求以触发监控
        for i in range(5):
            await client.chat_completion([
                {"role": "user", "content": f"测试消息 {i}"}
            ])
            await asyncio.sleep(1)  # 间隔1秒
    
    # 停止监控
    monitor.stop()
    print("监控已停止")

async def rate_limiting_example():
    """速率限制示例"""
    
    # 创建速率限制器 (每10秒最多20个请求)
    rate_limiter = RateLimiter(max_requests=20, window_seconds=10)
    
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
    )
    
    async def rate_limited_request(index: int):
        """受速率限制的请求"""
        await rate_limiter.acquire()
        start_time = time.time()
        
        response = await client.chat_completion([
            {"role": "user", "content": f"速率限制测试 {index}"}
        ])
        
        elapsed = time.time() - start_time
        print(f"请求 {index} 完成，耗时: {elapsed:.2f}s")
        return response
    
    async with client:
        print("开始速率限制测试 (20请求/10秒)...")
        
        # 尝试发送30个请求
        tasks = []
        for i in range(30):
            task = asyncio.create_task(rate_limited_request(i))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        print("所有请求完成!")

# 性能测试函数
async def performance_test():
    """性能测试"""
    
    print("=== OpenAI客户端性能测试 ===\n")
    
    # 测试配置
    test_configs = [
        {"concurrency": 10, "requests": 50, "model": "gpt-4.1-nano"},
        {"concurrency": 20, "requests": 100, "model": "gpt-4o-mini"},
        {"concurrency": 5, "requests": 20, "model": "gpt-4o-mini"},
    ]
    
    for config in test_configs:
        print(f"\n测试配置: {config}")
        
        # 创建客户端
        client = AsyncOpenAIClientWithRetry(
            api_key=global_configs.non_ds_key,
            base_url=global_configs.base_url_non_ds,
            model_name=config['model'],
            provider="ds_internal",
            global_concurrency=config['concurrency'],
            log_file=f"./logs/perf_test_{config['model']}_{config['concurrency']}.log"
        )
        
        async with client:
            start_time = time.time()
            
            # 创建请求任务
            tasks = []
            for i in range(config['requests']):
                task = asyncio.create_task(
                    client.chat_completion([
                        {"role": "user", "content": f"性能测试请求 {i}"}
                    ])
                )
                tasks.append(task)
            
            # 执行并计时
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = time.time() - start_time
            
            # 统计结果
            successes = sum(1 for r in results if not isinstance(r, Exception))
            failures = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"  完成时间: {elapsed:.2f}秒")
            print(f"  请求/秒: {config['requests']/elapsed:.2f}")
            print(f"  成功: {successes}, 失败: {failures}")
            
            summary = client.get_cost_summary()
            print(f"  总成本: ${summary['total_cost']:.4f}")
            print(f"  平均成本/请求: ${summary['total_cost']/config['requests']:.4f}")

# 错误处理示例
async def error_handling_example():
    """错误处理示例"""
    
    # 创建客户端，故意使用错误的配置
    client = AsyncOpenAIClientWithRetry(
        api_key="invalid-key",  # 无效的API密钥
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        max_retries=2,  # 减少重试次数以加快测试
        log_file="./logs/error_handling.log"
    )
    
    async with client:
        try:
            # 这应该会失败
            response = await client.chat_completion([
                {"role": "user", "content": "这个请求应该会失败"}
            ])
        except Exception as e:
            print(f"捕获到预期的错误: {type(e).__name__}: {e}")
        
        # 测试超长输入
        try:
            very_long_message = "很长的消息 " * 10000  # 创建一个非常长的消息
            response = await client.chat_completion([
                {"role": "user", "content": very_long_message}
            ])
        except Exception as e:
            print(f"超长输入错误: {type(e).__name__}: {e}")

async def tool_call_example():
    """Tool call 使用示例"""
    
    # 定义工具函数
    def get_weather(location: str, unit: str = "celsius") -> str:
        """获取天气的模拟函数"""
        return f"The weather in {location} is 22°{unit[0].upper()} and sunny."
    
    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            result = eval(expression)
            return f"The result is: {result}"
        except Exception as e:
            return f"Error calculating: {str(e)}"
    
    # 创建工具管理器
    tool_manager = ToolManager()
    
    # 定义工具
    tool_manager.create_tool(
        name="get_weather",
        description="Get the current weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and country, e.g. San Francisco, USA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit for temperature"
                }
            },
            "required": ["location"]
        }
    )
    
    tool_manager.create_tool(
        name="calculate",
        description="Calculate a mathematical expression",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to calculate"
                }
            },
            "required": ["expression"]
        }
    )
    
    # 注册函数
    tool_manager.register_function("get_weather", get_weather)
    tool_manager.register_function("calculate", calculate)
    
    # 创建客户端
    client = AsyncOpenAIClientWithRetry(
        api_key=global_configs.non_ds_key,
        base_url=global_configs.base_url_non_ds,
        model_name="gpt-4o-mini",
        provider="ds_internal",
        log_file="./logs/tool_calls.log"
    )
    
    async with client:
        # 测试1：天气查询
        messages = [
            {"role": "user", "content": "What's the result of pi^9.19111, round to 10 decimal"}
        ]

        content, tool_calls, _ = await client.chat_completion(
            messages,
            tools=tool_manager.get_tools_list(),
            return_tool_calls=True
        )
        
        if tool_calls:
            print("Tool calls detected:")
            for tc in tool_calls:
                print(f"  - {tc.function.name}({tc.function.arguments})")
            
            # 添加assistant的tool_calls消息
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [tc.model_dump() for tc in tool_calls]
            })
            
            # 执行tool calls
            for tool_call in tool_calls:
                result = await tool_manager.execute_tool_call(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result
                })
            
            # 获取最终响应
            final_response = await client.chat_completion(messages)
            print(f"Final response: {final_response}")
        else:
            print(f"Direct response: {content}")

# 命令行接口
def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAI客户端示例")
    parser.add_argument("example", choices=[
        "basic", "logging", "advanced", "batch", "monitor", 
        "rate_limit", "performance", "error", "tool"  # 添加tool
    ], help="要运行的示例")
    
    args = parser.parse_args()
    
    example_map = {
        "basic": basic_example,
        "logging": example_with_logging,
        "advanced": advanced_example,
        "batch": batch_processing_example,
        "monitor": monitor_example,
        "rate_limit": rate_limiting_example,
        "performance": performance_test,
        "error": error_handling_example,
        "tool": tool_call_example,
    }
    
    # 运行选定的示例
    asyncio.run(example_map[args.example]())

if __name__ == "__main__":
    # 如果直接运行，执行一个默认示例
    main()