import asyncio
import threading
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class SmartAsyncSemaphore:
    """
    Smart asynchronous semaphore for Python 3.12+.
    Automatically detects the calling environment and chooses the appropriate semaphore implementation.
    """

    def __init__(self, value: int):
        self._value = value
        self._asyncio_semaphore = None
        self._threading_semaphore = threading.Semaphore(value)
        self._loop = None
        self._warned = False
        self._lock = threading.Lock()

    def _get_loop_and_semaphore(self):
        """Lazily initialize asyncio semaphore if needed."""
        try:
            loop = asyncio.get_running_loop()
            if self._asyncio_semaphore is None:
                self._asyncio_semaphore = asyncio.Semaphore(self._value)
            return loop, self._asyncio_semaphore
        except RuntimeError:
            return None, None

    @asynccontextmanager
    async def acquire_context(self):
        """
        Context manager for acquiring the semaphore.
        Uses asyncio.Semaphore if in the main async event loop and main thread,
        otherwise falls back to threading.Semaphore.
        """
        loop, async_sem = self._get_loop_and_semaphore()

        # Check if we are in the main event loop and main thread
        if loop is not None and threading.current_thread() == threading.main_thread():
            if not self._warned:
                with self._lock:
                    if not self._warned:
                        logger.debug(f"Using asyncio.Semaphore (thread: {threading.current_thread().name})")
                        self._warned = True

            async with async_sem:
                yield
        else:
            # Fallback to threading.Semaphore for non-async or non-main-thread contexts
            if not self._warned:
                with self._lock:
                    if not self._warned:
                        logger.debug(f"Using threading.Semaphore (thread: {threading.current_thread().name})")
                        self._warned = True

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
