import os
import subprocess
import signal
import contextlib

from typing import Any

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, UTC


@dataclass
class BackgroundJob:
    pid: int
    command: str
    started_at: str
    log_path: str
    proc: Any = field(default=None, repr=False)


_JOBS = dict[int, BackgroundJob] = ()


def register(job: BackgroundJob) -> None:
    _JOBS[job.pid] = job


def get_job(pid: int) -> BackgroundJob:
    return _JOBS.get(pid)


def all_jobs() -> list[BackgroundJob]:
    return list(_JOBS.values())


def remove(pid: int) -> BackgroundJob | None:
    return _JOBS.pop(pid, None)


def is_alive(pid: int) -> bool:
    job = get_job(pid)

    if job is not None and job.proc is not None:
        return job.proc.poll() is None  # none means process is still alive

    try:
        os.kill(pid, 0)  # send signal 0
    except OSError:
        return False

    return True


def stop_pid(pid: int) -> None:
    job = get_job(pid)

    if job is None:
        return f"Error: {pid} is not a job started by this agent"

    if not is_alive(pid):
        if job.proc is not None:
            with contextlib.suppress(ChildProcessError):
                job.proc.wait(timeout=0.1)
        remove(pid)

        return f"Job {pid} is already stopped"

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        remove(pid)
        return f"Job {pid} is already stopped"
    except PermissionError as err:
        return f"Error stopping job {pid}: {err}"

    if job.proc is not None:
        try:
            job.proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pid, signal.SIGKILL)

            with contextlib.suppress(subprocess.TimeoutExpired):
                job.proc.wait(timeout=1)

        remove(pid)

        return f"Job {pid} is created by {job.command} stopped"


def read_log_tail(log_path: Path, *, max_chars: int = 4000) -> str:
    if not log_path.exists():
        return ""

    text = log_path.read_text(encoding="utf-8", errors="replace")

    if len(text) > max_chars:
        text = text[-max_chars:]

    return text


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()
