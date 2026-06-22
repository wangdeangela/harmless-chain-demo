"""ChainForge 无害化攻击链验证 — 控制台 API"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "orchestrator"))
sys.path.insert(0, str(ROOT / "collector"))

from chainforge_sim import run_pipeline_data, build_verdict  # noqa: E402
from collector_mock import analyze_logs  # noqa: E402

PLATFORM = json.loads((ROOT / "config" / "platform_config.json").read_text(encoding="utf-8"))
LOG_FILES = {
    "sqli-waf-demo": ROOT / "config" / "mock_logs_sqli.json",
    "apt-lateral-blocked": ROOT / "config" / "mock_logs_apt.json",
}
TOPO_FILES = {
    "sqli-waf-demo": ROOT / "config" / "topology_sqli.json",
    "apt-lateral-blocked": ROOT / "config" / "topology_apt.json",
}


def _load_topology(scenario_id: str) -> dict:
    path = TOPO_FILES.get(scenario_id)
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

app = Flask(__name__, template_folder="templates", static_folder="static")
TARGET_URL = os.environ.get("TARGET_URL", "http://127.0.0.1:8099")
OPENAEV_URL = os.environ.get("OPENAEV_URL", "http://127.0.0.1:8888")

MATRIX = [
    {"poc": "confirmed", "collector": "alerted + blocked", "status": "blocked", "gap": "—"},
    {"poc": "confirmed", "collector": "alerted + 未阻断", "status": "confirmed", "gap": "detect_no_block"},
    {"poc": "confirmed", "collector": "silent", "status": "confirmed", "gap": "detect_missing"},
    {"poc": "fail", "collector": "任意", "status": "blocked", "gap": "—"},
]


def _load_logs(scenario_id: str) -> dict:
    path = LOG_FILES.get(scenario_id)
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@app.route("/")
def index():
    resp = app.make_response(render_template("dashboard.html", openaev_url=OPENAEV_URL, target_url=TARGET_URL))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/version")
def version():
    return jsonify({"build": "20260615-v2", "feature": "deferred-verdict"})


@app.route("/api/health")
def health():
    target_ok = openaev_ok = False
    try:
        target_ok = requests.get(f"{TARGET_URL}/health", timeout=3).status_code == 200
    except requests.RequestException:
        pass
    try:
        openaev_ok = requests.get(OPENAEV_URL, timeout=3).status_code < 500
    except requests.RequestException:
        pass
    return jsonify({"portal": "ok", "target": target_ok, "openaev": openaev_ok,
                    "targetUrl": TARGET_URL, "openaevUrl": OPENAEV_URL})


@app.route("/api/scenarios")
def scenarios():
    return jsonify([s for s in PLATFORM["scenarios"] if s.get("demo")])


@app.route("/api/matrix")
def matrix():
    return jsonify(MATRIX)


@app.route("/api/platform")
def platform_config():
    return jsonify(PLATFORM)


@app.route("/api/topology/<scenario_id>")
def scenario_topology(scenario_id: str):
    topo = _load_topology(scenario_id)
    if not topo:
        return jsonify({"error": "unknown scenario"}), 404
    return jsonify(topo)


@app.route("/api/logs/<scenario_id>")
def scenario_logs(scenario_id: str):
    logs = _load_logs(scenario_id)
    if not logs:
        return jsonify({"error": "unknown scenario"}), 404
    return jsonify(logs)


@app.route("/api/run/<scenario_id>", methods=["POST"])
def run_validation(scenario_id: str):
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "simulated")
    if mode == "live" and scenario_id == "sqli-waf-demo":
        data = _run_live_sqli(scenario_id)
    else:
        data = run_pipeline_data(scenario_id, mode=mode)

    logs = _load_logs(scenario_id)
    topo = _load_topology(scenario_id)
    data["runAt"] = datetime.now(timezone.utc).isoformat()
    data["logs"] = logs
    data["topology"] = topo
    data["runContext"] = _run_context(scenario_id, data, logs)
    return jsonify(data)


def _run_context(scenario_id: str, data: dict, logs: dict) -> dict:
    v = data.get("verdict", {})
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


def _run_live_sqli(scenario_id: str) -> dict:
    from dataclasses import asdict
    from poc_runner import run_template
    from openaev_runner import run_inject

    base = run_pipeline_data(scenario_id, mode="live")
    plan = json.loads((ROOT / "config" / "validation_plan_sqli.json").read_text(encoding="utf-8"))
    poc_results, inject_results = [], []
    url = f"{TARGET_URL}/login"
    for step in plan["steps"]:
        if step.get("track") == "pentest-ai":
            poc_results.append(asdict(run_template({**step, "targetUrl": url})))
        elif step.get("track") == "openaev":
            inject_results.append(asdict(run_inject({**step, "targetUrl": url})))

    exec_result = {"mode": "live", "pocResults": poc_results, "injectResults": inject_results,
                   "alternativeProof": base["execution"].get("alternativeProof")}
    collector = analyze_logs("sqli_probe_detected\nWAF-SQLi-001 alert", ["sqli_probe"])
    verdict = build_verdict(exec_result, collector, base["attackPath"])
    return {**base, "mode": "live", "execution": exec_result,
            "collector": asdict(collector), "verdict": verdict}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8500, debug=False)
