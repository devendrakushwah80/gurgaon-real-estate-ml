"""Registration, login, profile, and preference endpoints."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import audit, connect, json_dumps, json_loads
from app.schemas import LoginRequest, PreferenceUpdate, RegisterRequest
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(tags=["auth"])


@router.post("/register", status_code=201)
def register(payload: RegisterRequest) -> dict[str, object]:
    if not any(character.isdigit() for character in payload.password) or not any(
        character.isalpha() for character in payload.password
    ):
        raise HTTPException(status_code=422, detail="Password must contain letters and numbers")
    try:
        with connect() as db:
            cursor = db.execute(
                "INSERT INTO users(email, password_hash, full_name) VALUES (?, ?, ?)",
                (
                    str(payload.email).lower(),
                    hash_password(payload.password),
                    payload.full_name.strip(),
                ),
            )
            user_id = cursor.lastrowid
            role = db.execute("SELECT id FROM roles WHERE name = 'USER'").fetchone()
            db.execute(
                "INSERT INTO user_roles(user_id, role_id) VALUES (?, ?)", (user_id, role["id"])
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    audit(user_id, "user.register", "user", str(user_id))
    return {"id": user_id, "email": str(payload.email).lower(), "roles": ["USER"]}


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, object]:
    with connect() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (str(payload.email),)
        ).fetchone()
        valid = (
            user is not None
            and bool(user["is_active"])
            and verify_password(payload.password, user["password_hash"])
        )
        roles = (
            []
            if not valid
            else [
                row["name"]
                for row in db.execute(
                    "SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = ?",
                    (user["id"],),
                )
            ]
        )
    if not valid:
        audit(None, "auth.login_failed", "user", str(payload.email))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    token = create_access_token(user["id"], user["email"], roles)
    audit(user["id"], "auth.login", "user", str(user["id"]))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "roles": roles,
        },
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return user


@router.get("/preferences")
def get_preferences(user: dict = Depends(get_current_user)) -> dict:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?", (user["id"],)
        ).fetchone()
    if row is None:
        return {
            "user_id": user["id"],
            "preferred_bhk": [],
            "preferred_localities": [],
            "min_trust_score": 0,
        }
    result = dict(row)
    result["preferred_bhk"] = json_loads(result.pop("preferred_bhk_json"), [])
    result["preferred_localities"] = json_loads(result.pop("preferred_localities_json"), [])
    return result


@router.put("/preferences")
def update_preferences(payload: PreferenceUpdate, user: dict = Depends(get_current_user)) -> dict:
    if (
        payload.budget_min is not None
        and payload.budget_max is not None
        and payload.budget_min > payload.budget_max
    ):
        raise HTTPException(status_code=422, detail="budget_min cannot exceed budget_max")
    values = payload.model_dump()
    with connect() as db:
        db.execute(
            """INSERT INTO user_preferences(user_id, budget_min, budget_max, preferred_bhk_json, preferred_localities_json, property_type, min_area_sqft, furnishing, usage, min_trust_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET budget_min=excluded.budget_min, budget_max=excluded.budget_max,
            preferred_bhk_json=excluded.preferred_bhk_json, preferred_localities_json=excluded.preferred_localities_json,
            property_type=excluded.property_type, min_area_sqft=excluded.min_area_sqft, furnishing=excluded.furnishing,
            usage=excluded.usage, min_trust_score=excluded.min_trust_score, updated_at=CURRENT_TIMESTAMP""",
            (
                user["id"],
                values["budget_min"],
                values["budget_max"],
                json_dumps(values["preferred_bhk"]),
                json_dumps(values["preferred_localities"]),
                values["property_type"],
                values["min_area_sqft"],
                values["furnishing"],
                values["usage"],
                values["min_trust_score"],
            ),
        )
    audit(user["id"], "preferences.update", "user", str(user["id"]))
    return get_preferences(user)
