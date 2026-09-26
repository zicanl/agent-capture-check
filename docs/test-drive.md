# Test drive as a new user

This is a clean-room test of the current alpha. Approach it as a user evaluating whether the project helps, not as someone trying to confirm its design.

## 1. Install from a fresh clone

Requirements: Git and Python 3.10 or newer.

```bash
git clone https://github.com/zicanl/agent-capture-check.git
cd agent-capture-check
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Some minimal Debian and Ubuntu images install Python without `ensurepip`, so
`python3 -m venv .venv` exits with a message asking for `python3-venv` (or a
versioned package such as `python3.12-venv`). Install that OS package and retry,
or use [`uv`](https://docs.astral.sh/uv/) without modifying the system Python:

```bash
uv venv --python python3 .venv
source .venv/bin/activate
uv pip install --python .venv/bin/python -e '.[test]'
```

## 2. Verify the known examples

```bash
pytest
agent-capture-check tests/fixtures/complete_run.json --profile baseline
agent-capture-check tests/fixtures/missing_blindspots.json --profile baseline
```

Expected behavior:

- the test suite passes;
- `complete_run.json` exits with code `0`;
- `missing_blindspots.json` reports failures and exits with code `1`.

If installation or these commands are confusing, that is useful feedback. Do not work around it silently.

## 3. Try one real workflow

Start with `baseline`:

```bash
agent-capture-check path/to/exported-trace.json --profile baseline
```

Supported inputs currently include:

- generic JSON evidence documents similar to the included fixtures;
- OTLP JSON with a top-level `resourceSpans` array;
- JSON documents with a top-level `spans` array and OpenTelemetry/OpenInference-style attributes.

If auto-detection is wrong, specify `--input-format generic`, `otlp-json`, or `span-json`.
For a custom producer schema, provide a versioned
[evidence map](evidence-maps.md). For example:

```bash
agent-capture-check session_breakdown.json \
  --evidence-map examples/evidence-maps/hyperloom-session-breakdown-v6.json
```

Do not change your agent prompts for the first test. The first question is whether passive evidence already present in the workflow is recognized correctly.

## 4. Review the findings skeptically

For every failure or warning, ask:

- Was the data actually missing, or did the adapter fail to find it?
- Could it be reconstructed reliably from another field?
- Would losing it prevent a real debugging, evaluation, replay, or learning task?
- Is the proposed remediation cheaper than the information is worth?
- Is the rule applicable to this workflow at all?

Record false positives and false negatives. Both are more valuable than a high score.

## 5. Send feedback by PR

Use the pull request template. The most helpful PR includes one of:

- a documentation correction;
- a minimized sanitized fixture plus a failing test;
- an adapter improvement;
- a rule change justified by a concrete workflow.

Never attach a raw private trace. Follow the privacy guidance in [CONTRIBUTING.md](../CONTRIBUTING.md).
