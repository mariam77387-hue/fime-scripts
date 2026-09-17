import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    session,
    send_from_directory,
)

from werkzeug.security import check_password_hash


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fime.db"


# =========================================================
# FLASK
# =========================================================

app = Flask(
    __name__,
    static_folder=".",
    static_url_path=""
)


# =========================================================
# SECURITY / ENV
# =========================================================

app.secret_key = os.environ.get("SESSION_SECRET")

if not app.secret_key:
    raise RuntimeError("SESSION_SECRET is missing.")


OWNER_USERNAME = os.environ.get(
    "OWNER_USERNAME",
    "owner"
)

OWNER_PASSWORD_HASH = os.environ.get(
    "OWNER_PASSWORD_HASH"
)

if not OWNER_PASSWORD_HASH:
    raise RuntimeError(
        "OWNER_PASSWORD_HASH is missing."
    )


# Secure session settings
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    db = sqlite3.connect(
        DATABASE,
        timeout=10
    )

    db.row_factory = sqlite3.Row

    return db


def init_db():
    db = get_db()

    # -----------------------------------------------------
    # CATEGORIES
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------------------
    # SCRIPTS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            category TEXT NOT NULL
                DEFAULT 'Scripts',

            game TEXT NOT NULL
                DEFAULT '',

            type TEXT NOT NULL
                DEFAULT 'Script',

            tags TEXT NOT NULL
                DEFAULT '',

            code TEXT NOT NULL,

            image TEXT
                DEFAULT '',

            featured INTEGER NOT NULL
                DEFAULT 0,

            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------------------
    # MIGRATION FOR OLD DATABASES
    # -----------------------------------------------------

    columns = {
        row["name"]
        for row in db.execute(
            "PRAGMA table_info(scripts)"
        ).fetchall()
    }


    if "type" not in columns:
        db.execute("""
            ALTER TABLE scripts
            ADD COLUMN type TEXT NOT NULL
            DEFAULT 'Script'
        """)


    if "tags" not in columns:
        db.execute("""
            ALTER TABLE scripts
            ADD COLUMN tags TEXT NOT NULL
            DEFAULT ''
        """)


    # -----------------------------------------------------
    # DEFAULT CATEGORIES
    # -----------------------------------------------------

    db.execute("""
        INSERT OR IGNORE INTO categories (name)
        VALUES (?)
    """, ("Scripts",))


    db.execute("""
        INSERT OR IGNORE INTO categories (name)
        VALUES (?)
    """, ("Hacks",))


    db.commit()
    db.close()


# =========================================================
# OWNER AUTH
# =========================================================

def owner_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get(
            "owner_authenticated"
        ):

            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 401

        return func(
            *args,
            **kwargs
        )

    return wrapper


# =========================================================
# HELPERS
# =========================================================

def clean_string(value, default=""):
    return str(
        value if value is not None else default
    ).strip()


def parse_tags(value):
    """
    Supports:

    ["MM2", "Roblox"]

    or

    "MM2, Roblox"
    """

    if isinstance(value, list):

        return [
            clean_string(tag)
            for tag in value
            if clean_string(tag)
        ]


    if isinstance(value, str):

        return [
            tag.strip()
            for tag in value.split(",")
            if tag.strip()
        ]


    return []


def tags_to_string(tags):
    return ",".join(
        parse_tags(tags)
    )


def row_to_script(row):
    tags = []

    if row["tags"]:
        tags = [
            tag.strip()
            for tag in row["tags"].split(",")
            if tag.strip()
        ]


    return {
        "id": row["id"],
        "title": row["title"],
        "name": row["title"],
        "description": row["description"],
        "category": row["category"],
        "game": row["game"],
        "type": row["type"],
        "tags": tags,
        "code": row["code"],
        "image": row["image"],
        "featured": bool(row["featured"]),
        "author": "Fime",
        "created_at": row["created_at"],
    }


# =========================================================
# PUBLIC PAGES
# =========================================================

@app.get("/")
def index():
    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.get("/scripts")
def scripts_page():
    return send_from_directory(
        BASE_DIR,
        "scripts.html"
    )


@app.get("/hacks")
def hacks_page():
    return send_from_directory(
        BASE_DIR,
        "hacks.html"
    )


@app.get("/script")
def script_page():
    return send_from_directory(
        BASE_DIR,
        "script.html"
    )


@app.get("/owner")
def owner_page():
    return send_from_directory(
        BASE_DIR,
        "owner.html"
    )


# =========================================================
# OWNER LOGIN
# =========================================================

@app.post("/api/owner/login")
def owner_login():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    username = clean_string(
        data.get("username")
    )

    password = str(
        data.get("password", "")
    )


    if username != OWNER_USERNAME:

        return jsonify({
            "success": False,
            "error":
                "بيانات الدخول غير صحيحة."
        }), 401


    try:

        password_valid = check_password_hash(
            OWNER_PASSWORD_HASH,
            password
        )

    except Exception:

        password_valid = False


    if not password_valid:

        return jsonify({
            "success": False,
            "error":
                "بيانات الدخول غير صحيحة."
        }), 401


    session.clear()

    session["owner_authenticated"] = True

    return jsonify({
        "success": True
    })


