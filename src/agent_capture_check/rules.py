from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .evidence import first_present, flatten_attribute_maps, steps
from .model import CheckResult, Status


RuleCheck = Callable[[Mapping[str, Any]], CheckResult]


@dataclass(frozen=True)
class Rule:
    id: str
    check: RuleCheck


def _presence_rule(
    rule_id: str,
    paths: tuple[str, ...],
    success: str,
    failure: str,
    remediation: str,
    *,
    missing_status: Status = Status.FAIL,
) -> Rule:
    def check(data: Mapping[str, Any]) -> CheckResult:
        evidence = first_present(data, paths)
        if evidence:
            return CheckResult(rule_id, Status.PASS, success, (evidence[0],))

        attributes = flatten_attribute_maps(data)
        evidence = first_present(attributes, paths)
        if evidence:
            return CheckResult(
                rule_id,
                Status.PASS,
                success,
                (f"attributes.{evidence[0]}",),
            )
        return CheckResult(rule_id, missing_status, failure, remediation=remediation)

    return Rule(rule_id, check)


def _version_check(data: Mapping[str, Any]) -> CheckResult:
    attributes = flatten_attribute_maps(data)
    sources = (data, attributes)
    groups = {
        "agent": ("configuration.agent_version", "agent.version", "gen_ai.agent.version"),
        "model": ("configuration.model", "agent.model_name", "gen_ai.request.model", "llm.model_name"),
        "prompt": ("configuration.prompt_version", "gen_ai.prompt.version", "prompt.version"),
    }
    found: list[str] = []
    missing: list[str] = []
    for name, paths in groups.items():
        evidence = next((first_present(source, paths) for source in sources if first_present(source, paths)), None)
        if evidence:
            found.append(f"{name}:{evidence[0]}")
        else:
            missing.append(name)
    if not missing:
        return CheckResult(
            "configuration.versions",
            Status.PASS,
            "Agent, model, and prompt versions are preserved.",
            tuple(found),
        )
    return CheckResult(
        "configuration.versions",
        Status.FAIL,
        f"Missing version evidence for: {', '.join(missing)}.",
        tuple(found),
        "Record immutable agent/model identifiers and the rendered prompt or prompt version used for the run.",
    )


def _action_result_link_check(data: Mapping[str, Any]) -> CheckResult:
    all_steps = steps(data)
    call_ids: set[str] = set()
    result_ids: set[str] = set()
    for step in all_steps:
        action = step.get("action")
        if isinstance(action, Mapping) and action.get("id"):
            call_ids.add(str(action["id"]))
        for call in step.get("tool_calls", []) if isinstance(step.get("tool_calls"), list) else []:
            if isinstance(call, Mapping):
                call_id = call.get("id") or call.get("tool_call_id")
                if call_id:
                    call_ids.add(str(call_id))
        observation = step.get("observation")
        observations = observation if isinstance(observation, list) else [observation]
        for item in observations:
            if isinstance(item, Mapping):
                source_id = item.get("source_action_id") or item.get("source_call_id")
                if source_id:
                    result_ids.add(str(source_id))

    if not call_ids:
        return CheckResult(
            "actions.results_linked",
            Status.UNKNOWN,
            "No structured actions were found; linkage cannot be assessed.",
            remediation="Expose tool/action identifiers and their corresponding observation identifiers.",
        )
    unlinked = sorted(call_ids - result_ids)
    if unlinked:
        return CheckResult(
            "actions.results_linked",
            Status.FAIL,
            f"{len(unlinked)} action(s) have no linked observation: {', '.join(unlinked)}.",
            remediation="Give every action a stable ID and copy it to the resulting observation.",
        )
    return CheckResult(
        "actions.results_linked",
        Status.PASS,
        "Actions can be linked to their observations.",
        tuple(f"action:{call_id}" for call_id in sorted(call_ids)),
    )


def _outcome_evidence_check(data: Mapping[str, Any]) -> CheckResult:
    attributes = flatten_attribute_maps(data)
    paths = ("outcome.evidence", "feedback", "evaluation.result")
    for prefix, source in (("", data), ("attributes.", attributes)):
        evidence = first_present(source, paths)
        if evidence:
            return CheckResult(
                "outcome.evidence",
                Status.PASS,
                "The run outcome includes evidence.",
                (f"{prefix}{evidence[0]}",),
            )

    status = first_present(data, ("outcome.status",))
    if status:
        return CheckResult(
            "outcome.evidence",
            Status.FAIL,
            "A completion status is preserved, but no observed outcome or feedback evidence was found.",
            (status[0],),
            "Record observed results separately from completion or success labels.",
        )
    return CheckResult(
        "outcome.evidence",
        Status.FAIL,
        "No observed outcome or feedback evidence was found.",
        remediation="Record observed results separately from success labels inferred later.",
    )


