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

from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# FIME SCRIPTS — FLASK BACKEND
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fime.db"

app = Flask(
    __name__,
    static_folder=".",
    static_url_path=""
)


# =========================================================
# SESSION / SECURITY
# =========================================================

SESSION_SECRET = os.environ.get("SESSION_SECRET")

if not SESSION_SECRET:
    raise RuntimeError(
        "SESSION_SECRET is missing. "
        "Add it to Render Environment Variables."
    )

app.secret_key = SESSION_SECRET

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_NAME="fime_owner_session",
)


# =========================================================
# OWNER LOGIN
# =========================================================

OWNER_USERNAME = os.environ.get(
    "OWNER_USERNAME",
    "owner"
).strip()

OWNER_PASSWORD = os.environ.get(
    "OWNER_PASSWORD"
)

if not OWNER_PASSWORD:
    raise RuntimeError(
        "OWNER_PASSWORD is missing. "
        "Add it to Render Environment Variables."
    )

OWNER_PASSWORD_HASH = generate_password_hash(
    OWNER_PASSWORD
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

    # جدول السكربتات
    db.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            category TEXT NOT NULL
                DEFAULT 'Scripts',

            game TEXT NOT NULL
                DEFAULT '',

            code TEXT NOT NULL,

            image TEXT DEFAULT '',

            featured INTEGER NOT NULL
                DEFAULT 0,

            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول التصنيفات
    db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL UNIQUE,

            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # التصنيفات الأساسية
    default_categories = [
        "Scripts",
        "Hacks"
    ]

    for category in default_categories:
        db.execute("""
            INSERT OR IGNORE INTO categories (name)
            VALUES (?)
        """, (category,))

    # التأكد أن أي تصنيف قديم موجود في scripts
    # يتم إضافته أيضًا إلى جدول categories.
    existing_categories = db.execute("""
        SELECT DISTINCT category
        FROM scripts
        WHERE category IS NOT NULL
        AND TRIM(category) != ''
    """).fetchall()

    for row in existing_categories:
        category_name = row["category"].strip()

        if category_name:
            db.execute("""
                INSERT OR IGNORE INTO categories (name)
                VALUES (?)
            """, (category_name,))

    db.commit()
    db.close()


# =========================================================
# OWNER AUTH
# =========================================================

def owner_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get(
            "owner_authenticated",
            False
        ):
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 401

        return func(*args, **kwargs)

    return wrapper


# =========================================================
# SECURITY HEADERS
# =========================================================

@app.after_request
def security_headers(response):

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["X-Frame-Options"] = "DENY"

    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    response.headers["Permissions-Policy"] = (
        "camera=(), "
        "microphone=(), "
        "geolocation=(), "
        "payment=(), "
        "usb=()"
    )

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests"
    )

    return response


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

    data = request.get_json(
        silent=True
    ) or {}

    username = str(
        data.get(
            "username",
            ""
        )
    ).strip()

    password = str(
        data.get(
            "password",
            ""
        )
    )

    # يسمح بالدخول من command-bar بكلمة المرور فقط.
    if not username:
        username = OWNER_USERNAME

    if username != OWNER_USERNAME:

        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة."
        }), 401

    if not password:

        return jsonify({
            "success": False,
            "error": "كلمة المرور مطلوبة."
        }), 400

    if not check_password_hash(
        OWNER_PASSWORD_HASH,
        password
    ):

        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة."
        }), 401

    session.clear()

    session["owner_authenticated"] = True

    return jsonify({
        "success": True
    })


# =========================================================
# OWNER LOGOUT
# =========================================================

@app.post("/api/owner/logout")
def owner_logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================================================
# OWNER SESSION
# =========================================================

@app.get("/api/owner/me")
def owner_me():

    authenticated = bool(
        session.get(
            "owner_authenticated",
            False
        )
    )

    return jsonify({
        "authenticated": authenticated
    })


# =========================================================
# PUBLIC — CATEGORIES
# =========================================================

