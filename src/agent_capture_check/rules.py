from __future__ import annotations

from collections import Counter
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


def _records(data: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _record_ids(data: Mapping[str, Any], key: str) -> set[str]:
    return {
        str(item["id"])
        for item in _records(data, key)
        if item.get("id") not in (None, "")
    }


def _graph_identity_check(data: Mapping[str, Any]) -> CheckResult:
    collections = ("actors", "observations", "capability_sets", "decisions", "handoffs")
    issues: list[str] = []
    for key in collections:
        records = _records(data, key)
        ids = [str(item.get("id") or "") for item in records]
        missing = [index for index, record_id in enumerate(ids) if not record_id]
        duplicates = sorted(
            record_id
            for record_id, count in Counter(ids).items()
            if record_id and count > 1
        )
        if missing:
            issues.append(f"{key} missing id at indexes {missing}")
        if duplicates:
            issues.append(f"{key} duplicate ids {duplicates}")
    if issues:
        return CheckResult(
            "graph.identities_unique",
            Status.FAIL,
            "Graph identities are incomplete or ambiguous: " + "; ".join(issues) + ".",
            collections,
            "Give every actor, observation, capability set, decision, and handoff a unique stable ID.",
        )
    return CheckResult(
        "graph.identities_unique",
        Status.PASS,
        "Recorded multi-agent graph identities are unique.",
        collections,
    )


def _decision_observation_scope_check(data: Mapping[str, Any]) -> CheckResult:
    decisions = _records(data, "decisions")
    if not decisions:
        return CheckResult(
            "decision.observations_scoped",
            Status.FAIL,
            "No actor-scoped decision records were found.",
            remediation="Record each decision with actor_id and the observation IDs effective for that decision.",
        )

    actor_ids = _record_ids(data, "actors")
    observation_ids = _record_ids(data, "observations")
    invalid: list[int] = []
    for index, decision in enumerate(decisions):
        actor_id = str(decision.get("actor_id") or "")
        refs = decision.get("observation_refs")
        refs = refs if isinstance(refs, list) else []
        normalized_refs = {str(ref) for ref in refs if ref not in (None, "")}
        if (
            not decision.get("id")
            or not actor_id
            or actor_id not in actor_ids
            or not normalized_refs
            or not normalized_refs.issubset(observation_ids)
        ):
            invalid.append(index)

    covered = len(decisions) - len(invalid)
    if invalid:
        return CheckResult(
            "decision.observations_scoped",
            Status.FAIL,
            f"{covered}/{len(decisions)} decisions have valid actor-scoped observations; "
            f"invalid indexes: {invalid}.",
            ("actors", "observations", "decisions"),
            "Give every decision a stable ID, a known actor_id, and observation_refs that resolve to recorded observations.",
        )
    return CheckResult(
        "decision.observations_scoped",
        Status.PASS,
        f"{covered}/{len(decisions)} decisions have valid actor-scoped observations.",
        ("actors", "observations", "decisions"),
    )


def _decision_capability_scope_check(data: Mapping[str, Any]) -> CheckResult:
    decisions = _records(data, "decisions")
    if not decisions:
        return CheckResult(
            "decision.capabilities_scoped",
            Status.FAIL,
            "No actor-scoped decision records were found.",
            remediation="Record each decision and its effective capability-set reference.",
        )

    capability_ids = _record_ids(data, "capability_sets")
    invalid = [
        index
        for index, decision in enumerate(decisions)
        if not decision.get("capability_set_ref")
        or str(decision["capability_set_ref"]) not in capability_ids
    ]
    covered = len(decisions) - len(invalid)
    if invalid:
        return CheckResult(
            "decision.capabilities_scoped",
            Status.FAIL,
            f"{covered}/{len(decisions)} decisions reference a recorded capability set; "
            f"invalid indexes: {invalid}.",
            ("capability_sets", "decisions"),
            "Version effective tool, permission, policy, and budget sets and reference one from every decision.",
        )
    return CheckResult(
        "decision.capabilities_scoped",
        Status.PASS,
        f"{covered}/{len(decisions)} decisions reference a recorded capability set.",
        ("capability_sets", "decisions"),
    )


def _payload_identity(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    for key in ("digest", "ref", "id"):
        candidate = value.get(key)
        if candidate not in (None, ""):
            return str(candidate)
    return ""


def _payload_descriptor_is_valid(
    value: Any,
    observation_ids: set[str],
) -> bool:
    if not isinstance(value, Mapping) or not _payload_identity(value):
        return False
    ref = value.get("ref")
    return ref in (None, "") or str(ref) in observation_ids


def _handoff_receipt_check(data: Mapping[str, Any]) -> CheckResult:
    actor_ids = _record_ids(data, "actors")
    handoffs = _records(data, "handoffs")
    observation_ids = _record_ids(data, "observations")
    if len(actor_ids) < 2:
        return CheckResult(
            "handoff.receipt_linked",
            Status.FAIL,
            "The multi-agent profile requires at least two recorded actors.",
            remediation="Record stable identities for every actor participating in the workflow.",
        )
    if not handoffs:
        return CheckResult(
            "handoff.receipt_linked",
            Status.FAIL,
            "No sender/receiver handoff records were found.",
            remediation="Record each consequential handoff with sender, receiver, sent payload, and received payload.",
        )

    invalid: list[int] = []
    for index, handoff in enumerate(handoffs):
        sender = str(handoff.get("from_actor_id") or "")
        receiver = str(handoff.get("to_actor_id") or "")
        if (
            not handoff.get("id")
            or sender not in actor_ids
            or receiver not in actor_ids
            or not _payload_descriptor_is_valid(handoff.get("sent"), observation_ids)
            or not _payload_descriptor_is_valid(handoff.get("received"), observation_ids)
        ):
            invalid.append(index)

    covered = len(handoffs) - len(invalid)
    if invalid:
        return CheckResult(
            "handoff.receipt_linked",
            Status.FAIL,
            f"{covered}/{len(handoffs)} handoffs preserve linked send/receive evidence; "
            f"invalid indexes: {invalid}.",
            ("actors", "observations", "handoffs"),
            "Record known actors plus sent and received payload identities for every handoff.",
        )
    return CheckResult(
        "handoff.receipt_linked",
        Status.PASS,
        f"{covered}/{len(handoffs)} handoffs preserve linked send/receive evidence.",
        ("actors", "observations", "handoffs"),
    )


def _handoff_transformation_check(data: Mapping[str, Any]) -> CheckResult:
    handoffs = _records(data, "handoffs")
    required = 0
    invalid: list[int] = []
    for index, handoff in enumerate(handoffs):
        sent = _payload_identity(handoff.get("sent"))
        received = _payload_identity(handoff.get("received"))
        if not sent or not received or sent == received:
            continue
        required += 1
        transformation = handoff.get("transformation")
        if not isinstance(transformation, Mapping):
            invalid.append(index)
            continue
        input_refs = transformation.get("input_refs")
        normalized_inputs = (
            {str(ref) for ref in input_refs if ref not in (None, "")}
            if isinstance(input_refs, list)
            else set()
        )
        if (
            not transformation.get("kind")
            or sent not in normalized_inputs
            or str(transformation.get("output_ref") or "") != received
        ):
            invalid.append(index)

    covered = required - len(invalid)
    if invalid:
        return CheckResult(
            "handoff.transformation_declared",
            Status.FAIL,
            f"{covered}/{required} identity-changing handoffs declare their transformation; "
            f"invalid indexes: {invalid}.",
            ("handoffs",),
            "For changed payload identities, record transformation kind, input_refs, and output_ref.",
        )
    return CheckResult(
        "handoff.transformation_declared",
        Status.PASS,
        f"{covered}/{required} identity-changing handoffs declare their transformation.",
        ("handoffs",),
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
    _presence_rule(
        "outcome.evidence",
        ("outcome.evidence", "outcome.status", "feedback", "evaluation.result"),
        "The run outcome includes evidence.",
        "No observed outcome or feedback evidence was found.",
        "Record observed results separately from success labels inferred later.",
    ),
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

MULTI_AGENT_RULES = (
    Rule("graph.identities_unique", _graph_identity_check),
    Rule("decision.observations_scoped", _decision_observation_scope_check),
    Rule("decision.capabilities_scoped", _decision_capability_scope_check),
    Rule("handoff.receipt_linked", _handoff_receipt_check),
    Rule("handoff.transformation_declared", _handoff_transformation_check),
)


PROFILES: dict[str, tuple[Rule, ...]] = {
    "baseline": BASELINE_RULES,
    "learning-ready": BASELINE_RULES + LEARNING_RULES,
    "elicited": BASELINE_RULES + LEARNING_RULES + ELICITED_RULES,
    "multi-agent": BASELINE_RULES + MULTI_AGENT_RULES,
}
