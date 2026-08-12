import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "templates" / "evidence-record.schema.json"
PROTOCOL_PATH = REPO_ROOT / "docs" / "research-protocol-v0.md"
BRIEF_PATH = REPO_ROOT / "templates" / "research-brief.md"
REPORT_PATH = REPO_ROOT / "templates" / "research-report.md"
USER_DECISION_PATH = REPO_ROOT / "templates" / "user-decision.md"
PRD_PATH = REPO_ROOT / "docs" / "product-requirements-v0.md"
GITIGNORE_PATH = REPO_ROOT / ".gitignore"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
METHODOLOGY_PATH = REPO_ROOT / "docs" / "pickscout-methodology-v1.md"
SOP_PATH = REPO_ROOT / "docs" / "pickscout-sop-v1.md"
RUN_CHECKLIST_PATH = REPO_ROOT / "templates" / "task-run-checklist.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    assert start != -1, f"missing section start: {start_marker}"
    end = text.find(end_marker, start + len(start_marker))
    if end == -1:
        end = len(text)
    return text[start:end]


def _extract_line_enum(text: str) -> set:
    """Extract enum-like tokens from inline backticks on one line."""
    values = set()
    for token in re.findall(r"`([^`]+)`", text):
        inner = token.strip().strip("<> ")
        if "/" in inner:
            for part in inner.split("/"):
                clean = part.strip().strip("<>").strip()
                if clean:
                    values.add(clean)
        elif re.fullmatch(r"[A-Za-z_]+", inner):
            values.add(inner)
    return values


def _extract_row_enum(text: str, field: str) -> set:
    marker = f"`{field}`"
    for line in text.splitlines():
        if marker in line:
            values = _extract_line_enum(line)
            values.discard(field)
            if values:
                return values
    raise AssertionError(f"No enum-style row found for field: {field}")


def _extract_first_col_backtick_tokens(section_text: str) -> set:
    matches = re.findall(r"^\|\s*`([^`]+)`\s*\|", section_text, flags=re.M)
    return set(matches)


def _extract_bullet_backtick_values(section_text: str) -> set:
    values = set()
    for line in section_text.splitlines():
        if line.lstrip().startswith("-"):
            for token in re.findall(r"`([A-Za-z_]+)`", line):
                values.add(token)
    return values


def _extract_backtick_values_from_line(text: str, anchor: str) -> set:
    for line in text.splitlines():
        if anchor in line:
            return set(re.findall(r"`([^`]+)`", line))
    raise AssertionError(f"No line found containing anchor: {anchor}")


def _resolve_ref(schema: dict, node: dict) -> dict:
    if "$ref" not in node:
        return node
    ref = node["$ref"]
    if not ref.startswith("#/$defs/"):
        raise AssertionError(f"Unsupported ref format in schema: {ref}")
    def_name = ref.split("/")[-1]
    return schema["$defs"][def_name]


class ResearchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(_read_text(SCHEMA_PATH))
        cls.protocol = _read_text(PROTOCOL_PATH)
        cls.brief = _read_text(BRIEF_PATH)
        cls.report = _read_text(REPORT_PATH)
        cls.user_decision = _read_text(USER_DECISION_PATH)
        cls.prd = _read_text(PRD_PATH)
        cls.gitignore = _read_text(GITIGNORE_PATH)
        cls.agents = _read_text(AGENTS_PATH)
        cls.methodology = _read_text(METHODOLOGY_PATH)
        cls.sop = _read_text(SOP_PATH)
        cls.run_checklist = _read_text(RUN_CHECKLIST_PATH)

    def test_schema_is_loadable_and_draft_2020_12(self):
        self.assertEqual(
            self.schema.get("$schema"),
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_schema_required_fields_include_key_contract_fields(self):
        required = set(self.schema.get("required", []))
        mandatory = {
            "evidence_id",
            "task_id",
            "candidate_id",
            "claim_id",
            "signal_type",
            "source_family",
            "independence_basis",
            "decision_impact",
            "source",
            "timing",
            "scope",
            "extraction",
            "quality",
            "stance",
            "conflict",
            "version",
            "record_status",
        }
        self.assertTrue(mandatory.issubset(required))

    def test_schema_enum_contracts_cover_quality_decision_and_support_dimensions(self):
        properties = self.schema["properties"]
        decision_impact = properties["decision_impact"]["enum"]
        stance = properties["stance"]["enum"]
        record_status = properties["record_status"]["enum"]
        source_family = properties["source_family"]["enum"]
        signal_type = properties["signal_type"]["enum"]
        conflict_status = properties["conflict"]["properties"]["status"]["enum"]

        quality_sample = properties["quality"]["properties"]["relevance"]
        quality_rating = _resolve_ref(self.schema, quality_sample)["properties"]["rating"]["enum"]

        self.assertTrue({"high", "medium", "low"}.issubset(set(quality_rating)))
        self.assertEqual(
            set(decision_impact),
            {"hard_gate", "status_change", "confidence_only", "context_only"},
        )
        self.assertEqual(set(stance), {"supports", "opposes", "neutral"})
        self.assertEqual(
            set(record_status),
            {"active", "superseded", "invalidated"},
        )
        self.assertEqual(
            set(conflict_status),
            {"none", "open", "explained", "escalated", "resolved"},
        )
        self.assertEqual(
            set(source_family),
            {
                "amazon_official_or_authorized",
                "regulator_or_standards",
                "licensed_third_party_structured",
                "user_owned_operating_data",
                "supplier_logistics_testing",
                "public_industry_research",
                "community_or_personal_experience",
            },
        )
        self.assertEqual(
            set(signal_type),
            {
                "amazon_demand_behavior",
                "off_amazon_search_interest",
                "price_bsr_offer_history",
                "competition_structure",
                "consumer_feedback_returns",
                "unit_economics",
                "supply_chain_fulfillment",
                "compliance_ip",
            },
        )

    def test_cross_document_task_status_alignment(self):
        protocol_task_section = _extract_section(
            self.protocol,
            "## 3. ",
            "## 4.",
        )
        protocol_task_status = _extract_first_col_backtick_tokens(protocol_task_section)

        brief_task_status = _extract_row_enum(self.brief, "status")
        report_task_status = _extract_row_enum(self.report, "task_status")

        self.assertEqual(protocol_task_status, brief_task_status)
        self.assertTrue(report_task_status.issubset(protocol_task_status))

    def test_cross_document_stop_reason_alignment(self):
        protocol_stop_section = _extract_section(
            self.protocol,
            "其他停止原因不会自动进入 `ready_for_review`：",
            "## 8. Agent 建议",
        )
        protocol_stop_reasons = _extract_first_col_backtick_tokens(protocol_stop_section)

        brief_stop_reason = _extract_row_enum(self.brief, "stop_reason")
        report_stop_reason = _extract_row_enum(self.report, "stop_reason")

        self.assertTrue(
            {"budget_exhausted", "source_unavailable", "user_stopped"}.issubset(
                brief_stop_reason
            )
        )
        self.assertIn("criteria_satisfied", brief_stop_reason)
        self.assertEqual(brief_stop_reason, report_stop_reason)
        self.assertTrue(protocol_stop_reasons.issubset(brief_stop_reason))

    def test_cross_document_recommendation_alignment_with_prd_protocol(self):
        protocol_recommendation_section = _extract_section(
            self.protocol,
            "## 8. Agent 建议",
            "## 9. 暂停、恢复、范围变化与版本",
        )
        protocol_recommendation = _extract_bullet_backtick_values(
            protocol_recommendation_section
        )

        report_recommendation = _extract_line_enum(
            next(
                line
                for line in self.report.splitlines()
                if "- Agent 建议：" in line
            )
        )

        prd_recommendation = _extract_backtick_values_from_line(
            self.prd, "- 建议状态："
        )

        self.assertEqual(protocol_recommendation, report_recommendation)
        self.assertEqual(prd_recommendation, {"advance", "observe", "reject", "insufficient"})
        self.assertEqual(protocol_recommendation, prd_recommendation)

    def test_claim_type_and_decision_status_alignment(self):
        claim_section = _extract_section(
            self.protocol,
            "### 5.1 Claim 管理",
            "### 5.2 证据记录",
        )
        protocol_claim_types = _extract_bullet_backtick_values(claim_section)

        report_claim_line = next(
            line
            for line in self.report.splitlines()
            if "fact / inference / hypothesis" in line
        )
        report_claim_types = _extract_line_enum(report_claim_line)
        report_claim_types.discard("ID")

        self.assertEqual(protocol_claim_types, report_claim_types)

        self.assertTrue(
            "fact / inference / hypothesis" in self.prd
            or "事实 / 推断 / 假设" in self.prd
        )
        user_decision_status = _extract_row_enum(self.user_decision, "decision_status")
        prd_user_decision_line = _extract_backtick_values_from_line(
            self.prd, "- `decision_status`："
        )
        prd_user_decision_line.discard("decision_status")

        self.assertEqual(user_decision_status, {
            "continue",
            "observe",
            "drop",
            "undecided",
        })
        self.assertEqual(prd_user_decision_line, {
            "continue",
            "observe",
            "drop",
            "undecided",
        })

    def test_template_markers_preserve_recovery_and_decision_separation(self):
        self.assertTrue("停止与恢复" in self.brief)
        self.assertIn("任务状态", self.brief)
        self.assertIn("决策标准", self.brief)

        self.assertIn("报告元数据", self.report)
        self.assertIn("本报告保存 Agent 建议", self.report)
        self.assertIn("另行填写 `user-decision.md`", self.report)

        self.assertIn("本文件不得从 Agent 建议自动预填", self.user_decision)
        self.assertIn("与 Agent 建议的关系", self.user_decision)
        self.assertIn("disagrees_with_agent", self.user_decision)

    def test_gitignore_guards_private_runtime_artifacts(self):
        lines = [line.strip() for line in self.gitignore.splitlines()]
        self.assertIn("data/", lines)
        self.assertIn("artifacts/", lines)

    def test_operating_method_is_routed_from_agent_contract(self):
        for required_ref in (
            "docs/pickscout-methodology-v1.md",
            "docs/pickscout-sop-v1.md",
            "templates/task-run-checklist.md",
        ):
            self.assertIn(required_ref, self.agents)

    def test_methodology_defines_all_decision_stages(self):
        for stage in (
            "A 候选发现",
            "B 候选筛选",
            "C 样品筛选",
            "D 样品验证",
            "E 采购与单位经济",
            "F FBA 与首票物流",
            "G 上线复盘",
        ):
            self.assertIn(stage, self.methodology)

    def test_sop_and_run_checklist_preserve_stage_and_authorization_separation(self):
        for marker in (
            "固定操作步骤",
            "恢复步骤 R",
            "外部动作审批表",
            "状态必须带对象和阶段",
        ):
            self.assertIn(marker, self.sop)

        for marker in (
            "current_stage",
            "decision_question",
            "高价值未知项队列",
            "建议、决定与授权",
            "执行事实",
        ):
            self.assertIn(marker, self.run_checklist)


if __name__ == "__main__":
    unittest.main()
