from typing import List, Dict, Any, Optional, Callable
from utils.api_model.model_provider import API_MAPPINGS
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
import asyncio

# Utility functions
def format_messages_for_display(messages: List[Dict[str, str]], max_length: int = 50) -> str:
    """Format a list of messages for display."""
    formatted = []
    for msg in messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if len(content) > max_length:
            content = content[:max_length] + "..."
        formatted.append(f"{role}: {content}")
    return " | ".join(formatted)

def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in the text (rough estimation)."""
    # Rough estimation: assume 1 token for every 4 characters
    return len(text) // 4

def calculate_batch_cost(messages_list: List[List[Dict[str, str]]], model: str) -> float:
    """Estimate the cost for a batch of requests."""
    if model not in API_MAPPINGS:
        return 0.0

    total_tokens = 0
    for messages in messages_list:
        for msg in messages:
            total_tokens += estimate_tokens(msg.get('content', ''))

    # Assume input:output token ratio is 1:2
    input_tokens = total_tokens
    output_tokens = total_tokens * 2

    prices = API_MAPPINGS[model]['price']
    input_cost = (input_tokens / 1000) * prices[0]
    output_cost = (output_tokens / 1000) * prices[1]

    return input_cost + output_cost

# Batch processing helper function
async def batch_process_with_progress(
    client: AsyncOpenAIClientWithRetry,
    tasks: List[Dict[str, Any]],
    batch_size: int = 10,
    progress_callback: Optional[Callable[[int, int], Any]] = None
) -> List[Any]:
    """Batch process with progress callback."""
    results = []
    total_tasks = len(tasks)

    for i in range(0, total_tasks, batch_size):
        batch = tasks[i:i + batch_size]

        # Use TaskGroup for batch processing (Python 3.12+)
        async with asyncio.TaskGroup() as tg:
            batch_tasks = []
            for task_data in batch:
                task = tg.create_task(
                    client.chat_completion(
                        task_data['messages'],
                        **task_data.get('kwargs', {})
                    )
                )
                batch_tasks.append(task)

        # Collect results
        batch_results = [t.result() for t in batch_tasks]
        results.extend(batch_results)

        # Progress callback
        if progress_callback:
            await progress_callback(len(results), total_tasks)

    return results
