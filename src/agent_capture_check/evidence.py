from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


MISSING = object()


def get_path(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return MISSING
        current = current[part]
    return current


def first_present(data: Mapping[str, Any], paths: Iterable[str]) -> tuple[str, Any] | None:
    for path in paths:
        value = get_path(data, path)
        if value is not MISSING and value not in (None, "", [], {}):
            return path, value
    return None


def flatten_attribute_maps(data: Any) -> dict[str, Any]:
    """Collect common attribute envelopes without pretending to normalize a trace."""
    merged: dict[str, Any] = {}
    if isinstance(data, Mapping):
        attributes = data.get("attributes")
        if isinstance(attributes, Mapping):
            merged.update(attributes)
        resource = data.get("resource")
        if isinstance(resource, Mapping):
            resource_attributes = resource.get("attributes")
            if isinstance(resource_attributes, Mapping):
                merged.update(resource_attributes)
        for value in data.values():
            if isinstance(value, (Mapping, list)):
                merged.update(flatten_attribute_maps(value))
    elif isinstance(data, list):
        for item in data:
            merged.update(flatten_attribute_maps(item))
    return merged


def steps(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("steps", "spans", "observations", "events"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []
