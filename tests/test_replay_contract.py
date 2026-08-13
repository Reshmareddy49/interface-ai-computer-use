from pathlib import Path
from replay.engine import load_artifact


def test_seed_artifact_is_loadable():
    artifact = load_artifact(str(Path('artifacts/member_lookup_savings_balance.json')))
    assert artifact.capability_id == 'member.lookup.savings_balance'
    assert artifact.inputs['member_id']['type'] == 'string'
    assert artifact.checkpoint.expected == 'Member record loaded successfully'
