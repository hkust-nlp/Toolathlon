import asyncio
import time
import threading
from typing import Dict, Optional, List, Callable
import logging
from utils.api_model.semaphore import SmartAsyncSemaphore
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class ConcurrencyManager:
    """
    Advanced concurrency manager supporting:
    - Dynamic adjustment of concurrency limits
    - Sliding window rate limiting
    - Priority queuing
    """

    def __init__(self, default_limit: int = 10):
        self.default_limit = default_limit
        self.semaphores: Dict[str, SmartAsyncSemaphore] = {}
        self.rate_limiters: Dict[str, 'RateLimiter'] = {}
        self._lock = threading.Lock()

    def get_semaphore(self, key: str, limit: Optional[int] = None) -> SmartAsyncSemaphore:
        """Get or create a semaphore for the provided key."""
        with self._lock:
            if key not in self.semaphores:
                self.semaphores[key] = SmartAsyncSemaphore(limit or self.default_limit)
            return self.semaphores[key]

    def update_limit(self, key: str, new_limit: int):
        """Dynamically update the concurrency limit for a given key."""
        with self._lock:
            # Replace the old semaphore with a new one with the updated limit
            self.semaphores[key] = SmartAsyncSemaphore(new_limit)
            logger.info(f"Updated concurrency limit for {key} to {new_limit}")

class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire permission for a request.
        If the rate limit is reached, this method will wait until a slot is available.
        """
        async with self._lock:
            now = time.time()
            # Remove expired request timestamps
            self.requests = [t for t in self.requests if now - t < self.window_seconds]

            if len(self.requests) >= self.max_requests:
                # Need to wait until the oldest timestamp leaves the window
                sleep_time = self.window_seconds - (now - self.requests[0])
                await asyncio.sleep(sleep_time)
                # Recursively try again
                return await self.acquire()

            # Record new request time
            self.requests.append(now)

class PriorityRequestQueue:
    """A priority-based asynchronous request queue."""

    def __init__(self, client: AsyncOpenAIClientWithRetry):
        self.client = client
        self.queue = asyncio.PriorityQueue()
        self.workers = []
        self.running = False

    async def add_request(
        self,
        messages: List[Dict[str, str]],
        priority: int = 0,  # Lower value means higher priority
        callback: Optional[Callable[[int, any, Optional[Exception]], any]] = None
    ):
        """
        Add a request to the queue.

        Args:
            messages: List of message dicts for the client.
            priority: Integer priority (lower is higher priority).
            callback: Async callback(request_id, result, exception).
        Returns:
            request_id: Unique id for the request instance.
        """
        request_id = id(messages)
        await self.queue.put((priority, request_id, messages, callback))
        return request_id

    async def _worker(self, worker_id: int):
        """
        Worker coroutine to process requests from the queue.
        """
        while self.running:
            try:
                # Use timeout to avoid blocking permanently
                priority, request_id, messages, callback = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
                logger.debug(f"Worker {worker_id} is processing request {request_id}")

                try:
                    result = await self.client.chat_completion(messages)
                    if callback:
                        await callback(request_id, result, None)
                except Exception as e:
                    logger.error(f"Request {request_id} failed: {e}")
                    if callback:
                        await callback(request_id, None, e)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} encountered an error: {e}")

    async def start(self, num_workers: int = 5):
        """
        Start worker coroutines.

        Args:
            num_workers: Number of worker coroutines.
        """
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(num_workers)
        ]

    async def stop(self):
        """
        Stop worker coroutines and wait for them to exit.
        """
        self.running = False
        await asyncio.gather(*self.workers, return_exceptions=True)