@app.get("/api/categories")
def get_categories():

    db = get_db()

    rows = db.execute("""
        SELECT
            id,
            name
        FROM categories
        ORDER BY
            id ASC
    """).fetchall()

    db.close()

    return jsonify([
        {
            "id": row["id"],
            "name": row["name"]
        }
        for row in rows
    ])


# =========================================================
# OWNER — CREATE CATEGORY
# =========================================================

@app.post("/api/owner/categories")
@owner_required
def create_category():

    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    if not name:

        return jsonify({
            "success": False,
            "error": "اكتب اسم التصنيف."
        }), 400

    if len(name) > 80:

        return jsonify({
            "success": False,
            "error": "اسم التصنيف طويل جدًا."
        }), 400

    db = get_db()

    existing = db.execute("""
        SELECT id
        FROM categories
        WHERE LOWER(name) = LOWER(?)
    """, (name,)).fetchone()

    if existing:

        db.close()

        return jsonify({
            "success": False,
            "error": "هذا التصنيف موجود بالفعل."
        }), 409

    cursor = db.execute("""
        INSERT INTO categories (name)
        VALUES (?)
    """, (name,))

    db.commit()

    category_id = cursor.lastrowid

    db.close()

    return jsonify({
        "success": True,
        "id": category_id,
        "name": name
    }), 201


# =========================================================
# OWNER — DELETE CATEGORY
# =========================================================

@app.delete("/api/owner/categories/<int:category_id>")
@owner_required
def delete_category(category_id):

    db = get_db()

    category = db.execute("""
        SELECT
            id,
            name
        FROM categories
        WHERE id = ?
    """, (category_id,)).fetchone()

    if not category:

        db.close()

        return jsonify({
            "success": False,
            "error": "التصنيف غير موجود."
        }), 404

    category_name = category["name"]

    # لا نحذف Scripts و Hacks الأساسيين.
    if category_name.lower() in {
        "scripts",
        "hacks"
    }:

        db.close()

        return jsonify({
            "success": False,
            "error": "لا يمكن حذف التصنيف الأساسي."
        }), 400

    # لا نحذف تصنيفًا يحتوي على سكربتات.
    scripts_count = db.execute("""
        SELECT COUNT(*)
        AS count
        FROM scripts
        WHERE category = ?
    """, (category_name,)).fetchone()["count"]

    if scripts_count > 0:

        db.close()

        return jsonify({
            "success": False,
            "error": (
                "لا يمكن حذف هذا التصنيف لأنه يحتوي "
                "على سكربتات. انقل السكربتات أولًا."
            )
        }), 400

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
# PUBLIC — ALL SCRIPTS
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

    scripts = []

    for row in rows:

        scripts.append({

            "id":
                row["id"],

            "title":
                row["title"],

            "description":
                row["description"],

            "category":
                row["category"],

            "game":
                row["game"],

            "code":
                row["code"],

            "image":
                row["image"],

            "featured":
                bool(row["featured"]),

            "author":
                "Fime"
        })

    return jsonify(scripts)


