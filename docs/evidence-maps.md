# Evidence maps

Evidence maps let a producer translate its existing JSON field names into the
canonical evidence slots checked by Agent Capture Check. They are versioned
configuration, not a new trace format and not a substitute for missing data.

```bash
agent-capture-check session_breakdown.json \
  --evidence-map examples/evidence-maps/hyperloom-session-breakdown-v6.json
```

## Format

```json
{
  "mapping_version": "agent-capture-map.v1",
  "name": "my-runtime-v2",
  "fields": {
    "run.identity": "metadata.run_id",
    "goal.explicit": ["request.objective", "request.input"],
    "outcome.evidence": [
      "result.measurement",
      "result.external_feedback"
    ]
  }
}
```

Each selector is a dot-separated path through JSON object keys. Array indexing
and expression evaluation are intentionally out of scope for V1. For a
single-valued evidence slot, a list of selectors is an ordered fallback. For a
collection slot, values from every present selector are collected.

Supported canonical fields:

- `run.identity`
- `goal.explicit`
- `context.effective`
- `configuration.agent_version`
- `configuration.model`
- `configuration.prompt_version`
- `capabilities.available`
- `actions.steps`
- `outcome.status`
- `outcome.evidence`
- `changes.state_delta`
- `artifacts.versions`
- `feedback.linked`
- `missingness.declared`

Unknown canonical fields, malformed selectors, and unsupported mapping
versions fail closed.

## Semantic boundary

An evidence map changes names, not meanings. A workload model must not be
mapped as the model that made an agent decision, conversation history must not
be mapped as effective context unless it is the rendered model input, and tool
output must not be mapped as an external state delta without verification.

The checker rejects lifecycle-only selectors such as `outcome.status`,
`stop_reason`, and `stage_reached` when they are assigned to
`outcome.evidence`. Rule-specific validators remain authoritative after
mapping.

Maps should be reviewed and versioned with the producer schema. The selected
map name is included in the report's input format so a result can be traced
back to the interpretation used.

## Hyperloom example

The included Hyperloom V6 map recognizes evidence directly preserved by
`session_breakdown.json`: session identity, optimization objective, Hyperloom
code revision, and measured outcome blocks.

It deliberately does not map the optimized workload model as the acting agent
model or infer decision context, capabilities, and action/result linkage from
the summary. Those facts may exist in sibling session ledgers, but checking a
complete session directory requires a separate evidence-bundle contract.
