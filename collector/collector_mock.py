#!/usr/bin/env python3
"""
Collector 防护回采模拟 — 120 秒窗口内检索 WAF/SIEM 日志
Demo 阶段读取靶场容器 stdout 日志，模拟 alerted / blocked / silent 判定。
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CollectorResult:
    stepId: str
    collectorVerdict: str  # blocked | alerted_not_blocked | silent | late_alert
    hits: int
    matchedEvents: list[dict[str, Any]]
    windowSec: int
    defenseGap: str | None


def fetch_docker_logs(container: str, since_sec: int = 120) -> str:
    try:
        out = subprocess.run(
            ["docker", "logs", "--since", f"{since_sec}s", container],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return out.stdout + out.stderr
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def fetch_local_target_log(log_path: Path) -> str:
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="replace")


def analyze_logs(logs: str, expected_rules: list[str]) -> CollectorResult:
    hits = []
    for line in logs.splitlines():
        lower = line.lower()
        if "sqli_probe_detected" in lower or "sqli" in lower:
            hits.append({"ruleId": "sqli_probe", "line": line.strip(), "action": "alert"})
        if "waf" in lower and "block" in lower:
            hits.append({"ruleId": "waf-block", "line": line.strip(), "action": "deny"})

    blocked = any(h.get("action") == "deny" for h in hits)
    alerted = len(hits) > 0

    if blocked:
        verdict, gap = "blocked", None
    elif alerted:
        verdict, gap = "alerted_not_blocked", "detect_no_block"
    else:
        verdict, gap = "silent", "detect_missing"

    return CollectorResult(
        stepId="step-2c",
        collectorVerdict=verdict,
        hits=len(hits),
        matchedEvents=hits,
        windowSec=120,
        defenseGap=gap,
    )


def merge_verdict(poc_status: str, inject_status: str, collector: CollectorResult) -> dict:
    """技术方案 7.1 联合判定矩阵"""
    exec_status = "confirmed" if poc_status == "confirmed" or inject_status == "confirmed" else poc_status
    if exec_status == "fail" and inject_status == "fail":
        exec_status = "fail"

    cv = collector.collectorVerdict
    defense_gap = collector.defenseGap

    if exec_status == "confirmed" and cv == "blocked":
        status = "blocked"
        defense_gap = None
    elif exec_status == "confirmed" and cv == "alerted_not_blocked":
        status = "confirmed"
    elif exec_status == "confirmed" and cv == "silent":
        status = "confirmed"
        defense_gap = "detect_missing"
    elif exec_status in ("fail", "blocked"):
        status = "blocked" if exec_status == "blocked" else "inconclusive"
        defense_gap = None
    else:
        status = exec_status

    return {
        "status": status,
        "defenseGap": defense_gap,
        "pocTrack": poc_status,
        "injectTrack": inject_status,
        "collectorVerdict": cv,
    }


def feasibility_score(step_results: list[dict]) -> float:
    weights = {"PP-02": 1.2, "PP-05": 1.5, "PP-01": 1.0}
    scores = {"confirmed": 1.0, "alternative_proof": 0.6, "blocked": 0.0, "inconclusive": 0.3}
    w_sum = 0.0
    s_sum = 0.0
    for r in step_results:
        pp = r.get("proofPointId", "PP-01")
        w = weights.get(pp, 1.0)
        s = scores.get(r.get("status", "inconclusive"), 0.3)
        w_sum += w
        s_sum += w * s
    return round(s_sum / w_sum, 2) if w_sum else 0.0


def verdict_label(score: float, inconclusive_count: int) -> str:
    if inconclusive_count >= 2:
        return "需人工复核"
    if score >= 0.85:
        return "成立"
    if score >= 0.50:
        return "部分成立"
    return "不成立"


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Collector 回采 + 裁决")
    parser.add_argument("--container", default="harmless-demo-target")
    parser.add_argument("--local-log", type=Path, default=None)
    parser.add_argument("--poc-result", type=Path)
    parser.add_argument("--inject-result", type=Path)
    parser.add_argument("--wait", type=int, default=3, help="模拟 120s 窗口（demo 缩短为秒）")
    args = parser.parse_args()

    time.sleep(args.wait)
    if args.local_log and args.local_log.exists():
        logs = fetch_local_target_log(args.local_log)
    else:
        logs = fetch_docker_logs(args.container, since_sec=max(args.wait, 30))
    collector = analyze_logs(logs, ["sqli_probe", "waf-alert"])

    poc_status = "inconclusive"
    inject_status = "inconclusive"
    if args.poc_result and args.poc_result.exists():
        poc_list = json.loads(args.poc_result.read_text())
        if poc_list:
            poc_status = poc_list[0].get("status", "inconclusive")
    if args.inject_result and args.inject_result.exists():
        inj_list = json.loads(args.inject_result.read_text())
        if inj_list:
            inject_status = inj_list[0].get("status", "inconclusive")

    merged = merge_verdict(poc_status, inject_status, collector)
    step_results = [
        {"proofPointId": "PP-02", "status": merged["status"]},
        {"proofPointId": "PP-05", "status": "alternative_proof"},
    ]
    score = feasibility_score(step_results)
    inconclusive = sum(1 for r in step_results if r["status"] == "inconclusive")

    verdict = {
        "validationRunId": f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "merged": merged,
        "collector": asdict(collector),
        "feasibilityScore": score,
        "verdict": verdict_label(score, inconclusive),
        "defenseGaps": [g for g in [merged.get("defenseGap")] if g],
        "recommendation": (
            "建议 WAF 规则升级为阻断模式" if merged.get("defenseGap") == "detect_no_block" else
            "建议检查 WAF/SIEM 日志接入与规则覆盖" if merged.get("defenseGap") == "detect_missing" else
            "防护有效，链已阻断" if merged["status"] == "blocked" else
            "攻击链部分成立，需加固防护"
        ),
    }
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
