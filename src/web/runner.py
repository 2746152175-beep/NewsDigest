"""Run the R0-R4 pipeline in a subprocess and track its progress."""

import os
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from src.config_loader import load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_STAGE_RE = re.compile(r"\[R([0-3])\]")


class _Task:
    def __init__(self, task_id: str, proc: subprocess.Popen):
        self.task_id = task_id
        self.proc = proc
        self.stage: str | None = None
        self.output: list[str] = []


class PipelineRunner:
    """Owns the single active pipeline subprocess."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._task: _Task | None = None

    def start(self) -> str | None:
        with self._lock:
            if self._task is not None and self._task.proc.poll() is None:
                return None

            config = load_config()
            key_env = (config.get("llm") or {}).get("api_key_env") or "LLM_API_KEY"

            env = os.environ.copy()
            env.pop(key_env, None)
            env["PYTHONUTF8"] = "1"
            env["PYTHONUNBUFFERED"] = "1"

            proc = subprocess.Popen(
                [sys.executable, "-m", "src.scheduler.run"],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=env,
            )
            task = _Task(uuid.uuid4().hex, proc)
            self._task = task
            threading.Thread(target=self._read_output, args=(task,), daemon=True).start()
            return task.task_id

    def status(self) -> dict:
        with self._lock:
            if self._task is None:
                return {"running": False, "stage": None, "output": "", "exit_code": None}
            code = self._task.proc.poll()
            return {
                "running": code is None,
                "stage": self._task.stage,
                "output": "\n".join(self._task.output[-500:]),
                "exit_code": code,
            }

    def _read_output(self, task: _Task) -> None:
        try:
            assert task.proc.stdout is not None
            for raw in task.proc.stdout:
                line = raw.rstrip("\r\n")
                if not line:
                    continue
                task.output.append(line)
                match = _STAGE_RE.search(line)
                if match:
                    task.stage = f"R{match.group(1)}"
        finally:
            if task.proc.stdout is not None:
                task.proc.stdout.close()
            task.proc.wait()


runner = PipelineRunner()