@app.post("/api/owner/logout")
def owner_logout():

    session.clear()

    return jsonify({
        "success": True
    })


@app.get("/api/owner/me")
def owner_me():

    return jsonify({
        "authenticated": bool(
            session.get(
                "owner_authenticated"
            )
        )
    })


# =========================================================
# PUBLIC CATEGORIES
# =========================================================

@app.get("/api/categories")
def get_categories():

    db = get_db()

    rows = db.execute("""
        SELECT
            id,
            name,
            created_at
        FROM categories
        ORDER BY
            id ASC
    """).fetchall()

    db.close()


    return jsonify([
        {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"]
        }
        for row in rows
    ])


# =========================================================
# OWNER CATEGORY CREATE
# =========================================================

@app.post("/api/owner/categories")
@owner_required
def create_category():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    name = clean_string(
        data.get("name")
    )


    if not name:

        return jsonify({
            "success": False,
            "error":
                "اكتب اسم القسم."
        }), 400


    if len(name) > 80:

        return jsonify({
            "success": False,
            "error":
                "اسم القسم طويل جدًا."
        }), 400


    db = get_db()


    try:

        cursor = db.execute("""
            INSERT INTO categories (name)
            VALUES (?)
        """, (name,))

        db.commit()

        category_id = cursor.lastrowid


    except sqlite3.IntegrityError:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "هذا القسم موجود بالفعل."
        }), 409


    db.close()


    return jsonify({
        "success": True,
        "id": category_id,
        "name": name
    }), 201


# =========================================================
# OWNER CATEGORY UPDATE
# =========================================================

@app.put("/api/owner/categories/<int:category_id>")
@owner_required
def update_category(category_id):

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    new_name = clean_string(
        data.get("name")
    )


    if not new_name:

        return jsonify({
            "success": False,
            "error":
                "اكتب اسم القسم."
        }), 400


    if len(new_name) > 80:

        return jsonify({
            "success": False,
            "error":
                "اسم القسم طويل جدًا."
        }), 400


    db = get_db()


    old_row = db.execute("""
        SELECT name
        FROM categories
        WHERE id = ?
    """, (category_id,)).fetchone()


    if not old_row:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "القسم غير موجود."
        }), 404


    old_name = old_row["name"]


    try:

        db.execute("""
            UPDATE categories
            SET name = ?
            WHERE id = ?
        """, (
            new_name,
            category_id
        ))


        # Update scripts belonging to old category
        db.execute("""
            UPDATE scripts
            SET category = ?
            WHERE category = ?
        """, (
            new_name,
            old_name
        ))


        db.commit()


    except sqlite3.IntegrityError:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "هذا الاسم مستخدم بالفعل."
        }), 409


    db.close()


    return jsonify({
        "success": True
    })


# =========================================================
# OWNER CATEGORY DELETE
# =========================================================

@app.delete("/api/owner/categories/<int:category_id>")
@owner_required
def delete_category(category_id):

    db = get_db()


    row = db.execute("""
        SELECT name
        FROM categories
        WHERE id = ?
    """, (category_id,)).fetchone()


    if not row:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "القسم غير موجود."
        }), 404


    category_name = row["name"]


    # Prevent deleting a category that still
    # contains scripts.
    script_count = db.execute("""
        SELECT COUNT(*)
        AS count
        FROM scripts
        WHERE category = ?
    """, (category_name,)).fetchone()["count"]


    if script_count > 0:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "لا يمكن حذف قسم يحتوي على سكربتات. انقل السكربتات أولًا."
        }), 409


    db.execute("""
        DELETE FROM categories
        WHERE id = ?
    """, (category_id,))


    db.commit()
    db.close()


    return jsonify({
        "success": True
    })


# =========================================================
# PUBLIC SCRIPTS
# =========================================================

@app.get("/api/scripts")
def get_scripts():

    db = get_db()


    rows = db.execute("""
        SELECT
            id,
            title,
            description,
            category,
            game,
            type,
            tags,
            code,
            image,
            featured,
            created_at

        FROM scripts

        ORDER BY
            featured DESC,
            id DESC
    """).fetchall()


    db.close()


    return jsonify([
        row_to_script(row)
        for row in rows
    ])


# =========================================================
# PUBLIC SINGLE SCRIPT
# =========================================================

@app.get("/api/scripts/<int:script_id>")
def get_script(script_id):

    db = get_db()


    row = db.execute("""
        SELECT
            id,
            title,
            description,
            category,
            game,
            type,
            tags,
            code,
            image,
            featured,
            created_at

        FROM scripts

        WHERE id = ?
    """, (
        script_id,
    )).fetchone()


    db.close()


    if not row:

        return jsonify({
            "success": False,
            "error":
                "Script not found."
        }), 404


    return jsonify(
        row_to_script(row)
    )


