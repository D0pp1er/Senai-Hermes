"""Bounded POSIX process groups for noninteractive scheduled execution."""

import os
import signal
import subprocess


class ExecutionUncertain(RuntimeError):
    """Execution stopped after launch; external effects cannot be inferred."""


def _signal_group(process, sig):
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def run_bounded(command, *, cwd, env, stdout, stderr, timeout):
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr, start_new_session=True)
    try:
        return subprocess.CompletedProcess(command, process.wait(timeout=timeout))
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        _signal_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        finally:
            # Include descendants even if their immediate parent already exited.
            _signal_group(process, signal.SIGKILL)
            process.wait()
        raise ExecutionUncertain("Scheduled execution stopped after launch; effects unknown. Review before resuming.") from None
