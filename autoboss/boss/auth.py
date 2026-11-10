"""固定浏览器目录之外，额外保存本站登录状态供下次恢复。"""

import json
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from autoboss.common.storage import json_text, write_files


LOGIN_COOKIES = {"bst", "wt2", "zp_at", "geek_zp_token"}


def site_cookie(cookie):
    domain = cookie.get("domain", "").lstrip(".").lower()
    return domain == "zhipin.com" or domain.endswith(".zhipin.com")


def usable(cookie):
    expiry = cookie.get("expires", -1)
    return site_cookie(cookie) and cookie.get("value") and (expiry == -1 or expiry > time.time())


def has_login_cookies(context):
    """凭证存在只说明可尝试复用，不代表服务端仍认可这次登录。"""
    return any(c.get("name") in LOGIN_COOKIES and usable(c) for c in context.cookies())


def save_auth(context, profile_dir):
    state = context.storage_state()
    cookies = [c for c in state["cookies"] if site_cookie(c)]
    if not any(c["name"] in LOGIN_COOKIES and usable(c) for c in cookies):
        return False
    origins = [o for o in state.get("origins", []) if urlsplit(o["origin"]).hostname == "www.zhipin.com"]
    folder = profile_dir / "autoboss-auth"
    folder.mkdir(mode=0o700, exist_ok=True)
    folder.chmod(0o700)
    # 不输出 Cookie 内容，也不通过网页接口返回认证文件。
    write_files({folder / "state.json": json_text({"cookies": cookies, "origins": origins}),
                 folder / "metadata.json": json_text({"saved_at": datetime.now(timezone.utc).isoformat(),
                                                       "cookie_count": len(cookies)})}, force=True)
    return True


def restore_auth(context, profile_dir):
    path = profile_dir / "autoboss-auth/state.json"
    if not path.is_file() or has_login_cookies(context):
        return False
    try:
        state = json.loads(path.read_text())
        cookies = [c for c in state.get("cookies", []) if usable(c)]
        if not any(c["name"] in LOGIN_COOKIES for c in cookies):
            return False
        context.add_cookies(cookies)
        origins = {o["origin"]: o.get("localStorage", []) for o in state.get("origins", [])
                   if o.get("origin") == "https://www.zhipin.com"}
        script = """(() => {
            const origins = __STATE__;
            for (const item of origins[location.origin] || []) {
                if (localStorage.getItem(item.name) === null) localStorage.setItem(item.name, item.value);
            }
        })();""".replace("__STATE__", json.dumps(origins))
        context.add_init_script(script=script)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False
