import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_ROOT = REPO_ROOT / "adapters" / "codex" / "pickscout-agent"

MIRRORED_FILES = {
    REPO_ROOT / "docs" / "pickscout-methodology-v1.md": (
        ADAPTER_ROOT / "references" / "pickscout-methodology-v1.md"
    ),
    REPO_ROOT / "docs" / "pickscout-sop-v1.md": (
        ADAPTER_ROOT / "references" / "pickscout-sop-v1.md"
    ),
    REPO_ROOT / "docs" / "research-protocol-v0.md": (
        ADAPTER_ROOT / "references" / "research-protocol-v0.md"
    ),
    REPO_ROOT / "scripts" / "unit_economics.py": (
        ADAPTER_ROOT / "scripts" / "unit_economics.py"
    ),
    REPO_ROOT / "scripts" / "hard_gates.py": (
        ADAPTER_ROOT / "scripts" / "hard_gates.py"
    ),
}

for template_path in (REPO_ROOT / "templates").iterdir():
    if template_path.is_file():
        MIRRORED_FILES[template_path] = (
            ADAPTER_ROOT / "assets" / "templates" / template_path.name
        )


class DistributionPackageTests(unittest.TestCase):
    def test_required_adapter_files_exist(self):
        for relative_path in (
            "SKILL.md",
            "agents/openai.yaml",
            "references/pickscout-methodology-v1.md",
            "references/pickscout-sop-v1.md",
            "references/research-protocol-v0.md",
            "scripts/unit_economics.py",
            "scripts/hard_gates.py",
            "assets/templates/task-run-checklist.md",
            "assets/templates/evidence-record.schema.json",
        ):
            self.assertTrue((ADAPTER_ROOT / relative_path).is_file(), relative_path)

    def test_adapter_has_complete_frontmatter_and_no_scaffold_todos(self):
        skill_text = (ADAPTER_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: pickscout-agent\n"))
        self.assertRegex(skill_text, r"\ndescription: .+\n---\n")
        self.assertNotIn("TODO", skill_text)

    def test_adapter_routes_all_bundled_resources(self):
        skill_text = (ADAPTER_ROOT / "SKILL.md").read_text(encoding="utf-8")
        referenced_paths = set(
            re.findall(
                r"`((?:references|assets|scripts)/[^`]+)`",
                skill_text,
            )
        )
        for referenced_path in referenced_paths:
            if "<" in referenced_path:
                continue
            self.assertTrue(
                (ADAPTER_ROOT / referenced_path).exists(),
                referenced_path,
            )

    def test_openai_metadata_invokes_pickscout_agent(self):
        metadata = (ADAPTER_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('display_name: "PickScout Agent"', metadata)
        self.assertIn("$pickscout-agent", metadata)

    def test_release_package_mirrors_source_material(self):
        for source_path, packaged_path in MIRRORED_FILES.items():
            self.assertEqual(
                source_path.read_bytes(),
                packaged_path.read_bytes(),
                f"Skill package is stale: {packaged_path.relative_to(REPO_ROOT)}",
            )


if __name__ == "__main__":
    unittest.main()
