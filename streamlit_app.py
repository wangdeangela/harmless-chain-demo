"""
ChainForge 在线离线演示 — Streamlit Cloud 部署入口

保留完整 90 秒拓扑动画（嵌入 portal/templates/dashboard.html）。
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from embed.embed_builder import build_embed_html

st.set_page_config(
    page_title="ChainForge · 无害化攻击链验证",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("### ChainForge · 无害化攻击链验证")
st.caption(
    "在线离线演示 · 日志还原 → 无害复现 → 防护对账 → 验证结论 · "
    "点击下方控制台内 **「启动验证」** 开始约 90 秒推演"
)

with st.expander("使用说明", expanded=False):
    st.markdown(
        """
        - **模式**：仅离线推演（Mock 日志 + 模拟双轨执行），无需靶场与 OpenAEV
        - **场景**：SQL 注入 + WAF、APT 横向截断
        - **动画**：与本地控制台相同的拓扑高亮与日志流式输出
        - **注意**：推演进行中请勿刷新页面（约 90 秒）
        """
    )

@st.cache_data(show_spinner="正在加载演示数据…")
def _cached_embed_html() -> str:
    return build_embed_html()

components.html(_cached_embed_html(), height=940, scrolling=True)

st.divider()
st.caption(
    "源码：[github.com/wangdeangela/harmless-chain-demo](https://github.com/wangdeangela/harmless-chain-demo) · "
    "MIT License · 仅用于授权环境无害验证演示"
)
