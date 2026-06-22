#!/usr/bin/env bash
# Docker Desktop 一键部署图形化双轨验证 Demo
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT"

echo "=============================================="
echo " OpenAEV + pentest-ai 双轨验证 — Docker 部署"
echo "=============================================="

if ! docker info >/dev/null 2>&1; then
  echo "错误: Docker Desktop 未运行，请先启动 Docker Desktop"
  exit 1
fi

echo "[1/2] 构建并启动容器..."
docker compose up -d --build

echo "[2/2] 等待服务就绪..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8500/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ""
echo "=============================================="
echo " 部署完成！图形化控制台："
echo "   http://127.0.0.1:8500"
echo ""
echo " 靶场 API："
echo "   http://127.0.0.1:8099/health"
echo ""
echo " OpenAEV（可选，需单独部署）："
echo "   http://127.0.0.1:8888"
echo "   bash scripts/start-openaev.sh"
echo "=============================================="

curl -s http://127.0.0.1:8500/api/health | python3 -m json.tool 2>/dev/null || true
