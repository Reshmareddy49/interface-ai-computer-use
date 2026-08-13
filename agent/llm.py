from __future__ import annotations

import base64
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """You are a computer-use agent operating a safe local banking demo.
You must choose exactly ONE next action from the allowed actions.
The goal is to complete the user's task, not to explore unnecessarily.
Never invent values. Use only visible controls and the goal's supplied inputs.
Prefer semantic locators: role, label or visible text.Use a stable element id when it is clearly associated with the intended control.Use CSS only as a lastresort.
Use 'finish' when the requested goal has been successfully completed and the requested output is available.

Use 'finish_business_outcome' ONLY when the application reports a legitimate negative or non-success business result that the caller needs to know about, such as 'record not found' or 'account restricted'.

For example, if the requested member is found and the savings balance is visible, choose 'finish' and provide the savings balance as the output.

If member 12345 is found with savings balance $8421.17, this is SUCCESS, not a business outcome.
If blocked by a risky action, choose 'escalate'.
Return JSON only with this shape:
{
  "action": "navigate|fill|click|extract|wait|finish|finish_business_outcome|escalate",
  "locator": {"strategy":"role|label|text|id|css|url|none", "value":"..."},
  "value": "...",
  "output_name": "...",
  "reason": "short reason",
  "checkpoint": "short expected state"
}
For navigate, locator.strategy must be url and locator.value is the URL.
For fill, value is the text to type.
For extract, use this action when the requested output is visible on the page. output_name must be supplied and locator must point directly to the value. Inspect the provided HTML when choosing an extraction locator; prefer an element id or semantic locator that points to the value itself.

If the requested output is visible and can be read, ALWAYS choose 'extract' first. Do not put the extracted value in a 'finish' or 'finish_business_outcome' action.
The state may contain extracted_outputs from actions already performed.
If extracted_outputs contains the requested output and the value is non-empty, the requested output has already been obtained.
Choose 'finish' instead of repeating the extraction.
Never repeat an extract action for an output that is already present in extracted_outputs.

After the extraction has been performed and the goal is complete, choose 'finish'.

Use 'finish_business_outcome' ONLY for legitimate negative business results such as 'record not found' or 'account restricted'. A successfully found member with a visible savings balance is NOT a business outcome.
"""


class LLMError(RuntimeError):
    pass


def _response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return "\n".join(chunks)


def decide(goal: str, state: dict, screenshot_path: str | None = None) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY is required for a genuine discovery run")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    user_content = [
        {"type": "input_text", "text": json.dumps({"goal": goal, "state": state}, ensure_ascii=False)},
    ]
    if screenshot_path:
        with open(screenshot_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        user_content.append({"type": "input_image", "image_url": f"data:image/png;base64,{b64}"})

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }
    r = requests.post(f"{base_url}/responses", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=60)
    if r.status_code >= 400:
        raise LLMError(f"LLM request failed: {r.status_code} {r.text[:500]}")
    text = _response_text(r.json()).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM returned invalid JSON: {text[:500]}") from exc
