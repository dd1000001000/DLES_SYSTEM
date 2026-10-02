# -*- coding: utf-8 -*-
import threading
import time


class TooManyAttemptsError(Exception):
    pass


class RateLimiter:
    """
    滑动窗口计数器（单进程内存实现）：window_seconds 秒内记录达到 max_events 次就视为被限制。
    多进程/多机部署时需要换成 Redis 之类的共享存储。
    """

    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        events = [t for t in self._events.get(key, []) if now - t < self.window_seconds]
        if events:
            self._events[key] = events
        else:
            self._events.pop(key, None)
        return events

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.time())) >= self.max_events

    def record(self, key: str) -> None:
        with self._lock:
            now = time.time()
            events = self._prune(key, now)
            events.append(now)
            self._events[key] = events
            # 偶尔清理其他已经过期的 key，避免字典无限增长
            if len(self._events) > 10000:
                for other in list(self._events):
                    self._prune(other, now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)
