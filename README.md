# PickScout Agent

跨境商机探测与选品分析助手。

本项目希望把分散的市场信号、商品数据和经营约束转化为可解释、可验证的商机判断，帮助初步进入 Amazon US FBA 的个人卖家更快地发现机会、排除伪需求并形成选品决策。

## 当前阶段

项目已完成第一轮方向调研，进入产品验证准备阶段。v0 聚焦个人卖家的 Amazon US FBA 选品前研究，以“Agent 搜集和整理可信信息、结合用户条件提供建议、用户最终决策”为核心工作流。

- [v0 产品需求文档](docs/product-requirements-v0.md)
- [产品方向决策](docs/decisions/0001-amazon-us-fba-evidence-first.md)
- [早期产品简报](docs/product-brief.md)

## 初步能力方向

- 捕捉市场、趋势、竞品与消费者需求信号
- 评估商品的需求、竞争、利润、合规与履约风险
- 生成有证据链的候选商机与选品建议
- 保存分析过程、假设与反馈，持续校准判断

当前 v0 范围与验收标准见 [产品需求文档](docs/product-requirements-v0.md)。

## 仓库结构

```text
.
├── .github/              # GitHub 协作模板
├── docs/
│   ├── decisions/        # 架构与产品决策记录
│   ├── product-brief.md  # 早期产品问题与假设
│   └── product-requirements-v0.md
├── .editorconfig
├── .env.example
├── CONTRIBUTING.md
└── README.md
```

## 下一步

1. 确认首位用户的经营模式、资金范围、账号权限和现有数据源。
2. 用统一研究模板完成 10 个真实候选的人工决策档案。
3. 验证哪些证据最能改变决定，以及哪些数据长期无法可靠获得。
4. 根据人工试点结果制定 Evidence-first v0 的实现计划。

## 状态

Private / Product validation
