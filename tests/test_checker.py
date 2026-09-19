import json
from pathlib import Path

import pytest

from agent_capture_check import check_run


FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_complete_run_passes_all_profiles() -> None:
    run = load("complete_run.json")
    for profile in ("baseline", "learning-ready", "elicited"):
        report = check_run(run, profile)
        assert not report.failed, report.to_dict()


def test_missing_blindspots_fail_baseline() -> None:
    report = check_run(load("missing_blindspots.json"), "baseline")
    failed = {result.rule_id for result in report.results if result.status.value == "fail"}
    assert "context.effective" in failed
    assert "configuration.versions" in failed
    assert "capabilities.available" in failed
    assert "actions.results_linked" in failed


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        check_run({}, "future-perfect")


def test_pytest_fixture_accepts_mapping(capture_check) -> None:
    capture_check(load("complete_run.json"), profile="baseline")
