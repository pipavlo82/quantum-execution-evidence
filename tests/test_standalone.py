"""Standalone repository invariants."""
import ast
import json
from pathlib import Path
import unittest

from qev import adapters, source_inventory as pins, sources

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = {"composition", "crystal_receipt", "receiptos", "relational_security_invariants", "rsi"}
FORBIDDEN_TEXT = ("C:" + "/Users/", "D:" + "/PAVLO", "\\" + "Users" + "\\msi", "Codex" + " Runs")

class StandaloneTests(unittest.TestCase):
    def test_qev_has_no_old_runtime_imports(self):
        for path in (ROOT/"qev").glob("*.py"):
            tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names={n.name.split(".")[0] for n in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names={node.module.split(".")[0]}
                else:
                    continue
                self.assertTrue(names.isdisjoint(FORBIDDEN_IMPORTS), (path, names))

    def test_tracked_candidate_text_has_no_machine_paths(self):
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in {".py",".md",".json",".mjs",".yml",".yaml",".toml",".txt",".gitignore",".gitattributes"} and path.name not in {".gitignore",".gitattributes"}:
                continue
            text=path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_TEXT:
                self.assertNotIn(marker, text, (path, marker))

    def test_vendor_inventory_is_exact_and_available(self):
        rows=adapters.verify_sources()
        self.assertEqual(rows, [dict(row) for row in pins.VENDOR_FILES])

    def test_source_lock_is_complete(self):
        result=sources.validate()
        self.assertTrue(sources.successful(result), result)
        self.assertEqual(result["local_files"], len(pins.LOCAL_FILES))
        self.assertEqual(result["vendor_files"], len(pins.ALL_VENDOR_FILES))

    def test_reference_pins_are_reference_only_and_portable(self):
        data=json.loads((ROOT/"docs/reference-pins.json").read_bytes())
        self.assertEqual(data["status"], "SOURCE_PINNED_REFERENCE")
        raw=(ROOT/"docs/reference-pins.json").read_text(encoding="utf-8")
        self.assertNotIn("local_repository", raw)
        for row in data["records"]:
            self.assertRegex(row["commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")

if __name__=="__main__":
    unittest.main()
