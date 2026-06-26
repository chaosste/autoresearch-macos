from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / ".codex" / "skills" / "autoresearch-lab" / "scripts" / "autoresearch_ops.py"


class AutoresearchOpsTests(unittest.TestCase):
    def run_helper(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HELPER), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_check_setup_repo_only_succeeds_without_cache(self) -> None:
        result = self.run_helper("check-setup", "--json", "--repo-only")
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["repo_ready"])
        self.assertTrue(payload["repo_only"])
        self.assertIn("ready_for_training", payload)


if __name__ == "__main__":
    unittest.main()
