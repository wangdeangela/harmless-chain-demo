# Streamlit Cloud 在线演示部署

将 ChainForge 离线演示版部署到 [Streamlit Community Cloud](https://streamlit.io/cloud)（免费），**保留约 90 秒拓扑动画**。

## 前置条件

- GitHub 仓库已推送最新代码（含 `streamlit_app.py`）
- Streamlit Cloud 账号（可用 GitHub 登录）

## 部署步骤

1. 打开 https://share.streamlit.io/
2. 点击 **New app**
3. 配置：
   - **Repository**：`wangdeangela/harmless-chain-demo`
   - **Branch**：`main`
   - **Main file path**：`streamlit_app.py`
4. **Advanced settings** → Python version **3.11**
5. 点击 **Deploy**

首次构建约 2～5 分钟。完成后获得地址，形如：

```
https://harmless-chain-demo-xxxx.streamlit.app
```

## 本地验证

```bash
cd harmless-chain-demo
pip install -r requirements.txt
streamlit run streamlit_app.py
```

浏览器打开 http://localhost:8501 ，在嵌入控制台内点击 **「启动验证」**。

## 架构说明

```
streamlit_app.py
    └─ st.components.v1.html
         └─ dashboard.html + embed/embed_tail.js（注入 __CF_EMBED__）
              └─ playTopologyAnimation()  ← 原 90 秒动画逻辑
```

- 数据由 `embed/offline_data.py` 在服务端预计算（`run_pipeline_data`）
- 不依赖 Flask、靶场 8099、OpenAEV
- 仅 `simulated` 离线推演模式

## 常见问题

**Q: 推演到一半页面刷新了？**  
A: Streamlit 上方控件会触发 rerun；演示时只操作 iframe 内的「启动验证」，不要点页面其他按钮。

**Q: 与本地 :8500 有什么区别？**  
A: 动画与 UI 基本一致；健康检查显示「在线演示 / 靶场(离线)」；无实网验证模式。

**Q: 想更新演示数据？**  
A: 修改 `config/` 下 JSON 后推送 GitHub，Streamlit Cloud 会自动重建。

## 自定义域名（可选）

Streamlit Cloud 免费版可在应用 Settings 中配置自定义子域名。
