"""App-level smoke tests via TestClient (MOCK mode, no browser)."""
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_scan_mock():
    r = client.post("/scan", json={"url": "example.org"})
    assert r.status_code == 200
    assert "scan" in r.json()


def test_auth_and_protected_routes():
    # signup issues a token
    r = client.post("/auth/signup", json={"email": "app@example.com", "password": "supersecret1", "name": "App"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}

    # protected routes reject without a token
    assert client.get("/scans").status_code in (401, 403)
    assert client.get("/watch").status_code in (401, 403)

    # and accept with one
    assert client.get("/scans", headers=hdr).status_code == 200
    assert client.get("/watch", headers=hdr).status_code == 200
    assert client.get("/auth/me", headers=hdr).status_code == 200


def test_webhook_validation():
    r = client.post("/auth/signup", json={"email": "wh@example.com", "password": "supersecret1", "name": "W"})
    hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # non-https webhook is rejected
    bad = client.put("/settings/webhook", json={"url": "http://insecure.example.com"}, headers=hdr)
    assert bad.status_code == 422
