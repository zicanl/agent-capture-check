from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .evidence import MISSING, get_path


@dataclass(frozen=True)
class AdaptedRun:
    data: Mapping[str, Any]
    input_format: str


@dataclass(frozen=True)
class _EvidenceMapTarget:
    path: str
    collect: bool = False
    preserve_source: bool = False


_EVIDENCE_MAP_VERSION = "agent-capture-map.v1"
_EVIDENCE_MAP_TARGETS: dict[str, _EvidenceMapTarget] = {
    "run.identity": _EvidenceMapTarget("run.id"),
    "goal.explicit": _EvidenceMapTarget("goal.requested"),
    "context.effective": _EvidenceMapTarget("context.effective", collect=True),
    "configuration.agent_version": _EvidenceMapTarget("configuration.agent_version"),
    "configuration.model": _EvidenceMapTarget("configuration.model"),
    "configuration.prompt_version": _EvidenceMapTarget("configuration.prompt_version"),
    "capabilities.available": _EvidenceMapTarget("configuration.tools", collect=True),
    "actions.steps": _EvidenceMapTarget("steps", collect=True),
    "outcome.status": _EvidenceMapTarget("outcome.status"),
    "outcome.evidence": _EvidenceMapTarget(
        "outcome.evidence",
        collect=True,
        preserve_source=True,
    ),
    "changes.state_delta": _EvidenceMapTarget("changes", collect=True),
    "artifacts.versions": _EvidenceMapTarget("artifacts", collect=True),
    "feedback.linked": _EvidenceMapTarget("outcome.feedback", collect=True),
    "missingness.declared": _EvidenceMapTarget("missingness", collect=True),
}
_LIFECYCLE_ONLY_SUFFIXES = (".status", ".stop_reason", ".stage_reached")


def adapt_run(
    data: Mapping[str, Any],
    input_format: str = "auto",
    evidence_map: Mapping[str, Any] | None = None,
) -> AdaptedRun:
    if evidence_map is not None:
        if input_format not in {"auto", "generic"}:
            raise ValueError("An evidence map cannot be combined with a built-in input adapter.")
        mapped, name = _apply_evidence_map(data, evidence_map)
        return AdaptedRun(mapped, f"evidence-map:{name}")

    selected = detect_format(data) if input_format == "auto" else input_format
    if selected == "generic":
        return AdaptedRun(data, "generic")
    if selected == "otlp-json":
        return AdaptedRun(_adapt_otlp(data), "otlp-json")
    if selected == "span-json":
        return AdaptedRun(_adapt_span_document(data), "span-json")
    raise ValueError(f"Unknown input format {selected!r}")


def detect_format(data: Mapping[str, Any]) -> str:
    if isinstance(data.get("resourceSpans"), list):
        return "otlp-json"
    spans = data.get("spans")
    if isinstance(spans, list) and any(
        isinstance(span, Mapping) and "attributes" in span for span in spans
    ):
        return "span-json"
    return "generic"


def _decode_any_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    scalar_keys = (
        "stringValue",
        "boolValue",
        "intValue",
        "doubleValue",
        "bytesValue",
    )
    for key in scalar_keys:
        if key in value:
            decoded = value[key]
            if key == "stringValue" and isinstance(decoded, str):
                stripped = decoded.strip()
                if stripped.startswith(("{", "[")):
                    try:
                        return json.loads(stripped)
                    except json.JSONDecodeError:
                        pass
            return decoded
    array = value.get("arrayValue")
    if isinstance(array, Mapping):
        return [_decode_any_value(item) for item in array.get("values", [])]
    kvlist = value.get("kvlistValue")
    if isinstance(kvlist, Mapping):
        return {
            item["key"]: _decode_any_value(item.get("value"))
            for item in kvlist.get("values", [])
            if isinstance(item, Mapping) and "key" in item
        }
    return value


def _attributes(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, list):
        return {}
    return {
        str(item["key"]): _decode_any_value(item.get("value"))
        for item in value
        if isinstance(item, Mapping) and "key" in item
    }


