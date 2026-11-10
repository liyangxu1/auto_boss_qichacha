#!/bin/sh
# 仅使用已有的 AutoBOSS 环境，不自动安装依赖或下载浏览器。
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
PYTHON_BIN=${AUTOBOSS_PYTHON:-"$HOME/data/deploy/python/miniconda/envs/AutoBOSS/bin/python"}
if [ ! -x "$PYTHON_BIN" ]; then
    echo '未找到现有 AutoBOSS 解释器，请用 AUTOBOSS_PYTHON 指定。' >&2
    exit 2
fi
exec "$PYTHON_BIN" -m autoboss.web.server "${1:-start}"
