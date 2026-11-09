"""Explicit gate shared by native execution and fresh-session confirmation."""

from contextlib import contextmanager
import threading

__all__ = ['SessionGate']


class SessionGate:
    def __init__(self, *, is_idle=None):
        self._lock = threading.Lock()
        self.is_idle = is_idle or (lambda: True)

    @contextmanager
    def execution(self):
        with self._lock:
            yield

    @contextmanager
    def idle(self):
        acquired = self._lock.acquire(blocking=False)
        try:
            yield acquired and bool(self.is_idle())
        finally:
            if acquired:
                self._lock.release()

    def wrap(self, runner):
        return _GuardedRunner(self, runner)


class _GuardedRunner:
    def __init__(self, gate, runner):
        self.gate, self.runner = gate, runner

    def __call__(self, job):
        with self.gate.execution():
            return self.runner(job)

    def __getattr__(self, name):
        return getattr(self.runner, name)
