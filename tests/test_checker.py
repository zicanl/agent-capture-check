import json
from copy import deepcopy
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
    assert "outcome.evidence" in failed


def test_completion_status_is_not_outcome_evidence() -> None:
    run = deepcopy(load("complete_run.json"))
    run["outcome"] = {"status": "completed"}

    report = check_run(run, "baseline")
    outcome = next(result for result in report.results if result.rule_id == "outcome.evidence")

    assert outcome.status.value == "fail"
    assert outcome.evidence == ("outcome.status",)
    assert "completion status" in outcome.message.lower()


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        check_run({}, "future-perfect")


def test_openinference_otlp_is_detected_and_passes_baseline() -> None:
    report = check_run(load("openinference_otlp.json"), "baseline")
    assert report.input_format == "otlp-json"
    assert not report.failed, report.to_dict()


def test_otlp_trace_is_not_enough_when_decision_context_is_omitted() -> None:
    run = deepcopy(load("openinference_otlp.json"))
    root_attributes = run["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
    root_attributes[:] = [
        attribute
        for attribute in root_attributes
        if attribute["key"] not in {"gen_ai.input.messages", "gen_ai.tool.definitions"}
    ]

    report = check_run(run, "baseline")
    failed = {result.rule_id for result in report.results if result.status.value == "fail"}

    assert "context.effective" in failed
    assert "capabilities.available" in failed


def test_pytest_fixture_accepts_mapping(capture_check) -> None:
    capture_check(load("complete_run.json"), profile="baseline")
