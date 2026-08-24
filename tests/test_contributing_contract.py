import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContributingContractTests(unittest.TestCase):
    def test_issue_to_pr_responsibility_boundaries_are_documented(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        required_terms = (
            "确认问题、变更范围和可验证的验收方式",
            "独立分支或 worktree",
            "禁止直接向 `main` 提交",
            "一个 PR 只解决一个 Issue",
            "`Closes #N`",
            "实际执行的验证命令和结果",
            "已知风险与未验证项",
            "Coding Agent 提供了哪些辅助",
            "Agent 的输出不能替代人工复核",
            "超出当前 Issue 范围的反馈另开 Issue",
            "安全问题请通过私密渠道报告",
            "未经脱敏的业务数据不得进入公开 Issue",
        )

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, contributing)


if __name__ == "__main__":
    unittest.main()
