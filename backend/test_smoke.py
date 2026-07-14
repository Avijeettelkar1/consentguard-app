"""Fast, dependency-light smoke tests for CI (no network, no browser, no DB writes needed).

Covers the pure logic of the auth, watch-scoring, and notification modules.
"""
import jwt

import auth
import watch
import notify


def test_password_hash_roundtrip():
    h = auth._hash_password("supersecret1")
    assert h != "supersecret1"
    assert auth._verify_password("supersecret1", h) is True
    assert auth._verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token = auth._make_token(42, "user@example.com")
    payload = jwt.decode(token, auth.JWT_SECRET, algorithms=[auth.JWT_ALG])
    assert payload["sub"] == "42"
    assert payload["email"] == "user@example.com"


def test_email_validation():
    ok = auth.SignupReq(email="a@b.com", password="password1")
    assert ok.email == "a@b.com"
    for bad in ("not-an-email", "a@b", "@b.com"):
        try:
            auth.SignupReq(email=bad, password="password1")
            assert False, f"expected {bad!r} to be rejected"
        except Exception:
            pass


def test_compliance_score():
    # clean site => perfect A
    assert watch._score(0, 0, True) == (100, "A")
    # any undeclared tracker drops below A
    score, grade = watch._score(1, 0, True)
    assert score < 90 and grade != "A"
    # more trackers => lower score, floored at 5
    assert watch._score(50, 0, True)[0] == 5
    # score is monotonic non-increasing in undeclared count
    assert watch._score(2, 0, True)[0] <= watch._score(1, 0, True)[0]


def test_notify_payload_shapes():
    slack = notify._build_body("https://hooks.slack.com/services/x", "bbc.com", "regression", "msg", 80, 50)
    assert "text" in slack and "bbc.com" in slack["text"]
    generic = notify._build_body("https://example.com/hook", "bbc.com", "regression", "msg", 80, 50)
    assert generic["source"] == "consentguard"
    assert generic["domain"] == "bbc.com"
    assert generic["event"] == "regression"
