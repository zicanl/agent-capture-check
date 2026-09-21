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


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        check_run({}, "future-perfect")


def test_openinference_otlp_is_detected_and_passes_baseline() -> None:
    report = check_run(load("openinference_otlp.json"), "baseline")
    assert report.input_format == "otlp-json"
    assert not report.failed, report.to_dict()


def test_complete_multi_agent_run_passes_continuity_profile() -> None:
    report = check_run(load("multi_agent_complete.json"), "multi-agent")
    results = {result.rule_id: result for result in report.results}

    assert not report.failed, report.to_dict()
    assert results["decision.observations_scoped"].status.value == "pass"
    assert results["decision.capabilities_scoped"].status.value == "pass"
    assert results["handoff.receipt_linked"].status.value == "pass"
    assert results["handoff.transformation_declared"].status.value == "pass"


def test_baseline_profile_does_not_detect_a_broken_handoff() -> None:
    run = deepcopy(load("multi_agent_complete.json"))
    del run["handoffs"][1]["received"]

    report = check_run(run, "baseline")

    assert not report.failed, report.to_dict()


def test_multi_agent_profile_detects_a_missing_receiver_record() -> None:
    run = deepcopy(load("multi_agent_complete.json"))
    del run["handoffs"][1]["received"]

    report = check_run(run, "multi-agent")
    receipt = next(result for result in report.results if result.rule_id == "handoff.receipt_linked")

    assert receipt.status.value == "fail"
    assert "1/2 handoffs" in receipt.message


def test_multi_agent_profile_requires_changed_payload_transformations() -> None:
    run = deepcopy(load("multi_agent_complete.json"))
    del run["handoffs"][1]["transformation"]

    report = check_run(run, "multi-agent")
    transformation = next(
        result for result in report.results if result.rule_id == "handoff.transformation_declared"
    )

    assert transformation.status.value == "fail"
    assert "0/1 identity-changing handoffs" in transformation.message


def test_multi_agent_profile_requires_decision_scoped_observations() -> None:
    run = deepcopy(load("multi_agent_complete.json"))
    run["decisions"][2]["observation_refs"] = ["payload:not-recorded"]

    report = check_run(run, "multi-agent")
    observations = next(
        result for result in report.results if result.rule_id == "decision.observations_scoped"
    )

    assert observations.status.value == "fail"
    assert "2/3 decisions" in observations.message


def test_multi_agent_profile_requires_decision_scoped_capabilities() -> None:
    run = deepcopy(load("multi_agent_complete.json"))
    run["decisions"][1]["capability_set_ref"] = "capabilities:not-recorded"

    report = check_run(run, "multi-agent")
    capabilities = next(
        result for result in report.results if result.rule_id == "decision.capabilities_scoped"
    )

    assert capabilities.status.value == "fail"
    assert "2/3 decisions" in capabilities.message


def test_multi_agent_profile_rejects_ambiguous_graph_identities() -> None:
    run = deepcopy(load("multi_agent_complete.json"))
    run["observations"][1]["id"] = "observation:input"

    report = check_run(run, "multi-agent")
    identities = next(
        result for result in report.results if result.rule_id == "graph.identities_unique"
    )

    assert identities.status.value == "fail"
    assert "duplicate ids" in identities.message


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
