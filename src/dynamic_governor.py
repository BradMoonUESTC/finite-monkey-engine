import asyncio
import time
from collections import deque

class DynamicGovernor:
    def __init__(self, initial_limit=5, window_size=10, fast_threshold=1.0, slow_threshold=3.0):
        self.limit = initial_limit
        self.semaphore = asyncio.Semaphore(self.limit)
        self.window_size = window_size
        # Store the last window_size durations
        self.task_durations = deque(maxlen=window_size)
        self.fast_threshold = fast_threshold
        self.slow_threshold = slow_threshold

    async def acquire(self):
        await self.semaphore.acquire()

    def release(self, duration: float):
        self.task_durations.append(duration)
        self.semaphore.release()
        self.adjust_limit()

    def adjust_limit(self):
        if not self.task_durations:
            return
        # Compute the moving average of task durations
        avg_duration = sum(self.task_durations) / len(self.task_durations)
        new_limit = self.limit
        if avg_duration < self.fast_threshold:
            new_limit = self.limit * 2
        elif avg_duration > self.slow_threshold:
            new_limit = max(1, int(self.limit * 2 / 3))
        # Only adjust if there is a change
        if new_limit != self.limit:
            print(f"Adjusting concurrency limit from {self.limit} to {new_limit} (avg_duration={avg_duration:.2f}s)")
            self.limit = new_limit
            # Reinitialize the semaphore to the new limit.
            self.semaphore = asyncio.Semaphore(self.limit)

async def governed_task(task_fn, governor: DynamicGovernor, *args, **kwargs):
    await governor.acquire()
    start = time.monotonic()
    try:
        result = await task_fn(*args, **kwargs)
        return result
    finally:
        duration = time.monotonic() - start
        governor.release(duration)
