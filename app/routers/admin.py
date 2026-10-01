"""Administrative moderation and platform overview APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.database import audit, connect
from app.security import require_permission

router = APIRouter(tags=["admin"])


@router.get("/overview")
def overview(user: dict = Depends(require_permission("analytics.view_admin"))) -> dict[str, object]:
    with connect() as db:
        counts = {
            "total_users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "agent_listings": db.execute(
                "SELECT COUNT(*) FROM properties WHERE owner_id IS NOT NULL"
            ).fetchone()[0],
            "active_listings": db.execute(
                "SELECT COUNT(*) FROM properties WHERE status='active'"
            ).fetchone()[0],
            "pending_verifications": db.execute(
                "SELECT COUNT(*) FROM listing_verifications WHERE status='pending'"
            ).fetchone()[0],
            "audit_events": db.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0],
        }
        low_trust = db.execute(
            "SELECT COUNT(*) FROM listing_trust_scores WHERE total_score < 60"
        ).fetchone()[0]
    counts["low_trust_properties"] = low_trust
    return counts


@router.get("/users")
def users(user: dict = Depends(require_permission("user.manage"))) -> dict[str, object]:
    with connect() as db:
        rows = db.execute(
            "SELECT id, email, full_name, is_active, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            roles = [
                item["name"]
                for item in db.execute(
                    "SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id=r.id WHERE ur.user_id=?",
                    (row["id"],),
                )
            ]
            result.append({**dict(row), "roles": roles})
    return {"users": result}


@router.post("/users/{user_id}/roles")
def set_role(
    user_id: int, role: str, admin_user: dict = Depends(require_permission("role.manage"))
) -> dict[str, object]:
    role = role.upper().strip()
    if role not in {"USER", "AGENT", "ADMIN"}:
        raise HTTPException(status_code=422, detail="role must be USER, AGENT, or ADMIN")
    with connect() as db:
        if db.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail="User not found")
        role_row = db.execute("SELECT id FROM roles WHERE name=?", (role,)).fetchone()
        db.execute(
            "INSERT OR IGNORE INTO user_roles(user_id, role_id) VALUES (?, ?)",
            (user_id, role_row["id"]),
        )
    audit(admin_user["id"], "role.change", "user", str(user_id), {"role": role})
    return {"user_id": user_id, "role": role}


@router.get("/properties/pending")
def pending_properties(
    user: dict = Depends(require_permission("listing.approve")),
) -> dict[str, object]:
    with connect() as db:
        rows = db.execute(
            "SELECT id, owner_id, title, locality, listing_price, verification_status, updated_at FROM properties WHERE verification_status='pending' OR status='pending' ORDER BY updated_at DESC"
        ).fetchall()
    return {"properties": [dict(row) for row in rows]}


@router.post("/properties/{property_id}/moderate")
def moderate(
    property_id: str, action: str, user: dict = Depends(require_permission("listing.approve"))
) -> dict[str, str]:
    allowed = {"approve": "active", "reject": "rejected", "deactivate": "inactive"}
    if action not in allowed:
        raise HTTPException(status_code=422, detail="action must be approve, reject, or deactivate")
    with connect() as db:
        cursor = db.execute(
            "UPDATE properties SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (allowed[action], property_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Property not found")
        db.execute(
            "UPDATE listing_verifications SET status=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP WHERE property_id=? AND status='pending'",
            (action, user["id"], property_id),
        )
    audit(user["id"], f"listing.{action}", "property", property_id)
    return {"property_id": property_id, "status": allowed[action]}
