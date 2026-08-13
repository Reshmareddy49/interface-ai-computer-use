from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class ReplayResult(BaseModel):
    status: Literal["success", "business_outcome", "recoverable", "failure", "escalated"]
    capability_id: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    business_outcome: str | None = None
    error_code: str | None = None
    failed_step: str | None = None
    expected: str | None = None
    observed: str | None = None
    evidence_path: str | None = None
    message: str = ""
