"""本机工作台 API 与静态页面；不提供投递或发消息接口。"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from autoboss.matching.models import MatchingRules, default_rules
from autoboss.models.search import BossSearchProfile, ExperienceFilter, SearchPreferences, ShortText
from . import workflows
from .browser import browser_status, enqueue
from .store import LOCK, ROOT, create_project, project_dir, project_list, read, save, update_project, validate_resume
from .tasks import ACTIVE, TaskManager


@asynccontextmanager
async def lifespan(app):
    app.state.tasks = TaskManager()
    yield
    app.state.tasks.pool.shutdown(wait=False)


app = FastAPI(title="AutoBOSS 本地工作台", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])


@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        parsed = urlsplit(origin)
        if parsed.netloc != request.headers.get("host") or parsed.scheme != "http":
            return JSONResponse({"detail": "仅允许本机工作台页面操作。"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({"detail": str(exc)[:500] if not isinstance(exc, ValidationError) else "字段格式不正确，请检查输入。"}, status_code=400)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse({"detail": "输入格式不正确：" + "；".join(".".join(map(str, e["loc"][1:])) + " " + e["msg"] for e in exc.errors())[:400]}, status_code=422)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchEdit(Input):
    cities: list[ShortText] = Field(min_length=1, max_length=10)
    primary_search_keywords: list[ShortText] = Field(min_length=1, max_length=6)
    experience_filter: ExperienceFilter
    target_directions: str = Field(default="", max_length=300)
    experience_note: str = Field(default="", max_length=500)
    employment_type: Literal["全职", "不限"] = "全职"


class CollectionLimits(Input):
    max_jobs_per_search: int = Field(default=6, ge=1, le=20)
    max_jobs_total: int = Field(default=36, ge=1, le=100)
    collect_company_details: bool = False


class Control(Input):
    action: Literal["pause", "resume", "cancel"]


class Connection(Input):
    project_id: str | None = None


def manager():
    return app.state.tasks


def idle(project_id):
    project_dir(project_id)
    if any(t["status"] in ACTIVE for t in manager().list(project_id)):
        raise ValueError("当前任务还在执行，请完成后再修改。")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "autoboss-workbench"}


@app.get("/api/state")
def state():
    try:
        ai = workflows.client()
        model = {"configured": True, "name": ai.config.model}
    except ValueError:
        model = {"configured": False, "name": None}
    return {"projects": project_list(), "browser": browser_status(), "model": model,
            "defaults": default_rules().model_dump()}


@app.get("/api/projects/{project_id}")
def project(project_id: str):
    return {**workflows.project_view(project_id), "tasks": manager().list(project_id)}


@app.post("/api/resumes")
async def upload(file: UploadFile = File(...)):
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "PDF 不能超过20MB。")
    if not content.startswith(b"%PDF-"):
        raise ValueError("请上传有效的 PDF 简历。")
    workflows.client()
    filename = Path((file.filename or "简历.pdf").replace("\\", "/")).name[:180]
    meta = create_project(filename)
    path = project_dir(meta["id"]) / "input.pdf"
    path.write_bytes(content)
    path.chmod(0o600)
    task = manager().submit("parse", meta["id"], lambda task_id, progress: workflows.parse_resume(meta["id"], progress))
    return {"project_id": meta["id"], "task": task}


@app.put("/api/projects/{project_id}/resume")
def edit_resume(project_id: str, value: dict):
    idle(project_id)
    validate_resume(value)
    save(project_dir(project_id) / "resume.json", value)
    update_project(project_id, status="ready", search_confirmed=False)
    return {"ok": True}


@app.post("/api/projects/{project_id}/keywords")
def keywords(project_id: str, preferences: SearchPreferences):
    directory = project_dir(project_id)
    if not (directory / "resume.json").is_file():
        raise ValueError("请先完成简历解析。")
    values = preferences.model_dump()
    return manager().submit("keywords", project_id, lambda task_id, progress: workflows.generate_keywords(project_id, values, progress))


@app.post("/api/projects/{project_id}/parse")
def retry_parse(project_id: str, fresh: bool = False):
    project_dir(project_id)
    return manager().submit("parse", project_id, lambda task_id, progress: workflows.parse_resume(project_id, progress, reuse=not fresh))


@app.put("/api/projects/{project_id}/search")
def edit_search(project_id: str, value: SearchEdit):
    idle(project_id)
    directory = project_dir(project_id)
    old = read(directory / "search.json")
    if not old:
        raise ValueError("请先让 AI 生成搜索建议。")
    changes = value.model_dump()
    prefs = {key: changes.pop(key) for key in ("target_directions", "experience_note", "employment_type")}
    # 主筛选由界面明确指定，历史扩展条件不混入本轮采集。
    old.update(changes, additional_experience_filters=[])
    old["secondary_search_keywords"] = [k for k in old["secondary_search_keywords"] if k not in old["primary_search_keywords"]]
    profile = BossSearchProfile.model_validate(old)
    save(directory / "search.json", profile.model_dump())
    update_project(project_id, search_confirmed=True, preferences={**prefs, "cities": value.cities})
    return {"ok": True}


@app.put("/api/projects/{project_id}/rules")
def edit_rules(project_id: str, rules: MatchingRules):
    idle(project_id)
    path = project_dir(project_id) / "rules.json"
    old = MatchingRules.model_validate(read(path))
    count = workflows.reweight(project_id, old, rules)
    save(path, rules.model_dump())
    return {"ok": True, "reweighted": count}


@app.post("/api/browser/connect")
def connect_browser(value: Connection | None = None):
    if any(t["kind"] == "collect" and t["status"] in ACTIVE for t in manager().list()):
        raise ValueError("正在采集，请使用已打开的 BOSS 窗口。")
    payload = {}
    if value and value.project_id:
        from autoboss.boss.plan import city_codes
        meta = read(project_dir(value.project_id) / "project.json")
        cities = meta["preferences"].get("cities", [])
        if cities:
            code = city_codes(ROOT / "data/boss/city-data.json").get(cities[0].removesuffix("市"))
            if code:
                payload["entry_url"] = "https://www.zhipin.com/web/geek/jobs?city=" + code
    return {"command_id": enqueue("connect", payload)}


@app.post("/api/projects/{project_id}/collect")
def collect_jobs(project_id: str, limits: CollectionLimits):
    project_dir(project_id)
    if any(t["kind"] == "collect" and t["status"] in ACTIVE for t in manager().list()):
        raise ValueError("BOSS 正在采集其他任务，请等待完成。")
    return manager().submit("collect", project_id, lambda task_id, progress: workflows.collect(project_id, limits, progress))


@app.post("/api/projects/{project_id}/collection-control")
def control(project_id: str, value: Control):
    directory = project_dir(project_id)
    meta = read(directory / "project.json")
    if not meta.get("last_run") or not any(t["kind"] == "collect" and t["status"] in ACTIVE for t in manager().list(project_id)):
        raise ValueError("当前没有正在执行的采集任务。")
    output = directory / "runs" / meta["last_run"]
    if value.action == "resume":
        (output / "pause").unlink(missing_ok=True)
    else:
        (output / ("pause" if value.action == "pause" else "cancel")).touch()
    return {"ok": True, "message": "已请求，完成当前岗位后生效"}


@app.post("/api/projects/{project_id}/match")
def match_jobs(project_id: str):
    project_dir(project_id)
    return manager().submit("match", project_id, lambda task_id, progress: workflows.match(project_id, progress))


@app.get("/api/projects/{project_id}/export")
def export(project_id: str, include_excluded: bool = False):
    view = workflows.project_view(project_id)
    jobs = view["jobs"] if include_excluded else [j for j in view["jobs"] if not j["excluded"]]
    return JSONResponse(content=jobs, headers={"Content-Disposition": 'attachment; filename="autoboss-jobs.json"'})


@app.get("/api/projects/{project_id}/pdf")
def pdf(project_id: str):
    path = project_dir(project_id) / "input.pdf"
    if not path.is_file():
        raise HTTPException(404, "这份简历没有保留原 PDF。")
    return FileResponse(path, media_type="application/pdf", filename="resume.pdf", content_disposition_type="inline")


STATIC = Path(__file__).parent / "static"


@app.get("/{path:path}")
def frontend(path: str):
    target = (STATIC / path).resolve()
    if path.startswith("api/") or not target.is_relative_to(STATIC.resolve()):
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    if path and "." in path:
        raise HTTPException(404)
    return FileResponse(STATIC / "index.html")