def _missingness_check(data: Mapping[str, Any]) -> CheckResult:
    declared = data.get("missingness")
    if not isinstance(declared, list) or not declared:
        return CheckResult(
            "missingness.declared",
            Status.WARN,
            "No missingness manifest is present; absent data is ambiguous.",
            remediation="List intentionally absent fields with reasons such as unavailable, redacted, unsampled, or not_applicable.",
        )
    invalid = [
        index
        for index, item in enumerate(declared)
        if not isinstance(item, Mapping) or not item.get("field") or not item.get("reason")
    ]
    if invalid:
        return CheckResult(
            "missingness.declared",
            Status.FAIL,
            f"Missingness entries lack field or reason at indexes: {invalid}.",
            remediation="Every missingness entry must name the field and why it was not captured.",
        )
    return CheckResult(
        "missingness.declared",
        Status.PASS,
        "Missing or redacted data has an explicit reason.",
        ("missingness",),
    )


def _self_report_check(data: Mapping[str, Any]) -> CheckResult:
    reports: list[Mapping[str, Any]] = []
    for step in steps(data):
        value = step.get("self_report")
        if isinstance(value, Mapping):
            reports.append(value)
    if not reports:
        return CheckResult(
            "self_report.labeled",
            Status.WARN,
            "No elicited agent self-report is present. This is optional and may be appropriate.",
            remediation="Only add a self-report probe when its expected value justifies cost and observer effects.",
        )
    unlabeled = [i for i, report in enumerate(reports) if report.get("evidence_class") != "agent_self_report"]
    if unlabeled:
        return CheckResult(
            "self_report.labeled",
            Status.FAIL,
            "Some elicited reports are not labeled as agent_self_report.",
            remediation="Never store model-generated explanations as runtime facts or ground-truth reasoning.",
        )
    return CheckResult(
        "self_report.labeled",
        Status.PASS,
        "Elicited reports are separated from runtime facts.",
        tuple(f"steps[{index}].self_report" for index in range(len(reports))),
    )


BASELINE_RULES = (
    _presence_rule(
        "run.identity",
        ("run.id", "trace_id", "session.id", "gen_ai.conversation.id"),
        "Run identity is preserved.",
        "No stable run or trace identity was found.",
        "Record a stable run/trace identifier and propagate it across agent boundaries.",
    ),
    _presence_rule(
        "goal.explicit",
        ("goal.requested", "goal", "input", "input.value"),
        "An explicit run goal is preserved.",
        "No explicit run goal was found.",
        "Capture the requested goal separately from later summaries or inferred intent.",
    ),
    _presence_rule(
        "context.effective",
        ("context.effective", "llm.input_messages", "gen_ai.input.messages", "input.messages"),
        "Effective model context is preserved.",
        "The context actually supplied to the model cannot be identified.",
        "Capture the rendered model input or content-addressed references at each decision point.",
    ),
    Rule("configuration.versions", _version_check),
    _presence_rule(
        "capabilities.available",
        ("configuration.tools", "agent.tool_definitions", "gen_ai.tool.definitions", "llm.tools"),
        "Available tools or capabilities are preserved.",
        "Only chosen actions may be visible; the available capability set is missing.",
        "Capture the advertised tool definitions, permissions, or capability-set version at decision time.",
    ),
    Rule("actions.results_linked", _action_result_link_check),
    Rule("outcome.evidence", _outcome_evidence_check),
    Rule("missingness.declared", _missingness_check),
)


LEARNING_RULES = (
    _presence_rule(
        "changes.state_delta",
        ("changes", "state_delta", "outcome.state_delta"),
        "A state change or state-delta record is preserved.",
        "Tool outputs are present, but external state change is not preserved.",
        "Record a bounded before/after reference or verified state delta for mutating actions.",
    ),
    _presence_rule(
        "artifacts.versions",
        ("artifacts", "artifact_versions", "context.artifacts"),
        "Artifacts carry identity or version evidence.",
        "Referenced artifacts cannot be tied to stable versions.",
        "Record content hashes, revisions, snapshot IDs, or immutable references.",
    ),
    _presence_rule(
        "feedback.linked",
        ("outcome.feedback", "feedback", "evaluations"),
        "Feedback is preserved and can be associated with the run.",
        "No immediate or delayed feedback is linked to the run.",
        "Preserve feedback with run/step IDs, source, timestamp, and derivation method.",
        missing_status=Status.WARN,
    ),
)


ELICITED_RULES = (Rule("self_report.labeled", _self_report_check),)


PROFILES: dict[str, tuple[Rule, ...]] = {
    "baseline": BASELINE_RULES,
    "learning-ready": BASELINE_RULES + LEARNING_RULES,
    "elicited": BASELINE_RULES + LEARNING_RULES + ELICITED_RULES,
}
