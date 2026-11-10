"""仅使用当前 AutoBOSS 环境，不借用其他项目的解释器。"""

from importlib.metadata import PackageNotFoundError, version
import sys
from pathlib import Path


PATCHRIGHT_VERSION = "1.62.1"


def browser_python() -> str:
    if Path(sys.prefix).name != "AutoBOSS":
        raise ValueError("请使用 Conda AutoBOSS 环境运行 main.py；不再切换到 script 等其他环境。")
    try:
        installed = version("patchright")
    except PackageNotFoundError:
        raise ValueError("AutoBOSS 环境缺少 Patchright，请按项目依赖配置安装。") from None
    if installed != PATCHRIGHT_VERSION:
        raise ValueError(f"需要 Patchright {PATCHRIGHT_VERSION}，当前版本为 {installed}。")
    return sys.executable
