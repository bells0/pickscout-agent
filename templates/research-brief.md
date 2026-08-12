# 研究简报

## 任务元数据

| 字段 | 值 |
| --- | --- |
| `task_id` | `<稳定任务 ID>` |
| `brief_version` | `<正整数>` |
| `status` | `<draft / researching / needs_input / blocked / ready_for_review / decided / archived>` |
| `created_at` | `<ISO 8601 时间>` |
| `updated_at` | `<ISO 8601 时间>` |
| `stop_reason` | `<criteria_satisfied / budget_exhausted / source_unavailable / user_stopped / 未停止>` |
| `seller_profile_snapshot` | `<profile_id、version、文件引用>` |

## 研究种子与核心问题

- `seed_type`：`<keyword / need / subcategory / asin / url / candidate_list>`
- `seed_value_or_ref`：`<原始值或被忽略文件的仓库内引用>`
- 核心问题：`<本任务要支持的经营判断>`
- 预期产物：`<阶段性判断、单候选报告或候选比较>`

## 候选与范围

| `candidate_id` | 需求 / 关键词簇 | 代表 ASIN 或商品 | 目标规格与价格带 | 当前 Agent 建议摘要 | 当前用户决定摘要 |
| --- | --- | --- | --- | --- | --- |
| `<稳定候选 ID>` | `<描述>` | `<ASIN、URL 或未确定>` | `<范围或未确认>` | `<状态、报告版本或尚无>` | `<状态、决定版本或尚无>` |

- 市场与履约：`<市场、站点、FBA 边界>`
- 允许扩展：`<关键词、细分需求、代表商品的扩展边界>`
- 明确排除：`<类目、商品、地区、商业模式或其他边界>`
- 重大范围假设：`<会改变研究对象的假设；没有则写“无”>`

## 来源、权限与预算

- 允许的来源：`<公开来源、用户文件、授权数据或其他边界>`
- 已有权限：`<当前可用账号、导出或数据服务>`
- 需另行确认的动作：`<付费、授权或外部影响动作；没有则写“无”>`
- 时间预算：`<上限和已使用>`
- 数据成本预算：`<币种、上限和已使用>`

## 决策标准

### 适用硬门槛

| 硬门槛 | 判定规则或用户阈值 | 当前状态 | 证据或缺口 ID |
| --- | --- | --- | --- |
| `<门槛>` | `<可验证条件>` | `<pass / fail / unknown>` | `<ID>` |

### 必填分析维度

| 分析维度 | 覆盖状态 | 关键 Evidence / Claim / Gap ID |
| --- | --- | --- |
| 需求与趋势 | `<covered / partial / missing / skipped_due_to_decisive_hard_gate>` | `<ID>` |
| 竞争与进入壁垒 | `<状态>` | `<ID>` |
| 消费者问题与差异化空间 | `<状态>` | `<ID>` |
| 单位经济与现金占用 | `<状态>` | `<ID>` |
| 供应链与履约风险 | `<状态>` | `<ID>` |
| 合规与知识产权风险 | `<状态>` | `<ID>` |
| 证据完整度与不确定性 | `<状态>` | `<ID>` |

## 当前高价值问题与动态计划

此表记录当前优先判断，不表示固定工具顺序。新证据到达后更新优先级和动作。

| 优先级 | 未解决问题 | `decision_impact` | 为什么现在处理 | 下一可逆动作 | 预计成本 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `<高 / 中 / 低>` | `<问题>` | `<hard_gate / status_change / confidence_only / context_only>` | `<预期改变的判断>` | `<搜索、询问、导入或计算>` | `<时间 / 数据成本>` | `<open / in_progress / resolved / blocked / skipped>` |

## 开放信息缺口

| Gap ID | 候选 | 分析维度 / `signal_type` | `decision_impact` | 可取得性与阻塞原因 | 建议取得方式 | 状态 / 版本 |
| --- | --- | --- | --- | --- | --- | --- |
| `<稳定 ID>` | `<candidate_id>` | `<维度和信号>` | `<hard_gate / status_change / confidence_only / context_only>` | `<说明>` | `<动作与预计成本>` | `<open / resolved / waived；版本>` |

## 停止与恢复

- `criteria_satisfied` 检查结果：`<满足 / 不满足；关键原因>`
- 当前停止说明：`<停止原因及其与任务状态的关系>`
- 最近完成的产物：`<文件、版本和时间>`
- 恢复时先核对：`<范围、需刷新来源、阻塞项或用户输入>`
- 下一项最高价值动作：`<一个明确动作>`

## 变更记录

| 版本 | 时间 | 用户纠正、新证据或范围变化 | 受影响的证据、计算或结论 |
| --- | --- | --- | --- |
| `<版本>` | `<ISO 8601 时间>` | `<变化>` | `<仍适用 / 部分适用 / 已失效及对应 ID>` |
