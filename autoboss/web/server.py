"""复用当前 Conda 环境启动、查看或停止本机 Web 服务。"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .store import DATA, ROOT, read, save


URL = "http://127.0.0.1:8765"


def healthy():
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL + "/api/health", timeout=2) as response:
            return json.load(response).get("service") == "autoboss-workbench"
    except (OSError, ValueError):
        return False


def server_alive(pid):
    if not pid:
        return False
    result = subprocess.run(["ps", "-p", str(pid), "-o", "stat=,command="], capture_output=True, text=True)
    return bool(result.stdout.strip() and not result.stdout.lstrip().startswith("Z")
                and "autoboss.web.app:app" in result.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(description="管理本地 AutoBOSS 工作台")
    parser.add_argument("action", choices=["start", "stop", "status"], nargs="?", default="start")
    action = parser.parse_args(argv).action
    pidfile = DATA / "server.json"
    if action == "status":
        print(f"{'运行中' if healthy() else '未运行'}：{URL}")
        return
    if action == "stop":
        state = read(pidfile, {})
        pid = state.get("pid")
        if not pid:
            print("没有由启动脚本管理的服务进程。")
            return
        # 仅停止本启动器记录、且命令确为工作台的进程，浏览器进程独立保留。
        if server_alive(pid):
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if not server_alive(pid):
                    break
                time.sleep(.1)
            else:
                print("工作台正在退出，等待当前请求结束；请稍后查看状态。BOSS 窗口保留。")
                return
            print("工作台已停止，BOSS 窗口保留。")
        pidfile.unlink(missing_ok=True)
        return
    if healthy():
        print(f"工作台已运行：{URL}")
        return
    if server_alive(read(pidfile, {}).get("pid")):
        raise SystemExit("上次服务仍在退出，请等待当前模型请求结束后再启动，避免同时写入结果。")
    if os.path.basename(sys.prefix) != "AutoBOSS":
        raise SystemExit("请在现有 AutoBOSS Conda 环境中启动。")
    if not (ROOT / "autoboss/web/static/index.html").is_file():
        raise SystemExit("前端尚未构建，请在 frontend 目录运行 npm run build。")
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "server.log").open("a") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "autoboss.web.app:app", "--host", "127.0.0.1",
                                    "--port", "8765", "--no-access-log"], cwd=ROOT, stdout=log, stderr=log,
                                   start_new_session=True)
    save(pidfile, {"pid": process.pid, "url": URL})
    for _ in range(50):
        if healthy():
            print(f"工作台已启动：{URL}\n日志：{DATA / 'server.log'}")
            return
        if process.poll() is not None:
            break
        time.sleep(.2)
    raise SystemExit(f"工作台启动失败，请查看 {DATA / 'server.log'}。")


if __name__ == "__main__":
    main()
