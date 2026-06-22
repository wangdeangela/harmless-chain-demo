#!/usr/bin/env bash
# 本地 Python 启动靶场（Docker 不可用时 fallback）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]]; then
  source "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
  conda activate wangxj01brain
fi

pip install -q flask requests 2>/dev/null || true

# 若已有进程占用 8099 则跳过
if curl -sf http://127.0.0.1:8099/health >/dev/null 2>&1; then
  echo "靶场已在运行: http://127.0.0.1:8099"
  exit 0
fi

echo "本地启动靶场 :8099 ..."
nohup python "$ROOT/target/app.py" > "$ROOT/output/target.log" 2>&1 &
echo $! > "$ROOT/output/target.pid"
sleep 2
curl -sf http://127.0.0.1:8099/health | python3 -m json.tool
echo "靶场已就绪 (PID $(cat "$ROOT/output/target.pid"))"
