"""连接本机浏览器，使用独立用户目录保留 BOSS 登录状态。"""

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from patchright.sync_api import sync_playwright

from .network import check_direct_network, direct_environment
from .auth import restore_auth, save_auth


BOSS_ENTRY_URL = "https://www.zhipin.com/web/geek/jobs"
BOSS_LOGIN_URL = "https://www.zhipin.com/web/user/?ka=header-login"
QR_SWITCH_SELECTORS = (".btn-sign-switch.ewm-switch", "li.sign-switch-tip")


class BrowserSession:
    def __init__(self, profile_dir, *, channel="chrome", timeout_ms=30000):
        self.profile_dir = Path(profile_dir)
        self.channel, self.timeout_ms = channel, timeout_ms
        self.playwright = None
        self.context = None
        self.closed = False

    def __enter__(self):
        try:
            check_direct_network()
            self._prepare_profile()
            self.playwright = sync_playwright().start()
            # 参照 get_jobs 的 PlaywrightManager，使用同版本 Patchright 持久化会话。
            self.context = self.playwright.chromium.launch_persistent_context(
                str(self.profile_dir.resolve()), channel=self.channel, headless=False,
                no_viewport=True, chromium_sandbox=True, slow_mo=50,
                env=direct_environment(), timeout=self.timeout_ms,
                args=["--no-proxy-server", "--proxy-bypass-list=*", "--no-first-run",
                      "--no-default-browser-check", "--disable-session-crashed-bubble",
                      "--hide-crash-restore-bubble", "--test-type"],
            )
            self.context.set_default_timeout(self.timeout_ms)
            self.context.on("close", lambda _: setattr(self, "closed", True))
            restore_auth(self.context, self.profile_dir)
            # 拦截沟通、发送简历和投递动作；采集代码只导航、阅读和滚动。
            self.context.route(re.compile(r"/wapi/.*(?:friend/add|chat/send|resume/(?:send|deliver)|job/(?:apply|deliver))"),
                               lambda route: route.abort())
            # 原项目明确不复用启动标签页，业务页创建完成后关闭启动空白页。
            startup_pages = list(self.context.pages)
            self.page = self.context.new_page()
            for startup in startup_pages:
                startup.close()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _prepare_profile(self):
        paths = {
            "chrome": Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            "msedge": Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        }
        executable = paths.get(self.channel)
        if executable is None or not executable.is_file():
            raise ValueError("没有找到已有浏览器，请选择已安装的 chrome 或 msedge；不会自动下载。")
        self.profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.profile_dir / "SingletonLock"
        if lock.is_symlink():
            try:
                pid = int(str(lock.readlink()).rsplit("-", 1)[1])
                os.kill(pid, 0)
            except ProcessLookupError:
                # 仅清理由已经退出的专用浏览器留下的锁，不碰日常浏览器目录。
                for name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
                    (self.profile_dir / name).unlink(missing_ok=True)
            except (ValueError, PermissionError):
                raise ValueError("无法确认采集浏览器的锁是否失效，请先关闭专用采集窗口。") from None
            else:
                raise ValueError("专用浏览器目录正在使用，请先关闭该采集窗口。")
        # 仅修复本项目专用目录的崩溃标记，避免恢复提示框阻塞页面控制。
        preferences = self.profile_dir / "Default" / "Preferences"
        if preferences.is_file():
            data = json.loads(preferences.read_text(encoding="utf-8"))
            profile = data.get("profile")
            if isinstance(profile, dict) and (profile.get("exit_type") != "Normal"
                                             or not profile.get("exited_cleanly", True)):
                profile.update(exit_type="Normal", exited_cleanly=True)
                temporary = preferences.with_name("Preferences.autoboss.tmp")
                temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                temporary.replace(preferences)

    def __exit__(self, *args):
        try:
            if self.context:
                if not self.closed:
                    save_auth(self.context, self.profile_dir)
                self.context.close()
        except Exception:
            pass
        finally:
            if self.playwright:
                self.playwright.stop()

    def wait_until_closed(self):
        """采集结果已保存后保留页面，由用户关闭窗口结束等待。"""
        print("采集结果已保存，浏览器保持打开；手动关闭专用窗口后程序退出。", flush=True)
        while not self.closed and self.context.pages:
            try:
                self.context.pages[0].wait_for_timeout(500)
            except Exception:
                if self.closed or not self.context.pages:
                    break
                raise


