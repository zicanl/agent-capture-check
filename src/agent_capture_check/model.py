from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class CheckResult:
    rule_id: str
    status: Status
    message: str
    evidence: tuple[str, ...] = ()
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(frozen=True)
class Report:
    profile: str
    input_format: str
    results: tuple[CheckResult, ...]

    @property
    def failed(self) -> bool:
        return any(result.status is Status.FAIL for result in self.results)

    def counts(self) -> dict[str, int]:
        return {
            status.value: sum(result.status is status for result in self.results)
            for status in Status
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "input_format": self.input_format,
            "summary": self.counts(),
            "results": [result.to_dict() for result in self.results],
        }


RunData = Mapping[str, Any]
