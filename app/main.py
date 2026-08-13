from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)

app = FastAPI(title="Interface Computer-Use Automation Demo", version="1.0.0")

MEMBERS = {
    "12345": {"name": "Jordan Lee", "savings_balance": "8421.17", "status": "Active"},
    "54321": {"name": "Taylor Morgan", "savings_balance": "1598.42", "status": "Active"},
    "11111": {"name": "Casey Patel", "savings_balance": "0.00", "status": "Restricted"},
}

SESSIONS: dict[str, dict[str, Any]] = {}


class ActionRequest(BaseModel):
    session_id: str
    action: str
    value: str | None = None


class ResumeRequest(BaseModel):
    session_id: str
    note: str = "Human completed intervention"


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>{title}</title>
<style>
body{{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;color:#1f2937}}
.header{{background:#18324b;color:#fff;padding:18px 28px}}
.wrap{{max-width:920px;margin:30px auto;background:#fff;padding:28px;border-radius:10px;box-shadow:0 3px 14px #0001}}
label{{display:block;font-weight:700;margin:14px 0 6px}}
input,button,select{{font-size:16px;padding:10px;border:1px solid #aab4bf;border-radius:5px}}
button{{background:#18324b;color:white;cursor:pointer}}
button.secondary{{background:#64748b}}
.alert{{padding:12px;border-radius:6px;margin:16px 0;background:#fff4cc}}
.error{{background:#fee2e2;color:#991b1b}}
.success{{background:#dcfce7;color:#166534}}
table{{width:100%;border-collapse:collapse;margin-top:18px}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}
.small{{color:#667085;font-size:13px}}
</style></head><body><div class='header'><strong>Legacy Member Servicing Console</strong></div><div class='wrap'>{body}</div></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return page("Member Search", """
<h1>Member Search</h1>
<p class='small'>Demo surface: intentionally plain server-rendered HTML with table-style layout and no test IDs.</p>
<form method='post' action='/search'>
<label for='member_number'>Member number</label>
<input id='member_number' name='member_number' autocomplete='off' />
<button type='submit'>Search</button>
</form>
""")


@app.post("/search", response_class=HTMLResponse)
async def search(request: Request) -> str:
    form = await request.form()
    member_number = str(form.get("member_number", "")).strip()
    if not member_number:
        return page("Validation Error", """
<h1>Validation error</h1><div class='alert error'>Member number is required.</div>
<a href='/'>Return to search</a>
""")
    if member_number == "TIMEOUT":
        import time
        time.sleep(3)
    member = MEMBERS.get(member_number)
    if not member:
        return page("Member Not Found", f"""
<h1>Member lookup</h1>
<div class='alert error' role='alert'>Record not found for member {member_number}.</div>
<a href='/'>Return to search</a>
""")
    session_id = uuid.uuid4().hex
    SESSIONS[session_id] = {"member_number": member_number, "state": "detail"}
    return page("Member Detail", f"""
<h1>Member detail</h1>
<table aria-label='Member detail'>
<tr><th>Member number</th><td>{member_number}</td></tr>
<tr><th>Member name</th><td>{member['name']}</td></tr>
<tr><th>Account status</th><td>{member['status']}</td></tr>
<tr><th>Savings balance</th><td id='savings-balance'>${member['savings_balance']}</td></tr>
</table>
<div class='alert success' role='status'>Member record loaded successfully.</div>
<form method='get' action='/'><button class='secondary' type='submit'>Back to search</button></form>
""")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/operator/action")
def operator_action(req: ActionRequest) -> JSONResponse:
    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(404, "session not found")
    # Minimal operator seam: commands target the same browser session conceptually.
    # The real browser controller stores the live session id and executes Playwright actions.
    if req.action not in {"resume", "acknowledge", "note"}:
        raise HTTPException(400, "unsupported operator action")
    session.setdefault("operator_actions", []).append({"action": req.action, "value": req.value, "at": datetime.now(timezone.utc).isoformat()})
    return JSONResponse({"ok": True, "session_id": req.session_id, "action": req.action})


@app.post("/api/operator/resume")
def operator_resume(req: ResumeRequest) -> JSONResponse:
    session = SESSIONS.setdefault(req.session_id, {})
    session["human_control"] = False
    session["resume_note"] = req.note
    return JSONResponse({"ok": True, "session_id": req.session_id, "human_control": False})
