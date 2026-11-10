"""耗时工作在后台执行，任务状态落盘并按简历隔离。"""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from .store import DATA, LOCK, now, read, save


ACTIVE = {"queued", "running", "paused", "needs_login", "needs_verification"}


class TaskManager:
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="autoboss-task")
        self.folder = DATA / "tasks"
        self.folder.mkdir(parents=True, exist_ok=True)
        for path in self.folder.glob("*.json"):
            task = read(path)
            if task["status"] in ACTIVE:
                task.update(status="interrupted", message="服务重启，已保存结果保留，可重新执行。", finished_at=now())
                save(path, task)

    def list(self, project_id=None):
        values = [read(path) for path in self.folder.glob("*.json")]
        return sorted([t for t in values if not project_id or t["project_id"] == project_id],
                      key=lambda t: t["created_at"], reverse=True)[:30]

    def update(self, task_id, **changes):
        with LOCK:
            path = self.folder / (task_id + ".json")
            task = read(path)
            task.update(changes, updated_at=now())
            save(path, task)
        return task

    def submit(self, kind, project_id, function):
        with LOCK:
            if any(t["status"] in ACTIVE for t in self.list(project_id)):
                raise ValueError("这份简历还有任务正在执行，请等待完成或停止采集。")
            task_id = uuid4().hex
            task = {"id": task_id, "kind": kind, "project_id": project_id, "status": "queued",
                    "message": "任务已排队", "current": 0, "total": 0,
                    "created_at": now(), "updated_at": now(), "finished_at": None}
            save(self.folder / (task_id + ".json"), task)

        def execute():
            self.update(task_id, status="running", message="正在执行")
            try:
                function(task_id, lambda **kwargs: self.update(task_id, **kwargs))
                current = read(self.folder / (task_id + ".json"))
                if current["status"] in ACTIVE:
                    self.update(task_id, status="completed", message="任务已完成", finished_at=now())
            except Exception as exc:
                self.update(task_id, status="error", message=str(exc)[:400], finished_at=now())

        self.pool.submit(execute)
        return task
