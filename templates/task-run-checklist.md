# PickScout 任务运行清单

> 真实任务开始或恢复时复制到 `artifacts/<task-id>/task-run-checklist.md`。本清单固定操作外环，不替代研究简报、证据账本、报告或决策日志。

## 1. 任务定位

| 字段 | 值 |
| --- | --- |
| `task_id` | `<稳定任务 ID>` |
| `checklist_version` | `<正整数>` |
| `updated_at` | `<ISO 8601 时间>` |
| `current_stage` | `<A_discovery / B_screening / C_sample_screen / D_sample_validation / E_procurement_economics / F_fba_logistics / G_live_review>` |
| `decision_question` | `<本轮要支持的一个经营决定>` |
| `candidate_ids` | `<稳定候选 ID>` |
| `seller_profile_snapshot` | `<文件和版本>` |

## 2. 启动或恢复检查

- [ ] 已读取 `AGENTS.md`。
- [ ] 已读取 `docs/pickscout-methodology-v1.md`。
- [ ] 已读取 `docs/pickscout-sop-v1.md`。
- [ ] 已读取 `docs/research-protocol-v0.md`。
- [ ] 已读取与当前阶段相关的决策记录。
- [ ] 恢复任务时已读取总进度、任务决策日志、研究简报和最新报告。
- [ ] 已核对哪些证据需要刷新。

## 3. 当前阶段门槛

- 阶段输入：`<已有输入>`
- 阶段输出：`<预期产物>`
- 本轮适用硬门槛：`<门槛或引用>`
- 本轮明确不处理的后续门槛：`<门槛>`
- `advance` 条件：`<条件>`
- `observe` 条件：`<条件>`
- `reject` 条件：`<条件>`
- `insufficient` 条件：`<条件>`

## 4. 候选最低可比证据包

| 候选 | 产品定义 | Amazon 类目/ASIN | 需求与竞争 | 失败主题 | 供应 | 合规/IP | 可比状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<candidate_id>` | `<有/缺>` | `<有/缺；数量>` | `<有/缺>` | `<有/缺>` | `<有/缺>` | `<有/缺/不适用>` | `<comparable / discovery_only>` |

严格排序前检查：

- [ ] 所有参与排序的候选均为 `comparable`。
- [ ] Amazon 样本用途、价格带和观察时间一致。
- [ ] 样本已经固定，不因结论倾向随意替换。
- [ ] 多个平台的上游来源已经去重。

## 5. 高价值未知项队列

| 优先级 | Gap ID | 问题 | `decision_impact` | 为什么现在查 | 最小取得动作 | 授权要求 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<高/中/低>` | `<ID>` | `<问题>` | `<hard_gate / status_change / confidence_only / context_only>` | `<会改变什么>` | `<动作>` | `<无需 / 需确认>` | `<open / in_progress / resolved / blocked / skipped>` |

当前最高价值动作：`<只写一个>`

## 6. 证据与反证检查

- [ ] 关键事实有来源、时间、市场、口径和适用范围。
- [ ] 事实、推断和假设使用稳定 Claim ID。
- [ ] 支持与反对证据都已记录。
- [ ] 已写出最强反对理由。
- [ ] 模型总结没有被当作证据。
- [ ] 公开低价、购买标签和第三方估算没有被越界解释。

## 7. 阶段专用执行

### A/B 候选发现与筛选

- [ ] 候选覆盖多个功能家族，不只集中在易搜集形态。
- [ ] 社交信号只用于发现。
- [ ] 深筛候选固定 5–10 个可比 ASIN。
- [ ] 研究优先级没有被写成采购排序。

### C/D 样品筛选与验证

- [ ] 1688 offer ID、SKU、页面价和 MOQ 已记录。
- [ ] 页面能回答的字段已先从页面取得。
- [ ] 供应商问题只保留会改变当前决定的字段。
- [ ] 对外文案已由用户确认。
- [ ] 评论失败主题已转为样品测试项。
- [ ] 已记录用户最终包装的实测重尺。

### E 采购与单位经济

- [ ] 正式 RFQ、MOQ、交期和质检条件已取得。
- [ ] Amazon 官方费用已取得。
- [ ] 头程、广告、退货、损耗、税费和汇率有来源。
- [ ] 三情景单位经济已由脚本完成。
- [ ] 供应硬门槛已由脚本完成。

### F/G FBA、物流与上线复盘

- [ ] FBA SKU、实际 FC 和封箱实测已取得。
- [ ] 物流商按同口径全费用报价。
- [ ] 税费、IOR、保险、异常费和特殊货物合规已确认。
- [ ] 外部创建、订舱、付款有单独授权。
- [ ] 上线后真实经营数据已回填并与原情景比较。

## 8. 建议、决定与授权

| 对象与阶段 | Agent 建议 | 用户决定 | 动作授权 | 执行事实 |
| --- | --- | --- | --- | --- |
| `<candidate_id> / <stage>` | `<advance / observe / reject / insufficient>` | `<continue / observe / drop / undecided / pending>` | `<not_required / pending / approved / denied>` | `<not_started / attempted / completed / failed>` |

- [ ] Agent 建议没有自动填成用户决定。
- [ ] 继续研究没有被写成买样或采购授权。
- [ ] 已授权未执行与已执行已经分开。

## 9. 充分性与停止

- [ ] 必填分析维度已覆盖或明确标缺。
- [ ] 所有适用硬门槛均有 `pass / fail / unknown`。
- [ ] 未解决 `hard_gate` 或 `status_change` Gap：`<ID 或无>`。
- [ ] 三情景输入均有来源并可复算。
- [ ] 来源冲突已经保留和解释。
- [ ] 只有满足研究协议时才使用 `criteria_satisfied`。

当前任务状态：`<draft / researching / needs_input / blocked / ready_for_review / decided / archived>`

停止原因：`<criteria_satisfied / budget_exhausted / source_unavailable / user_stopped / 未停止>`

## 10. 交付与交接

- [ ] 对话先给结论，再给证据和限制。
- [ ] 已列当前阶段、最强支持、最强反对、关键未知和下一动作。
- [ ] 决策检查点已追加到 `decision-log.md`。
- [ ] `artifacts/research-progress.md` 已同步。
- [ ] 用户明确决定时已更新 `user-decision.md`。
- [ ] 执行交付物已按读者分层，SKU、数量、链接和版本无歧义。
- [ ] 暂停时已保存恢复动作。

下一项最低成本动作：`<动作>`

恢复时第一步：`<动作或需读取的文件>`

## 11. 变更记录

| 版本 | 时间 | 当前阶段 | 变化 |
| --- | --- | --- | --- |
| `<版本>` | `<ISO 8601 时间>` | `<阶段>` | `<范围、证据、门槛、建议或决定变化>` |
