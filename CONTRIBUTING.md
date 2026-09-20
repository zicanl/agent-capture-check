# Contributing

The most valuable contribution right now is evidence that a rule is useful, misleading, missing, or too expensive—not a larger schema.

## Good contributions

- a minimized, sanitized trace shape that the current adapter cannot read;
- a false positive or false negative with a clear expected result;
- evidence that a proposed field can already be reconstructed reliably;
- a capture blind spot observed in a real agent workflow;
- a simpler collection method with lower latency, privacy, or storage cost;
- documentation fixes from a clean installation.

## Before opening a PR

```bash
python -m pip install -e '.[test]'
pytest
agent-capture-check tests/fixtures/complete_run.json --profile baseline
```

Add or update a fixture when behavior changes. Prefer a small synthetic fixture that preserves the relevant event structure over a full trace dump.

## Privacy and confidential data

Do not commit raw traces containing:

- user prompts or personal information;
- proprietary system prompts;
- credentials, tokens, cookies, or signed URLs;
- private repository paths or source code;
- customer, employer, or third-party identifiers;
- internal tool outputs or business data.

Replace content with synthetic values while preserving the fields, nesting, IDs, and relationships needed to reproduce the issue. If sanitization would destroy the evidence, describe the shape and behavior without attaching the trace.

## Rule changes

For a new or changed rule, explain:

1. what information is lost;
2. when it was available;
3. why it cannot be reconstructed reliably;
4. which downstream use is affected;
5. the least intrusive way to capture it;
6. whether the rule should fail, warn, be unknown, or be profile-specific.

An LLM inference about missing information does not make the capture check pass.
