"""为 BOSS 请求隔离代理设置，不修改系统代理或 Clash 配置。"""

import os
import re
import urllib.request
from pathlib import Path


def direct_opener():
    """显式禁用 Python 的环境变量和系统代理发现。"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def direct_environment():
    """只清除采集子进程的代理变量，Codex 和主进程的环境保持原状。"""
    excluded = {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "FTP_PROXY"}
    env = {key: value for key, value in os.environ.items() if key.upper() not in excluded}
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    return env


def check_direct_network():
    """已知 Clash 开启 TUN 时停止，避免误把浏览器直连当作物理直连。"""
    default = Path.home() / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
    path = Path(os.getenv("BOSS_CLASH_CONFIG", str(default)))
    enabled = None
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            if line.strip() == "tun:" and not line.startswith(" "):
                for child in lines[index + 1:]:
                    if child.strip() and not child[0].isspace():
                        break
                    match = re.match(r"\s+enable:\s*(true|false)\b", child, re.I)
                    if match:
                        enabled = match[1].lower() == "true"
                        break
    if enabled:
        raise ValueError("检测到 Clash TUN 已开启，无法保证 BOSS 使用原网络。请保留 Codex 的代理，"
                         "改用非 TUN 系统代理模式后再采集；程序没有修改任何节点或系统设置。")
    return {"mode": "direct", "browser_proxy_disabled": True, "proxy_environment_removed": True,
            "clash_tun_enabled": enabled}