def switch_to_qr_login(page):
    """查看登录页后显式调用；选择器参照 get_jobs 的登录引导实现。"""
    state, _ = page_state(page, "search")
    if state != "needs_login":
        return False
    for selector in QR_SWITCH_SELECTORS:
        control = page.locator(selector).first
        if control.is_visible():
            control.click(timeout=3000)
            return True
    return False


def boss_url(url: str, kinds=("/job_detail/", "/gongsi/")) -> str | None:
    parsed = urlsplit(url)
    if (parsed.scheme == "https" and parsed.hostname == "www.zhipin.com"
            and not parsed.username and not parsed.password and any(parsed.path.startswith(k) for k in kinds)):
        return url
    return None


def page_state(page, kind):
    """识别登录、验证、空结果和正常内容；空白页不会当成采集成功。"""
    data = page.evaluate("""() => {
      const visible = s => [...document.querySelectorAll(s)].some(e => e.getClientRects().length > 0);
      return {url:location.href, text:(document.body?.innerText || '').slice(0,80000),
        captcha:visible('iframe[src*="captcha"], iframe[src*="verify"], .geetest_panel, #captcha, .verify-wrap'),
        login:visible('.sign-form, .sign-wrap, .login-dialog, .dialog-login, .btn-sign-switch, li.sign-switch-tip'),
        cards:[...document.querySelectorAll('li.job-card-box, li.job-card-wrapper')].filter(e=>e.querySelector('.job-name,.job-title')?.textContent?.trim()).length,
        description:[...document.querySelectorAll('.job-sec-text,.job-detail-section')].some(e=>e.getClientRects().length && e.innerText.trim().length>30),
        company:visible('.company-banner, .company-info, .company-introduction, .company-home'),
        authenticated:visible('.nav-figure img, a[href*="/web/geek/resume"]')};
    }""")
    text, url = data["text"], data["url"]
    if data["captcha"] or any(s in url for s in ["security-check", "captcha", "verify"]):
        return "needs_verification", data
    if len(text) < 2500 and any(s in text for s in ["您的访问行为异常", "请完成安全验证", "访问过于频繁"]):
        return "needs_verification", data
    if data["login"] or "/web/user/" in url:
        return "needs_login", data
    if (not data["authenticated"] and ((not data["cards"] and "尝试登录查看全部职位" in text)
            or (kind == "job" and "登录查看完整内容" in text))):
        return "needs_login", data
    if kind == "search" and any(s in text for s in ["没有找到相关职位", "暂无符合条件的职位", "没有符合条件的职位"]):
        return "no_results", data
    if ((kind == "search" and data["cards"]) or (kind == "job" and data["description"])
            or (kind == "company" and data["company"] and len(text) > 200)):
        return "ready", data
    return "loading", data


def wait_content(page, kind, seconds=25, manual_wait=0, on_wait=None):
    deadline = time.monotonic() + seconds
    prompted = False
    state, data = "loading", {"url": page.url, "text": ""}
    while time.monotonic() < deadline:
        try:
            state, data = page_state(page, kind)
        except Exception:
            page.wait_for_timeout(400)
            continue
        if state in {"ready", "no_results"}:
            return state, data
        if prompted and data.get("authenticated") and state not in {"needs_login", "needs_verification"}:
            return "authenticated", data
        if state in {"needs_login", "needs_verification"}:
            if manual_wait and not prompted:
                print("需要手动登录或完成验证，请在采集浏览器中操作；程序不会处理验证码。", flush=True)
                if on_wait:
                    on_wait(state)
                deadline = time.monotonic() + manual_wait
                prompted = True
            elif not manual_wait:
                return state, data
        # 同步驱动在等待时仍需派发网络路由、页面跳转等事件。
        page.wait_for_timeout(500)
    return (state if state != "loading" else "page_unavailable"), data
