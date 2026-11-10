"""每份简历独立保存，保留岗位、规则版本和匹配缓存。"""

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from autoboss.common.storage import json_text, write_files
from autoboss.matching.models import default_rules


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "web"
LOCK = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path, fallback=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else fallback


def save(path, value):
    with LOCK:
        write_files({path: json_text(value)}, force=True)


def project_dir(project_id):
    if not re.fullmatch(r"[a-f0-9]{32}", project_id):
        raise ValueError("项目标识无效。")
    directory = DATA / "projects" / project_id
    if not (directory / "project.json").is_file():
        raise ValueError("没有找到这份简历。")
    return directory


def validate_resume(value):
    fields = {"identity": dict, "intent": dict, "summary": list, "employment": list,
              "projects": list, "skills": list, "education": list, "certifications": list, "other": list}
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("简历必须只包含约定的9类字段。")
    if any(not isinstance(value[key], kind) for key, kind in fields.items()):
        raise ValueError("简历字段类型不正确，请保留原有对象和列表结构。")
    return value


def create_project(filename):
    project_id = uuid4().hex
    directory = DATA / "projects" / project_id
    directory.mkdir(parents=True)
    meta = {"id": project_id, "filename": filename, "created_at": now(), "updated_at": now(),
            "status": "uploaded", "search_confirmed": False, "last_run": None,
            "preferences": {"cities": [], "experience_note": "", "target_directions": "", "employment_type": "全职"}}
    save(directory / "project.json", meta)
    save(directory / "rules.json", default_rules().model_dump())
    save(directory / "matches.json", {})
    return meta


def update_project(project_id, **changes):
    directory = project_dir(project_id)
    with LOCK:
        meta = read(directory / "project.json")
        meta.update(changes, updated_at=now())
        save(directory / "project.json", meta)
    return meta


def project_list():
    projects = [read(path) for path in (DATA / "projects").glob("*/project.json")]
    return sorted(projects, key=lambda p: p["created_at"], reverse=True)
