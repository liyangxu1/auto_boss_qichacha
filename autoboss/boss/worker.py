"""在 AutoBOSS 的 Patchright 环境中执行只读采集，逐条保存进度。"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from patchright.sync_api import TimeoutError as BrowserTimeoutError

from autoboss.common.storage import json_text, write_files
from .browser import BOSS_ENTRY_URL, BrowserSession, boss_url, page_state, wait_content
from .capture import DetailCapture
from .extract import (CARD_SELECTOR, company_summary, is_detail_response, qualification,
                      read_cards, read_company, read_job, record_id)
from .network import check_direct_network
from .auth import save_auth


def now():
    return datetime.now(timezone.utc).isoformat()


class Collector:
    def __init__(self, settings):
        self.settings = settings
        self.output = Path(settings["output_dir"])
        self.options = settings["options"]
        self.jobs, self.companies = {}, {}
        self.company_attempted = set()
        self.run = {"mode": "collect_only", "status": "running", "started_at": now(),
                    "network": check_direct_network(), "errors": [],
                    "queries": [{"search": task, "status": "pending", "card_count": 0,
                                 "filters_in_url": False} for task in settings["tasks"]]}

    def save(self):
        self.run.update(updated_at=now(), job_count=len(self.jobs), company_count=len(self.companies))
        # 每个岗位直接附带公司信息，同时保留独立公司列表供后续分析复用。
        jobs = [{**job, "company": self.companies.get(job["company_id"])} for job in self.jobs.values()]
        write_files({self.output / "jobs.json": json_text(jobs),
                     self.output / "companies.json": json_text(list(self.companies.values())),
                     self.output / "run.json": json_text(self.run)}, force=True)

    def diagnostic(self, page, name):
        folder = self.output / "diagnostics"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            write_files({folder / (name + ".txt"): page.locator("body").inner_text(timeout=3000)}, force=True)
            page.screenshot(path=str(folder / (name + ".png")))
        except Exception:
            pass

    def visit(self, page, url, kind):
        check_direct_network()
        response = page.goto(url, wait_until="domcontentloaded", timeout=self.options["timeout_seconds"] * 1000)
        if response and response.status >= 400:
            return "page_unavailable", {"url": page.url, "text": ""}
        def waiting(state):
            self.run["status"] = state
            self.save()
        state, data = wait_content(page, kind, seconds=self.options["timeout_seconds"],
                                  manual_wait=self.options["manual_wait_seconds"], on_wait=waiting)
        if state == "authenticated" or (state == "ready" and kind == "search"
                and parse_qs(urlsplit(page.url).query) != parse_qs(urlsplit(url).query)):
            # 登录后可能回到首页，重新打开原搜索地址，避免把首页推荐当作筛选结果。
            page.goto(url, wait_until="domcontentloaded", timeout=self.options["timeout_seconds"] * 1000)
            state, data = wait_content(page, kind, seconds=self.options["timeout_seconds"],
                                      manual_wait=self.options["manual_wait_seconds"], on_wait=waiting)
        if state in {"ready", "no_results"}:
            self.run["status"] = "running"
        return state, data

    def add_job(self, card, detail, task, status):
        url = boss_url(detail.get("url") or "") or boss_url(card.get("url") or "")
        name = detail.get("company_name") or card.get("company_name")
        company_url = boss_url(detail.get("company_url") or card.get("company_url") or "", ("/gongsi/",))
        job_id = record_id(url, "|".join(str(card.get(k) or "") for k in ["title", "company_name", "area", "salary"]))
        anonymous = bool(name and (name.startswith("某") or any(s in name for s in ["某大型", "某中型", "某小型"])))
        # 匿名招聘的同名占位公司不代表同一雇主，不能按名称跨岗位合并。
        company_key = f"{name}|{job_id}" if anonymous else name
        company_id = record_id(company_url, company_key) if name or company_url else None
        exp, degree = qualification((detail.get("primary_text") or "") + " " + " ".join(card.get("tags") or []))
        record = {"id": job_id, "url": url or task["url"], "title": detail.get("title") or card["title"],
                  "salary": detail.get("salary") or card.get("salary"), "city": detail.get("city") or task["city"],
                  "area": card.get("area"), "address": detail.get("address"),
                  "experience": detail.get("experience") or exp, "education": detail.get("education") or degree,
                  "description": detail.get("description"), "tags": detail.get("tags") or card.get("tags") or [],
                  "recruitment_status": detail.get("recruitment_status"),
                  "benefits": detail.get("benefits") or [], "company_id": company_id, "company_name": name,
                  "source_kind": detail.get("source_kind") or ("page" if detail else "list"),
                  "access_limited": detail.get("access_limited", False),
                  "detail_status": status, "collected_at": now(), "source_text_file": None, "searches": [task]}
        if record["salary"] and any(0xE000 <= ord(char) <= 0xF8FF for char in record["salary"]):
            # 页面字体混淆字符不作为薪资值，优先使用详情响应中的明文。
            record["salary"] = None
            record["access_limited"] = True
            record["detail_status"] = "list_only"
        allowed = {"在校生", "应届生", "在校/应届"} if task["experience"] == "在校/应届" else {task["experience"]}
        if detail.get("city") and task["city"].removesuffix("市") not in detail["city"]:
            print(f"跳过城市不符合筛选的岗位：{record['title']}（{record['city']}）", flush=True)
            return None
        if record["experience"] and task["experience_code"] and record["experience"] not in allowed:
            print(f"跳过经验不符合筛选的岗位：{record['title']}（{record['experience']}）", flush=True)
            return None
        if job_id in self.jobs:
            if task not in self.jobs[job_id]["searches"]:
                self.jobs[job_id]["searches"].append(task)
            return self.jobs[job_id]
        raw = detail.get("text") or card.get("text") or ""
        if raw:
            suffix = "json" if detail.get("response_data") else "txt"
            relative = Path("pages") / f"job-{job_id}.{suffix}"
            write_files({self.output / relative: raw}, force=True)
            record["source_text_file"] = str(relative)
        self.jobs[job_id] = record
        if company_id:
            if company_id not in self.companies:
                financing, size = company_summary(detail.get("company_text"))
                self.companies[company_id] = {"id": company_id, "name": name, "anonymous": anonymous, "url": company_url,
                    "industry": None, "financing": financing, "size": size,
                    "description": detail.get("company_description"), "address": None, "website": None,
                    "business_info": {}, "job_ids": [], "detail_status": "summary_only",
                    "collected_at": now(), "source_text_file": None}
            company = self.companies[company_id]
            # 原项目在同一个岗位详情响应的 brandComInfo 中读取公司信息。
            for key, value in (detail.get("company") or {}).items():
                if key in company and value:
                    company[key] = value
            if detail.get("company"):
                company["source_text_file"] = record["source_text_file"]
            if job_id not in company["job_ids"]:
                company["job_ids"].append(job_id)
        return record

    def collect_company(self, page, record):
        company_id = record["company_id"]
        if not company_id:
            return
        company = self.companies[company_id]
        if not company["url"] or company_id in self.company_attempted:
            return
        self.company_attempted.add(company_id)
        page.wait_for_timeout(self.options["request_delay_seconds"] * 1000)
        state, _ = self.visit(page, company["url"], "company")
        if state != "ready":
            self.diagnostic(page, "company-" + company_id)
            self.run["errors"].append({"stage": "company", "id": company_id, "status": state})
            if state in {"needs_login", "needs_verification"}:
                raise CollectionPaused(state)
            return
        data = read_company(page)
        financing, size = company_summary(data.get("primary_text"))
        for key in ["name", "industry", "description", "address", "website", "business_info"]:
            if data.get(key):
                company[key] = data[key]
        company["financing"] = data.get("financing") or financing or company["financing"]
        company["size"] = data.get("size") or size or company["size"]
        company["detail_status"] = "complete" if company.get("description") else "summary_only"
        company["collected_at"] = now()
        relative = Path("pages") / f"company-{company_id}.txt"
        write_files({self.output / relative: data["text"]}, force=True)
        company["source_text_file"] = str(relative)

    def checkpoint(self, page):
        """在岗位边界响应暂停和停止，保留浏览器与已保存内容。"""
        cancel = getattr(self, "cancel_file", None)
        pause = getattr(self, "pause_file", None)
        if cancel and cancel.exists():
            raise CollectionPaused("cancelled")
        while pause and pause.exists():
            if self.run["status"] != "paused":
                self.run["status"] = "paused"
                self.save()
            if cancel and cancel.exists():
                raise CollectionPaused("cancelled")
            page.wait_for_timeout(300)
        if self.run["status"] == "paused":
            self.run["status"] = "running"
            self.save()

    def collect_query(self, session, query):
        self.checkpoint(session.page)
        task = query["search"]
        print(f"搜索：{task['city']} / {task['keyword']} / {task['experience']}", flush=True)
        page = session.page
        self.capture.responses.clear()
        self.capture.parsed.clear()
        state, _ = self.visit(page, task["url"], "search")
        if state != "ready":
            query["status"] = state
            if state != "no_results":
                self.diagnostic(page, "search-" + hashlib.sha256(task["url"].encode()).hexdigest()[:12])
            if state in {"needs_login", "needs_verification"}:
                raise CollectionPaused(state)
            return
        actual = parse_qs(urlsplit(page.url).query)
        query["filters_in_url"] = (actual.get("city") == [task["city_code"]]
            and actual.get("query") == [task["keyword"]]
            and (not task["experience_code"] or actual.get("experience") == [task["experience_code"]]))
        if not query["filters_in_url"]:
            query["status"] = "filters_unconfirmed"
            self.diagnostic(page, "filters-unconfirmed")
            return
        cards = read_cards(page)
        for _ in range(self.options["max_scroll_rounds"]):
            if len(cards) >= self.options["max_jobs_per_search"]:
                break
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(self.options["request_delay_seconds"] * 1000)
            updated = read_cards(page)
            if len(updated) <= len(cards):
                break
            cards = updated
        query["card_count"] = len(cards)
        company_page = session.context.new_page() if self.options["collect_company_details"] else None
        try:
            for index, card in enumerate(cards[:self.options["max_jobs_per_search"]]):
                self.checkpoint(page)
                if len(self.jobs) >= self.options["max_jobs_total"]:
                    query["status"] = "limit_reached"
                    return
                page.wait_for_timeout(self.options["request_delay_seconds"] * 1000)
                url = boss_url(card.get("url") or "")
                if url and record_id(url, "") in self.jobs:
                    old = self.jobs[record_id(url, "")]
                    if task not in old["searches"]:
                        old["searches"].append(task)
                    self.save()
                    continue
                try:
                    data = self.capture.find(card)
                    target = page
                    opened = []
                    if not data:
                        if not page.locator(CARD_SELECTOR).count():
                            state, _ = self.visit(page, task["url"], "search")
                            if state != "ready":
                                raise CollectionPaused(state)
                        # 首个岗位可能默认展开；参照原项目先切第二个，再切回第一个。
                        if index == 0 and len(cards) > 1:
                            page.locator(CARD_SELECTOR).nth(1).locator("a.job-name,.job-name,.job-title").first.click()
                            page.wait_for_timeout(600)
                        # 仅点击职位标题，禁止使用通用按钮或“沟通/投递”定位器。
                        before = list(session.context.pages)
                        since = len(self.capture.responses)
                        control = page.locator(CARD_SELECTOR).nth(card["index"]).locator("a.job-name,.job-name,.job-title").first
                        try:
                            with page.expect_response(lambda response: is_detail_response(response), timeout=5000):
                                control.click(timeout=5000)
                        except BrowserTimeoutError:
                            # 已展开的详情可能不再请求接口，随后仅检查当前页面可见内容。
                            pass
                        page.wait_for_timeout(500)
                        opened = [p for p in session.context.pages if p not in before]
                        target = opened[0] if opened else page
                        data = self.capture.find(card, since)
                    state, _ = page_state(target, "job")
                    if state in {"needs_login", "needs_verification"}:
                        raise CollectionPaused(state)
                    if not data:
                        state, _ = wait_content(target, "job", self.options["timeout_seconds"],
                                                self.options["manual_wait_seconds"])
                        if state in {"needs_login", "needs_verification"}:
                            raise CollectionPaused(state)
                        visible = read_job(target) if state == "ready" else {}
                        visible["url"] = boss_url(target.url) or url
                        data = visible if visible.get("title") and DetailCapture.matches(card, visible) else {}
                    for popup in opened:
                        popup.close()
                    if not data:
                        self.run["errors"].append({"stage": "job", "title": card["title"], "status": "detail_unavailable"})
                    status = "complete" if data.get("description") and not data.get("access_limited") else "list_only"
                    record = self.add_job(card, data, task, status)
                    if record:
                        self.save()
                        print(f"已采集 {len(self.jobs)} 个岗位：{record['title']}", flush=True)
                        if company_page:
                            self.collect_company(company_page, record)
                except CollectionPaused:
                    raise
                except Exception as exc:
                    self.run["errors"].append({"stage": "job", "title": card["title"], "error": str(exc)[:300]})
                    self.add_job(card, {}, task, "list_only")
                self.save()
            query["status"] = "sampled" if len(cards) > self.options["max_jobs_per_search"] else "completed"
        finally:
            if company_page:
                company_page.close()

    def collect_in_session(self, session):
        """复用同一浏览器会话，供命令行和网页共同调用。"""
        with DetailCapture(session.context) as capture:
            self.capture = capture
            # 参照原项目，先进入岗位入口建立会话，再执行城市和经验筛选。
            entry_state, _ = self.visit(session.page, BOSS_ENTRY_URL, "search")
            if entry_state not in {"ready", "no_results"}:
                self.diagnostic(session.page, "entry")
                raise CollectionPaused(entry_state)
            for index, query in enumerate(self.run["queries"]):
                if index >= self.options["max_searches"] or len(self.jobs) >= self.options["max_jobs_total"]:
                    self.run["status"] = "limit_reached"
                    break
                try:
                    self.collect_query(session, query)
                except CollectionPaused as exc:
                    query["status"] = str(exc)
                    self.run["status"] = str(exc)
                    break
                except Exception as exc:
                    query["status"] = "error"
                    self.run["errors"].append({"stage": "search", "error": str(exc)[:300]})
                self.save()
            else:
                self.run["status"] = "completed"
        if self.run["status"] == "completed" and (self.run["errors"] or any(
                q["status"] not in {"completed", "sampled", "no_results"} for q in self.run["queries"])):
            self.run["status"] = "partial"
        if self.run["status"] == "completed" and any(j["detail_status"] != "complete" for j in self.jobs.values()):
            self.run["status"] = "partial"

    def execute(self):
        self.save()
        session = None
        try:
            session = BrowserSession(self.settings["profile_dir"], channel=self.options["browser_channel"],
                                     timeout_ms=self.options["timeout_seconds"] * 1000)
            session.__enter__()
            self.collect_in_session(session)
        except CollectionPaused as exc:
            self.run["status"] = str(exc)
        except KeyboardInterrupt:
            self.run["status"] = "stopped"
        except Exception as exc:
            self.run["status"] = "error"
            self.run["errors"].append({"stage": "browser", "error": str(exc)[:300]})
        finally:
            self.run["finished_at"] = now()
            self.save()
        print(f"采集结束：{self.run['status']}，岗位 {len(self.jobs)}，公司 {len(self.companies)}。", flush=True)
        print(f"岗位列表：{self.output / 'jobs.json'}", flush=True)
        try:
            if (session and session.context and not session.closed and self.run["status"] != "stopped"
                    and self.options.get("keep_browser_open", True)):
                save_auth(session.context, session.profile_dir)
                # 先保存结果，再等待用户关闭；浏览器等待时间不计入采集耗时。
                self.run["browser_status"] = "open"
                self.save()
                session.wait_until_closed()
        finally:
            if session:
                session.__exit__()
            self.run["browser_status"] = "closed"
            self.save()
        return self.run


class CollectionPaused(Exception):
    """遇到需要人工处理的登录或验证时保留已采集数据。"""


if __name__ == "__main__":
    settings = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Collector(settings).execute()
