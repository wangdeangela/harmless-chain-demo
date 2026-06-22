#!/usr/bin/env bash
# 本地图形化 Demo（无需 Docker 拉镜像，Docker Desktop 可用时仍推荐 docker-up.sh）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
mkdir -p "$ROOT/output"

if [[ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]]; then
  source "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
  conda activate wangxj01brain 2>/dev/null || true
fi

pip install -q flask requests 2>/dev/null || true

# 靶场
if ! curl -sf http://127.0.0.1:8099/health >/dev/null 2>&1; then
  echo "[1/2] 启动本地靶场 :8099 ..."
  bash "$SCRIPT_DIR/start-target-local.sh"
else
  echo "[1/2] 靶场已在运行 :8099"
fi

# Portal（每次启动均重启，确保加载最新页面逻辑）
echo "[2/2] 启动图形化控制台 :8500 ..."
if [[ -f "$ROOT/output/portal.pid" ]]; then
  kill "$(cat "$ROOT/output/portal.pid")" 2>/dev/null || true
fi
pkill -f "portal/app.py" 2>/dev/null || true
pkill -f "$ROOT/portal/app.py" 2>/dev/null || true
sleep 1
export TARGET_URL="${TARGET_URL:-http://127.0.0.1:8099}"
export OPENAEV_URL="${OPENAEV_URL:-http://127.0.0.1:8888}"
nohup python "$ROOT/portal/app.py" > "$ROOT/output/portal.log" 2>&1 &
echo $! > "$ROOT/output/portal.pid"
sleep 2

echo ""
echo "=============================================="
echo " ChainForge 无害化攻击链验证"
echo "   控制台:  http://127.0.0.1:8500"
echo "   验证靶场: http://127.0.0.1:8099"
echo "   OpenAEV:  http://127.0.0.1:8888（可选）"
echo "=============================================="
echo "浏览器打开控制台，点击「启动验证任务」"

# macOS 自动打开浏览器
if [[ "$(uname)" == "Darwin" ]]; then
  open "http://127.0.0.1:8500" 2>/dev/null || true
fi
