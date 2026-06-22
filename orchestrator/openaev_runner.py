#!/usr/bin/env python3
"""
OpenAEV 链路 A — 无害 HTTP Inject 模拟执行器
真实环境应通过 OpenAEV API 下发 Simulation；Demo 阶段本地模拟 Inject 行为。
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any

import requests

TIMEOUT = 10


@dataclass
class InjectResult:
    stepId: str
    templateId: str
    track: str
    status: str  # confirmed | fail | blocked
    executionSuccess: bool
    executionLog: str
    durationMs: int
    detail: dict[str, Any]


def http_sqli_inject_safe(step_id: str, target_url: str, params: dict) -> InjectResult:
    t0 = time.time()
    method = params.get("method", "POST").upper()
    payload = params.get("payload", {"username": "admin' OR '1'='1'--", "password": "probe"})
    headers = {"User-Agent": "OpenAEV-Inject/http-sqli-inject-safe", "X-Validation-Tag": f"validation:{step_id}"}

    try:
        if method == "POST":
            resp = requests.post(target_url, json=payload, headers=headers, timeout=TIMEOUT, allow_redirects=False)
        else:
            resp = requests.get(target_url, params=payload, headers=headers, timeout=TIMEOUT, allow_redirects=False)
        success = resp.status_code in (200, 302)
        log = f"inject_end status={resp.status_code} template=http-sqli-inject-safe target={target_url}"
        return InjectResult(
            stepId=step_id,
            templateId="http-sqli-inject-safe",
            track="openaev",
            status="confirmed" if success else "fail",
            executionSuccess=success,
            executionLog=log,
            durationMs=int((time.time() - t0) * 1000),
            detail={"code": resp.status_code, "headers": dict(resp.headers)},
        )
    except requests.RequestException as exc:
        return InjectResult(
            stepId=step_id,
            templateId="http-sqli-inject-safe",
            track="openaev",
            status="blocked",
            executionSuccess=False,
            executionLog=f"inject_error {exc}",
            durationMs=int((time.time() - t0) * 1000),
            detail={"error": str(exc)},
        )


TEMPLATE_REGISTRY = {
    "http-sqli-inject-safe": http_sqli_inject_safe,
}


def run_inject(step: dict) -> InjectResult:
    fn = TEMPLATE_REGISTRY.get(step["templateId"])
    if not fn:
        return InjectResult(
            stepId=step["stepId"],
            templateId=step.get("templateId", "unknown"),
            track="openaev",
            status="inconclusive",
            executionSuccess=False,
            executionLog="unknown template",
            durationMs=0,
            detail={},
        )
    return fn(step["stepId"], step["targetUrl"], step.get("params", {}))


def try_openaev_api(base_url: str, token: str) -> dict | None:
    """探测 OpenAEV 平台是否在线"""
    try:
        resp = requests.get(
            f"{base_url.rstrip('/')}/api/platform",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="OpenAEV 无害 Inject 执行")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--openaev-url", default="http://127.0.0.1:8888")
    parser.add_argument("--openaev-token", default="")
    args = parser.parse_args()

    if args.openaev_token:
        platform = try_openaev_api(args.openaev_url, args.openaev_token)
        if platform:
            print(json.dumps({"openaev": "online", "platform": platform}, ensure_ascii=False), flush=True)

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    results = []
    for step in plan["steps"]:
        if step.get("track") != "openaev":
            continue
        results.append(run_inject(step))
        time.sleep(1)  # 步间 ≥30s 的 demo 简化版
    print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
