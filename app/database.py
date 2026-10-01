"""Small SQLite persistence layer for EstateIQ application state.

The ML CSVs remain immutable source data. SQLite stores users, preferences,
agent-created listings, scores, favourites, moderation state, and audit data.
Keeping this layer dependency-light makes local development and tests simple;
the schema can be moved to PostgreSQL behind the same repository boundary.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "data" / "estateiq.db")))

PERMISSIONS = (
    "property.read",
    "property.create",
    "property.update_own",
    "property.delete_own",
    "property.update_any",
    "property.delete_any",
    "property.verify",
    "user.manage",
    "role.manage",
    "analytics.view_admin",
    "listing.approve",
)

ROLE_PERMISSIONS = {
    "USER": {"property.read"},
    "AGENT": {"property.read", "property.create", "property.update_own", "property.delete_own"},
    "ADMIN": set(PERMISSIONS),
}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Yield a configured connection and commit successful transactions."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    """Create the application schema and seed stable roles/permissions."""

    with connect() as db:
        db.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            );
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role_id, permission_id)
            );
            CREATE TABLE IF NOT EXISTS properties (
                id TEXT PRIMARY KEY,
                owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                source TEXT NOT NULL DEFAULT 'EstateIQ',
                source_listing_id TEXT,
                source_url TEXT,
                title TEXT NOT NULL,
                description TEXT,
                property_type TEXT,
                bhk INTEGER,
                locality TEXT,
                sector TEXT,
                city TEXT NOT NULL DEFAULT 'Gurgaon',
                latitude REAL,
                longitude REAL,
                area_sqft REAL,
                listing_price REAL,
                price_per_sqft REAL,
                furnishing TEXT,
                floor TEXT,
                total_floors INTEGER,
                property_age TEXT,
                amenities_json TEXT NOT NULL DEFAULT '[]',
                seller_type TEXT,
                rera_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                verification_status TEXT NOT NULL DEFAULT 'not_requested',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS property_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
                image_url TEXT NOT NULL,
                is_primary INTEGER NOT NULL DEFAULT 0,
                UNIQUE(property_id, image_url)
            );
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                property_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, property_id)
            );
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                budget_min REAL,
                budget_max REAL,
                preferred_bhk_json TEXT NOT NULL DEFAULT '[]',
                preferred_localities_json TEXT NOT NULL DEFAULT '[]',
                property_type TEXT,
                min_area_sqft REAL,
                furnishing TEXT,
                usage TEXT,
                min_trust_score REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS listing_trust_scores (
                property_id TEXT PRIMARY KEY,
                total_score REAL NOT NULL,
                breakdown_json TEXT NOT NULL,
                positive_signals_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS investment_scores (
                property_id TEXT PRIMARY KEY,
                total_score REAL NOT NULL,
                breakdown_json TEXT NOT NULL,
                positive_signals_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS property_predictions (
                property_id TEXT PRIMARY KEY,
                listing_price REAL,
                fair_value REAL,
                difference_value REAL,
                difference_percent REAL,
                classification TEXT,
                calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS recommendation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                property_id TEXT NOT NULL,
                score REAL NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS listing_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id TEXT NOT NULL,
                requested_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS current_listings (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_listing_id TEXT,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                property_type TEXT,
                bhk INTEGER,
                locality TEXT,
                sector TEXT,
                city TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                area_sqft REAL,
                listing_price REAL,
                price_per_sqft REAL,
                furnishing TEXT,
                floor TEXT,
                total_floors INTEGER,
                property_age TEXT,
                amenities_json TEXT NOT NULL DEFAULT '[]',
                seller_type TEXT,
                verified_seller INTEGER,
                rera_id TEXT,
                listing_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                status_reason TEXT,
                last_verified_at TEXT,
                project_name TEXT,
                image_url TEXT,
                image_source TEXT,
                image_verified_at TEXT,
                image_match_confidence REAL,
                image_urls_json TEXT NOT NULL DEFAULT '[]',
                posted_date TEXT,
                updated_date TEXT,
                ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                raw_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_current_listings_city_status ON current_listings(city, listing_status);
            CREATE INDEX IF NOT EXISTS idx_current_listings_source_id ON current_listings(source, source_listing_id);
            CREATE TABLE IF NOT EXISTS current_listing_images (
                listing_id TEXT NOT NULL REFERENCES current_listings(id) ON DELETE CASCADE,
                image_url TEXT NOT NULL,
                image_source TEXT,
                image_verified_at TEXT,
                image_match_confidence REAL,
                PRIMARY KEY (listing_id, image_url)
            );
            """
        )
        _migrate_properties(db)
        for role_name in ROLE_PERMISSIONS:
            db.execute("INSERT OR IGNORE INTO roles(name) VALUES (?)", (role_name,))
        for permission in PERMISSIONS:
            db.execute("INSERT OR IGNORE INTO permissions(name) VALUES (?)", (permission,))
        for role_name, permissions in ROLE_PERMISSIONS.items():
            role = db.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            for permission in permissions:
                permission_row = db.execute(
                    "SELECT id FROM permissions WHERE name = ?", (permission,)
                ).fetchone()
                db.execute(
                    "INSERT OR IGNORE INTO role_permissions(role_id, permission_id) VALUES (?, ?)",
                    (role["id"], permission_row["id"]),
                )


def _migrate_properties(db: sqlite3.Connection) -> None:
    """Add non-destructive metadata columns to databases created by older builds."""

    existing = {row["name"] for row in db.execute("PRAGMA table_info(properties)").fetchall()}
    columns = {
        "listing_status": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        "status_reason": "TEXT",
        "last_verified_at": "TEXT",
        "project_name": "TEXT",
        "image_source": "TEXT",
        "image_verified_at": "TEXT",
        "image_match_confidence": "REAL",
        "posted_date": "TEXT",
        "updated_date_source": "TEXT",
        "ingested_at": "TEXT",
        "possession_status": "TEXT",
        "facing": "TEXT",
        "carpet_area_sqft": "REAL",
    }
    for name, definition in columns.items():
        if name not in existing:
            db.execute(f"ALTER TABLE properties ADD COLUMN {name} {definition}")
    db.execute("UPDATE properties SET city='gurgaon' WHERE lower(city) IN ('gurgaon', 'gurugram')")
    current_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(current_listings)").fetchall()
    }
    if "image_urls_json" not in current_columns:
        db.execute(
            "ALTER TABLE current_listings ADD COLUMN image_urls_json TEXT NOT NULL DEFAULT '[]'"
        )
    if "verified_seller" not in current_columns:
        db.execute("ALTER TABLE current_listings ADD COLUMN verified_seller INTEGER")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def audit(
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO audit_logs(user_id, action, entity_type, entity_id, metadata_json) VALUES (?, ?, ?, ?, ?)",
            (user_id, action, entity_type, entity_id, json_dumps(metadata or {})),
        )


init_db()
