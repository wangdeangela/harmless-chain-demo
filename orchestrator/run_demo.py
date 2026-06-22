#!/usr/bin/env python3
"""
无害化攻击链验证 Demo — 双轨编排器
OpenAEV Inject + pentest-ai PoC + Collector 回采 → ValidationVerdict
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "config" / "validation_plan_sqli.json"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)


def run_cmd(cmd: list[str], outfile: Path | None = None) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if outfile and result.stdout.strip():
        outfile.write_text(result.stdout, encoding="utf-8")
    return result.returncode


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    poc_out = OUT / f"poc_{ts}.json"
    inject_out = OUT / f"inject_{ts}.json"
    verdict_out = OUT / f"verdict_{ts}.json"

    print("=" * 60)
    print("无害化攻击链验证 — SQL 注入 + WAF 防护对账")
    print("=" * 60)

    # 健康检查
    import requests
    try:
        r = requests.get("http://127.0.0.1:8099/health", timeout=5)
        print(f"靶场状态: {r.json()}")
    except Exception as exc:
        print(f"靶场未就绪: {exc}")
        print("请先运行: bash scripts/start-target.sh")
        return 1

    py = sys.executable
    rc = run_cmd([py, str(ROOT / "orchestrator" / "poc_runner.py"), "--plan", str(PLAN)], poc_out)
    if rc != 0:
        return rc

    rc = run_cmd([py, str(ROOT / "orchestrator" / "openaev_runner.py"), "--plan", str(PLAN)], inject_out)
    if rc != 0:
        return rc

    rc = run_cmd(
        [
            py,
            str(ROOT / "collector" / "collector_mock.py"),
            "--container", "harmless-demo-target",
            "--local-log", str(ROOT / "output" / "target.log"),
            "--poc-result", str(poc_out),
            "--inject-result", str(inject_out),
            "--wait", "3",
        ],
        verdict_out,
    )
    if rc != 0:
        return rc

    print("\n" + "=" * 60)
    print(f"验证完成。裁决报告: {verdict_out}")
    if verdict_out.exists():
        verdict = json.loads(verdict_out.read_text(encoding="utf-8"))
        print(f"  feasibilityScore: {verdict.get('feasibilityScore')}")
        print(f"  verdict: {verdict.get('verdict')}")
        print(f"  recommendation: {verdict.get('recommendation')}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
