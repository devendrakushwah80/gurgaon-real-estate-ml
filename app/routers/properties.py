"""Property discovery, scoring, agent ownership, favourites, and compare APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.database import audit, connect, json_dumps, json_loads
from app.schemas import CompareRequest, PropertyCreate, RecommendationQuery
from app.security import get_current_user, require_permission
from app.services.intelligence import (
    enrich_property,
    rank_properties,
    save_score_snapshot,
    save_score_snapshots,
)
from app.services.property_catalog import find_property, search_catalog

router = APIRouter(tags=["properties"])


@router.get("/user/favorites")
def favorites_preferred_route(user: dict = Depends(get_current_user)) -> dict[str, object]:
    with connect() as db:
        rows = db.execute(
            "SELECT property_id FROM favorites WHERE user_id=? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    properties = []
    for row in rows:
        record = find_property(row["property_id"]) or _stored_property(row["property_id"])
        if record:
            properties.append(enrich_property(record))
    return {"properties": properties}


@router.get("/mine")
def my_properties(user: dict = Depends(require_permission("property.create"))) -> dict[str, object]:
    with connect() as db:
        rows = db.execute(
            "SELECT id FROM properties WHERE owner_id=? AND status='active' ORDER BY updated_at DESC",
            (user["id"],),
        ).fetchall()
    properties = []
    for row in rows:
        record = _stored_property(row["id"])
        if record:
            item = enrich_property(record)
            save_score_snapshot(item)
            properties.append(item)
    return {"properties": properties}


@router.get("")
def list_properties(query: RecommendationQuery = Depends()) -> dict[str, object]:
    records = search_catalog(
        city=query.city,
        budget_min=query.budget_min,
        budget_max=query.budget_max,
        bhk=query.bhk,
        locality=query.locality,
        property_type=query.property_type,
        min_area_sqft=query.min_area_sqft,
        max_area_sqft=query.max_area_sqft,
    )
    ranked = rank_properties(records)[: query.top_n]
    if query.min_trust_score:
        ranked = [item for item in ranked if item["trust"]["score"] >= query.min_trust_score]
    save_score_snapshots(ranked)
    return {
        "properties": ranked,
        "count": len(ranked),
        "image_data_note": "The current source exports do not contain image URLs; cards use an honest placeholder.",
    }


@router.get("/{property_id}")
def property_detail(property_id: str) -> dict[str, object]:
    record = find_property(property_id) or _stored_property(property_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    result = enrich_property(record)
    save_score_snapshot(result)
    return result


@router.post("", status_code=201)
def create_property(
    payload: PropertyCreate, user: dict = Depends(require_permission("property.create"))
) -> dict[str, object]:
    property_id = f"agent-{uuid.uuid4().hex}"
    values = payload.model_dump()
    with connect() as db:
        db.execute(
            """INSERT INTO properties(id, owner_id, source, source_url, title, description, property_type, bhk, locality, sector, city, area_sqft, listing_price, price_per_sqft, furnishing, floor, total_floors, property_age, amenities_json, seller_type, rera_id)
            VALUES (?, ?, 'EstateIQ agent', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                property_id,
                user["id"],
                values["source_url"],
                values["title"],
                values["description"],
                values["property_type"],
                values["bhk"],
                values["locality"],
                values["sector"],
                values["city"],
                values["area_sqft"],
                values["listing_price"],
                values["listing_price"] * 10_000_000 / values["area_sqft"],
                values["furnishing"],
                values["floor"],
                values["total_floors"],
                values["property_age"],
                json_dumps(values["amenities"]),
                values["seller_type"],
                values["rera_id"],
            ),
        )
        for index, image_url in enumerate(values["image_urls"]):
            db.execute(
                "INSERT OR IGNORE INTO property_images(property_id, image_url, is_primary) VALUES (?, ?, ?)",
                (property_id, image_url, int(index == 0)),
            )
    audit(user["id"], "property.create", "property", property_id)
    return property_detail(property_id)


