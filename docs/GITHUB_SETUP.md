# GitHub 仓库设置说明

以下内容需在 GitHub 网页端手动配置（无法通过 Git 文件直接写入）。

## About 描述

进入仓库首页 → 右侧 **About** → 点击齿轮编辑：

**Description（描述）：**
```
ChainForge 无害化攻击链验证 Demo — 双轨复现 + 防护对账 + 动态拓扑推演
```

**Website（可选）：**
```
http://127.0.0.1:8500
```
（本地 Demo 地址，公开仓库可留空或填项目文档链接）

## Topics（标签）

在 About 编辑框中添加 Topics：

```
security
cybersecurity
attack-chain
digital-twin
demo
flask
waf
validation
pentest
```

## Release（可选）

1. 进入 **Releases** → **Create a new release**
2. Tag：`v1.0.0`
3. Title：`v1.0.0 — 首个公开 Demo`
4. 描述可复制 [CHANGELOG.md](../CHANGELOG.md) 中 v1.0.0 段落

## 推送本仓库更新

```bash
cd harmless-chain-demo
git add .
git commit -m "补充文档、截图与 LICENSE"
git push origin main
```

推送需 GitHub Personal Access Token（勾选 `repo` 权限）。
