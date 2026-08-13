# Computer-Use Automation System

A focused end-to-end implementation for the interface.ai take-home project. The system uses an LLM for **discovery**, converts the successful run into a typed capability artifact, then uses a **deterministic replay engine** with no LLM in the decision loop.

The target is a local, intentionally plain member-servicing application. It is safe to run and contains synthetic data only.

## What is implemented

- Goal + target input.
- Genuine LLM-driven observe → decide → act discovery loop.
- Browser computer-use surface using Playwright screenshots + visible controls.
- Typed, versioned capability artifact with inputs, outputs, locator strategy, checkpoints, risk, and action policy.
- Deterministic replay with no LLM calls.
- Stable semantic locator strategy with fallback support.
- Business outcomes separated from failures (`member_not_found`, `validation_error`).
- Recoverable waits/retries and hard-failure reporting.
- Allowlisted origin and action types.
- Screenshot evidence and structured discovery/replay logs.
- Human handoff seam that pauses the same Playwright page/session and accepts bounded operator commands before resuming.
- Design discussion for legacy web, desktop surfaces, tenant/version reuse, and drift.
- Tests for schema, policy, and target behavior.

## Project layout

```text
.
├── agent/
│   ├── browser.py       # Observe and browser actions
│   ├── discover.py      # LLM discovery + artifact recording
│   ├── llm.py           # OpenAI-compatible LLM adapter
│   ├── operator.py      # Minimal human handoff console
│   └── policy.py        # Safety allowlist
├── app/main.py          # Local synthetic banking target
├── artifacts/           # Generated capability artifacts
├── evidence/            # Discovery/replay evidence
├── models/              # Artifact/result contracts
├── replay/engine.py     # Deterministic production path
├── tests/
├── REPORT.md
└── requirements.txt
```

## Setup

### 1. Python environment

Python 3.11+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

If Chromium is already installed on your machine, set `CHROMIUM_PATH` to its executable path. The code defaults to `/usr/bin/chromium` in Linux environments where that binary exists.
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium

If Chromium is already installed on your machine, set `CHROMIUM_PATH` to its executable path. The code defaults to `/usr/bin/chromium` in Linux environments where that binary exists.
```

### 2. Start the target application

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` if you want to inspect the target manually.

### 3. Configure the LLM

Copy `.env.example` to `.env` and provide your own model API key. The discovery path intentionally requires a real model API call because the assignment explicitly asks for at least one genuine LLM-driven run.

```bash
cp .env.example .env
```

Then load the environment in your shell, for example:

```bash
export OPENAI_API_KEY="YOUR_KEY"
export OPENAI_MODEL="gpt-4.1-mini"
```

Never commit `.env`.

## Exact demo path

### Discovery

With the target server running:

```bash
python -m agent.discover \
  --goal "Look up member {{member_id}} and read their current savings balance" \
  --target "http://127.0.0.1:8000/" \
  --member-id "12345"
```

The successful run creates:

```text
artifacts/member_lookup_savings_balance.json
evidence/discovery-<session>/discovery_decisions.json
evidence/discovery-<session>/discovery_events.json
evidence/discovery-<session>/discovery_result.json
evidence/discovery-<session>/step-*.png
```

The generated artifact is the reusable capability. It is decoupled from the raw LLM transcript.

### Deterministic replay

```bash
python -m replay.engine artifacts/member_lookup_savings_balance.json --member-id 12345
```

No LLM is called by replay.

### Exceptional-state replay

Use a member that does not exist:

```bash
python -m replay.engine artifacts/member_lookup_savings_balance.json --member-id 99999
```

Expected result:

```text
status = business_outcome
business_outcome = member_not_found
```

This is deliberately not reported as a crash: `member_not_found` is an expected business result for a caller.

## Human handoff demo

The discovery agent can return `escalate` when it cannot safely proceed. It writes an intervention request containing the session ID, current URL, screenshot, reason, and allowed operator actions.

Use the displayed command:

```bash
python -m agent.operator --session <SESSION_ID> --fill-label "Member number" --value "12345"
python -m agent.operator --session <SESSION_ID> --click "Search"
python -m agent.operator --session <SESSION_ID> --resume
```

The commands are bounded and are executed by the waiting discovery process against the same Playwright page. This is intentionally a minimal operator seam rather than a full co-browsing product.

## Tests

```bash
pytest -q
```

## Safety

The default policy only permits the local demo origin and safe browser actions. Risky/irreversible actions are not in the action allowlist. Secrets are environment variables only. Synthetic member data is used; the artifact and logs should not contain credentials, tokens, or full PII.

## Limitations / honest cut line

The implementation does not attempt to build queues, a production operator co-browsing UI, native desktop automation, or multi-tenant infrastructure. Those are intentionally kept behind the surface adapter / operator seams and are described in `REPORT.md`. The discovery run requires the evaluator's own model API key.
