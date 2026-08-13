# Interface AI – Computer-Use Automation

This project is a small implementation of a computer-use automation system for a local banking application.

The system uses an LLM to discover browser workflows and saves successful workflows as reusable capability artifacts. These artifacts can then be replayed deterministically without calling the LLM again.

For this demo, the system works with a local banking application containing synthetic member data.

## Project Structure

```text
interface-computer-use/
├── agent/
│   ├── browser.py
│   ├── discover.py
│   ├── llm.py
│   ├── operator.py
│   └── policy.py
├── app/
│   └── main.py
├── artifacts/
│   └── member_lookup_savings_balance.json
├── models/
│   ├── artifact.py
│   └── result.py
├── replay/
│   └── engine.py
├── target_app/
├── tests/
├── .env.example
├── README.md
├── REPORT.md
├── requirements.txt
└── pytest.ini
The evidence/ directory is generated during discovery and replay and is excluded from Git.

Requirements
Python 3.13
Playwright
Chromium
OpenAI API key for LLM discovery

The project uses synthetic/local banking data only.

Setup

Clone the repository:

git clone https://github.com/Reshmareddy49/interface-ai-computer-use.git
cd interface-ai-computer-use

Create and activate the virtual environment:

python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Install Playwright Chromium:

playwright install chromium

Create the environment file:

cp .env.example .env

Open .env:

nano .env

Add your OpenAI API key:

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1

ALLOWED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
MAX_AGENT_STEPS=12
AGENT_TIMEOUT_SECONDS=90

Never commit .env to Git.

Verify Installation

Compile the project:

python -m py_compile agent/discover.py agent/llm.py agent/browser.py models/artifact.py replay/engine.py

Run the tests:

pytest -q

Expected result:

6 passed
Run the Local Application

Start the local demo application:

python -m app.main

The application runs at:

http://127.0.0.1:8000/

Keep the application running while using discovery or replay.

Open another terminal and activate the environment:

cd interface-computer-use
source .venv/bin/activate
Run AI Discovery

Discovery uses the LLM to observe the browser and decide the next action.

Run:

python -m agent.discover \
  --goal "Look up member 12345 and read their current savings balance" \
  --target "http://127.0.0.1:8000/" \
  --member-id "12345"

A successful run creates:

artifacts/member_lookup_savings_balance.json

The artifact contains the reusable browser actions, locators, inputs, outputs, and checkpoint information.

The member ID is parameterized as:

{{member_id}}

This allows the same capability to be reused for different members.

Replay

Replay the saved capability without using the LLM:

python -m replay.engine artifacts/member_lookup_savings_balance.json --member-id "12345"

Example result:

{
  "status": "success",
  "capability_id": "member.lookup.savings_balance",
  "outputs": {
    "savings_balance": "$8421.17"
  },
  "business_outcome": null,
  "error_code": null,
  "failed_step": null,
  "expected": null,
  "observed": null,
  "message": "Deterministic replay completed and checkpoint verified."
}

The same artifact can be reused with other member IDs:

python -m replay.engine artifacts/member_lookup_savings_balance.json --member-id "54321"

python -m replay.engine artifacts/member_lookup_savings_balance.json --member-id "11111"

Local test results:

12345 -> $8421.17
54321 -> $1598.42
11111 -> $0.00

The replay process does not call the LLM.

Discovery vs Replay

Discovery:

Natural Language Goal
        ↓
Browser Observation
        ↓
LLM Decision
        ↓
Playwright Action
        ↓
Successful Workflow
        ↓
Capability Artifact

Replay:

Input Parameters
        ↓
Capability Artifact
        ↓
Deterministic Replay Engine
        ↓
Playwright
        ↓
Output Extraction
        ↓
Checkpoint Verification
        ↓
Structured Result

The LLM is used to discover a workflow. Once the workflow is saved, the same workflow can be executed deterministically.

Safety

The project is designed for a local banking demo.

Only synthetic banking data is used.
The policy layer restricts browser actions.
Allowed URLs are checked before navigation.
The artifact records allowed action types.
Human handoff is available when the agent cannot safely continue.
.env is excluded from Git.
Runtime evidence is excluded from Git.

Do not use real banking credentials or real customer information with this project.

Human Handoff

If the discovery agent cannot safely determine the next action, it can stop and request human intervention.

The handoff can record:

Session ID
Current URL
Screenshot
Reason for stopping
Allowed operator actions

The operator module can be inspected with:

python -m agent.operator --help
Evidence

Discovery and replay generate local evidence.

View generated evidence:

find evidence -maxdepth 2 -type f -print

Find discovery decisions:

find evidence -name "discovery_decisions.json" -print

View the most recent discovery decisions:

ls -lt evidence/*/discovery_decisions.json

Replay results are stored under directories similar to:

evidence/replay-<SESSION_ID>/

The evidence directory is intentionally excluded from Git.

Current Validation

The project currently passes:

6 passed

Replay has been successfully tested with:

12345 -> $8421.17
54321 -> $1598.42
11111 -> $0.00

Each successful replay returned:

status: success

and:

Deterministic replay completed and checkpoint verified.
Limitations

This is currently a proof-of-concept focused on one local browser application.

Current limitations include:

One local demo application
LLM discovery requires an OpenAI API key
UI changes may require a new discovery run
Locator fallback strategies can be improved
Browser failure recovery can be improved
Human handoff is command-line based
Business outcome handling can be expanded
Artifact versioning can be improved
Replay testing can be expanded
Production authentication and authorization are not implemented
Production monitoring is not implemented
This project is not intended for real banking systems
Future Improvements

Possible next steps:

Improve locator fallback strategies.
Add stronger browser error recovery.
Add artifact versioning.
Expand business outcome handling.
Build a web interface for human handoff.
Add replay metrics and monitoring.
Add more automated tests.
Add support for additional web applications.
Add Docker support.
Add CI/CD with automated testing.
Add stronger audit logging and security controls.
Quick Commands

Setup:

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env

Start application:

python -m app.main

Run tests:

pytest -q

Run discovery:

python -m agent.discover \
  --goal "Look up member 12345 and read their current savings balance" \
  --target "http://127.0.0.1:8000/" \
  --member-id "12345"

Replay:

python -m replay.engine artifacts/member_lookup_savings_balance.json --member-id "12345"

Check Git:

git status

Commit README changes:

git add README.md
git commit -m "Update README"
git push
Project Status

The core workflow is working:

Natural Language Goal
        ↓
LLM Browser Discovery
        ↓
Capability Artifact
        ↓
Deterministic Replay
        ↓
Output Extraction
        ↓
Checkpoint Verification
        ↓
Structured Result
The project demonstrates how an LLM can discover a browser workflow once and convert that workflow into a reusable deterministic capability.
