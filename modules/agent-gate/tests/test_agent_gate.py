import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "agent-gate" / "src"))

import agent_gate


class AgentGateTests(unittest.TestCase):
    def test_parse_frontmatter(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write("---\ndate: 2026-11-06\ndocs_impact: true\n---\n\n# body\n")
            path = Path(handle.name)
        data, body = agent_gate.parse_frontmatter(path)
        self.assertEqual(str(data["date"]), "2026-11-06")
        self.assertTrue(data["docs_impact"])
        self.assertIn("# body", body)
        path.unlink()

    def test_validate_manifests(self):
        errors, warnings = agent_gate.validate_manifests(ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_links(self):
        errors = agent_gate.check_links(ROOT)
        self.assertEqual(errors, [])

    def test_docs_history_leak(self):
        errors = agent_gate.docs_history_leak(ROOT)
        self.assertEqual(errors, [])

    def test_empty_range(self):
        errors, warnings = agent_gate.check(ROOT, base="HEAD")
        self.assertEqual(errors, [])

    def test_existing_commits(self):
        try:
            subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "origin/main"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            self.skipTest("origin/main 不可用")
        errors, warnings = agent_gate.check(ROOT, base="origin/main")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()