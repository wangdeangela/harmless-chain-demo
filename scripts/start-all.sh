#!/usr/bin/env bash
# 一键启动无害化攻击链验证 Demo
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
mkdir -p "$ROOT/output"

# 激活 conda 环境
if [[ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]]; then
  # shellcheck disable=SC1091
  source "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
  conda activate wangxj01brain
fi

echo "============================================"
echo " ChainForge 无害化攻击链验证"
echo " OpenAEV + pentest-ai 双轨证明"
echo "============================================"

# 1. 靶场（Docker 失败时自动 fallback 本地 Python）
if ! bash "$SCRIPT_DIR/start-target.sh" 2>/dev/null; then
  echo "[fallback] Docker 构建失败，改用本地 Python 靶场"
  bash "$SCRIPT_DIR/start-target-local.sh"
fi

# 2. OpenAEV（可选，资源占用大；未启动时使用本地 Inject 模拟）
if [[ "${START_OPENAEV:-0}" == "1" ]]; then
  bash "$SCRIPT_DIR/start-openaev.sh"
else
  echo ""
  echo "[提示] 跳过 OpenAEV Docker 部署（默认使用本地 Inject 模拟器）"
  echo "       如需完整 OpenAEV UI，请运行: START_OPENAEV=1 bash scripts/start-all.sh"
fi

# 3. 检查 ptai
if command -v ptai &>/dev/null; then
  echo ""
  echo "[pentest-ai] ptai 已安装"
else
  echo ""
  echo "[pentest-ai] 尝试安装 ptai（网络慢时可跳过，编排器内置 PoC 模板）..."
  pip install -q ptai || echo "[warn] ptai 安装失败，将使用内置 poc_runner"
fi

# 4. 运行双轨验证
echo ""
python "$ROOT/orchestrator/run_demo.py"

echo ""
echo "Demo 完成。输出目录: $ROOT/output/"
