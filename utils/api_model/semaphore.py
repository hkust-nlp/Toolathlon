import asyncio
import threading
import logging
from contextlib import asynccontextmanager

# 设置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Python 3.12+ 版本的智能信号量
class SmartAsyncSemaphore:
    """
    Python 3.12+ 的智能异步信号量
    自动检测调用环境并选择合适的信号量实现
    """
    
    def __init__(self, value: int):
        self._value = value
        self._asyncio_semaphore = None
        self._threading_semaphore = threading.Semaphore(value)
        self._loop = None
        self._warned = False
        self._lock = threading.Lock()
    
    def _get_loop_and_semaphore(self):
        """延迟初始化 asyncio 信号量"""
        try:
            loop = asyncio.get_running_loop()
            if self._asyncio_semaphore is None:
                self._asyncio_semaphore = asyncio.Semaphore(self._value)
            return loop, self._asyncio_semaphore
        except RuntimeError:
            return None, None
    
    @asynccontextmanager
    async def acquire_context(self):
        """Python 3.12+ 使用 asynccontextmanager"""
        loop, async_sem = self._get_loop_and_semaphore()
        
        # 检查是否在事件循环中
        if loop is not None and threading.current_thread() == threading.main_thread():
            # 在主事件循环中，使用 asyncio.Semaphore
            if not self._warned:
                with self._lock:
                    if not self._warned:
                        logger.debug(f"使用 asyncio.Semaphore (线程: {threading.current_thread().name})")
                        self._warned = True
            
            async with async_sem:
                yield
        else:
            # 不在事件循环或在其他线程中，使用 threading.Semaphore
            if not self._warned:
                with self._lock:
                    if not self._warned:
                        logger.debug(f"使用 threading.Semaphore (线程: {threading.current_thread().name})")
                        self._warned = True
            
            # Python 3.12+ 可以直接使用 asyncio.to_thread
            await asyncio.to_thread(self._threading_semaphore.acquire)
            try:
                yield
            finally:
                self._threading_semaphore.release()
    
    async def __aenter__(self):
        self._context = self.acquire_context()
        return await self._context.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._context.__aexit__(exc_type, exc_val, exc_tb)
