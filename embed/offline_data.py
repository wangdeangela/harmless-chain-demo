"""离线演示数据包 — 供 Streamlit 嵌入版使用（无需 Flask / 靶场）"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "orchestrator"))

from chainforge_sim import run_pipeline_data  # noqa: E402

PLATFORM = json.loads((ROOT / "config" / "platform_config.json").read_text(encoding="utf-8"))
LOG_FILES = {
    "sqli-waf-demo": ROOT / "config" / "mock_logs_sqli.json",
    "apt-lateral-blocked": ROOT / "config" / "mock_logs_apt.json",
}
TOPO_FILES = {
    "sqli-waf-demo": ROOT / "config" / "topology_sqli.json",
    "apt-lateral-blocked": ROOT / "config" / "topology_apt.json",
}
DEMO_SCENARIOS = ["sqli-waf-demo", "apt-lateral-blocked"]

MATRIX = [
    {"poc": "confirmed", "collector": "alerted + blocked", "status": "blocked", "gap": "—"},
    {"poc": "confirmed", "collector": "alerted + 未阻断", "status": "confirmed", "gap": "detect_no_block"},
    {"poc": "confirmed", "collector": "silent", "status": "confirmed", "gap": "detect_missing"},
    {"poc": "fail", "collector": "任意", "status": "blocked", "gap": "—"},
]


def _run_context(scenario_id: str, data: dict, logs: dict) -> dict:
    path = data.get("attackPath", {})
    collector = data.get("collector", {})
    pp_used = list({s.get("proofPointId") for s in path.get("steps", []) if s.get("proofPointId")})
    return {
        "authLevel": path.get("authLevel", "L2"),
        "proofPointsUsed": pp_used,
        "collectorVerdict": collector.get("collectorVerdict"),
        "collectorHits": logs.get("collectorHits", collector.get("matchedEvents", [])),
        "reconciliation": PLATFORM["reconciliation"].get(collector.get("collectorVerdict", ""), ""),
    }


def build_run_data(scenario_id: str) -> dict:
    logs = json.loads(LOG_FILES[scenario_id].read_text(encoding="utf-8"))
    topo = json.loads(TOPO_FILES[scenario_id].read_text(encoding="utf-8"))
    data = run_pipeline_data(scenario_id, mode="simulated")
    data["mode"] = "simulated"
    data["runAt"] = datetime.now(timezone.utc).isoformat()
    data["logs"] = logs
    data["topology"] = topo
    data["runContext"] = _run_context(scenario_id, data, logs)
    return data


def build_embed_boot() -> dict:
    assets = {}
    for sc in DEMO_SCENARIOS:
        run = build_run_data(sc)
        assets[sc] = {
            "logs": run["logs"],
            "topology": run["topology"],
            "runData": run,
        }
    return {
        "platform": PLATFORM,
        "matrix": MATRIX,
        "defaultScenario": "sqli-waf-demo",
        "assets": assets,
        "build": "streamlit-embed-v1",
    }
