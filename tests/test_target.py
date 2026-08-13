from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_member_found():
    r = client.post('/search', data={'member_number': '12345'})
    assert r.status_code == 200
    assert 'Savings balance' in r.text
    assert '$8421.17' in r.text


def test_member_not_found_is_business_outcome():
    r = client.post('/search', data={'member_number': '99999'})
    assert r.status_code == 200
    assert 'Record not found' in r.text
