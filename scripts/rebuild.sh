#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

cd "$ROOT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  echo "创建虚拟环境: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [ ! -x "$VENV_DIR/bin/python3" ]; then
  echo "错误: 未找到虚拟环境 Python 可执行文件"
  exit 1
fi

if ! "$VENV_DIR/bin/python3" -c "import markdown" >/dev/null 2>&1; then
  echo "安装依赖: markdown"
  "$VENV_DIR/bin/pip" install markdown
fi

echo "开始重建 legalwiki 静态站点..."
"$VENV_DIR/bin/python3" build.py

echo
echo "重建完成。可直接打开: $ROOT_DIR/index.html"
