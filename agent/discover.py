from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from agent.browser import BrowserController
from agent.llm import decide
from models.artifact import ActionStep, CapabilityArtifact, Checkpoint, Locator

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
ARTIFACTS = ROOT / "artifacts"
EVIDENCE.mkdir(exist_ok=True)
ARTIFACTS.mkdir(exist_ok=True)


def locator_from(raw: dict) -> Locator:
    return Locator(strategy=raw.get("strategy", "none"), value=raw.get("value", ""), description=raw.get("description", ""))


def build_artifact(goal: str, target: str, actions: list[dict], created_at: str) -> CapabilityArtifact:
    steps: list[ActionStep] = []
    outputs: dict = {}
    steps.append(
        ActionStep(
            id="step-00",
            action="navigate",
            target=Locator(
                strategy="url",
                value=target,
                description="Local demo application",
            ),
            value_template=None,
            output_name=None,
            output_type=None,
            risk="safe",
            timeout_ms=10000,
            retryable=False,
            rationale="Open the target application before replaying the recorded workflow",
        )
    )
    for i, action in enumerate(actions, 1):
        kind = action.get("action")
        if kind not in {"navigate", "fill", "click", "extract", "wait", "assert"}:
            continue
        output_name = action.get("output_name") if kind == "extract" else None
        if output_name:
            outputs[output_name] = {"type": "string", "description": f"Value extracted from {action.get('locator', {}).get('value', '')}"}
        steps.append(ActionStep(
            id=f"step-{i:02d}",
            action=kind,
            target=locator_from(action.get("locator") or {"strategy":"none","value":""}) if kind != "navigate" else locator_from(action.get("locator") or {"strategy":"url","value":target}),
            value_template=(
            "{{member_id}}"
            if kind == "fill" and action.get("locator", {}).get("value") == "member_number"
            else action.get("value")),
            output_name=output_name,
            output_type="string" if output_name else None,
            risk="safe",
            retryable=kind in {"wait", "click"},
            rationale=action.get("reason", "LLM discovery decision"),
        ))
    artifact = CapabilityArtifact(
        capability_id="member.lookup.savings_balance",
        name="Look up member savings balance",
        description=goal,
        target_origin=f"{urlparse(target).scheme}://{urlparse(target).netloc}",
        inputs={"member_id": {"type": "string", "required": True, "description": "Member number"}},
        outputs=outputs or {"savings_balance": {"type": "string", "description": "Current savings balance"}},
        steps=steps,
        checkpoint=Checkpoint(type="text", locator=Locator(strategy="text", value="Member record loaded successfully"), expected="Member record loaded successfully", description="Member detail page loaded successfully"),
        allowed_actions=["navigate", "fill", "click", "extract", "wait", "assert"],
        created_at=created_at,
        metadata={"discovery_goal": goal, "recorded_from": "genuine LLM-driven run", "surface_notes": "server-rendered browser UI"},
    )
    return artifact


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def wait_for_human(evidence_dir: Path, session_id: str, page, controller: BrowserController) -> None:
    request = {
        "session_id": session_id,
        "status": "waiting_for_human",
        "current_url": page.url,
        "reason": "Agent could not safely decide the next action.",
        "screenshot": str(evidence_dir / "handoff.png"),
        "allowed_operator_actions": ["click", "fill", "navigate", "resume"],
    }
    page.screenshot(path=str(evidence_dir / "handoff.png"), full_page=True)
    write_json(evidence_dir / "intervention.json", request)
    print(f"HUMAN_HANDOFF session={session_id}")
    print(f"Operator: python -m agent.operator --session {session_id}")
    deadline = time.time() + int(os.getenv("AGENT_TIMEOUT_SECONDS", "90"))
    resume_file = evidence_dir / "resume.json"
    while time.time() < deadline:
        command_file = evidence_dir / "operator_command.json"
        if command_file.exists():
            cmd = json.loads(command_file.read_text())
            command_file.unlink()
            controller.act(cmd, {})
            request["last_operator_command"] = cmd
            write_json(evidence_dir / "intervention.json", request)
        if resume_file.exists():
            request["status"] = "resumed"
            write_json(evidence_dir / "intervention.json", request)
            resume_file.unlink()
            return
        time.sleep(0.5)
    raise TimeoutError("human intervention timed out")


def run(goal: str, target: str, member_id: str) -> Path:
    session_id = uuid.uuid4().hex
    evidence_dir = EVIDENCE / f"discovery-{session_id}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    actions: list[dict] = []
    max_steps = int(os.getenv("MAX_AGENT_STEPS", "12"))
    extracted_outputs: dict[str, Any] = {}

    with sync_playwright()as p: 
        browser = p.chromium.launch( headless=True, args=["--no-sandbox"],)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        controller = BrowserController(page, evidence_dir)
        page.goto(target, wait_until="domcontentloaded")
        for step in range(max_steps):
            state = controller.observe(f"step-{step:02d}")
            state["inputs"] = {"member_id": member_id}
            state["extracted_outputs"] = extracted_outputs

            decision = decide(goal, state, state["screenshot"])
            decision["step_number"] = step + 1

            actions.append(decision)
            write_json(
                evidence_dir / "discovery_decisions.json",
                actions,
            )

            kind = decision.get("action")

            if kind == "finish":
                break

            if kind == "finish_business_outcome":
                write_json(
                    evidence_dir / "discovery_result.json",
                    {
                        "status": "business_outcome",
                        "decision": decision,
                        "actions": actions,
                    },
                )
                browser.close()
                raise RuntimeError(
                    "discovery ended in a business outcome; "
                    "use a valid member for artifact creation"
                )

            if kind == "escalate":
                wait_for_human(
                    evidence_dir,
                    session_id,
                    page,
                    controller,
                )
                continue

            try:
                result = controller.act(
                    decision,
                    {"member_id": member_id},
                )

                if kind == "extract" and result.get("status") == "ok":
                    output_name = decision.get("output_name")

                    if output_name:
                        extracted_outputs[output_name] = result.get("value")

            except Exception as exc:
                write_json(
                    evidence_dir / "discovery_result.json",
                    {
                        "status": "failure",
                        "error": str(exc),
                        "decision": decision,
                        "events": controller.event_log,
                    },
                )
                raise

        else:
            raise RuntimeError("max agent steps reached")
        write_json(evidence_dir / "discovery_events.json", controller.event_log)
        write_json(evidence_dir / "discovery_result.json", {"status": "success", "actions": actions, "events": controller.event_log, "session_id": session_id})
        artifact = build_artifact(goal, target, actions, created_at)
        artifact_path = ARTIFACTS / f"{artifact.capability_id.replace('.', '_')}.json"
        write_json(artifact_path, artifact.model_dump(mode="json"))
        browser.close()
    return artifact_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="Look up member {{member_id}} and read their current savings balance")
    parser.add_argument("--target", default="http://127.0.0.1:8000/")
    parser.add_argument("--member-id", default="12345")
    args = parser.parse_args()
    path = run(args.goal, args.target, args.member_id)
    print(path)
