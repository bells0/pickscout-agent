# 决策检查点日志

> 本文件按时间追加，不覆盖历史。Agent 建议与用户决定必须分开；用户没有明确表态时写 `pending`。

## 日志元数据

| 字段 | 值 |
| --- | --- |
| `task_id` | `<稳定任务 ID>` |
| `log_version` | `<正整数>` |
| `updated_at` | `<ISO 8601 时间>` |
| `current_stage` | `<研究、筛选、询价、样品、单位经济、采购前审阅或复盘>` |
| `current_checkpoint_id` | `<最近检查点 ID>` |

## 当前摘要

- 当前 Agent 建议：`<advance / observe / reject / insufficient>`
- 当前用户决定：`<continue / observe / drop / undecided / pending>`
- 当前阻塞或关键未知：`<Gap ID 或说明>`
- 下一项需要用户决定：`<问题；没有则写“无”>`
- 下一项可逆动作：`<动作>`

## 检查点

### `<checkpoint_id>`：`<简短标题>`

| 字段 | 值 |
| --- | --- |
| `occurred_at` | `<ISO 8601 时间>` |
| `candidate_id` | `<稳定候选 ID；跨候选时写“multiple”>` |
| `stage` | `<阶段>` |
| `trigger` | `<用户要求、新证据、计算结果或状态变化>` |
| `supersedes` | `<旧 checkpoint_id；没有则写“无”>` |
| `status` | `<active / superseded / completed / paused>` |

**当时选项**

1. `<选项 A>`
2. `<选项 B>`

**Agent 建议**

- 状态：`<advance / observe / reject / insufficient>`
- 建议：`<建议内容>`
- 理由：`<最重要的支持和反对理由>`

**用户决定**

- 状态：`<continue / observe / drop / undecided / pending>`
- 明确决定：`<用户原意；未明确时写“尚未明确决定”>`
- 确认依据：`<对话时间或 user-decision.md；没有则写“无”>`

**依据与限制**

- 依据文件：`<报告、证据、计算或日志引用>`
- 关键未知：`<Gap ID 或说明>`
- 接受风险：`<用户明确接受的风险；没有则写“无”>`

**后续**

- 下一动作：`<动作>`
- 负责人：`<Agent / 用户 / 供应商 / 其他>`
- 复盘条件：`<日期或触发条件>`

## 变更记录

| 版本 | 时间 | 变化 |
| --- | --- | --- |
| `<版本>` | `<ISO 8601 时间>` | `<新增或替代了哪些检查点>` |
