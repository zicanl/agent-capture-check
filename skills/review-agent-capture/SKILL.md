---
name: review-agent-capture
description: Review an agentic workflow, its instrumentation, or an exported run for execution-data capture gaps that may prevent later debugging, evaluation, replay, or learning. Use when a developer asks what agent data they are failing to preserve; do not use as a general code-quality or model-output evaluator.
---

# Review Agent Capture

Identify information that exists during an agent run but may be unrecoverable afterward. Work with the project's existing tracing stack; do not recommend a new telemetry backend unless the user asks for one.

## Review modes

Choose the narrowest applicable mode:

- For an exported run, execute `agent-capture-check <path>` when the CLI is available, then inspect failed and unknown evidence manually.
- For source code, locate model-call, tool-call, context-transformation, handoff, mutation, and outcome boundaries. Identify which boundaries emit evidence and which silently discard it.
- For a proposed workflow, produce a minimal capture plan before suggesting implementation.

Read [references/capture-model.md](references/capture-model.md) when deciding whether a field is required, optional, or too intrusive.

## Evidence rules

- Distinguish runtime facts, external observations, agent self-reports, and derived interpretations.
- Do not treat model-generated explanations as ground-truth reasoning.
- Do not treat conversation history as proof of the effective model context.
- Do not treat a tool response as proof that external state changed.
- Do not treat an inferred value as captured data. Mark it as derived and leave the capture gap open.
- Prefer IDs, versions, references, and bounded deltas before recommending full snapshots or copied payloads.
- State when privacy, retention, latency, or cost justifies omission, and require an explicit missingness reason.

## Output

Report only consequential gaps. For each one include:

1. the missing evidence;
2. when it existed;
3. why it cannot be reliably reconstructed;
4. the least intrusive capture method;
5. the downstream use it enables;
6. cost, privacy, or observer-effect concerns.

Classify each finding as required for the selected profile, recommended, optional elicitation, or not applicable. Avoid prescribing elicitation prompts unless passive capture cannot provide the signal.
