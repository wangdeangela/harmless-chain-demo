"""
无害化攻击链验证 Demo 靶场 — 模拟内网登录应用（含布尔 SQLi 探针可观测差异）
仅用于本地授权验证，禁止对未授权目标使用。
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = Path(__file__).parent / "demo.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WAF-DEMO] %(levelname)s %(message)s",
)
logger = logging.getLogger("waf-demo")


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)"
    )
    conn.execute("DELETE FROM users")
    conn.executemany(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        [("admin", "Admin@2026"), ("guest", "guest123")],
    )
    conn.commit()
    conn.close()


@app.before_request
def log_request() -> None:
    logger.info(
        "request method=%s path=%s remote=%s ua=%s",
        request.method,
        request.path,
        request.remote_addr,
        request.headers.get("User-Agent", "-"),
    )
    payload = request.get_json(silent=True) or request.form.to_dict() or request.args.to_dict()
    if payload:
        logger.info("payload=%s", payload)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "intra-app-demo"})


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    故意使用字符串拼接实现 SQL 查询，便于布尔 SQLi 无害探针产生可观测差异。
    GET:  /login?username=x&password=y
    POST: JSON {"username":"x","password":"y"}
    """
    if request.method == "GET":
        username = request.args.get("username", "")
        password = request.args.get("password", "")
    else:
        data = request.get_json(silent=True) or request.form
        username = (data or {}).get("username", "")
        password = (data or {}).get("password", "")

    # 无害探针特征：' AND '1'='1 / '1'='2
    if "'" in username or "'" in password:
        logger.warning("sqli_probe_detected username=%r password=%r", username, password)

    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT id, username FROM users WHERE username='{username}' AND password='{password}'"
    logger.info("sql_query=%s", query)
    try:
        row = conn.execute(query).fetchone()
    except sqlite3.Error as exc:
        conn.close()
        return jsonify({"success": False, "error": str(exc), "redirect": None}), 400
    conn.close()

    if row:
        return jsonify({"success": True, "user_id": row[0], "redirect": "/dashboard"}), 302
    return jsonify({"success": False, "message": "invalid credentials", "redirect": None}), 401


@app.route("/api/users/<int:user_id>")
def api_user(user_id: int):
    """越权边界探针：id=1 vs id=2 响应差异，不含 PII"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, username FROM users WHERE id=?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"found": False}), 404
    return jsonify({"found": True, "id": row[0], "username": row[1], "role": "user"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8099, debug=False)
