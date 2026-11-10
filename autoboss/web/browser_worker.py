"""浏览器始终由同一线程操作，任务结束后保留窗口并接受下一次采集。"""

import fcntl
import os
import time
from pathlib import Path

from autoboss.boss.browser import BOSS_ENTRY_URL, BOSS_LOGIN_URL, BrowserSession, page_state, switch_to_qr_login
from autoboss.boss.worker import Collector, CollectionPaused, now
from autoboss.boss.auth import has_login_cookies, save_auth
from .browser import BROWSER
from .store import ROOT, read, save


class BrowserWorker:
    def __init__(self):
        self.session = None
        self.last_status = 0
        self.last_auth_save = 0

    def status(self, status=None, message=None):
        previous = read(BROWSER / "status.json", {})
        previous.update(pid=os.getpid(), updated_at=now())
        if status:
            previous["status"] = status
        if message:
            previous["message"] = message
        if self.session and not self.session.closed:
            previous["url"] = self.session.page.url
        else:
            previous.pop("url", None)
        save(BROWSER / "status.json", previous)

    def connect(self, entry_url=None):
        if self.session and not self.session.closed:
            return
        self.status("connecting", "正在打开网页专用 BOSS 窗口")
        # 网页和命令行始终复用已经登录过的专用目录。
        self.session = BrowserSession(ROOT / "data/browser/boss")
        self.session.__enter__()
        page = self.session.page
        page.goto(entry_url or BOSS_ENTRY_URL, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(1800)
        state, data = page_state(page, "search")
        if state == "needs_verification":
            self.status(state, "请在专用 BOSS 窗口手动完成验证")
        elif not data["authenticated"] and has_login_cookies(self.session.context):
            self.status("checking", "已有登录资料，正在检查网页状态；不重复打开扫码页")
        elif not data["authenticated"]:
            page.goto(BOSS_LOGIN_URL, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(800)
            switch_to_qr_login(page)
            self.status("needs_login", "请在新打开的专用 BOSS 窗口使用 APP 扫码登录")
        else:
            save_auth(self.session.context, self.session.profile_dir)
            self.status("ready", "BOSS 已连接，可以开始采集")
        self.observe()

    def observe(self):
        if self.session and not self.session.closed:
            self.session.page.screenshot(path=str(BROWSER / "current.png"))
            state, data = page_state(self.session.page, "search")
            save(BROWSER / "observation.json", {"url": self.session.page.url, "state": state,
                "authenticated": data["authenticated"], "observed_at": now()})

    def collect(self, settings):
        self.connect()
        _, data = page_state(self.session.page, "search")
        if not data["authenticated"]:
            raise ValueError("请先在专用 BOSS 窗口扫码登录，再点击开始搜索岗位。")
        self.status("collecting", "正在按已保存条件采集岗位")
        collector = Collector(settings)
        collector.pause_file = Path(settings["output_dir"]) / "pause"
        collector.cancel_file = Path(settings["output_dir"]) / "cancel"
        collector.save()
        try:
            collector.collect_in_session(self.session)
        except CollectionPaused as exc:
            collector.run["status"] = str(exc)
        except Exception as exc:
            collector.run["status"] = "error"
            collector.run["errors"].append({"stage": "collection", "error": str(exc)[:300]})
        finally:
            collector.run.update(finished_at=now(), browser_status="open")
            collector.save()
            save_auth(self.session.context, self.session.profile_dir)
            self.status("ready", "采集结束，BOSS 窗口已保留")
            self.observe()
        return collector.run

    def tick(self):
        if not self.session or self.session.closed:
            if self.session:
                self.session.__exit__()
            self.session = None
            self.status("disconnected", "连接 BOSS 后可开始采集")
            time.sleep(0.2)
            return
        self.session.page.wait_for_timeout(200)
        if time.monotonic() - self.last_status < 2:
            return
        self.last_status = time.monotonic()
        state, data = page_state(self.session.page, "search")
        if state == "needs_verification":
            self.status(state, "请在专用 BOSS 窗口手动完成验证")
        elif data["authenticated"]:
            if time.monotonic() - self.last_auth_save > 60:
                save_auth(self.session.context, self.session.profile_dir)
                self.last_auth_save = time.monotonic()
            self.status("ready", "BOSS 已连接，可以开始采集")
        elif state == "needs_login":
            self.status(state, "请在专用 BOSS 窗口扫码登录")
        else:
            self.status()

    def run(self):
        self.status("disconnected", "连接 BOSS 后可开始采集")
        while True:
            commands = sorted((BROWSER / "commands").glob("*.json"))
            if commands:
                path = commands[0]
                command = read(path)
                try:
                    if command["kind"] == "collect":
                        result = self.collect(command["payload"])
                    elif command["kind"] == "observe":
                        result = self.observe()
                    else:
                        result = self.connect(command["payload"].get("entry_url"))
                    save(BROWSER / "results" / (command["id"] + ".json"), {"status": "completed", "result": result})
                except Exception as exc:
                    save(BROWSER / "results" / (command["id"] + ".json"), {"status": "error", "message": str(exc)[:400]})
                    self.status("error", str(exc)[:200])
                    if self.session and self.session.closed:
                        self.session = None
                finally:
                    path.unlink(missing_ok=True)
            try:
                self.tick()
            except Exception:
                if self.session and self.session.closed:
                    self.session.__exit__()
                    self.session = None
                time.sleep(0.5)


if __name__ == "__main__":
    BROWSER.mkdir(parents=True, exist_ok=True)
    with (BROWSER / "owner.lock").open("w") as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(0)
        BrowserWorker().run()