# =========================================================
# OWNER CREATE SCRIPT
# =========================================================

@app.post("/api/owner/scripts")
@owner_required
def create_script():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    title = clean_string(
        data.get("title")
    )

    description = clean_string(
        data.get("description")
    )

    category = clean_string(
        data.get("category")
    )

    game = clean_string(
        data.get("game")
    )

    script_type = clean_string(
        data.get(
            "type",
            "Script"
        )
    ) or "Script"

    tags = parse_tags(
        data.get("tags")
    )

    code = str(
        data.get(
            "code",
            ""
        )
    )

    image = clean_string(
        data.get("image")
    )

    featured = bool(
        data.get(
            "featured",
            False
        )
    )


    if not title:

        return jsonify({
            "success": False,
            "error":
                "اكتب اسم السكربت."
        }), 400


    if not description:

        return jsonify({
            "success": False,
            "error":
                "اكتب وصف السكربت."
        }), 400


    if not category:

        return jsonify({
            "success": False,
            "error":
                "اختر قسمًا."
        }), 400


    if not code:

        return jsonify({
            "success": False,
            "error":
                "ضع كود السكربت."
        }), 400


    db = get_db()


    category_exists = db.execute("""
        SELECT id
        FROM categories
        WHERE name = ?
    """, (
        category,
    )).fetchone()


    if not category_exists:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "القسم غير موجود."
        }), 400


    cursor = db.execute("""
        INSERT INTO scripts (
            title,
            description,
            category,
            game,
            type,
            tags,
            code,
            image,
            featured
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        description,
        category,
        game,
        script_type,
        tags_to_string(tags),
        code,
        image,
        int(featured)
    ))


    db.commit()

    script_id = cursor.lastrowid

    db.close()


    return jsonify({
        "success": True,
        "id": script_id
    }), 201


# =========================================================
# OWNER UPDATE SCRIPT
# =========================================================

@app.put("/api/owner/scripts/<int:script_id>")
@owner_required
def update_script(script_id):

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    title = clean_string(
        data.get("title")
    )

    description = clean_string(
        data.get("description")
    )

    category = clean_string(
        data.get("category")
    )

    game = clean_string(
        data.get("game")
    )

    script_type = clean_string(
        data.get(
            "type",
            "Script"
        )
    ) or "Script"

    tags = parse_tags(
        data.get("tags")
    )

    code = str(
        data.get(
            "code",
            ""
        )
    )

    image = clean_string(
        data.get("image")
    )

    featured = bool(
        data.get(
            "featured",
            False
        )
    )


    if not title or not description or not code:

        return jsonify({
            "success": False,
            "error":
                "بعض البيانات المطلوبة ناقصة."
        }), 400


    if not category:

        return jsonify({
            "success": False,
            "error":
                "اختر قسمًا."
        }), 400


    db = get_db()


    category_exists = db.execute("""
        SELECT id
        FROM categories
        WHERE name = ?
    """, (
        category,
    )).fetchone()


    if not category_exists:

        db.close()

        return jsonify({
            "success": False,
            "error":
                "القسم غير موجود."
        }), 400


    cursor = db.execute("""
        UPDATE scripts

        SET
            title = ?,
            description = ?,
            category = ?,
            game = ?,
            type = ?,
            tags = ?,
            code = ?,
            image = ?,
            featured = ?

        WHERE id = ?
    """, (
        title,
        description,
        category,
        game,
        script_type,
        tags_to_string(tags),
        code,
        image,
        int(featured),
        script_id
    ))


    db.commit()

    changed = cursor.rowcount

    db.close()


    if not changed:

        return jsonify({
            "success": False,
            "error":
                "السكربت غير موجود."
        }), 404


    return jsonify({
        "success": True
    })


# =========================================================
# OWNER DELETE SCRIPT
# =========================================================

@app.delete("/api/owner/scripts/<int:script_id>")
@owner_required
def delete_script(script_id):

    db = get_db()


    cursor = db.execute("""
        DELETE FROM scripts
        WHERE id = ?
    """, (
        script_id,
    ))


    db.commit()

    deleted = cursor.rowcount

    db.close()


    if not deleted:

        return jsonify({
            "success": False,
            "error":
                "السكربت غير موجود."
        }), 404


    return jsonify({
        "success": True
    })


# =========================================================
# STATIC FILES
# =========================================================

@app.get("/<path:path>")
def static_files(path):

    requested = (
        BASE_DIR / path
    ).resolve()


    # Prevent path traversal
    try:
        requested.relative_to(
            BASE_DIR.resolve()
        )

    except ValueError:

        return jsonify({
            "error": "Not found"
        }), 404


    if (
        requested.exists()
        and requested.is_file()
    ):

        return send_from_directory(
            BASE_DIR,
            path
        )


    return jsonify({
        "error": "Not found"
    }), 404


# =========================================================
# DATABASE INIT
# =========================================================

init_db()


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port
    )