"""Create or promote the first local EstateIQ administrator.

Usage: ``python -m app.bootstrap_admin admin@example.com``. The password is
requested interactively and is never placed in shell history or source files.
"""

from __future__ import annotations

import getpass
import sys

from app.database import connect, init_db
from app.security import hash_password


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.bootstrap_admin admin@example.com")
    email = sys.argv[1].strip().lower()
    password = getpass.getpass("Admin password (8+ chars): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters")
    init_db()
    with connect() as db:
        user = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if user is None:
            cursor = db.execute(
                "INSERT INTO users(email, password_hash, full_name) VALUES (?, ?, ?)",
                (email, hash_password(password), "EstateIQ Admin"),
            )
            user_id = cursor.lastrowid
        else:
            user_id = user["id"]
            db.execute(
                "UPDATE users SET password_hash=?, is_active=1 WHERE id=?",
                (hash_password(password), user_id),
            )
        role = db.execute("SELECT id FROM roles WHERE name='ADMIN'").fetchone()
        db.execute(
            "INSERT OR IGNORE INTO user_roles(user_id, role_id) VALUES (?, ?)",
            (user_id, role["id"]),
        )
    print(f"Admin account ready: {email}")


if __name__ == "__main__":
    main()
