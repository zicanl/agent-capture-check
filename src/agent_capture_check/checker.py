from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapters import adapt_run
from .model import CheckResult, Report
from .rules import PROFILES


def check_run(
    data: Mapping[str, Any],
    profile: str = "baseline",
    input_format: str = "auto",
    evidence_map: Mapping[str, Any] | None = None,
) -> Report:
    if profile not in PROFILES:
        options = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile {profile!r}. Choose one of: {options}")
    adapted = adapt_run(data, input_format, evidence_map)
    results: tuple[CheckResult, ...] = tuple(
        rule.check(adapted.data) for rule in PROFILES[profile]
    )
    return Report(profile=profile, input_format=adapted.input_format, results=results)
