# PickScout Agent

基于 Codex 的对话式跨境商机探测与选品研究 Agent。

本项目希望把分散的市场信号、商品数据和经营约束转化为可解释、可验证的商机判断，帮助初步进入 Amazon US FBA 的个人卖家更快地发现机会、排除伪需求并形成选品决策。

## 当前阶段

项目已形成可运行的 v0 方法论、SOP、模板、确定性工具和 Codex 兼容适配器。v0 直接运行在 Codex 对话中，聚焦个人卖家的 Amazon US FBA 选品前研究，以“Agent 动态研究、证据与计算工具支撑、用户最终决策”为核心工作流。

- [v0 产品需求文档](docs/product-requirements-v0.md)
- [产品方向决策](docs/decisions/0001-amazon-us-fba-evidence-first.md)
- [Codex 仓库级 Agent 决策](docs/decisions/0002-codex-conversation-first-agent.md)
- [PickScout 方法论 v1](docs/pickscout-methodology-v1.md)
- [标准操作程序（SOP）v1](docs/pickscout-sop-v1.md)
- [PickScout Agent 分发决策](docs/decisions/0008-publish-distributable-pickscout-agent.md)
- [公开迁移与历史保留决策](docs/decisions/0009-archive-private-incubation-and-publish-sanitized-history.md)
- [研究协议 v0](docs/research-protocol-v0.md)
- [参与开发与贡献指南](CONTRIBUTING.md)
- [选品专员职责](docs/selection-team.md)

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
4. 先复用可比证据，再让Agent解决最高价值未知项。统计排名按同口径数据计算；商业推荐顺序可以由专业取舍形成，不以固定ASIN数量阻止建议。
5. 需要时用仓库脚本完成三情景单位经济和供应硬门槛。
6. 每个改变后续行动的节点更新任务决策日志和跨任务总进度。
7. 用户明确决定和外部动作授权分别记录；未经授权不联系、下单、付款、订舱或修改 Amazon 数据。

后续 Agent 从本仓库启动时会通过根目录 `AGENTS.md` 自动读取并遵循上述方法和 SOP。

## 产品与品类市场研究

先看 [一页方法论与调用语句](docs/market-research-one-page.md)，详细执行 [八步研究规范](docs/market-research-v1.md)：界定市场→初筛方向→采集核对→需求趋势→竞争新品→关键词与买家需求→价格及进入条件→九章报告。用六维证据与反证形成建议，默认本地 HTML 主报告；表格、截图和用户指定交付格式均可使用。

唯一研究 Skill 维护入口是根 [skills/amazon-category-opportunity-research](skills/amazon-category-opportunity-research/SKILL.md)，`.agents/skills/` 只链接它；详细方法与模板共用根 `docs/`、`templates/`。完整 A–G Agent 适配器镜像同一规范，不依赖外仓或再安装一个 Skill。没有完整成本时经济性写“未评估”，不提前要求供应商/工厂/样品。

选品、品类、竞品、需求与市场研究由 PickScout 维护；Listing、Seller Central、FBA、库存订单及运营执行交 auto-amazon。归属调整见 [决策0014](docs/decisions/0014-pickscout-owned-market-research.md)。专业判断和按需协作见[决策0015](docs/decisions/0015-judgment-and-user-controlled-collaboration.md)，商业推荐、唯一当前简报和客户审读见[决策0016](docs/decisions/0016-ranking-current-brief-client-review.md)。

### 维护源与可复用版本

- 在本仓库工作时，研究入口为`skills/amazon-category-opportunity-research/`，共用根目录`docs/`、`templates/`与`scripts/`；该项目入口不作为脱离仓库的独立文件夹安装。
- 在其他工作区使用时，安装下面的自包含`adapters/codex/pickscout-agent/`，包内包含同源方法、模板和计算工具，不依赖本机目录或运营项目。
- 可复用规则进入Git版本；私人原件、研究报告、采购清单与运行绑定留在忽略目录。本地源码和分发镜像一致，不等于GitHub或其他使用者的安装已更新；公开安装来源以远端已交付版本为准。

## 通过 Agent 安装 PickScout Agent

PickScout Agent 的长期核心是本仓库中的方法论、SOP、研究协议、任务模板和确定性计算脚本。`adapters/codex/pickscout-agent/` 只是当前 Codex 可识别的兼容适配器；未来运行时变化时可以替换适配器，而不改变 PickScout Agent 本身。

用户不需要手动克隆或复制目录。把下面的请求交给 Codex Agent：

> 请使用 `$skill-installer` 从 GitHub 仓库 `bells0/pickscout-agent` 的 `adapters/codex/pickscout-agent` 路径安装 PickScout Agent。只安装这一个 Agent 适配器；完成后告诉我下一轮如何调用。

Agent 会调用当前 Codex 的标准安装能力，把兼容适配器安装到用户环境。安装完成后，在下一轮对话中使用 `$pickscout-agent`，并提供关键词、需求、细分类目、ASIN、URL、候选清单、供应商 offer 或已有研究产物。

手动克隆和复制只作为 Agent 安装不可用时的故障兜底，不作为标准安装流程。安装不要求用户理解当前的 Skill 目录机制，也不自动安装插件或 MCP。

发布适配器与根目录事实来源保持契约测试，并通过公开 GitHub 路径执行安装验收。

## 仓库结构

```text
.
├── AGENTS.md            # 本仓库内生效的 PickScout Agent 契约
├── .github/              # GitHub 协作模板
├── docs/
│   ├── decisions/        # 架构与产品决策记录
│   ├── pickscout-methodology-v1.md
│   ├── pickscout-sop-v1.md
│   ├── research-protocol-v0.md
│   └── product-requirements-v0.md
├── templates/            # 卖家画像、简报、证据、报告和决定模板
├── scripts/              # 确定性计算与校验工具
├── skills/               # 项目市场研究入口，引用同仓规范和模板
├── adapters/
│   └── codex/
│       └── pickscout-agent/ # 当前 Codex 的兼容安装入口
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

## 参与开发

可复用改进从一个已确认问题、范围和验收方式的 Issue 开始。从最新的 `main` 创建独立分支或 worktree，禁止直接向 `main` 提交；一个 Pull Request 只解决一个 Issue，并由其他成员 Review 后再合并。详细的 Issue-to-PR 流程、验证证据和安全边界见 [贡献指南](CONTRIBUTING.md)。

## 项目演进

1. 使用有明确研究种子和授权边界的真实任务持续验证工作流。
2. 识别最能改变经营决定的证据，并把稳定约束沉淀到仓库规则与研究协议。
3. 根据复盘结果迭代根目录 `AGENTS.md`、模板、确定性脚本和运行时适配器。
4. 通过 Issues 和 Pull Requests 讨论可复用的改进，不提交个人研究数据或凭据。

## 状态

Open source / Apache-2.0

## License

PickScout Agent is licensed under the [Apache License 2.0](LICENSE).
