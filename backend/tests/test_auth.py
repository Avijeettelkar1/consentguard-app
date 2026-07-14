"""Auth unit tests — pure logic, no browser / network required."""
import fastapi
from fastapi.security import HTTPAuthorizationCredentials

import auth

auth.init_db()


def _cred(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_password_hashing_roundtrip():
    h = auth._hash_password("supersecret1")
    assert auth._verify_password("supersecret1", h)
    assert not auth._verify_password("wrong", h)


def test_signup_login_and_me():
    r = auth.signup(auth.SignupReq(email="ci@example.com", password="supersecret1", name="CI"))
    assert r["token_type"] == "bearer"
    assert r["user"]["email"] == "ci@example.com"
    token = r["access_token"]

    user = auth.get_current_user(_cred(token))
    assert user["email"] == "ci@example.com"

    r2 = auth.login(auth.LoginReq(email="ci@example.com", password="supersecret1"))
    assert r2["user"]["id"] == r["user"]["id"]


def test_duplicate_signup_blocked():
    auth.signup(auth.SignupReq(email="dup@example.com", password="supersecret1", name="A"))
    try:
        auth.signup(auth.SignupReq(email="dup@example.com", password="supersecret1", name="B"))
        assert False, "duplicate signup should raise"
    except fastapi.HTTPException as e:
        assert e.status_code == 409


def test_wrong_password_rejected():
    auth.signup(auth.SignupReq(email="pw@example.com", password="supersecret1", name="A"))
    try:
        auth.login(auth.LoginReq(email="pw@example.com", password="nope"))
        assert False, "wrong password should raise"
    except fastapi.HTTPException as e:
        assert e.status_code == 401


def test_bad_token_rejected():
    try:
        auth.get_current_user(_cred("garbage.token.value"))
        assert False, "bad token should raise"
    except fastapi.HTTPException as e:
        assert e.status_code == 401
