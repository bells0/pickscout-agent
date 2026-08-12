# 用户决定

> 仅在用户明确表达决定后记录。本文件不得从 Agent 建议自动预填；没有明确决定时保持未记录，而不是推断用户选择。

## 决定元数据

| 字段 | 值 |
| --- | --- |
| `decision_id` | `<稳定决定 ID>` |
| `decision_version` | `<正整数>` |
| `task_id` | `<稳定任务 ID>` |
| `candidate_id` | `<稳定候选 ID>` |
| `based_on_report_version` | `<用户审阅的报告版本>` |
| `decider` | `<用户指定的姓名或角色>` |
| `decided_at` | `<ISO 8601 时间>` |
| `recorded_at` | `<ISO 8601 时间>` |
| `supersedes_decision_id` | `<被替代的决定 ID；没有则写“无”>` |

## 用户明确选择

- `decision_status`：`<continue / observe / drop / undecided>`
- `reason`：`<用户给出的主要理由>`
- 用户原意引用或确认记录：`<对话引用、文件引用或确认时间>`

## 用户接受的风险与未解决假设

- `accepted_risks`：
  - `<用户明确接受的风险；没有则写“无”>`
- 未解决假设：
  - `<用户决定时仍未解决的假设或 Gap ID；没有则写“无”>`

## 与 Agent 建议的关系

- `disagrees_with_agent`：`<true / false>`
- 说明：`<不一致之处及用户理由；一致时可写“无”>`

## 后续动作

- `next_action`：`<用户确认的具体动作；没有则写“无”>`
- 负责人：`<用户指定的人或角色>`
- `review_at`：`<ISO 8601 时间或触发复盘的条件>`

## 变更说明

`<若本决定替代旧版本，说明改变了什么以及依据哪一版报告或新证据；首次记录写“首次决定”。>`
