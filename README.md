# Agent Capture Check

**Test whether your agent runs are leaving behind the data you will wish you had later.**

Agent runs are often expensive or impossible to reproduce. Most tracing tools record what happened, but developers still discover too late that a decision-time input, tool set, environment change, or delayed outcome was never captured.

Agent Capture Check is a small, format-aware test tool for those blind spots. It does not store traces, provide a dashboard, or replace OpenTelemetry, OpenInference, ATIF, ATOF, Langfuse, MLflow, or another observability stack. It checks the evidence those systems emitted.

Status: early research prototype. The current rules are hypotheses to test against real workflows, not an industry standard.

## What it checks

The first rule set focuses on data that is easy to lose or mistake for being present:

- the effective context actually supplied at a decision point;
- the available tools and capabilities, not only the chosen tool;
- model, agent, and prompt versions;
- links from actions to observations;
- state changes, rather than tool output alone;
- outcome evidence and delayed feedback;
- explicit reasons for missing, redacted, sampled, or unavailable data;
- separation of runtime facts from agent self-reports and later inferences.

See [the capture model](docs/capture-model.md) for scope and collection tradeoffs.

## Quick start

```bash
git clone https://github.com/zicanl/agent-capture-check.git
cd agent-capture-check
python -m pip install -e '.[test]'
agent-capture-check tests/fixtures/complete_run.json --profile baseline
pytest
```

For a clean-room test on another machine, follow [Test drive as a new user](docs/test-drive.md). It explains what to try, what feedback is useful, and how to contribute a sanitized failing fixture without publishing private trace content.

Example output:

```text
Profile: baseline
PASS     run.identity                 Run identity is preserved.
PASS     goal.explicit                An explicit run goal is preserved.
PASS     context.effective            Effective model context is preserved.
PASS     configuration.versions       Agent, model, and prompt versions are preserved.
PASS     capabilities.available       Available tools or capabilities are preserved.
PASS     actions.results_linked       Actions can be linked to their observations.
PASS     outcome.evidence             The run outcome includes evidence.
PASS     missingness.declared         Missing or redacted data has an explicit reason.

8 passed, 0 warned, 0 failed, 0 unknown
```

## CLI

```bash
agent-capture-check path/to/run.json
agent-capture-check path/to/run.json --profile learning-ready
agent-capture-check path/to/otlp.json --input-format auto
agent-capture-check path/to/run.json --output-format json
```

Exit codes are CI-friendly:

- `0`: no failed checks;
- `1`: one or more failed checks;
- `2`: invalid input or usage.

## pytest

The package exposes a `capture_check` fixture:

```python
def test_research_agent_capture(capture_check):
    run = run_research_agent("Compare two papers")
    capture_check(run, profile="baseline")
```

The fixture accepts a Python mapping or a path to JSON and raises an assertion containing the full report when required evidence is missing.

## Input and adapters

The prototype accepts JSON objects and looks for semantic evidence rather than requiring a new interchange format. It currently auto-detects:

- generic JSON evidence documents;
- OTLP JSON with `resourceSpans`;
- JSON documents containing a `spans` array with OpenTelemetry/OpenInference-style attributes.

Adapters translate established formats into an internal evidence view used only for checking. This project should not become another trace storage format.

## Capture profiles

- `baseline` checks whether a run can be understood and its actions correlated.
- `learning-ready` adds state deltas, artifact versions, and feedback linkage.
- `elicited` adds optional agent self-reports and the metadata needed to interpret them safely.

Profiles are intentionally incremental. Not every workflow needs every field, and prompting the agent for extra information must remain optional because it adds cost and can change behavior.

## Design boundaries

- An LLM inference is not a substitute for missing runtime evidence.
- Agent explanations are `agent_self_report`, not ground-truth reasoning.
- A tool result is not automatically evidence of the external state change.
- `null` without a missingness reason is ambiguous.
- Privacy, retention, and cost can justify not capturing content; the omission should still be explicit.
- The deterministic checks are the core. Optional LLM review may assess semantic quality later, but it must never turn inferred data into a passing capture result.

## Repository layout

```text
src/agent_capture_check/     checker, rules, CLI, pytest plugin
tests/                       executable examples and regression tests
docs/capture-model.md        data classes, collection methods, tradeoffs
docs/multi-agent-evidence-continuity.md
                             per-decision and handoff checking design
docs/landscape.md            relationship to adjacent standards and tools
skills/review-agent-capture/ reusable coding-agent review skill
```

## Near-term validation

The next milestone is not more schema. It is running the checker against three real workflows—a coding agent, a research/browser agent, and a multi-agent workflow—and removing rules that do not identify consequential information loss.

The [multi-agent evidence continuity](docs/multi-agent-evidence-continuity.md)
design note defines the intended boundary for detecting information loss
between actors without requiring chain-of-thought or inline payload duplication.

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR, especially when feedback comes from a real production or personal trace.
