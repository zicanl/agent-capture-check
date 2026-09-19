# Capture review reference

## Profiles

### Baseline

Require stable run identity, explicit goal, effective context or immutable references, versioned configuration, available capability evidence, action-result linkage, observed outcome evidence, and explicit missingness.

### Learning-ready

Add bounded state deltas for mutations, artifact versions, and feedback linked to the relevant run or step with source and timestamp.

### Elicited

Add structured agent self-reports only when passive capture cannot provide the desired signal. Record the elicitation prompt version, model, timing, whether it entered the acting agent's context, and `evidence_class: agent_self_report`.

## Collection priority

Use the least intrusive viable method:

1. existing API-boundary data;
2. IDs, hashes, references, and links;
3. bounded snapshots or verification reads;
4. passive runtime hooks;
5. out-of-band model annotation;
6. in-band elicitation.

In-band elicitation can change the acting policy. Recommend a capture OFF/ON comparison when it is introduced.

## Missingness

Use explicit reasons such as `provider_unavailable`, `not_instrumented`, `redacted`, `retention_policy`, `sampled_out`, `truncated`, `capture_failed`, `not_applicable`, or `unknown`.
