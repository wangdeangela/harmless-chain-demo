# ChainForge 无害化攻击链验证

本地可运行的无害化攻击链验证平台，集成 **OpenAEV + pentest-ai** 双轨执行与 **Collector** 防护回采。

## 图形化控制台（推荐）

```bash
conda activate wangxj01brain
cd harmless-chain-demo
bash scripts/start-graphical-demo.sh
```

浏览器打开 **http://127.0.0.1:8500**，点击「启动验证任务」。

### 控制台模块

| 模块 | 功能 |
|------|------|
| **验证中心** | 启动任务、四阶段流水线、裁决摘要 |
| **策略与授权** | 分级授权 L0–L4、证明点、评分引擎 |
| **双轨执行** | pentest-ai PoC + OpenAEV Inject、联合判定矩阵 |
| **防护回采** | Collector 120s 窗口、SOC 查询、对账回写 |
| **攻击场景库** | 6 类内置场景、验证剧本与实测对照 |

## Docker 部署

```bash
bash scripts/docker-up.sh
```

| 服务 | 端口 |
|------|------|
| 控制台 | 8500 |
| 验证靶场 | 8099 |
| OpenAEV（可选） | 8888 |

## 命令行离线推演

```bash
bash scripts/run-sim-flow.sh
```

## 内置验证场景

| 场景 | 验证轨道 | 典型结论 |
|------|----------|----------|
| SQL 注入 + WAF 对账 | pentest-ai ∥ OpenAEV | 部分成立，detect_no_block |
| APT 横向 · 防火墙截断 | OpenAEV 单轨 | 不成立，链被阻断 |

## 安全说明

- 仅对本地授权靶场执行无害探针
- 默认授权级别 L2，止于 ProofPoint
- 禁止对未授权目标使用
