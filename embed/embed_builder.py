"""将 dashboard.html 打包为 Streamlit components.html 可嵌入的离线页面"""
from __future__ import annotations

import json
import re
from pathlib import Path

from embed.offline_data import build_embed_boot

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "portal" / "templates" / "dashboard.html"
EMBED_TAIL = Path(__file__).resolve().parent / "embed_tail.js"


def _safe_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_embed_html() -> str:
    html = DASHBOARD.read_text(encoding="utf-8")
    boot = build_embed_boot()
    boot_js = f"window.__CF_EMBED__={_safe_json(boot)};"

    html = html.replace(
        "const $=id=>document.getElementById(id);",
        f"{boot_js}\nconst $=id=>document.getElementById(id);",
        1,
    )

    tail = EMBED_TAIL.read_text(encoding="utf-8")
    pattern = r"\$\('runBtn'\)\.onclick=async\(\)=>\{[\s\S]*\ninit\(\);\n"
    if not re.search(pattern, html):
        raise RuntimeError("dashboard.html 结构已变，无法注入 embed_tail")
    html = re.sub(pattern, tail + "\n", html, count=1)

    # 嵌入 iframe 时收紧外边距
    html = html.replace(
        "<body>",
        "<body style='margin:0'>",
        1,
    )
    return html
