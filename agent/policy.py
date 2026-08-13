from __future__ import annotations
import os
from urllib.parse import urlparse

SAFE_ACTIONS = {"navigate", "fill", "click", "extract", "wait", "assert"}
RISKY_ACTIONS = {"submit_payment", "delete", "transfer", "create_account"}


def allowed_origins() -> set[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    return {x.strip().rstrip("/") for x in raw.split(",") if x.strip()}


def assert_url_allowed(url: str) -> None:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if origin not in allowed_origins():
        raise PermissionError(f"origin not allowlisted: {origin}")


def assert_action_allowed(action: str) -> None:
    if action not in SAFE_ACTIONS:
        raise PermissionError(f"action type is not allowlisted: {action}")