def _otlp_spans(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for resource_span in data.get("resourceSpans", []):
        if not isinstance(resource_span, Mapping):
            continue
        for scope_span in resource_span.get("scopeSpans", []):
            if isinstance(scope_span, Mapping):
                result.extend(
                    span for span in scope_span.get("spans", []) if isinstance(span, Mapping)
                )
    return result


def _adapt_otlp(data: Mapping[str, Any]) -> Mapping[str, Any]:
    spans = _otlp_spans(data)
    return _normalize_spans(spans)


def _adapt_span_document(data: Mapping[str, Any]) -> Mapping[str, Any]:
    spans = [span for span in data.get("spans", []) if isinstance(span, Mapping)]
    return _normalize_spans(spans)


def _mapping_selectors(field: str, value: Any) -> tuple[str, ...]:
    if isinstance(value, str) and value:
        return (value,)
    if isinstance(value, list) and value and all(isinstance(item, str) and item for item in value):
        return tuple(value)
    raise ValueError(
        f"Evidence map field {field!r} must contain a non-empty selector "
        "or list of selectors."
    )


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _selected_values(
    data: Mapping[str, Any],
    selectors: tuple[str, ...],
    *,
    collect: bool,
    preserve_source: bool,
) -> Any:
    selected: list[Any] = []
    for selector in selectors:
        value = get_path(data, selector)
        if value is MISSING or value in (None, "", [], {}):
            continue
        if preserve_source:
            selected.append({"source_path": selector, "value": value})
        elif collect and isinstance(value, list):
            selected.extend(value)
        else:
            selected.append(value)
        if not collect:
            break
    if not selected:
        return MISSING
    return selected if collect else selected[0]


def _validate_evidence_selector(field: str, selector: str) -> None:
    if field != "outcome.evidence":
        return
    lowered = selector.lower()
    if lowered in {"status", "stop_reason", "stage_reached"} or lowered.endswith(
        _LIFECYCLE_ONLY_SUFFIXES
    ):
        raise ValueError(
            f"Evidence map field 'outcome.evidence' cannot select lifecycle-only "
            f"field {selector!r}."
        )


def _apply_evidence_map(
    data: Mapping[str, Any],
    evidence_map: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    version = evidence_map.get("mapping_version")
    if version != _EVIDENCE_MAP_VERSION:
        raise ValueError(
            f"Unsupported evidence map version {version!r}; "
            f"expected {_EVIDENCE_MAP_VERSION!r}."
        )
    name = str(evidence_map.get("name") or "").strip()
    if not name:
        raise ValueError("Evidence map must define a non-empty name.")
    fields = evidence_map.get("fields")
    if not isinstance(fields, Mapping) or not fields:
        raise ValueError("Evidence map must define a non-empty fields object.")

    normalized: dict[str, Any] = {}
    for field, raw_selectors in fields.items():
        if field not in _EVIDENCE_MAP_TARGETS:
            options = ", ".join(sorted(_EVIDENCE_MAP_TARGETS))
            raise ValueError(f"Unknown evidence map field {field!r}. Choose one of: {options}")
        selectors = _mapping_selectors(str(field), raw_selectors)
        for selector in selectors:
            _validate_evidence_selector(str(field), selector)
        target = _EVIDENCE_MAP_TARGETS[str(field)]
        value = _selected_values(
            data,
            selectors,
            collect=target.collect,
            preserve_source=target.preserve_source,
        )
        if value is not MISSING:
            _set_path(normalized, target.path, value)

    normalized.setdefault("steps", [])
    return normalized, name


def _first_attr(spans: list[Mapping[str, Any]], *keys: str) -> tuple[str, Any] | None:
    for span in spans:
        attrs = _attributes(span.get("attributes"))
        for key in keys:
            value = attrs.get(key)
            if value not in (None, "", [], {}):
                return key, value
    return None


def _prefixed_attrs(spans: list[Mapping[str, Any]], *prefixes: str) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for span in spans:
        for key, value in _attributes(span.get("attributes")).items():
            if key.startswith(prefixes) and value not in (None, "", [], {}):
                found[key] = value
    return found


def _normalize_spans(spans: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not spans:
        return {"steps": []}

    root = next((span for span in spans if not span.get("parentSpanId")), spans[0])
    trace_id = root.get("traceId") or root.get("trace_id")
    normalized: dict[str, Any] = {"steps": []}
    if trace_id:
        normalized["run"] = {"id": trace_id}

    goal = _first_attr(spans, "input.value", "input", "gen_ai.input")
    if goal:
        normalized["goal"] = {"requested": goal[1]}

    context = _first_attr(
        spans,
        "gen_ai.input.messages",
        "llm.input_messages",
        "gen_ai.system_instructions",
    )
    if context:
        normalized["context"] = {
            "effective": [{"source_attribute": context[0], "value": context[1]}]
        }

    configuration: dict[str, Any] = {}
    agent_version = _first_attr(spans, "gen_ai.agent.version", "agent.version")
    model = _first_attr(spans, "gen_ai.request.model", "llm.model_name")
    prompt_version = _first_attr(spans, "gen_ai.prompt.version", "prompt.version")
    if agent_version:
        configuration["agent_version"] = agent_version[1]
    if model:
        configuration["model"] = model[1]
    if prompt_version:
        configuration["prompt_version"] = prompt_version[1]

    tool_definition = _first_attr(spans, "gen_ai.tool.definitions", "llm.tools")
    flattened_tools = _prefixed_attrs(spans, "llm.tools.")
    if tool_definition:
        configuration["tools"] = tool_definition[1]
    elif flattened_tools:
        configuration["tools"] = flattened_tools
    if configuration:
        normalized["configuration"] = configuration

    for span in spans:
        attrs = _attributes(span.get("attributes"))
        kind = str(attrs.get("openinference.span.kind", "")).upper()
        operation = attrs.get("gen_ai.operation.name")
        is_tool = kind == "TOOL" or operation == "execute_tool"
        if not is_tool:
            continue
        call_id = (
            attrs.get("gen_ai.tool.call.id")
            or attrs.get("tool.call.id")
            or attrs.get("tool_call.id")
            or span.get("spanId")
            or span.get("span_id")
        )
        step: dict[str, Any] = {
            "id": span.get("spanId") or span.get("span_id") or span.get("name"),
            "action": {
                "id": call_id,
                "name": attrs.get("gen_ai.tool.name")
                or attrs.get("tool.name")
                or span.get("name"),
                "arguments": attrs.get("gen_ai.tool.call.arguments")
                or attrs.get("input.value"),
            },
        }
        result = attrs.get("gen_ai.tool.call.result") or attrs.get("output.value")
        if result not in (None, ""):
            step["observation"] = {
                "source_action_id": call_id,
                "content": result,
            }
        normalized["steps"].append(step)

    root_attrs = _attributes(root.get("attributes"))
    outcome_value = root_attrs.get("output.value") or root_attrs.get("gen_ai.output.messages")
    status = root.get("status")
    if outcome_value not in (None, "", [], {}) or status:
        normalized["outcome"] = {
            "status": status or "recorded",
            "evidence": [outcome_value] if outcome_value not in (None, "", [], {}) else [],
        }

    missingness = _first_attr(spans, "agent.capture.missingness")
    if missingness and isinstance(missingness[1], list):
        normalized["missingness"] = missingness[1]

    state_delta = _first_attr(spans, "agent.state.delta", "state.delta")
    if state_delta:
        normalized["changes"] = [state_delta[1]]
    artifact_versions = _first_attr(spans, "agent.artifact.versions", "artifact.versions")
    if artifact_versions:
        normalized["artifacts"] = artifact_versions[1]
    feedback = _first_attr(spans, "gen_ai.evaluation.result", "agent.feedback")
    if feedback:
        normalized.setdefault("outcome", {"status": "unknown", "evidence": []})
        normalized["outcome"]["feedback"] = [feedback[1]]

    return normalized
