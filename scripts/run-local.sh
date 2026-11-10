#!/bin/sh
# 默认使用 AutoBOSS Conda 环境，不在运行时创建环境或安装软件。
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

check_python() {
    "$1" -c 'import sys, pdfplumber, pypdf, pydantic; assert sys.version_info >= (3, 11); assert int(pydantic.__version__.split(".")[0]) >= 2' >/dev/null 2>&1
}

if [ -n "${AUTOBOSS_PYTHON:-}" ]; then
    if ! check_python "$AUTOBOSS_PYTHON"; then
        echo 'AUTOBOSS_PYTHON 指定的解释器不可用，或缺少 pdfplumber、pypdf、Pydantic 2。' >&2
        exit 2
    fi
    if [ "$#" -eq 0 ]; then
        exec "$AUTOBOSS_PYTHON" "$PROJECT_DIR/main.py"
    fi
    exec "$AUTOBOSS_PYTHON" -m autoboss "$@"
fi

CONDA_BIN=${CONDA_EXE:-}
if [ -z "$CONDA_BIN" ]; then
    CONDA_BIN=$(command -v conda || true)
fi
if [ -z "$CONDA_BIN" ]; then
    CONDA_BIN="$HOME/data/deploy/python/miniconda/bin/conda"
fi
if [ ! -x "$CONDA_BIN" ]; then
    echo '未找到 Conda，请先初始化本机 Conda，或用 AUTOBOSS_PYTHON 指定解释器。' >&2
    exit 2
fi

if [ "$#" -eq 0 ]; then
    exec "$CONDA_BIN" run --no-capture-output -n AutoBOSS python "$PROJECT_DIR/main.py"
fi
exec "$CONDA_BIN" run --no-capture-output -n AutoBOSS python -m autoboss "$@"
