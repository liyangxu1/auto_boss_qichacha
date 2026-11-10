"""将现有简历解析、搜索采集和匹配服务接到工作台。"""

import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from uuid import uuid4

from autoboss.boss.network import check_direct_network
from autoboss.boss.plan import build_search_plan
from autoboss.boss.runtime import browser_python
from autoboss.boss.service import CollectOptions
from autoboss.boss.employment import apply_preference
from autoboss.common.config import AIConfig
from autoboss.common.llm import JSONClient
from autoboss.matching.models import Assessment, DimensionAssessment, MatchingRules
from autoboss.matching.service import cache_key, calculate, fingerprint, match_job
from autoboss.models.search import SearchPreferences
from autoboss.resume.search_profile import generate_search_to_files
from autoboss.resume.service import analyze_to_file, extract_to_files
from .browser import BROWSER, browser_status, enqueue
from .catalog import all_jobs
from .store import DATA, LOCK, ROOT, now, project_dir, project_list, read, save, update_project


def client():
    env_file = ROOT / ".env"
    return JSONClient(AIConfig.load(env_file=env_file if env_file.is_file() else None))



def project_jobs(directory, meta):
    # 岗位库与简历分离，匹配结果仍按当前简历和规则隔离。
    return [apply_preference(job, meta["preferences"]) for job in all_jobs()]


def project_view(project_id):
    directory = project_dir(project_id)
    meta = read(directory / "project.json")
    resume = read(directory / "resume.json")
    rules = MatchingRules.model_validate(read(directory / "rules.json"))
    jobs, matches = project_jobs(directory, meta), read(directory / "matches.json", {})
    try:
        model = client().config.model
    except ValueError:
        model = None
    for job in jobs:
        result = matches.get(job["id"])
        current = cache_key(resume, job, meta["preferences"], rules, model) if resume and model else None
        job["match"] = result if not job["excluded"] and result and result.get("cache_key") == current else None
    run = read(directory / "runs" / meta["last_run"] / "run.json") if meta.get("last_run") else None
    return {"project": meta, "resume": resume, "search": read(directory / "search.json"),
            "rules": rules.model_dump(), "jobs": jobs, "run": run, "has_pdf": (directory / "input.pdf").is_file(),
            "catalog": {"total": len(jobs), "eligible": sum(not j["excluded"] for j in jobs),
                        "excluded": sum(j["excluded"] for j in jobs)}}


def generate_keywords(project_id, preferences, progress):
    directory = project_dir(project_id)
    progress(message="AI 正在根据简历和求职方向生成搜索条件")
    generate_search_to_files(directory / "resume.json", directory / "search.json", client(),
                             preferences=preferences, force=True)
    update_project(project_id, preferences=preferences, search_confirmed=False, status="ready")


def parse_resume(project_id, progress, *, reuse=True):
    directory = project_dir(project_id)
    update_project(project_id, status="parsing")
    try:
        progress(message="正在提取 PDF 文字", current=0, total=3)
        source = extract_to_files(directory / "input.pdf", directory / "extracted", force=True)
        reused = False
        for candidate in project_list() if reuse else []:
            if candidate["id"] == project_id:
                continue
            previous = project_dir(candidate["id"])
            pdf = previous / "input.pdf"
            if (previous / "resume.json").is_file() and pdf.is_file() and hashlib.sha256(pdf.read_bytes()).hexdigest() == source.sha256:
                save(directory / "resume.json", read(previous / "resume.json"))
                meta = read(directory / "project.json")
                if not meta["preferences"]["target_directions"]:
                    update_project(project_id, preferences=candidate["preferences"])
                progress(message="复用本机相同 PDF 的已解析结果，正在生成搜索建议", current=1, total=3)
                reused = True
                break
        if not reused:
            progress(message="AI 正在解析简历，通常需要1—5分钟，超时会明确提示", current=1, total=3)
            analyze_to_file(source, directory / "resume.json", client(), force=True)
        update_project(project_id, status="ready")
        progress(message="AI 正在生成搜索条件", current=2, total=3)
        meta = read(directory / "project.json")
        try:
            generate_keywords(project_id, meta["preferences"], progress)
        except Exception as exc:
            # 搜索建议失败不抹掉已经成功解析的简历。
            progress(status="partial", message=f"简历解析完成；搜索建议生成失败：{exc}", finished_at=now())
            return
        progress(status="completed", current=3, total=3, finished_at=now(),
                 message="简历和搜索建议已就绪" + ("（复用相同 PDF 的本地解析结果）" if reused else ""))
    except Exception:
        update_project(project_id, status="error" if not (directory / "resume.json").is_file() else "ready")
        raise


