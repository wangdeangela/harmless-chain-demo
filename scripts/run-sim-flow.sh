#!/usr/bin/env bash
# 模拟数据跑通无害化攻击链验证全流程（无需靶场 / Docker / 网络）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

if [[ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]]; then
  source "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
  conda activate wangxj01brain 2>/dev/null || true
fi

SCENARIO="${1:-all}"
python "$ROOT/orchestrator/chainforge_sim.py" --scenario "$SCENARIO"
