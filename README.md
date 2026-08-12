# PickScout Agent

基于 Codex 的对话式跨境商机探测与选品研究 Agent。

本项目希望把分散的市场信号、商品数据和经营约束转化为可解释、可验证的商机判断，帮助初步进入 Amazon US FBA 的个人卖家更快地发现机会、排除伪需求并形成选品决策。

## 当前阶段

项目已完成第一轮方向调研，并具备首轮真实候选试点能力。v0 直接运行在 Codex 对话中，聚焦个人卖家的 Amazon US FBA 选品前研究，以“Agent 动态研究、证据与计算工具支撑、用户最终决策”为核心工作流。

- [v0 产品需求文档](docs/product-requirements-v0.md)
- [产品方向决策](docs/decisions/0001-amazon-us-fba-evidence-first.md)
- [Codex 仓库级 Agent 决策](docs/decisions/0002-codex-conversation-first-agent.md)
- [PickScout 方法论 v1](docs/pickscout-methodology-v1.md)
- [标准操作程序（SOP）v1](docs/pickscout-sop-v1.md)
- [研究协议 v0](docs/research-protocol-v0.md)
- [全部任务上下文与经验总结](docs/thread-context-and-lessons-2026-08-13.md)
- [早期产品简报](docs/product-brief.md)

## 初步能力方向

- 通过持续对话理解目标、补充条件、调整研究方向
- 捕捉市场、趋势、竞品与消费者需求信号
- 评估商品的需求、竞争、利润、合规与履约风险
- 生成有证据链的候选商机与选品建议
- 将证据、计算、假设和用户决定保存为可复盘研究产物

当前 v0 范围与验收标准见 [产品需求文档](docs/product-requirements-v0.md)。

## 标准使用流程

第一次使用时按以下顺序：

1. 阅读 [PickScout 方法论 v1](docs/pickscout-methodology-v1.md)，理解 A–G 决策阶段和证据边界。
2. 按 [标准操作程序 v1](docs/pickscout-sop-v1.md) 先明确本轮只支持哪一个经营决定。
3. 新任务从 `templates/` 复制卖家画像、研究简报和 [任务运行清单](templates/task-run-checklist.md) 到 `artifacts/<task-id>/`；只读解释不创建空任务目录。
4. 先建立同口径最低证据包，再让 Agent 动态解决最高价值未知项。
5. 需要时用仓库脚本完成三情景单位经济和供应硬门槛。
6. 每个改变后续行动的节点更新任务决策日志和跨任务总进度。
7. 用户明确决定和外部动作授权分别记录；未经授权不联系、下单、付款、订舱或修改 Amazon 数据。

后续 Agent 从本仓库启动时会通过根目录 `AGENTS.md` 自动读取并遵循上述方法和 SOP。

## 仓库结构

```text
.
├── AGENTS.md            # 本仓库内生效的 PickScout Agent 契约
├── .github/              # GitHub 协作模板
├── docs/
│   ├── decisions/        # 架构与产品决策记录
│   ├── plans/            # 可执行实施计划
│   ├── pickscout-methodology-v1.md
│   ├── pickscout-sop-v1.md
│   ├── research-protocol-v0.md
│   ├── product-brief.md  # 早期产品问题与假设
│   └── product-requirements-v0.md
├── templates/            # 卖家画像、简报、证据、报告和决定模板
├── scripts/              # 确定性计算与校验工具
├── tests/                # 确定性工具回归测试
├── .editorconfig
├── .env.example
├── CONTRIBUTING.md
└── README.md
```

真实任务开始后，原始输入写入被忽略的 `data/`，任务产物写入被忽略的 `artifacts/<task-id>/`；两者都不会进入 Git。

## 开始第一个试点

在本仓库的 Codex 对话中提供至少一种研究种子：

- Amazon 关键词或明确需求
- ASIN 或商品 URL
- 明确的细分类目
- 候选商品清单

如已知，可同时提供经营模式、资金范围、单 SKU 最大资金占用、供应链优势、禁止类目和已有数据工具。Agent 会按 [方法论](docs/pickscout-methodology-v1.md)、[SOP](docs/pickscout-sop-v1.md) 和 [研究协议](docs/research-protocol-v0.md) 运行，只补问高影响缺口，并在真实任务需要时创建私有研究产物和任务运行清单。

确定性计算与硬门槛工具：

```bash
python3 scripts/unit_economics.py templates/unit-economics-input.json
python3 scripts/hard_gates.py templates/hard-gates-input.json
python3 -m unittest discover -s tests -v
```

示例 JSON 中的金额、数量和交期仅用于工具冒烟测试，不能直接作为真实候选的经营数据。单位经济输入会按逐项日期和配置的新鲜度阈值拒绝过期数据；供应硬门槛缺少关键输入时输出 `unknown`，不会猜测。

## 后续验证

1. 确认首位用户的经营模式、资金范围、账号权限和现有数据源。
2. 从第一个真实种子开始，完成 10 个候选的对话式决策档案。
3. 验证哪些证据最能改变决定，以及哪些稳定约束应沉淀到仓库规则与研究协议。
4. 根据试点结果迭代根目录 `AGENTS.md`、模板和确定性脚本。

## 状态

Private / Product validation
