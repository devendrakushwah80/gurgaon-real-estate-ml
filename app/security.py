"""Authentication and server-side permission dependencies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import connect

JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-me")
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password with salted PBKDF2; plaintext passwords are never stored."""

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt_text), int(rounds))
        return hmac.compare_digest(expected, _unb64(digest_text))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, email: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=TOKEN_MINUTES)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _segment(header)
    encoded_payload = _segment(payload)
    signature = hmac.new(
        JWT_SECRET.encode(), f"{encoded_header}.{encoded_payload}".encode(), hashlib.sha256
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".", 2)
        expected = hmac.new(
            JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            raise ValueError("invalid signature")
        body = json.loads(_unb64(payload))
        if int(body.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired token")
        return body
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = int(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc
    with connect() as db:
        user = db.execute(
            "SELECT id, email, full_name, is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None or not user["is_active"]:
            raise HTTPException(status_code=401, detail="User is inactive or no longer exists")
        roles = [
            row["name"]
            for row in db.execute(
                "SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = ?",
                (user_id,),
            )
        ]
    return {**dict(user), "roles": roles}


def require_permission(permission: str):
    """Return a dependency that checks a named permission server-side."""

    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        with connect() as db:
            row = db.execute(
                """
                SELECT 1 FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = ? AND p.name = ?
                LIMIT 1
                """,
                (user["id"], permission),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return user

    return dependency


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _segment(value: dict[str, Any]) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode())
