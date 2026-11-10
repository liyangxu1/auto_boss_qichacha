"""累计全部采集批次，按BOSS岗位链接去重并保留来源。"""

from copy import deepcopy
from datetime import datetime
from urllib.parse import urlsplit

from .store import DATA, LOCK, ROOT, read, save


_signature = None
_catalog = []


def job_key(job):
    path = urlsplit(job.get("url") or "").path
    if path.startswith("/job_detail/"):
        return path.rsplit("/", 1)[-1].removesuffix(".html")
    return job.get("id")


def stamp(job):
    try:
        return datetime.fromisoformat(job["collected_at"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError, TypeError):
        return 0


def unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def all_jobs():
    global _signature, _catalog
    files = sorted({*(ROOT / "data/boss").glob("run-*/jobs.json"),
                    *(DATA / "projects").glob("*/runs/*/jobs.json")})
    signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)
    with LOCK:
        if signature == _signature:
            return deepcopy(_catalog)
        observations = []
        for path in files:
            for job in read(path, []):
                if isinstance(job, dict) and job_key(job):
                    observations.append((stamp(job), path, job))
        merged = {}
        for _, path, source in sorted(observations, key=lambda row: row[0]):
            key = job_key(source)
            old = merged.get(key, {})
            job = {**old, **{k: v for k, v in source.items() if v not in (None, "", [])}}
            if old.get("detail_status") == "complete" and source.get("detail_status") != "complete":
                for field in ("description", "detail_status", "access_limited", "source_text_file"):
                    job[field] = old.get(field)
            for field in ("tags", "benefits", "searches"):
                job[field] = unique((old.get(field) or []) + (source.get(field) or []))
            job["company"] = {**(old.get("company") or {}), **{k:v for k,v in (source.get("company") or {}).items() if v not in (None, "", [])}}
            job.update(id=key, first_seen=old.get("first_seen") or source.get("collected_at"),
                       last_seen=source.get("collected_at"), source_run_dir=str(path.parent.relative_to(ROOT)),
                       source_runs=unique((old.get("source_runs") or []) + [str(path.parent.relative_to(ROOT))]))
            merged[key] = job
        _catalog = list(merged.values())
        save(DATA / "catalog/jobs.json", _catalog)
        _signature = signature
        return deepcopy(_catalog)
