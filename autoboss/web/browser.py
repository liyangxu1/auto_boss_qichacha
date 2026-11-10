"""网页与单一浏览器进程通过本地任务文件通信。"""

import os
import subprocess
import sys
import time
from uuid import uuid4

from autoboss.boss.network import direct_environment
from .store import DATA, ROOT, now, read, save


BROWSER = DATA / "browser"


def browser_status():
    state = read(BROWSER / "status.json", {"status": "disconnected", "message": "连接 BOSS 后可开始采集"})
    if state.get("pid") and not worker_alive(state["pid"]):
        return {"status": "disconnected", "message": "浏览器连接已断开，可重新连接并复用已保存登录"}
    metadata = read(ROOT / "data/browser/boss/autoboss-auth/metadata.json", {})
    state["auth_saved_at"] = metadata.get("saved_at")
    return state


def worker_alive(pid):
    try:
        os.kill(pid, 0)
        result = subprocess.run(["ps", "-p", str(pid), "-o", "stat=,command="], capture_output=True, text=True)
        return bool(result.stdout.strip() and not result.stdout.lstrip().startswith("Z")
                    and "autoboss.web.browser_worker" in result.stdout)
    except (ProcessLookupError, PermissionError):
        return False


def ensure_worker():
    BROWSER.mkdir(parents=True, exist_ok=True)
    state = browser_status()
    if state.get("pid"):
        return
    with (BROWSER / "worker.log").open("a") as log:
        subprocess.Popen([sys.executable, "-u", "-m", "autoboss.web.browser_worker"], cwd=ROOT,
                         env=direct_environment(), stdout=log, stderr=log, start_new_session=True)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = browser_status()
        if state.get("pid"):
            return
        time.sleep(0.1)
    raise ValueError("浏览器任务进程没有启动，请查看本地日志。")


def enqueue(kind, payload=None):
    ensure_worker()
    command_id = uuid4().hex
    path = BROWSER / "commands" / (f"{time.time_ns()}-{command_id}.json")
    save(path, {"id": command_id, "kind": kind, "payload": payload or {}, "created_at": now()})
    return command_id