def collect(project_id, limits, progress, *, auto_match=True):
    directory = project_dir(project_id)
    meta = read(directory / "project.json")
    if not meta["search_confirmed"]:
        raise ValueError("请先保存并确认城市、关键词和工作经验。")
    if browser_status()["status"] != "ready":
        raise ValueError("请先连接 BOSS，并在专用窗口完成登录。")
    browser_python()
    check_direct_network()
    options = CollectOptions(max_jobs_per_search=limits.max_jobs_per_search, max_jobs_total=limits.max_jobs_total,
                             max_searches=60, include_additional_experience=False, manual_wait_seconds=0,
                             collect_company_details=limits.collect_company_details)
    # 使用用户保存的关键词顺序，不让模型在采集阶段再次改写条件。
    tasks = build_search_plan(directory / "search.json", ROOT / "data/boss/city-data.json",
                              include_secondary=False, include_additional_experience=False)
    run_id = uuid4().hex
    output = directory / "runs" / run_id
    settings = {"tasks": [t.model_dump(mode="json") for t in tasks], "options": asdict(options),
                "output_dir": str(output), "profile_dir": str(ROOT / "data/browser/boss")}
    save(output / "settings.json", settings)
    save(output / "search-plan.json", settings["tasks"])
    update_project(project_id, last_run=run_id, origin="collected")
    command_id = enqueue("collect", settings)
    progress(message="正在搜索，请保留专用 BOSS 窗口", total=limits.max_jobs_total)
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline:
        result = read(BROWSER / "results" / (command_id + ".json"))
        run = read(output / "run.json", {})
        if result:
            if result["status"] == "error":
                raise ValueError(result["message"])
            status = run.get("status", "error")
            task_status = "completed" if status in {"completed", "limit_reached"} else ("cancelled" if status == "cancelled" else "partial")
            descriptions = {"needs_login": "需要重新登录，请在 BOSS 窗口扫码后重新搜索",
                            "needs_verification": "遇到 BOSS 验证，请手动完成后重新搜索",
                            "cancelled": "已停止采集，已保存的岗位和浏览器保留"}
            if auto_match and status in {"completed", "limit_reached"} and run.get("job_count", 0):
                # 同一任务切换阶段，采集和匹配之间不释放简历任务锁。
                progress(kind="match", source_kind="collect", phase="matching", status="running",
                         current=0, total=0, collection_run=run_id, collection_count=run["job_count"],
                         message=f"采集完成，已保存 {run['job_count']} 个岗位，正在自动匹配；BOSS 窗口保留")
                match(project_id, progress)
                return
            progress(status=task_status, current=run.get("job_count", 0), finished_at=now(),
                     message=descriptions.get(status, f"采集结束，已保存 {run.get('job_count', 0)} 个岗位；BOSS 窗口保留"))
            return
        paused = run.get("status") == "paused"
        progress(status="paused" if paused else "running", current=run.get("job_count", 0),
                 message="采集已暂停，可继续或停止" if paused else f"正在采集，已保存 {run.get('job_count', 0)} 个岗位")
        time.sleep(1)
    raise ValueError("采集超过2小时，界面监控已停止；浏览器与已保存岗位仍保留。")


def match(project_id, progress):
    directory = project_dir(project_id)
    meta = read(directory / "project.json")
    resume, rules = read(directory / "resume.json"), MatchingRules.model_validate(read(directory / "rules.json"))
    jobs, ai = [j for j in project_jobs(directory, meta) if not j["excluded"]], client()
    if not resume or not jobs:
        raise ValueError("请先解析简历并采集岗位。")
    failures = []
    save(directory / "match-errors.json", {})
    progress(message=f"正在匹配累计岗位，共 {len(jobs)} 个（最多同时2个）", total=len(jobs))
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="autoboss-match") as pool:
        pending = {pool.submit(match_job, resume, job, meta["preferences"], rules, ai, directory / "match-cache"): job for job in jobs}
        for index, future in enumerate(as_completed(pending), 1):
            job = pending[future]
            try:
                result = future.result()
                with LOCK:
                    matches = read(directory / "matches.json", {})
                    matches[job["id"]] = result
                    save(directory / "matches.json", matches)
            except Exception as exc:
                failures.append(f"{job['title']}：{exc}")
                with LOCK:
                    errors = read(directory / "match-errors.json", {})
                    errors[job["id"]] = {"title": job["title"], "message": str(exc), "failed_at": now()}
                    errors[job["id"]].update(code=getattr(exc, "code", type(exc).__name__),
                                             fields=getattr(exc, "fields", []),
                                             cause=type(exc.__cause__).__name__ if exc.__cause__ else None)
                    save(directory / "match-errors.json", errors)
            progress(message=f"已处理 {index}/{len(jobs)}：{job['title']}" + (f"；{len(failures)} 个失败" if failures else ""), current=index, total=len(jobs))
    progress(status="partial" if failures else "completed", current=len(jobs), finished_at=now(),
             message=f"完成 {len(jobs) - len(failures)}/{len(jobs)} 个岗位匹配" + (f"；{failures[0]}" if failures else "，已按匹配度排序"))


def reweight(project_id, old_rules, new_rules):
    """只调整权重或完整度阈值时，复用已经核验的逐维度分析。"""
    def analysis_rules(rules):
        return {"prompt": rules.prompt, "dimensions": [d.model_dump(exclude={"weight"}) for d in rules.dimensions]}
    if analysis_rules(old_rules) != analysis_rules(new_rules):
        return 0
    directory = project_dir(project_id)
    meta = read(directory / "project.json")
    resume, matches = read(directory / "resume.json"), read(directory / "matches.json", {})
    if not resume:
        return 0
    model, count = client().config.model, 0
    for job in project_jobs(directory, meta):
        result = matches.get(job["id"])
        if not result or result.get("cache_key") != cache_key(resume, job, meta["preferences"], old_rules, model):
            continue
        assessment = Assessment(summary=result["summary"], dimensions=[
            DimensionAssessment.model_validate({k:v for k,v in item.items() if k in DimensionAssessment.model_fields})
            for item in result["dimensions"]])
        key = cache_key(resume, job, meta["preferences"], new_rules, model)
        updated = {**result, **calculate(assessment, resume, new_rules), "cache_key": key,
                   "rules_version": fingerprint(new_rules.model_dump()), "reweighted_at": now()}
        matches[job["id"]] = updated
        save(directory / "match-cache" / (key + ".json"), updated)
        count += 1
    save(directory / "matches.json", matches)
    return count
