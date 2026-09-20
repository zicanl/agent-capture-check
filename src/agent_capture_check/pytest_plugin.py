from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import pytest

from .checker import check_run
from .cli import _render_text


class CaptureCheck(Protocol):
    def __call__(
        self,
        value: Mapping[str, Any] | str | Path,
        profile: str = "baseline",
        input_format: str = "auto",
    ) -> None: ...


@pytest.fixture
def capture_check() -> CaptureCheck:
    def run(
        value: Mapping[str, Any] | str | Path,
        profile: str = "baseline",
        input_format: str = "auto",
    ) -> None:
        if isinstance(value, (str, Path)):
            with Path(value).open(encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = value
        report = check_run(data, profile, input_format)
        if report.failed:
            pytest.fail(_render_text(report), pytrace=False)

    return run
