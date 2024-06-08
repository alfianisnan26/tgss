import asyncio
import time
from tgss.internal.config import Config
import logging

class AsyncCache:
    def __init__(self, default_ttl=60):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache = {}
        self._ttl = {}
        self.default_ttl = default_ttl
        self.lock = asyncio.Lock()

    async def start_cleanup_task(self):
        while True:
            await asyncio.sleep(1)
            current_time = time.time()
            async with self.lock:
                keys_to_delete = [key for key, expiry in self._ttl.items() if current_time > expiry]
                for key in keys_to_delete:
                    del self._cache[key]
                    del self._ttl[key]
                    
                    self.logger.debug(f"start_cleanup_task: Cache expired {key}")

    async def set(self, key, value, ttl=None):
        async with self.lock:
            self._cache[key] = value
            self._ttl[key] = time.time() + (ttl if ttl is not None else self.default_ttl)

    async def get(self, key):
        async with self.lock:
            if key in self._cache and time.time() < self._ttl[key]:
                return self._cache[key]
            elif key in self._cache:
                del self._cache[key]
                del self._ttl[key]
            return None

    async def fallback(self, key, fallback_func, ttl=None):
        async with self.lock:
            if key in self._cache and time.time() < self._ttl[key]:
                self.logger.debug(f"fallback: Cached response for {key}")
                return self._cache[key]
            else:
                self.logger.debug(f"fallback: Running fallback function")
                value = await fallback_func()
                
                self._cache[key] = value
                self._ttl[key] = time.time() + (ttl if ttl is not None else self.default_ttl)
                
                self.logger.debug(f"fallback: Real response for {key}")
                return value

    async def __repr__(self):
        async with self.lock:
            return f'AsyncCache({self._cache})'