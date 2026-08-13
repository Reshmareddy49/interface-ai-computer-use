from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"


def send(session: str, command: dict) -> None:
    path = EVIDENCE / f"discovery-{session}" / "operator_command.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(command, indent=2))
    print(f"Queued operator command: {path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Minimal human handoff console for a live agent session")
    p.add_argument("--session", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--click", help="Visible button/link text to click")
    p.add_argument("--fill-label", help="Input label")
    p.add_argument("--value", help="Value for --fill-label")
    args = p.parse_args()
    if args.resume:
        path = EVIDENCE / f"discovery-{args.session}" / "resume.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"session_id": args.session, "human": "operator", "action": "resume"}, indent=2))
        print("Resume signal sent")
        return
    if args.click:
        send(args.session, {"action": "click", "locator": {"strategy": "text", "value": args.click}, "reason": "Human operator intervention"})
        return
    if args.fill_label:
        send(args.session, {"action": "fill", "locator": {"strategy": "label", "value": args.fill_label}, "value": args.value or "", "reason": "Human operator intervention"})
        return
    p.error("Provide --resume, --click, or --fill-label")


if __name__ == "__main__":
    main()
