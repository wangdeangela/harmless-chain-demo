#!/usr/bin/env python3
"""
ChainForge 模拟编排器 — 用模拟数据跑通无害化攻击链验证全流程

阶段：
  P1 Log→Path   SIEM 告警 → AttackPath
  P2 Path→Plan  AttackPath → ValidationPlan（SHACL 校验）
  P3 Execute    pentest-ai PoC + OpenAEV Inject（模拟或 live）
  P4 Verdict    Collector 回采 → ValidationVerdict
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
OUT = ROOT / "output"

# 复用 collector 裁决逻辑
sys.path.insert(0, str(ROOT / "collector"))
from collector_mock import (  # noqa: E402
    CollectorResult,
    feasibility_score,
    merge_verdict,
    verdict_label,
)


@dataclass
class StageResult:
    stage: str
    artifact: str
    summary: str


# ── P1 Log→Path ──────────────────────────────────────────────

def log_to_path(siem: dict) -> dict:
    events = sorted(siem["events"], key=lambda e: e["timestamp"])
    steps = []
    for i, evt in enumerate(events, 1):
        steps.append({
            "stepId": f"step-{i}",
            "technique": evt["technique"],
            "eventId": evt["eventId"],
            "timestamp": evt["timestamp"],
            "targetUrl": evt.get("targetUrl", ""),
            "targetHostname": evt.get("targetHostname", evt.get("targetIp", "")),
            "sourceIp": evt.get("sourceIp", ""),
            "defenseControl": evt.get("defenseControl", ""),
            "proofPointId": _infer_proof_point(evt["technique"]),
            "priorAction": evt.get("action", "alert"),
        })
    return {
        "attackPathId": f"path-{siem['scenarioId']}",
        "title": f"还原路径 — {siem['scenarioId']}",
        "chainClosure": siem["twinContext"]["chainClosure"],
        "authLevel": "L2",
        "steps": steps,
        "twinContext": siem["twinContext"],
        "sourceEvents": [e["eventId"] for e in events],
    }


def _infer_proof_point(technique: str) -> str:
    mapping = {"T1190": "PP-02", "T1078": "PP-03", "T1213": "PP-05", "T1021": "PP-04", "T1041": "PP-06"}
    return mapping.get(technique, "PP-01")


# ── P2 Path→Plan ─────────────────────────────────────────────

PLAN_TEMPLATES = {
    "T1190": {
        "pentestAi": "sqli-boolean-probe",
        "openAev": "http-sqli-inject-safe",
        "targetUrl": "http://127.0.0.1:8099/login",
    },
    "T1021": {
        "openAev": "smb-portscan-single-hop",
        "targetUrl": "10.10.2.80:445",
    },
    "T1213": {
        "pentestAi": "api-unauth-page1",
        "maxAction": "alternative_proof",
        "targetUrl": "http://127.0.0.1:8099/api/users/1",
    },
}


def path_to_plan(path: dict, scenario_id: str) -> dict:
    plan_steps = []
    for step in path["steps"]:
        tpl = PLAN_TEMPLATES.get(step["technique"], {})
        if tpl.get("pentestAi"):
            plan_steps.append({
                "stepId": f"{step['stepId']}-a",
                "parentStepId": step["stepId"],
                "track": "pentest-ai",
                "templateId": tpl["pentestAi"],
                "proofPointId": step["proofPointId"],
                "targetUrl": tpl.get("targetUrl", step.get("targetUrl", "")),
            })
        if tpl.get("openAev"):
            plan_steps.append({
                "stepId": f"{step['stepId']}-b",
                "parentStepId": step["stepId"],
                "track": "openaev",
                "templateId": tpl["openAev"],
                "proofPointId": step["proofPointId"],
                "targetUrl": tpl.get("targetUrl", step.get("targetUrl", "")),
            })
        plan_steps.append({
            "stepId": f"{step['stepId']}-c",
            "parentStepId": step["stepId"],
            "track": "collector",
            "expectedRules": [step.get("defenseControl", "WAF")],
            "targetHostname": step.get("targetHostname", ""),
        })
        if tpl.get("maxAction") == "alternative_proof":
            plan_steps.append({
                "stepId": step["stepId"],
                "track": "alternative_proof",
                "templateId": tpl.get("pentestAi", "audit-replay"),
                "proofPointId": step["proofPointId"],
                "targetUrl": tpl.get("targetUrl", ""),
            })

    plan = {
        "planId": f"plan-{scenario_id}",
        "attackPathId": path["attackPathId"],
        "authLevel": path["authLevel"],
        "roe": ["127.0.0.1", "localhost", "10.10.0.0/16"],
        "collectorWindowSec": 120,
        "steps": plan_steps,
    }
    _shacl_validate(plan)
    return plan


def _shacl_validate(plan: dict) -> None:
    """简易 SHACL：maxAction ≤ authLevel，禁止 L4"""
    level = plan.get("authLevel", "L2")
    allowed = {"L0", "L1", "L2", "L3"}
    if level not in allowed:
        raise ValueError(f"SHACL 违规: authLevel={level} 不在 L0-L3")
    for step in plan["steps"]:
        if step.get("maxAction") == "L4":
            raise ValueError(f"SHACL 违规: step {step['stepId']} 禁止 L4")


# ── P3 Execute（模拟） ───────────────────────────────────────

def execute_simulated(plan: dict, mock_exec: dict, scenario_id: str) -> dict:
    data = mock_exec.get(scenario_id, {})
    return {
        "mode": "simulated",
        "pocResults": data.get("pocResults", []),
        "injectResults": data.get("injectResults", []),
        "alternativeProof": data.get("alternativeProof"),
        "planStepsExecuted": len(plan["steps"]),
    }


# ── P4 Collector + Verdict ─────────────────────────────────────

def collector_from_mock(events: list[dict]) -> CollectorResult:
    hits = []
    for evt in events:
        action = evt.get("action", "alert")
        hits.append({
            "ruleId": evt.get("ruleId", "unknown"),
            "line": evt.get("detail", ""),
            "action": "deny" if action == "deny" else "alert",
            "timestamp": evt.get("timestamp", ""),
        })
    blocked = any(h["action"] == "deny" for h in hits)
    alerted = len(hits) > 0 and not blocked
    if blocked:
        verdict, gap = "blocked", None
    elif alerted:
        verdict, gap = "alerted_not_blocked", "detect_no_block"
    else:
        verdict, gap = "silent", "detect_missing"
    return CollectorResult(
        stepId="collector",
        collectorVerdict=verdict,
        hits=len(hits),
        matchedEvents=hits,
        windowSec=120,
        defenseGap=gap,
    )


def build_verdict(exec_result: dict, collector: CollectorResult, path: dict) -> dict:
    poc_list = exec_result.get("pocResults", [])
    inj_list = exec_result.get("injectResults", [])
    poc_status = poc_list[0]["status"] if poc_list else "inconclusive"
    inject_status = inj_list[0]["status"] if inj_list else "inconclusive"

    merged = merge_verdict(poc_status, inject_status, collector)
    if collector.collectorVerdict == "blocked":
        merged["status"] = "blocked"
        merged["defenseGap"] = None

    alt = exec_result.get("alternativeProof")
    step_results = [
        {"proofPointId": "PP-02", "status": merged["status"]},
    ]
    if alt:
        step_results.append({"proofPointId": alt.get("proofPointId", "PP-05"), "status": alt["status"]})
    elif merged["status"] == "blocked":
        step_results = [{"proofPointId": "PP-04", "status": "blocked"}]

    score = feasibility_score(step_results)
    inconclusive = sum(1 for r in step_results if r["status"] == "inconclusive")

    gaps = [g for g in [merged.get("defenseGap")] if g]
    rec = {
        "detect_no_block": "建议 WAF 规则升级为阻断模式",
        "detect_missing": "建议检查 WAF/SIEM 日志接入与规则覆盖",
    }.get(merged.get("defenseGap"))
    if not rec:
        rec = "防护有效，链已阻断" if merged["status"] == "blocked" else "攻击链部分成立，需加固防护"

    return {
        "validationRunId": f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attackPathId": path["attackPathId"],
        "chainClosure": path.get("chainClosure"),
        "mode": exec_result.get("mode", "simulated"),
        "stepResults": step_results,
        "merged": merged,
        "collector": asdict(collector),
        "feasibilityScore": score,
        "verdict": verdict_label(score, inconclusive),
        "defenseGaps": gaps,
        "recommendation": rec,
        "verdictRefinesPath": {
            "blockRateEstimateDelta": -0.15 if gaps else 0,
            "defenseGapScore": 0.7 if "detect_no_block" in gaps else (0.9 if "detect_missing" in gaps else 0),
        },
    }


# ── 主流水线 ─────────────────────────────────────────────────

def _load_scenario_inputs(scenario: str) -> tuple[dict, dict, Path]:
    if scenario == "sqli-waf-demo":
        siem_file = CONFIG / "mock_siem_events_sqli.json"
    elif scenario == "apt-lateral-blocked":
        siem_file = CONFIG / "mock_siem_events_apt.json"
    else:
        raise ValueError(f"未知场景: {scenario}")
    siem = json.loads(siem_file.read_text(encoding="utf-8"))
    mock_exec = json.loads((CONFIG / "mock_execution_results.json").read_text(encoding="utf-8"))
    return siem, mock_exec, siem_file


def run_pipeline_data(scenario: str, mode: str = "simulated") -> dict[str, Any]:
    """返回完整流水线 JSON，供 API / 图形化 Portal 使用"""
    siem, mock_exec, _ = _load_scenario_inputs(scenario)
    path = log_to_path(siem)
    plan = path_to_plan(path, scenario)
    exec_result = execute_simulated(plan, mock_exec, scenario)
    exec_result["mode"] = mode
    collector = collector_from_mock(mock_exec[scenario]["collectorEvents"])
    verdict = build_verdict(exec_result, collector, path)
    return {
        "scenario": scenario,
        "mode": mode,
        "attackPath": path,
        "validationPlan": plan,
        "execution": exec_result,
        "collector": asdict(collector),
        "verdict": verdict,
        "stages": [
            {"id": "P1", "name": "Log→Path", "summary": f"{len(path['steps'])} 步攻击链"},
            {"id": "P2", "name": "Path→Plan", "summary": f"{len(plan['steps'])} 条验证步骤"},
            {"id": "P3", "name": "双轨 Execute", "summary": "pentest-ai + OpenAEV"},
            {"id": "P4", "name": "Collector→Verdict", "summary": verdict["verdict"]},
        ],
    }


def run_scenario(scenario: str, ts: str) -> list[StageResult]:
    OUT.mkdir(exist_ok=True)
    results: list[StageResult] = []
    data = run_pipeline_data(scenario)
    path = data["attackPath"]
    plan = data["validationPlan"]
    exec_result = data["execution"]
    verdict = data["verdict"]

    path_file = OUT / f"{ts}_01_attack_path_{scenario}.json"
    path_file.write_text(json.dumps(path, ensure_ascii=False, indent=2), encoding="utf-8")
    results.append(StageResult("P1 Log→Path", str(path_file), f"{len(path['steps'])} 步攻击链, chainClosure={path['chainClosure']}"))

    plan_file = OUT / f"{ts}_02_validation_plan_{scenario}.json"
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    results.append(StageResult("P2 Path→Plan", str(plan_file), f"{len(plan['steps'])} 条验证步骤, SHACL 通过"))

    exec_file = OUT / f"{ts}_03_execution_{scenario}.json"
    exec_file.write_text(json.dumps(exec_result, ensure_ascii=False, indent=2), encoding="utf-8")
    poc_n = len(exec_result["pocResults"])
    inj_n = len(exec_result["injectResults"])
    results.append(StageResult("P3 Execute", str(exec_file), f"pentest-ai {poc_n} 条 + OpenAEV {inj_n} 条（模拟）"))

    verdict_file = OUT / f"{ts}_04_verdict_{scenario}.json"
    verdict_file.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    results.append(StageResult(
        "P4 Verdict",
        str(verdict_file),
        f"feasibilityScore={verdict['feasibilityScore']} verdict={verdict['verdict']}",
    ))
    return results


def print_pipeline(results: list[StageResult]) -> None:
    print("\n" + "─" * 62)
    print("  ChainForge 模拟流水线")
    print("─" * 62)
    for r in results:
        print(f"  [{r.stage}]")
        print(f"    产出: {Path(r.artifact).name}")
        print(f"    摘要: {r.summary}")
    print("─" * 62)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="模拟数据跑通无害化攻击链验证全流程")
    parser.add_argument("--scenario", default="all", choices=["all", "sqli-waf-demo", "apt-lateral-blocked"])
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    scenarios = ["sqli-waf-demo", "apt-lateral-blocked"] if args.scenario == "all" else [args.scenario]

    print("=" * 62)
    print(" 无害化攻击链验证 — 离线推演")
    print("=" * 62)

    all_results: dict[str, list[StageResult]] = {}
    for sc in scenarios:
        print(f"\n▶ 场景: {sc}")
        all_results[sc] = run_scenario(sc, ts)
        print_pipeline(all_results[sc])
        vf = [r for r in all_results[sc] if r.stage == "P4 Verdict"][0]
        v = json.loads(Path(vf.artifact).read_text(encoding="utf-8"))
        print(f"  ★ 裁决: {v['verdict']}  |  评分: {v['feasibilityScore']}  |  缺口: {v['defenseGaps']}")
        print(f"  ★ 建议: {v['recommendation']}")

    summary_file = OUT / f"{ts}_00_pipeline_summary.json"
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "simulated",
        "scenarios": {
            sc: [{"stage": r.stage, "artifact": r.artifact, "summary": r.summary} for r in rs]
            for sc, rs in all_results.items()
        },
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n流水线摘要: {summary_file}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
