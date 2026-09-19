from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .model import CheckResult, Report
from .rules import PROFILES


def check_run(data: Mapping[str, Any], profile: str = "baseline") -> Report:
    if profile not in PROFILES:
        options = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown profile {profile!r}. Choose one of: {options}")
    results: tuple[CheckResult, ...] = tuple(rule.check(data) for rule in PROFILES[profile])
    return Report(profile=profile, results=results)
