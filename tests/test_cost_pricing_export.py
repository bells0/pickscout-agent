import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from scripts.export_cost_pricing import export_cost_pricing, rewrite_markdown

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {
    "SKILL.md", "agents/openai.yaml", "references/cost-pricing-methodology-v1.0.md",
    "references/decisions/0018-cost-pricing-capability.md", "scripts/cost_pricing.py",
    "scripts/unit_economics.py", "assets/cost-pricing-input.json", "LICENSE", "README.md", "SOURCE.json",
}


class CostPricingExportTests(unittest.TestCase):
    def test_real_zip_is_portable_and_has_only_public_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = export_cost_pricing(root / "delivery", "test-source-ref", source_root=ROOT)
            with ZipFile(result["zip"]) as archive:
                self.assertEqual(set(archive.namelist()), {"amazon-cost-pricing/" + path for path in EXPECTED_FILES})
                archive.extractall(root / "clean-unpack")
            package = root / "clean-unpack" / "amazon-cost-pricing"
            self.assertEqual((package / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
            source = json.loads((package / "SOURCE.json").read_text())
            self.assertEqual(source["source_ref"], "test-source-ref")
            self.assertEqual(len(source["source_files"]), 8)
            for path in package.rglob("*.md"):
                text = path.read_text()
                self.assertNotIn(str(ROOT), text)
                self.assertNotIn("/Users/", text)
                for target in re.findall(r"!?\[[^\]\n]*\]\(([^\s)]+)\)", text):
                    parsed = urlsplit(target)
                    if parsed.scheme or parsed.netloc or target.startswith("#"):
                        continue
                    resolved = (path.parent / unquote(target.split("#", 1)[0])).resolve()
                    self.assertTrue(resolved.is_relative_to(package.resolve()), target)
                    self.assertTrue(resolved.is_file(), target)
            cwd = root / "unrelated-working-directory"
            cwd.mkdir()
            env = dict(os.environ, PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
            completed = subprocess.run(
                [sys.executable, "-B", str(package / "scripts/cost_pricing.py"), str(package / "assets/cost-pricing-input.json")],
                cwd=cwd, env=env, text=True, capture_output=True, check=True,
            )
            case = json.loads(completed.stdout)["cases"][0]
            self.assertEqual(case["prices"][0]["operating_remainder"], "5.00")
            self.assertEqual(case["target_prices"]["break_even"]["price"], "12.31")
            self.assertEqual(case["target_prices"]["unit_profit"]["price"], "16.93")
            self.assertEqual(case["target_prices"]["margin"]["price"], "17.78")
            self.assertIsNone(case["prices"][0]["after_income_tax_subtotal"])

    def test_existing_output_is_not_overwritten_or_added_to_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "amazon-cost-pricing"
            package.mkdir()
            private = package / "my-private-input.json"
            private.write_text('{"private": true}')
            with self.assertRaises(FileExistsError):
                export_cost_pricing(root, "test-source-ref", source_root=ROOT)
            self.assertEqual(private.read_text(), '{"private": true}')
            self.assertFalse((root / "amazon-cost-pricing.zip").exists())

    def test_local_link_cannot_pull_private_research_into_package(self):
        with self.assertRaisesRegex(ValueError, "unbundled local link"):
            rewrite_markdown(
                "[private](../../artifacts/customer-research/report.md)",
                "skills/amazon-cost-pricing/SKILL.md", "SKILL.md",
            )


if __name__ == "__main__":
    unittest.main()
