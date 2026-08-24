# 协作约定

项目目前处于需求发现阶段。

## 工作方式

- 一项变更解决一个清晰问题。
- 产品或架构的重要决定写入 `docs/decisions/`。
- 新能力先说明用户问题、预期结果和验证方式。
- 不提交密钥、访问令牌、用户数据或未经脱敏的业务数据。

## Issue-to-PR 流程

1. 编码前先通过需求提案或正式 Issue 确认问题、变更范围和可验证的验收方式。安全问题请通过私密渠道报告；密钥、用户数据和未经脱敏的业务数据不得进入公开 Issue。
2. 从最新的 `main` 创建独立分支或 worktree 开发，禁止直接向 `main` 提交。
3. 一个 PR 只解决一个 Issue。PR 描述使用 `Closes #N` 关联对应 Issue，并说明实现范围。
4. PR 必须记录实际执行的验证命令和结果、已知风险与未验证项，以及 Coding Agent 提供了哪些辅助。Agent 的输出不能替代人工复核；提交者或指定 Reviewer 负责检查变更、验证证据、安全与数据脱敏，并决定是否批准合并。
5. Review 中超出当前 Issue 范围的反馈另开 Issue 跟踪，不在当前 PR 中顺带扩展。

合并前确认验收条件已满足、必要 Review 已完成且验证证据可复现；由具备合并权限的人类成员完成最终合并。

## 提交信息

使用带 scope 的 Conventional Commit 格式：`type(scope): summary`，例如 `docs(workflow): document issue-to-pr process`。

- `docs` 文档
- `feat` 新能力
- `fix` 修复
- `chore` 工程维护
- `test` 测试
