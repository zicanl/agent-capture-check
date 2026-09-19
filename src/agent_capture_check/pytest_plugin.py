from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

import pytest

from .checker import check_run
from .cli import _render_text


@pytest.fixture
def capture_check() -> Callable[[Mapping[str, Any] | str | Path, str], None]:
    def run(value: Mapping[str, Any] | str | Path, profile: str = "baseline") -> None:
        if isinstance(value, (str, Path)):
            with Path(value).open(encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = value
        report = check_run(data, profile)
        if report.failed:
            pytest.fail(_render_text(report), pytrace=False)

    return run
