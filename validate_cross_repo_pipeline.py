#!/usr/bin/env python3
"""Validate the cross-repo contract between the benchmark and orchestration repos."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_POLICY_PATH = REPO_ROOT / "policies" / "cross_repo_pipeline.yaml"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _load_yaml_with_ruby(path: Path) -> dict[str, Any]:
    ruby = shutil.which("ruby")
    if ruby is None:
        raise RuntimeError("ruby is required to parse YAML on this macOS setup.")

    ruby_script = (
        "require 'yaml'; "
        "require 'json'; "
        "data = YAML.load_file(ARGV[0]); "
        "puts JSON.generate(data)"
    )
    result = subprocess.run(
        [ruby, "-e", ruby_script, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ruby YAML parse failed")

    loaded = json.loads(result.stdout)
    if not isinstance(loaded, dict):
        raise RuntimeError("cross_repo_pipeline.yaml must parse to a mapping.")
    return loaded


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a mapping.")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be a list.")
    return value


def _resolve(path_like: str | os.PathLike[str]) -> Path:
    return Path(path_like).expanduser().resolve(strict=False)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _path_from_rule(entries: Iterable[str]) -> str:
    return ", ".join(entries)


def load_policy(path: Path) -> dict[str, Any]:
    root = _load_yaml_with_ruby(path)
    pipeline = _require_mapping(root.get("cross_repo_pipeline"), "cross_repo_pipeline")
    return pipeline


def validate_policy_contract(
    policy: dict[str, Any],
    *,
    working_directory: Path,
    report_paths: Iterable[Path] = (),
    promotion_targets: Iterable[Path] = (),
) -> list[CheckResult]:
    repositories = _require_mapping(policy.get("repositories"), "cross_repo_pipeline.repositories")
    benchmark = _require_mapping(repositories.get("benchmark"), "repositories.benchmark")
    orchestration = _require_mapping(repositories.get("orchestration"), "repositories.orchestration")
    canonical_rules = _require_mapping(
        policy.get("canonical_path_rules"), "cross_repo_pipeline.canonical_path_rules"
    )
    handoff_paths = _require_mapping(policy.get("handoff_paths"), "cross_repo_pipeline.handoff_paths")
    benchmark_inputs = _require_mapping(handoff_paths.get("benchmark_inputs"), "handoff_paths.benchmark_inputs")

    benchmark_root = _resolve(str(benchmark["root"]))
    orchestration_root = _resolve(str(orchestration["root"]))
    incumbent_root = _resolve(str(benchmark_inputs["incumbent_root"]))
    expected_incumbents = [_resolve(str(item)) for item in _require_list(benchmark_inputs.get("expected_incumbent_paths", []), "benchmark_inputs.expected_incumbent_paths")]
    forbidden_paths = [_resolve(str(item)) for item in _require_list(canonical_rules.get("forbid_active_use_of_paths", []), "canonical_path_rules.forbid_active_use_of_paths")]

    results: list[CheckResult] = []
    results.append(
        CheckResult(
            "benchmark_root_exists",
            benchmark_root.exists(),
            f"benchmark_root={benchmark_root}",
        )
    )
    results.append(
        CheckResult(
            "orchestration_root_exists",
            orchestration_root.exists(),
            f"orchestration_root={orchestration_root}",
        )
    )
    results.append(
        CheckResult(
            "incumbent_root_exists",
            incumbent_root.exists(),
            f"incumbent_root={incumbent_root}",
        )
    )

    cwd = working_directory.resolve(strict=False)
    in_canonical_repo = _is_within(cwd, benchmark_root) or _is_within(cwd, orchestration_root)
    in_forbidden_root = any(_is_within(cwd, forbidden_root) for forbidden_root in forbidden_paths)
    results.append(
        CheckResult(
            "working_directory_allowed",
            in_canonical_repo and not in_forbidden_root,
            f"working_directory={cwd}",
        )
    )

    for expected_path in expected_incumbents:
        results.append(
            CheckResult(
                f"expected_incumbent_exists:{expected_path.name}",
                expected_path.exists() and _is_within(expected_path, incumbent_root),
                f"path={expected_path}",
            )
        )

    for report_path in report_paths:
        resolved = report_path.resolve(strict=False)
        exists = resolved.exists()
        cites_benchmark = False
        inside_orchestration = _is_within(resolved, orchestration_root)
        if exists:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            cites_benchmark = str(benchmark_root) in content
        results.append(
            CheckResult(
                f"report_cites_benchmark_source:{resolved.name}",
                exists and inside_orchestration and cites_benchmark,
                f"report={resolved}",
            )
        )

    for promotion_target in promotion_targets:
        resolved = promotion_target.resolve(strict=False)
        results.append(
            CheckResult(
                f"promotion_target_within_incumbents:{resolved.name}",
                _is_within(resolved, incumbent_root),
                f"promotion_target={resolved}",
            )
        )

    return results


def _print_results(results: Iterable[CheckResult]) -> None:
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status} {result.name}: {result.detail}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the cross-repo pipeline contract, including canonical roots, "
            "expected incumbent paths, report citations, and promotion targets."
        )
    )
    parser.add_argument(
        "--policy",
        default=str(DEFAULT_POLICY_PATH),
        help="Path to cross_repo_pipeline.yaml (default: %(default)s)",
    )
    parser.add_argument(
        "--working-directory",
        default=os.getcwd(),
        help="Working directory to validate against canonical roots (default: current working directory)",
    )
    parser.add_argument(
        "--report",
        action="append",
        default=[],
        help="Report file that must cite benchmark-side source paths. Repeatable.",
    )
    parser.add_argument(
        "--promotion-target",
        action="append",
        default=[],
        help="Promotion target path that must live under the benchmark incumbents root. Repeatable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    policy_path = _resolve(args.policy)
    if not policy_path.exists():
        print(f"FAIL policy_exists: policy={policy_path}", file=sys.stderr)
        return 1

    try:
        policy = load_policy(policy_path)
        results = validate_policy_contract(
            policy,
            working_directory=_resolve(args.working_directory),
            report_paths=[_resolve(path) for path in args.report],
            promotion_targets=[_resolve(path) for path in args.promotion_target],
        )
    except RuntimeError as exc:
        print(f"FAIL policy_parse: {exc}", file=sys.stderr)
        return 1

    _print_results(results)
    failures = [result for result in results if not result.ok]
    if failures:
        print(f"SUMMARY {len(failures)} check(s) failed.")
        return 1

    print(f"SUMMARY all {len(results)} check(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
