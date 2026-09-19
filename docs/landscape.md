# Adjacent work and project boundary

Checked on 2026-09-19. This document records why Agent Capture Check should integrate with existing work instead of replacing it.

## Telemetry and semantic conventions

- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) define spans, events, metrics, and common attributes for GenAI systems. Agent conventions remain under active development, and sensitive content is opt-in.
- [OpenInference](https://github.com/Arize-ai/openinference) adds AI-specific span kinds and attributes on top of OpenTelemetry.

Use these as evidence sources and export targets. Do not create a competing transport.

## Observability and evaluation platforms

- [Langfuse](https://langfuse.com/docs/observability/overview)
- [MLflow Tracing](https://mlflow.org/docs/latest/genai/tracing)
- [Arize Phoenix](https://github.com/Arize-ai/phoenix)

These systems store, visualize, evaluate, and mine traces. Agent Capture Check should lint the completeness and interpretation of emitted records, not build another backend.

## Trajectory formats

- [ATIF](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md) is a JSON interchange format for agent trajectories used in debugging, replay, SFT, and RL.
- [NVIDIA ATOF](https://docs.nvidia.com/nemo/relay/latest/reference/atof-event-format) is a real-time runtime event format with conversion to ATIF.
- [Agent Data Protocol](https://www.agentdataprotocol.com/) unifies heterogeneous agent datasets for training pipelines.

These projects substantially overlap with any attempt to invent a new trajectory schema. The open question for this repo is narrower: whether the producer captured enough evidence in the first place.

## Learning systems

- [Agent Lightning](https://www.microsoft.com/en-us/research/project/agent-lightning/) collects traces and reward signals and converts them into training transitions.

This demonstrates downstream demand for high-quality execution data. It does not prove that every proposed capture requirement in this repo is useful.

## Working differentiation

Agent Capture Check focuses on four gaps:

1. capture-time obligations rather than storage;
2. explicit missingness rather than silent absence;
3. conformance profiles tied to downstream use;
4. separation of runtime facts, agent self-reports, and later inferences.

This differentiation must be tested against real runs. If existing defaults already satisfy a rule reliably, remove or demote that rule rather than preserving artificial novelty.
