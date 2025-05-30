import asyncio
import time
import threading
from typing import Dict, Optional, List
import logging
from utils.api_model.semaphore import SmartAsyncSemaphore
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry

# 设置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# 高级并发管理器
class ConcurrencyManager:
    """
    高级并发管理器，支持：
    - 动态调整并发限制
    - 基于时间窗口的速率限制
    - 优先级队列
    """
    
    def __init__(self, default_limit: int = 10):
        self.default_limit = default_limit
        self.semaphores: Dict[str, SmartAsyncSemaphore] = {}
        self.rate_limiters: Dict[str, 'RateLimiter'] = {}
        self._lock = threading.Lock()
    
    def get_semaphore(self, key: str, limit: Optional[int] = None) -> SmartAsyncSemaphore:
        """获取或创建信号量"""
        with self._lock:
            if key not in self.semaphores:
                self.semaphores[key] = SmartAsyncSemaphore(limit or self.default_limit)
            return self.semaphores[key]
    
    def update_limit(self, key: str, new_limit: int):
        """动态更新并发限制"""
        with self._lock:
            # 创建新的信号量替换旧的
            self.semaphores[key] = SmartAsyncSemaphore(new_limit)
            logger.info(f"更新 {key} 的并发限制为 {new_limit}")

class RateLimiter:
    """基于滑动窗口的速率限制器"""
    
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取许可"""
        async with self._lock:
            now = time.time()
            # 清理过期的请求记录
            self.requests = [t for t in self.requests if now - t < self.window_seconds]
            
            if len(self.requests) >= self.max_requests:
                # 需要等待
                sleep_time = self.window_seconds - (now - self.requests[0])
                await asyncio.sleep(sleep_time)
                # 递归调用重新检查
                return await self.acquire()
            
            # 记录新请求
            self.requests.append(now)

# 带优先级的请求队列
class PriorityRequestQueue:
    """优先级请求队列"""
    
    def __init__(self, client: AsyncOpenAIClientWithRetry):
        self.client = client
        self.queue = asyncio.PriorityQueue()
        self.workers = []
        self.running = False
    
    async def add_request(
        self,
        messages: List[Dict[str, str]],
        priority: int = 0,  # 数字越小优先级越高
        callback: Optional[callable] = None
    ):
        """添加请求到队列"""
        request_id = id(messages)
        await self.queue.put((priority, request_id, messages, callback))
        return request_id
    
    async def _worker(self, worker_id: int):
        """工作协程"""
        while self.running:
            try:
                # 设置超时避免永久阻塞
                priority, request_id, messages, callback = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
                
                logger.debug(f"Worker {worker_id} 处理请求 {request_id}")
                
                try:
                    result = await self.client.chat_completion(messages)
                    if callback:
                        await callback(request_id, result, None)
                except Exception as e:
                    logger.error(f"请求 {request_id} 失败: {e}")
                    if callback:
                        await callback(request_id, None, e)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} 错误: {e}")
    
    async def start(self, num_workers: int = 5):
        """启动工作协程"""
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(num_workers)
        ]
    
    async def stop(self):
        """停止工作协程"""
        self.running = False
        await asyncio.gather(*self.workers, return_exceptions=True)
