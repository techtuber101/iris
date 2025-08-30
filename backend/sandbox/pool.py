import asyncio
import os
from typing import Optional, Dict, Deque
from collections import deque

from utils.logger import logger
from .sandbox import daytona, create_sandbox, ensure_workspace_dir_sdk


class SandboxPool:
    """
    Maintains a small pool of pre-warmed Daytona sandboxes ready for assignment.
    """

    def __init__(self, target_size: int = 1):
        self.target_size = max(0, int(target_size))
        self._available: Deque = deque()
        self._in_use: Dict[str, object] = {}
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self.target_size <= 0:
            logger.info("SandboxPool disabled (target_size=0)")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._maintainer())
        logger.info(f"SandboxPool started (target_size={self.target_size})")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("SandboxPool stopped")

    async def acquire(self):
        async with self._lock:
            if self._available:
                sb = self._available.popleft()
                self._in_use[getattr(sb, 'id', str(id(sb)))] = sb
                return sb
        # If none available, create on demand
        return await self._create_one()

    async def release(self, sandbox):
        sid = getattr(sandbox, 'id', None)
        async with self._lock:
            if sid and sid in self._in_use:
                self._in_use.pop(sid, None)
            # Return to pool if under target
            if len(self._available) < self.target_size:
                self._available.append(sandbox)
            else:
                # Optionally delete extras later; keep for now
                pass

    async def _maintainer(self):
        try:
            while True:
                try:
                    await self._fill_to_target()
                except Exception as e:
                    logger.warning(f"SandboxPool maintainer error: {e}")
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            return

    async def _fill_to_target(self):
        async with self._lock:
            need = self.target_size - len(self._available)
        for _ in range(max(0, need)):
            try:
                sb = await self._create_one()
                async with self._lock:
                    self._available.append(sb)
            except Exception as e:
                logger.warning(f"Failed to create warm sandbox: {e}")

    async def _create_one(self):
        # Minimal warm setup using same image and defaults as create_sandbox
        password = os.getenv("IRIS_WARM_POOL_PASSWORD", "warm-pass")
        sb = create_sandbox(password)
        ensure_workspace_dir_sdk(sb)
        return sb


_pool: Optional[SandboxPool] = None


def get_pool() -> SandboxPool:
    global _pool
    if _pool is None:
        size = int(os.getenv("IRIS_SANDBOX_POOL_SIZE", "1"))
        _pool = SandboxPool(target_size=size)
    return _pool

