from models.artifact import CapabilityArtifact


def test_artifact_schema_accepts_typed_capability():
    artifact = CapabilityArtifact.model_validate({
        "capability_id": "demo.lookup",
        "name": "Demo lookup",
        "description": "Look up a record",
        "target_origin": "http://127.0.0.1:8000",
        "inputs": {"member_id": {"type": "string", "required": True}},
        "outputs": {"balance": {"type": "string"}},
        "steps": [],
        "checkpoint": {"type": "text", "expected": "OK", "description": "done"},
        "allowed_actions": ["navigate", "fill", "click", "extract", "wait", "assert"],
        "created_at": "2026-08-13T00:00:00Z",
    })
    assert artifact.schema_version == "1.0"
