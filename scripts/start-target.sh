#!/usr/bin/env bash
# 启动无害化验证 Demo 靶场（内网登录应用模拟）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
TARGET_DIR="$ROOT/target"

echo "[1/2] 构建靶场镜像..."
docker build -t harmless-demo-target:latest "$TARGET_DIR"

echo "[2/2] 启动容器 harmless-demo-target :8099 ..."
docker rm -f harmless-demo-target 2>/dev/null || true
docker run -d \
  --name harmless-demo-target \
  -p 8099:8099 \
  --restart unless-stopped \
  harmless-demo-target:latest

sleep 2
curl -sf http://127.0.0.1:8099/health | python3 -m json.tool
echo "靶场已就绪: http://127.0.0.1:8099/login"
