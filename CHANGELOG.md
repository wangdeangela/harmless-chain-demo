# Changelog

本文件记录 ChainForge 无害化攻击链验证 Demo 的主要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [Unreleased]

### 待办
- 接入 RCE+EDR、弱口令等 4 个待运行场景
- OpenAEV 实网 Inject 一键联调
- 演示截图 GIF 动画

## [1.0.0] - 2026-06-15

### 新增
- 图形化 Web 控制台（Flask，`:8500`）
- **验证推演**页：攻击面拓扑 + 日志侧栏合并布局
- 四阶段动态推演（P1 日志还原 → P2 验证计划 → P3 双轨复现 → P4 防护对账）
- 约 90 秒拓扑动画：攻击路径逐跳高亮、日志流式写入
- 验证结论延迟展示（推演结束后输出 score / verdict）
- 双轨执行 Tab：pentest-ai PoC + OpenAEV Inject + 联合判定矩阵
- 防护对账 Tab：120s 窗口查询、命中记录、对账结论
- 内置 2 个可运行场景：SQL 注入+WAF、APT 横向截断
- 场景库展示 6 类攻击场景配置
- 本地无害靶场（`:8099`）
- 命令行离线推演 `run-sim-flow.sh`
- Docker Compose 部署配置

### 变更
- 术语统一：「防护回采/Collector」→「防护对账」
- 「验证中心」「网络拓扑」合并为「验证推演」
- 启动脚本每次重启 Portal，避免加载旧页面缓存

### 文档
- README：克隆启动、项目结构、API、架构图
- MIT License
- 演示截图

[Unreleased]: https://github.com/wangdeangela/harmless-chain-demo/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/wangdeangela/harmless-chain-demo/releases/tag/v1.0.0
