# Multi-agent evidence continuity

Status: partially implemented. The `multi-agent` profile covers graph identity,
decision-scoped observations and capabilities, and handoff receipt and
transformation linkage. Action authorization, result linkage, and outcome
lineage remain proposed. This document defines checking semantics, not a new
trace transport or storage format.

## Problem

A run-level record can contain every required evidence class and still lose
information between actors:

```text
input -> agent A -> agent B -> agent C -> outcome
```

Agent A may observe a constraint that Agent B omits from a summary. Agent C can
then act without that constraint even though the run archive contains both the
original observation and a later context. A run-level presence check may pass
because it cannot show which actor observed which payload at which decision.

The required property is evidence continuity: every consequential decision can
be related to the information and capabilities effective for that actor, and
every handoff can be traced from what was sent to what was received.

## Scope

The deterministic checker should establish structural continuity:

- who produced an observation, message, artifact, or action;
- which actor and decision consumed it;
- what payload was sent and received at a handoff;
- whether a transformation, omission, or redaction was declared;
- which decision authorized an action;
- which external observation or state delta followed that action;
- how outcome evidence relates to the actions that may have contributed.

It should not claim that:

- every fact known by one actor should be propagated to every other actor;
- a summary preserved the most important semantics;
- a model explanation is the causal reason for an action;
- provenance alone proves causal attribution;
- hidden chain-of-thought is required.

Selective disclosure can be correct for privacy, least privilege, role
separation, or context cost. The checker evaluates declared continuity, not
universal information sharing.

## Canonical evidence objects

The following objects describe an internal checking view. Producer formats
should reach this view through built-in adapters or versioned Evidence Maps;
they do not need to adopt these field names on the wire.

### Actor

```json
{
  "id": "agent-c",
  "kind": "llm_agent",
  "version": "planner@7"
}
```

Actors may be LLM agents, deterministic controllers, tools, humans, verifiers,
or external services.

### Decision

```json
{
  "id": "decision-c-17",
  "actor_id": "agent-c",
  "observation_refs": ["payload:m2", "state:s9"],
  "capability_set_ref": "capabilities:agent-c:4",
  "action_id": "action-c-17"
}
```

An observation reference means the payload was effective for that decision,
not merely present elsewhere in the run.

### Handoff

```json
{
  "id": "handoff-b-c-9",
  "from_actor_id": "agent-b",
  "to_actor_id": "agent-c",
  "sent": {
    "ref": "payload:m2",
    "digest": "sha256:abc"
  },
  "received": {
    "ref": "payload:m2",
    "digest": "sha256:abc"
  },
  "transformation": null
}
```

When sent and received payloads differ, the handoff should identify the
transformation:

```json
{
  "kind": "summary",
  "version": "handoff-summary@3",
  "input_refs": ["payload:m1"],
  "output_ref": "payload:m2"
}
```

The transformation record proves that a change was intentional and locates its
inputs and output. It does not prove semantic fidelity.

### Action and external result

```json
{
  "action": {
    "id": "action-c-17",
    "decision_id": "decision-c-17",
    "executed_by": "tool:patch-applier"
  },
  "observation": {
    "id": "observation-c-17",
    "source_action_id": "action-c-17",
    "state_delta_ref": "delta:worktree:42"
  }
}
```

The proposed, authorized, and executed forms of an action should remain
distinct when a policy layer can deny or transform it.

## Deterministic checks

An initial multi-agent profile should evaluate:

### `decision.observations_scoped`

Every recorded decision identifies its actor and the observations effective
for that decision. A global conversation or run-level context does not satisfy
this rule.

### `decision.capabilities_scoped`

Every decision references the capability and permission set effective at that
time. A static registry is insufficient when phase, policy, resource, or
authorization state can change.

### `handoff.receipt_linked`

Every consequential handoff has sender, receiver, sent payload, and received
payload evidence. A producer record without a receiver-side receipt is
incomplete.

### `handoff.transformation_declared`

Different sent and received identities require a transformation record or an
explicit missingness reason. Matching references or digests require no
transformation.

### `action.decision_linked`

Every proposed or executed action points to the decision that produced or
authorized it. Policy transformations and denials remain visible.

### `action.result_linked`

Every executed action links to its tool result or external observation.
Mutating actions additionally link to a verified state delta or an explicit
reason it was not captured.

### `outcome.lineage_present`

Outcome evidence identifies the run, actions, artifacts, or state transition
it evaluates. This is provenance, not causal attribution.

## Coverage, not only pass/fail

Large workflows need denominators. Reports should include coverage such as:

```text
decision observation coverage        18 / 27
decision capability coverage          2 / 27
handoff sent/received linkage          6 / 10
declared handoff transformations       3 / 4
action/decision linkage               24 / 25
mutating-action state deltas            7 / 12
```

A run may therefore expose a localized gap instead of receiving one
undifferentiated failure.

## Semantic-loss boundary

Structural checks can detect a missing handoff, an unlinked payload, an
undeclared transformation, or a decision with no scoped observation. They
cannot determine whether a summary omitted the fact that mattered most.

Semantic continuity requires task-specific invariants or a derived evaluator.
Examples include preserving a user safety constraint, a benchmark objective,
or a required citation. Such evaluations must record method, version, inputs,
target handoff, and uncertainty. They must not turn inferred content into
captured runtime evidence.

## Capture cost

Stronger continuity checks do not require adding content to the acting model's
prompt. Passive hooks can record boundaries that already exist.

To limit storage and later analysis cost:

- store payloads once and reference them by stable ID;
- use content digests for identity and deduplication;
- retain bounded state deltas instead of full environment copies;
- version capability sets once and reference them from decisions;
- keep payload content in the producer's existing controlled store;
- fetch only the relevant evidence subgraph for later analysis.

A digest without retained, authorized access to the referenced payload proves
identity but does not make the content reconstructable. Retention and redaction
must therefore remain explicit.

In-band elicitation is not required. Asking the acting model to explain a
decision adds tokens, can change behavior, and produces a self-report rather
than ground-truth reasoning.

## Hyperloom application

A complete Hyperloom session distributes relevant evidence across the manifest,
state, conversation ledger, proposal/task mappings, decision trace, policy
records, action workspaces, and session breakdown.

Potential correlation keys include `session_id`, `call_id`, `proposal_msg_id`,
`task_id`, `dyn_id`, phase, tick, and turn. A future session-bundle adapter
should document which joins are authoritative before using them to satisfy a
continuity rule.

In particular, a full prompt can establish effective model context, while a
phase action catalogue alone may not establish effective permission or
resource availability. Policy and resource decisions need their own
decision-time evidence.

## Implementation status and next validation

The repository now has versioned Evidence Maps, a synthetic multi-agent
fixture, normalized actor/decision/handoff records, and deterministic coverage
checks under the opt-in `multi-agent` profile.

The next steps are:

1. Validate the implemented rules against a sanitized Hyperloom session bundle
   and at least one unrelated multi-agent runtime.
2. Define authoritative joins for multi-file evidence bundles before adding a
   bundle adapter.
3. Implement `action.decision_linked`, strengthened action/result linkage, and
   `outcome.lineage_present` only when real fixtures demonstrate the need.
4. Add optional semantic-continuity evaluation only after deterministic
   boundaries are stable.
