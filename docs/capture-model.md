# Capture model

This model is a set of testable requirements, not a new trace interchange format. Existing records should be evaluated through adapters wherever possible.

## Data classes

### Goal

Preserve the requested objective, success conditions, current subgoal when explicitly available, and termination condition. A later model inference about intent is derived data, not a substitute for the original goal.

### Context

The important object is effective context: what actually reached a decision point. A conversation archive is not sufficient when selection, truncation, summarization, memory retrieval, or prompt rendering changed the model input.

Capture methods, from least to most intrusive:

1. Store the rendered request already sent to the model.
2. Store content-addressed references to large inputs.
3. Record context transformations and their input/output references.
4. Ask the agent to identify relevant context only as an optional self-report.

### Configuration and capabilities

Preserve immutable agent, model, prompt, tool, skill, policy, permission, budget, and environment identifiers. The chosen action does not reconstruct the opportunity set that existed when the decision was made.

### Decision and action

Preserve structured calls and stable IDs. Candidate actions and rationales are optional and must state how they were produced. Never claim that a sampled candidate set is the complete action space.

### Change

Tool output describes what a tool returned. State delta describes what changed in the environment. For mutating actions, prefer bounded before/after references or read-after-write verification over copying an entire environment.

### Outcome and feedback

Separate completion status, observed evidence, human feedback, automated evaluation, and delayed business outcomes. Every derived score should retain its source, method, version, timestamp, and target run or step.

### Reasoning and self-report

Raw hidden reasoning may be unavailable and is not a requirement. Structured prompts can elicit goals, assumptions, uncertainty, expectations, and post-action assessments, but the result is `agent_self_report`. It may be useful without being factual.

## Is every class required?

No. Requirements depend on the intended capture profile and the workflow.

- `baseline`: enough evidence to understand the run and correlate actions with observations.
- `learning-ready`: adds state changes, artifact identity, and linked feedback.
- `elicited`: adds explicitly labeled self-reports when their expected value exceeds cost and observer effects.
- `multi-agent`: adds actor-scoped observations and capabilities plus
  sender/receiver evidence for handoffs and their transformations.

A field can be `not_applicable`, but that status should be explicit rather than inferred from absence.

### Multi-agent continuity

Run-level evidence is insufficient when one actor produces information for
another. Each consequential decision should identify its actor, effective
observation references, and effective capability-set reference. Each handoff
should preserve sender, receiver, sent payload identity, and received payload
identity. Actor, observation, capability-set, decision, and handoff IDs must be
stable and unique within the run.

Matching payload identities require no transformation. Different identities
require a transformation record that names its kind, input references, and
output reference. This proves that the change was recorded; it does not prove
that a summary or filter preserved every important semantic detail.

## Collection cost ladder

Prefer the least intrusive method that preserves the needed evidence:

1. Reuse data already present at an API boundary.
2. Add references, identifiers, and links.
3. Add a bounded state snapshot or verification read.
4. Add passive runtime hooks.
5. Add an out-of-band model annotation.
6. Add an in-band elicitation prompt to the acting agent.

The last two methods create derived data. In-band elicitation can alter the workflow and should be evaluated with capture OFF/ON comparisons.

## Missingness reasons

Recommended initial vocabulary:

- `provider_unavailable`
- `not_instrumented`
- `redacted`
- `retention_policy`
- `sampled_out`
- `truncated`
- `capture_failed`
- `not_applicable`
- `unknown`

The vocabulary should evolve from real traces rather than attempting to enumerate every cause in advance.
