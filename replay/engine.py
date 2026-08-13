from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from agent.browser import BrowserController
from agent.policy import assert_action_allowed, assert_url_allowed
from models.artifact import CapabilityArtifact
from models.result import ReplayResult

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"


class ReplayEngine:
    def __init__(self, artifact: CapabilityArtifact):
        self.artifact = artifact

    def _render(self, template: str | None, inputs: dict[str, Any]) -> str:
        value = template or ""
        for k, v in inputs.items():
            value = value.replace("{{" + k + "}}", str(v))
        return value

    def run(self, inputs: dict[str, Any]) -> ReplayResult:
        run_id = f"replay-{int(time.time())}"
        evidence_dir = EVIDENCE / run_id
        evidence_dir.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch( headless=True, args=["--no-sandbox"]
)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            controller = BrowserController(page, evidence_dir)
            outputs: dict[str, Any] = {}
            try:
                for step in self.artifact.steps:
                    assert_action_allowed(step.action)
                    target = step.target.model_dump() if step.target else {"strategy": "none", "value": ""}
                    # Deterministic executor: artifact is the source of decisions. No LLM calls.
                    if step.action == "navigate":
                        url = target["value"]
                        assert_url_allowed(url)
                        page.goto(url, wait_until="domcontentloaded", timeout=step.timeout_ms)
                    elif step.action == "fill":
                        controller.locator(target).fill(self._render(step.value_template, inputs), timeout=step.timeout_ms)
                    elif step.action == "click":
                        try:
                            controller.locator(target).click(timeout=step.timeout_ms)
                        except Exception as first:
                            recovered = False
                            for fallback in target.get("fallbacks", []):
                                try:
                                    controller.locator(fallback.model_dump() if hasattr(fallback, "model_dump") else fallback).click(timeout=step.timeout_ms)
                                    recovered = True
                                    break
                                except Exception:
                                    pass
                            if not recovered:
                                raise first
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=step.timeout_ms)
                        except PlaywrightTimeoutError:
                            pass
                    elif step.action == "wait":
                        page.wait_for_timeout(int(self._render(step.value_template, inputs) or 500))
                    elif step.action == "assert":
                        expected = self._render(step.value_template, inputs)
                        body = page.locator("body").inner_text(timeout=step.timeout_ms)
                        if expected not in body:
                            raise AssertionError(f"checkpoint text missing: {expected}")
                    elif step.action == "extract":
                        value = controller.locator(target).inner_text(timeout=step.timeout_ms)
                        outputs[step.output_name or "value"] = value

                    body = page.locator("body").inner_text(timeout=step.timeout_ms)
                    if "Record not found for member" in body:
                        match = re.search(r"Record not found for member\s+([\w-]+)", body)
                        browser.close()
                        result = ReplayResult(status="business_outcome", capability_id=self.artifact.capability_id, business_outcome="member_not_found", outputs={}, failed_step=step.id, observed=match.group(0) if match else body[:200], message="The member does not exist; this is an expected business outcome.", evidence_path=str(evidence_dir))
                        (evidence_dir / "result.json").write_text(result.model_dump_json(indent=2))
                        return result
                    if "Validation error" in body:
                        browser.close()
                        result = ReplayResult(status="business_outcome", capability_id=self.artifact.capability_id, business_outcome="validation_error", failed_step=step.id, observed="Validation error", message="Input validation failed in the target application.", evidence_path=str(evidence_dir))
                        (evidence_dir / "result.json").write_text(result.model_dump_json(indent=2))
                        return result

                checkpoint = self.artifact.checkpoint
                if checkpoint.type == "text":
                    observed = page.locator("body").inner_text()
                    if checkpoint.expected not in observed:
                        raise AssertionError(f"checkpoint failed: expected {checkpoint.expected}")
                page.screenshot(path=str(evidence_dir / "success.png"), full_page=True)
                browser.close()
                result = ReplayResult(status="success", capability_id=self.artifact.capability_id, outputs=outputs, evidence_path=str(evidence_dir), message="Deterministic replay completed and checkpoint verified.")
                (evidence_dir / "result.json").write_text(result.model_dump_json(indent=2))
                return result
            except PermissionError as exc:
                page.screenshot(path=str(evidence_dir / "failure.png"), full_page=True)
                browser.close()
                result = ReplayResult(status="failure", capability_id=self.artifact.capability_id, error_code="POLICY_BLOCK", message=str(exc), evidence_path=str(evidence_dir))
                (evidence_dir / "result.json").write_text(result.model_dump_json(indent=2))
                return result
            except Exception as exc:
                page.screenshot(path=str(evidence_dir / "failure.png"), full_page=True)
                browser.close()
                result = ReplayResult(status="failure", capability_id=self.artifact.capability_id, error_code="REPLAY_ERROR", message=str(exc), evidence_path=str(evidence_dir))
                (evidence_dir / "result.json").write_text(result.model_dump_json(indent=2))
                return result


def load_artifact(path: str) -> CapabilityArtifact:
    return CapabilityArtifact.model_validate(json.loads(Path(path).read_text()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    parser.add_argument("--member-id", default="12345")
    args = parser.parse_args()
    artifact = load_artifact(args.artifact)
    result = ReplayEngine(artifact).run({"member_id": args.member_id})
    print(result.model_dump_json(indent=2))
