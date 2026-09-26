import json
from copy import deepcopy
from pathlib import Path

import pytest

from agent_capture_check import check_run
from agent_capture_check.cli import _render_text


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


def test_explicit_not_applicable_is_reported_for_allowed_baseline_rules() -> None:
    run = deepcopy(load("complete_run.json"))
    del run["configuration"]["tools"]
    run["steps"] = []
    run["missingness"].extend(
        [
            {"field": "capabilities.available", "reason": "not_applicable"},
            {"field": "actions.results_linked", "reason": "not_applicable"},
        ]
    )

    report = check_run(run, "baseline")
    results = {result.rule_id: result for result in report.results}

    assert not report.failed
    assert results["capabilities.available"].status.value == "not_applicable"
    assert results["actions.results_linked"].status.value == "not_applicable"
    assert report.counts()["not_applicable"] == 2
    rendered = _render_text(report)
    assert "N/A      capabilities.available" in rendered
    assert "2 not applicable" in rendered


def test_learning_profile_allows_explicitly_inapplicable_optional_classes() -> None:
    run = deepcopy(load("complete_run.json"))
    del run["changes"]
    del run["artifacts"]
    del run["context"]["artifacts"]
    del run["outcome"]["feedback"]
    run["missingness"].extend(
        [
            {"field": "changes.state_delta", "reason": "not_applicable"},
            {"field": "artifacts.versions", "reason": "not_applicable"},
            {"field": "feedback.linked", "reason": "not_applicable"},
        ]
    )

    report = check_run(run, "learning-ready")
    results = {result.rule_id: result for result in report.results}

    assert not report.failed
    assert results["changes.state_delta"].status.value == "not_applicable"
    assert results["artifacts.versions"].status.value == "not_applicable"
    assert results["feedback.linked"].status.value == "not_applicable"


def test_not_applicable_cannot_bypass_a_required_rule() -> None:
    run = deepcopy(load("complete_run.json"))
    del run["context"]["effective"]
    run["missingness"].append(
        {"field": "context.effective", "reason": "not_applicable"}
    )

    report = check_run(run, "baseline")
    context = next(result for result in report.results if result.rule_id == "context.effective")

    assert context.status.value == "fail"


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        check_run({}, "future-perfect")


def test_openinference_otlp_is_detected_and_passes_baseline() -> None:
    report = check_run(load("openinference_otlp.json"), "baseline")
    assert report.input_format == "otlp-json"
    assert not report.failed, report.to_dict()


def test_span_document_does_not_combine_evidence_across_traces() -> None:
    document = {
        "spans": [
            {
                "traceId": "trace-a",
                "spanId": "a-root",
                "attributes": {
                    "input.value": "Goal from trace A",
                    "gen_ai.agent.version": "agent-a@1",
                    "output.value": "Output from trace A",
                },
            },
            {
                "traceId": "trace-b",
                "spanId": "b-root",
                "attributes": {
                    "gen_ai.request.model": "model-b",
                    "gen_ai.prompt.version": "prompt-b@1",
                    "gen_ai.input.messages": [{"role": "user", "content": "Context from trace B"}],
                    "gen_ai.tool.definitions": [{"name": "tool-b"}],
                },
            },
        ]
    }

    with pytest.raises(ValueError, match="found 2 trace IDs"):
        check_run(document, "baseline")


def test_otlp_document_with_multiple_traces_is_rejected() -> None:
    document = deepcopy(load("openinference_otlp.json"))
    spans = document["resourceSpans"][0]["scopeSpans"][0]["spans"]
    second_root = deepcopy(spans[0])
    second_root["traceId"] = "fedcba9876543210fedcba9876543210"
    second_root["spanId"] = "3333333333333333"
    spans.append(second_root)

    with pytest.raises(ValueError, match="found 2 trace IDs"):
        check_run(document, "baseline")


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
