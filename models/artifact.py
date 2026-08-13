from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


ActionType = Literal["navigate", "fill", "click", "extract", "wait", "assert"]
RiskClass = Literal["safe", "reversible", "risky", "irreversible"]


class Locator(BaseModel):
    strategy: Literal["role", "label", "text","id",  "css", "url", "none"]
    value: str
    fallbacks: list["Locator"] = Field(default_factory=list)
    description: str = ""


class ActionStep(BaseModel):
    id: str
    action: ActionType
    target: Locator | None = None
    value_template: str | None = None
    output_name: str | None = None
    output_type: str | None = None
    risk: RiskClass = "safe"
    timeout_ms: int = 10000
    retryable: bool = False
    rationale: str = ""


class Checkpoint(BaseModel):
    type: Literal["url", "text", "element", "value"]
    locator: Locator | None = None
    expected: str
    description: str


class CapabilityArtifact(BaseModel):
    schema_version: str = "1.0"
    capability_id: str
    name: str
    description: str
    surface: Literal["browser"] = "browser"
    target_origin: str
    version: int = 1
    inputs: dict[str, dict[str, Any]]
    outputs: dict[str, dict[str, Any]]
    steps: list[ActionStep]
    checkpoint: Checkpoint
    allowed_actions: list[ActionType]
    approval_state: Literal["draft", "approved"] = "approved"
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
