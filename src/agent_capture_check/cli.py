from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any

from .checker import check_run
from .model import Report
from .rules import PROFILES


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("The top-level JSON value must be an object.")
    return value


def _render_text(report: Report) -> str:
    lines = [f"Profile: {report.profile}", f"Input format: {report.input_format}"]
    for result in report.results:
        lines.append(f"{result.status.value.upper():8} {result.rule_id:30} {result.message}")
        if result.remediation and result.status.value != "pass":
            lines.append(f"         {'':30} Fix: {result.remediation}")
    counts = report.counts()
    lines.append("")
    lines.append(
        f"{counts['pass']} passed, {counts['warn']} warned, "
        f"{counts['fail']} failed, {counts['unknown']} unknown"
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-capture-check",
        description="Check an agent execution record for capture blind spots.",
    )
    parser.add_argument("path", type=Path, help="Path to a JSON execution record")
    try:
        package_version = importlib.metadata.version("agent-capture-check")
    except importlib.metadata.PackageNotFoundError:
        package_version = "0.1.0+local"
    parser.add_argument("--version", action="version", version=package_version)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="baseline")
    parser.add_argument(
        "--input-format",
        choices=("auto", "generic", "otlp-json", "span-json"),
        default="auto",
    )
    parser.add_argument(
        "--evidence-map",
        type=Path,
        help="Path to a versioned JSON map from source fields to canonical evidence",
    )
    parser.add_argument(
        "--output-format",
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = _load(args.path)
        evidence_map = _load(args.evidence_map) if args.evidence_map else None
        report = check_run(data, args.profile, args.input_format, evidence_map)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(_render_text(report))
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
