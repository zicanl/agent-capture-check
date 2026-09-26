# Roadmap

Agent Capture Check remains a small validation tool. The roadmap is driven by
real capture failures, not by a goal of owning storage, telemetry, or a new
trace standard.

## Now: validate the checks

Run the current profiles against sanitized evidence from three different
workflow shapes:

1. a coding agent with tool calls and repository state changes;
2. a research or browser agent with cited outcome evidence;
3. a multi-agent workflow with at least one transformed handoff.

Every blind spot found should become a minimized fixture and regression test.
Rules that do not distinguish consequential loss from harmless variation
should be narrowed or removed.

## Next: reduce integration friction

- Define an evidence-bundle contract for workflows whose evidence is split
  across several files. Joins must be explicit and authoritative before they
  are allowed to satisfy a rule.
- Add trace selection or per-trace reporting for OTLP exports containing more
  than one trace. Until then, mixed-trace inputs continue to fail closed.
- Add producer Evidence Maps only when backed by a real fixture. Mapping must
  remain field translation, not semantic inference.
- Improve diagnostics for rejected maps, unsupported producer shapes, and
  partially covered multi-agent graphs.

## Then: complete proven continuity gaps

The multi-agent design identifies three rules that are not implemented yet:

- action-to-decision or authorization linkage;
- action-to-result and mutating-action state-delta linkage;
- outcome lineage to the run, actions, artifacts, or state transitions it
  evaluates.

These should be added only after the validation corpus shows stable evidence
shapes and useful failure modes.

## Explicitly deferred

- trace storage, databases, dashboards, and hosted telemetry;
- declaring a universal interchange standard;
- mandatory in-band prompting or chain-of-thought capture;
- an LLM judge that can turn absent runtime evidence into a passing result.

Optional semantic review may be explored later, but deterministic evidence
boundaries remain authoritative.
