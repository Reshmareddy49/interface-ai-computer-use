from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from agent.policy import assert_action_allowed, assert_url_allowed


class BrowserController:
    def __init__(self, page: Page, evidence_dir: Path):
        self.page = page
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.event_log: list[dict[str, Any]] = []

    def observe(self, label: str) -> dict[str, Any]:
        screenshot = self.evidence_dir / f"{label}.png"
        self.page.screenshot(path=str(screenshot), full_page=True)
        state = {
            "url": self.page.url,
            "title": self.page.title(),
            "visible_text": self.page.locator("body").inner_text(timeout=5000)[:12000],
            "html": self.page.locator("body").inner_html(timeout=5000)[:20000],
            "controls": self.page.locator("input,button,select,a").evaluate_all("els => els.map(e => ({tag:e.tagName, text:(e.innerText||e.value||'').trim(), aria:e.getAttribute('aria-label'), name:e.getAttribute('name'), id:e.id, type:e.getAttribute('type')}))"),
            "screenshot": str(screenshot),
        }
        return state

    def locator(self, spec: dict[str, Any]):
        strategy, value = spec.get("strategy"), spec.get("value", "")
        if strategy == "role":
            # Expected syntax: button:Search or textbox:Member number
            role, _, name = value.partition(":")
            if name:
                return self.page.get_by_role(role, name=name, exact=True)
            return self.page.get_by_role(role)
        if strategy == "label":
            return self.page.get_by_label(value, exact=True)
        if strategy == "text":
            return self.page.get_by_text(value, exact=True)
        if strategy == "id":
            return self.page.locator(f"#{value}")
        if strategy == "css":
            return self.page.locator(value)
        if strategy == "url":
            return None
        raise ValueError(f"unsupported locator strategy {strategy}")

    def act(self, action: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
        kind = action.get("action")
        if kind in {"finish", "finish_business_outcome", "escalate"}:
            return {"status": kind}
        assert_action_allowed(kind)
        spec = action.get("locator") or {"strategy": "none", "value": ""}
        value = action.get("value")
        if isinstance(value, str):
            for k, v in inputs.items():
                value = value.replace("{{" + k + "}}", str(v))
        event = {"action": kind, "locator": spec, "value": value, "reason": action.get("reason", ""), "url_before": self.page.url}
        try:
            if kind == "navigate":
                url = spec.get("value", "")
                assert_url_allowed(url)
                self.page.goto(url, wait_until="domcontentloaded")
            elif kind == "fill":
                self.locator(spec).fill(str(value or ""))
            elif kind == "click":
                self.locator(spec).click()
                self.page.wait_for_load_state("domcontentloaded", timeout=8000)
            elif kind == "wait":
                self.page.wait_for_timeout(int(value or 500))
            elif kind == "assert":
                expected = str(value or action.get("checkpoint", ""))
                if expected not in self.page.locator("body").inner_text():
                    raise AssertionError(f"expected text not present: {expected}")
            elif kind == "extract":
                loc = self.locator(spec)
                result = loc.inner_text()
                event["extracted"] = result
                self.event_log.append(event)
                return {"status": "ok", "value": result}
            event["url_after"] = self.page.url
            self.event_log.append(event)
            return {"status": "ok"}
        except (PlaywrightTimeoutError, AssertionError, Exception) as exc:
            event["error"] = str(exc)
            event["url_after"] = self.page.url
            self.event_log.append(event)
            raise
