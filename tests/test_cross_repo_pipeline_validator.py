from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

import validate_cross_repo_pipeline as validator


@unittest.skipUnless(shutil.which("ruby"), "ruby is required for YAML parsing on this macOS setup")
class CrossRepoPipelineValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.benchmark_root = self.root / "ToM_AI_Research_Team"
        self.orchestration_root = self.root / "autoresearch-macos-tomx"
        self.legacy_root = self.root / "ToM AI Research Team"
        self.incumbent_root = self.benchmark_root / "incumbents"
        self.docs_root = self.orchestration_root / "docs"

        self.incumbent_names = (
            "ToM experiment incumbent",
            "ToM experiment incumbent v3-omx",
            "ToM experiment incumbent v4-postevidence-reengage",
            "ToM experiment incumbent v5-delayedtrust-split-candidate",
        )

        self.benchmark_root.mkdir(parents=True)
        self.orchestration_root.mkdir(parents=True)
        self.legacy_root.mkdir(parents=True)
        self.incumbent_root.mkdir(parents=True)
        self.docs_root.mkdir(parents=True)
        for name in self.incumbent_names:
            (self.incumbent_root / name).mkdir()

        self.policy_path = self.orchestration_root / "cross_repo_pipeline.yaml"
        self.policy_path.write_text(
            f"""
schema_version: "1.0"

cross_repo_pipeline:
  repositories:
    benchmark:
      root: "{self.benchmark_root}"
    orchestration:
      root: "{self.orchestration_root}"
  canonical_path_rules:
    forbid_active_use_of_paths:
      - "{self.legacy_root}"
  handoff_paths:
    benchmark_inputs:
      incumbent_root: "{self.incumbent_root}"
      expected_incumbent_paths:
        - "{self.incumbent_root / self.incumbent_names[0]}"
        - "{self.incumbent_root / self.incumbent_names[1]}"
        - "{self.incumbent_root / self.incumbent_names[2]}"
        - "{self.incumbent_root / self.incumbent_names[3]}"
""".strip(),
            encoding="utf-8",
        )

    def test_load_policy_reads_yaml(self) -> None:
        policy = validator.load_policy(self.policy_path)
        self.assertEqual(str(self.benchmark_root), policy["repositories"]["benchmark"]["root"])

    def test_validate_policy_contract_passes_for_canonical_setup(self) -> None:
        policy = validator.load_policy(self.policy_path)

        results = validator.validate_policy_contract(
            policy,
            working_directory=self.orchestration_root,
        )

        self.assertTrue(results)
        self.assertTrue(all(result.ok for result in results), msg=results)

    def test_report_must_cite_benchmark_root(self) -> None:
        policy = validator.load_policy(self.policy_path)
        report_path = self.docs_root / "report.md"
        report_path.write_text("No benchmark path here.\n", encoding="utf-8")

        results = validator.validate_policy_contract(
            policy,
            working_directory=self.orchestration_root,
            report_paths=[report_path],
        )

        failing = [result for result in results if result.name.startswith("report_cites_benchmark_source:")]
        self.assertEqual(len(failing), 1)
        self.assertFalse(failing[0].ok)

    def test_promotion_target_must_live_under_incumbents(self) -> None:
        policy = validator.load_policy(self.policy_path)
        invalid_target = self.benchmark_root / "logs" / "candidate"

        results = validator.validate_policy_contract(
            policy,
            working_directory=self.orchestration_root,
            promotion_targets=[invalid_target],
        )

        failing = [result for result in results if result.name.startswith("promotion_target_within_incumbents:")]
        self.assertEqual(len(failing), 1)
        self.assertFalse(failing[0].ok)

    def test_legacy_working_directory_is_rejected(self) -> None:
        policy = validator.load_policy(self.policy_path)

        results = validator.validate_policy_contract(
            policy,
            working_directory=self.legacy_root,
        )

        working_dir_results = [result for result in results if result.name == "working_directory_allowed"]
        self.assertEqual(len(working_dir_results), 1)
        self.assertFalse(working_dir_results[0].ok)


if __name__ == "__main__":
    unittest.main()