@router.put("/{property_id}")
def update_property(
    property_id: str, payload: PropertyCreate, user: dict = Depends(get_current_user)
) -> dict[str, object]:
    stored = _stored_property(property_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Agent property not found")
    _assert_owner_or_admin(stored, user, "property.update_own", "property.update_any")
    values = payload.model_dump()
    with connect() as db:
        db.execute(
            "UPDATE properties SET source_url=?, title=?, description=?, property_type=?, bhk=?, locality=?, sector=?, city=?, area_sqft=?, listing_price=?, price_per_sqft=?, furnishing=?, floor=?, total_floors=?, property_age=?, amenities_json=?, seller_type=?, rera_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (
                values["source_url"],
                values["title"],
                values["description"],
                values["property_type"],
                values["bhk"],
                values["locality"],
                values["sector"],
                values["city"],
                values["area_sqft"],
                values["listing_price"],
                values["listing_price"] * 10_000_000 / values["area_sqft"],
                values["furnishing"],
                values["floor"],
                values["total_floors"],
                values["property_age"],
                json_dumps(values["amenities"]),
                values["seller_type"],
                values["rera_id"],
                property_id,
            ),
        )
        db.execute("DELETE FROM property_images WHERE property_id = ?", (property_id,))
        for index, image_url in enumerate(values["image_urls"]):
            db.execute(
                "INSERT OR IGNORE INTO property_images(property_id, image_url, is_primary) VALUES (?, ?, ?)",
                (property_id, image_url, int(index == 0)),
            )
    audit(user["id"], "property.update", "property", property_id)
    return property_detail(property_id)


@router.delete("/{property_id}")
def delete_property(property_id: str, user: dict = Depends(get_current_user)) -> dict[str, str]:
    stored = _stored_property(property_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Agent property not found")
    _assert_owner_or_admin(stored, user, "property.delete_own", "property.delete_any")
    with connect() as db:
        db.execute(
            "UPDATE properties SET status='inactive', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (property_id,),
        )
    audit(user["id"], "property.delete", "property", property_id)
    return {"status": "deactivated"}


@router.post("/{property_id}/verification", status_code=201)
def request_verification(
    property_id: str, user: dict = Depends(require_permission("property.update_own"))
) -> dict[str, object]:
    stored = _stored_property(property_id)
    if stored is None or stored.get("owner_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Only the listing owner can request verification"
        )
    with connect() as db:
        db.execute(
            "INSERT INTO listing_verifications(property_id, requested_by) VALUES (?, ?)",
            (property_id, user["id"]),
        )
        db.execute("UPDATE properties SET verification_status='pending' WHERE id=?", (property_id,))
    audit(user["id"], "property.verification_requested", "property", property_id)
    return {"property_id": property_id, "status": "pending"}


@router.post("/{property_id}/favorite")
def add_favorite(property_id: str, user: dict = Depends(get_current_user)) -> dict[str, str]:
    if find_property(property_id) is None and _stored_property(property_id) is None:
        raise HTTPException(status_code=404, detail="Property not found")
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO favorites(user_id, property_id) VALUES (?, ?)",
            (user["id"], property_id),
        )
    audit(user["id"], "favorite.add", "property", property_id)
    return {"status": "saved", "property_id": property_id}


@router.delete("/{property_id}/favorite")
def remove_favorite(property_id: str, user: dict = Depends(get_current_user)) -> dict[str, str]:
    with connect() as db:
        db.execute(
            "DELETE FROM favorites WHERE user_id=? AND property_id=?", (user["id"], property_id)
        )
    audit(user["id"], "favorite.remove", "property", property_id)
    return {"status": "removed", "property_id": property_id}


@router.post("/compare")
def compare(payload: CompareRequest) -> dict[str, object]:
    properties = []
    for property_id in payload.property_ids:
        record = find_property(property_id) or _stored_property(property_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Property not found: {property_id}")
        properties.append(enrich_property(record))
    return {
        "properties": properties,
        "disclaimer": "Comparison highlights data differences; it is not a purchase recommendation.",
    }


def _stored_property(property_id: str) -> dict | None:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM properties WHERE id=? AND status='active'", (property_id,)
        ).fetchone()
        if row is None:
            return None
        images = db.execute(
            "SELECT image_url FROM property_images WHERE property_id=? ORDER BY is_primary DESC, id",
            (property_id,),
        ).fetchall()
    result = dict(row)
    result["amenities"] = json_loads(result.pop("amenities_json"), [])
    result["images"] = [image["image_url"] for image in images]
    result["model_payload"] = {}
    return result


def _assert_owner_or_admin(
    stored: dict, user: dict, own_permission: str, any_permission: str
) -> None:
    if stored.get("owner_id") == user["id"]:
        with connect() as db:
            allowed = db.execute(
                "SELECT 1 FROM user_roles ur JOIN role_permissions rp ON rp.role_id=ur.role_id JOIN permissions p ON p.id=rp.permission_id WHERE ur.user_id=? AND p.name=?",
                (user["id"], own_permission),
            ).fetchone()
        if allowed:
            return
    with connect() as db:
        allowed = db.execute(
            "SELECT 1 FROM user_roles ur JOIN role_permissions rp ON rp.role_id=ur.role_id JOIN permissions p ON p.id=rp.permission_id WHERE ur.user_id=? AND p.name=?",
            (user["id"], any_permission),
        ).fetchone()
    if not allowed:
        raise HTTPException(status_code=403, detail="You do not own this property")
