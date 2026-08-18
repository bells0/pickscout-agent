import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "pickscout-research"

MIRRORED_FILES = {
    REPO_ROOT / "docs" / "pickscout-methodology-v1.md": (
        SKILL_ROOT / "references" / "pickscout-methodology-v1.md"
    ),
    REPO_ROOT / "docs" / "pickscout-sop-v1.md": (
        SKILL_ROOT / "references" / "pickscout-sop-v1.md"
    ),
    REPO_ROOT / "docs" / "research-protocol-v0.md": (
        SKILL_ROOT / "references" / "research-protocol-v0.md"
    ),
    REPO_ROOT / "scripts" / "unit_economics.py": (
        SKILL_ROOT / "scripts" / "unit_economics.py"
    ),
    REPO_ROOT / "scripts" / "hard_gates.py": (
        SKILL_ROOT / "scripts" / "hard_gates.py"
    ),
}

for template_path in (REPO_ROOT / "templates").iterdir():
    if template_path.is_file():
        MIRRORED_FILES[template_path] = (
            SKILL_ROOT / "assets" / "templates" / template_path.name
        )


class SkillPackageTests(unittest.TestCase):
    def test_required_skill_files_exist(self):
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
            self.assertTrue((SKILL_ROOT / relative_path).is_file(), relative_path)

    def test_skill_has_complete_frontmatter_and_no_scaffold_todos(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: pickscout-research\n"))
        self.assertRegex(skill_text, r"\ndescription: .+\n---\n")
        self.assertNotIn("TODO", skill_text)

    def test_skill_routes_all_bundled_resources(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
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
                (SKILL_ROOT / referenced_path).exists(),
                referenced_path,
            )

    def test_openai_metadata_invokes_the_named_skill(self):
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('display_name: "PickScout Research"', metadata)
        self.assertIn("$pickscout-research", metadata)

    def test_release_package_mirrors_source_material(self):
        for source_path, packaged_path in MIRRORED_FILES.items():
            self.assertEqual(
                source_path.read_bytes(),
                packaged_path.read_bytes(),
                f"Skill package is stale: {packaged_path.relative_to(REPO_ROOT)}",
            )


if __name__ == "__main__":
    unittest.main()