# =========================================================
# PUBLIC — SINGLE SCRIPT
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
            code,
            image,
            featured,
            created_at
        FROM scripts
        WHERE id = ?
    """, (script_id,)).fetchone()

    db.close()

    if not row:

        return jsonify({
            "success": False,
            "error": "Script not found."
        }), 404

    return jsonify({

        "id":
            row["id"],

        "title":
            row["title"],

        "description":
            row["description"],

        "category":
            row["category"],

        "game":
            row["game"],

        "code":
            row["code"],

        "image":
            row["image"],

        "featured":
            bool(row["featured"]),

        "author":
            "Fime"
    })


# =========================================================
# OWNER — CREATE SCRIPT
# =========================================================

@app.post("/api/owner/scripts")
@owner_required
def create_script():

    data = request.get_json(
        silent=True
    ) or {}

    title = str(
        data.get(
            "title",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    category = str(
        data.get(
            "category",
            ""
        )
    ).strip()

    game = str(
        data.get(
            "game",
            ""
        )
    ).strip()

    code = str(
        data.get(
            "code",
            ""
        )
    )

    image = str(
        data.get(
            "image",
            ""
        )
    ).strip()

    featured = bool(
        data.get(
            "featured",
            False
        )
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if not title:

        return jsonify({
            "success": False,
            "error": "اكتب اسم السكربت."
        }), 400

    if not description:

        return jsonify({
            "success": False,
            "error": "اكتب وصف السكربت."
        }), 400

    if not category:

        return jsonify({
            "success": False,
            "error": "اختر تصنيفًا."
        }), 400

    if not code:

        return jsonify({
            "success": False,
            "error": "ضع كود السكربت."
        }), 400

    db = get_db()

    category_exists = db.execute("""
        SELECT id
        FROM categories
        WHERE LOWER(name) = LOWER(?)
    """, (category,)).fetchone()

    if not category_exists:

        db.close()

        return jsonify({
            "success": False,
            "error": "التصنيف غير موجود."
        }), 400

    # نستخدم الاسم الرسمي للتصنيف.
    category = category_exists["name"]

    cursor = db.execute("""
        INSERT INTO scripts (
            title,
            description,
            category,
            game,
            code,
            image,
            featured
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        description,
        category,
        game,
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
# OWNER — UPDATE SCRIPT
# =========================================================

@app.put("/api/owner/scripts/<int:script_id>")
@owner_required
def update_script(script_id):

    data = request.get_json(
        silent=True
    ) or {}

    title = str(
        data.get(
            "title",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    category = str(
        data.get(
            "category",
            ""
        )
    ).strip()

    game = str(
        data.get(
            "game",
            ""
        )
    ).strip()

    code = str(
        data.get(
            "code",
            ""
        )
    )

    image = str(
        data.get(
            "image",
            ""
        )
    ).strip()

    featured = bool(
        data.get(
            "featured",
            False
        )
    )

    if not title:

        return jsonify({
            "success": False,
            "error": "اسم السكربت مطلوب."
        }), 400

    if not description:

        return jsonify({
            "success": False,
            "error": "وصف السكربت مطلوب."
        }), 400

    if not category:

        return jsonify({
            "success": False,
            "error": "اختر تصنيفًا."
        }), 400

    if not code:

        return jsonify({
            "success": False,
            "error": "كود السكربت مطلوب."
        }), 400

    db = get_db()

    category_exists = db.execute("""
        SELECT id, name
        FROM categories
        WHERE LOWER(name) = LOWER(?)
    """, (category,)).fetchone()

    if not category_exists:

        db.close()

        return jsonify({
            "success": False,
            "error": "التصنيف غير موجود."
        }), 400

    category = category_exists["name"]

    cursor = db.execute("""
        UPDATE scripts
        SET
            title = ?,
            description = ?,
            category = ?,
            game = ?,
            code = ?,
            image = ?,
            featured = ?
        WHERE id = ?
    """, (
        title,
        description,
        category,
        game,
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
            "error": "السكربت غير موجود."
        }), 404

    return jsonify({
        "success": True
    })


# =========================================================
# OWNER — DELETE SCRIPT
# =========================================================

@app.delete("/api/owner/scripts/<int:script_id>")
@owner_required
def delete_script(script_id):

    db = get_db()

    cursor = db.execute("""
        DELETE FROM scripts
        WHERE id = ?
    """, (script_id,))

    db.commit()

    deleted = cursor.rowcount

    db.close()

    if not deleted:

        return jsonify({
            "success": False,
            "error": "السكربت غير موجود."
        }), 404

    return jsonify({
        "success": True
    })


# =========================================================
# STATIC FILES
# =========================================================

@app.get("/<path:path>")
def static_files(path):

    normalized = path.replace(
        "\\",
        "/"
    ).strip("/")

    blocked_files = {
        "fime.db",
        ".env",
        "app.py",
        "requirements.txt",
    }

    first_part = normalized.split("/")[0]

    if (
        normalized in blocked_files
        or first_part in {
            ".git",
            ".github"
        }
        or normalized.startswith(".")
    ):

        return jsonify({
            "error": "Not found"
        }), 404

    requested = (
        BASE_DIR / normalized
    ).resolve()

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
            normalized
        )

    return jsonify({
        "error": "Not found"
    }), 404


# =========================================================
# START
# =========================================================

init_db()


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