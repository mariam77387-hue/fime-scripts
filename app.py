import os
import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    session,
    send_from_directory,
    abort,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)


# =========================================================
# Fime Scripts — app.py
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "fime.db"

app = Flask(__name__, static_folder=None)


# =========================================================
# Environment
# =========================================================

SESSION_SECRET = os.getenv("SESSION_SECRET")

OWNER_USERNAME = os.getenv("OWNER_USERNAME")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD")


if not SESSION_SECRET:
    raise RuntimeError(
        "❌ SESSION_SECRET غير موجود في Environment Variables."
    )

if not OWNER_USERNAME:
    raise RuntimeError(
        "❌ OWNER_USERNAME غير موجود في Environment Variables."
    )

if not OWNER_PASSWORD:
    raise RuntimeError(
        "❌ OWNER_PASSWORD غير موجود في Environment Variables."
    )


app.secret_key = SESSION_SECRET

OWNER_PASSWORD_HASH = generate_password_hash(
    OWNER_PASSWORD
)


# =========================================================
# Session Security
# =========================================================

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_NAME="fime_owner_session",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,
)


# =========================================================
# Security Headers
# =========================================================

@app.after_request
def security_headers(response):

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["X-Frame-Options"] = "DENY"

    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    response.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=()"
    )

    response.headers[
        "Content-Security-Policy"
    ] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none';"
    )

    return response


# =========================================================
# Database
# =========================================================

def get_db():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    try:

        # -------------------------------------------------
        # Categories
        # -------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # -------------------------------------------------
        # Scripts
        # -------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT '',
                game TEXT DEFAULT '',
                code TEXT DEFAULT '',
                image TEXT DEFAULT '',
                featured INTEGER NOT NULL DEFAULT 0,
                author TEXT DEFAULT 'Fime',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # -------------------------------------------------
        # Default Categories
        # -------------------------------------------------

        conn.execute(
            """
            INSERT OR IGNORE INTO categories
            (name, is_default)
            VALUES (?, ?)
            """,
            ("Scripts", 1)
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO categories
            (name, is_default)
            VALUES (?, ?)
            """,
            ("Hacks", 1)
        )


        # -------------------------------------------------
        # Old database compatibility
        #
        # إذا كان عندك سكربتات قديمة بتصنيفات لم تكن موجودة
        # في جدول categories، نضيفها تلقائياً.
        # -------------------------------------------------

        old_categories = conn.execute(
            """
            SELECT DISTINCT category
            FROM scripts
            WHERE category IS NOT NULL
              AND TRIM(category) != ''
            """
        ).fetchall()

        for row in old_categories:

            category_name = str(
                row["category"]
            ).strip()

            if not category_name:
                continue

            conn.execute(
                """
                INSERT OR IGNORE INTO categories
                (name, is_default)
                VALUES (?, 0)
                """,
                (category_name,)
            )


        conn.commit()

    finally:
        conn.close()


# =========================================================
# Database Helpers
# =========================================================

def row_to_script(row):

    if row is None:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "category": row["category"] or "",
        "game": row["game"] or "",
        "code": row["code"] or "",
        "image": row["image"] or "",
        "featured": bool(row["featured"]),
        "author": row["author"] or "Fime",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def clean_text(value, max_length=10000):

    if value is None:
        return ""

    value = str(value).strip()

    return value[:max_length]


def clean_title(value):

    value = clean_text(value, 200)

    return value


def valid_image_url(value):

    value = clean_text(value, 2000)

    if not value:
        return ""

    if value.startswith("/"):
        return value

    if re.match(
        r"^https://",
        value,
        re.IGNORECASE
    ):
        return value

    if re.match(
        r"^http://",
        value,
        re.IGNORECASE
    ):
        return value

    return ""


# =========================================================
# Owner Authentication
# =========================================================

def owner_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("owner_authenticated") is not True:
            return jsonify({
                "error": "غير مصرح"
            }), 401

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# Public Pages
# =========================================================

@app.route("/")
def home():
    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route("/scripts")
def scripts_page():
    return send_from_directory(
        BASE_DIR,
        "scripts.html"
    )


@app.route("/hacks")
def hacks_page():
    return send_from_directory(
        BASE_DIR,
        "hacks.html"
    )


@app.route("/script")
def script_page():
    return send_from_directory(
        BASE_DIR,
        "script.html"
    )


@app.route("/owner")
def owner_page():
    return send_from_directory(
        BASE_DIR,
        "owner.html"
    )


# =========================================================
# Static Files
# =========================================================

@app.route("/css/<path:filename>")
def css_files(filename):

    if ".." in filename:
        abort(404)

    return send_from_directory(
        BASE_DIR / "css",
        filename
    )


@app.route("/js/<path:filename>")
def js_files(filename):

    if ".." in filename:
        abort(404)

    return send_from_directory(
        BASE_DIR / "js",
        filename
    )


@app.route("/assets/<path:filename>")
def asset_files(filename):

    if ".." in filename:
        abort(404)

    return send_from_directory(
        BASE_DIR / "assets",
        filename
    )


# =========================================================
# Block Sensitive Files
# =========================================================

@app.route("/<path:filename>")
def protected_files(filename):

    filename_lower = filename.lower()

    blocked = (
        ".env",
        ".git",
        ".github",
        "fime.db",
        "app.py",
        "requirements.txt",
        "__pycache__",
    )

    for item in blocked:

        if (
            filename_lower == item
            or filename_lower.startswith(item + "/")
        ):
            abort(404)

    if ".." in filename:
        abort(404)

    abort(404)


# =========================================================
# Owner Login
# =========================================================

@app.post("/api/owner/login")
def owner_login():

    data = request.get_json(
        silent=True
    ) or {}

    username = clean_text(
        data.get("username"),
        200
    )

    password = data.get("password")

    if password is None:
        password = ""

    password = str(password)

    # ---------------------------------------------
    # يسمح بإرسال username فارغ من command-bar
    # ويستخدم OWNER_USERNAME الموجود في Render
    # ---------------------------------------------

    if not username:
        username = OWNER_USERNAME

    if username != OWNER_USERNAME:
        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة."
        }), 401

    if not check_password_hash(
        OWNER_PASSWORD_HASH,
        password
    ):
        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة."
        }), 401

    session.clear()

    session.permanent = True

    session["owner_authenticated"] = True

    return jsonify({
        "success": True,
        "message": "تم تسجيل الدخول بنجاح."
    })


# =========================================================
# Owner Logout
# =========================================================

@app.post("/api/owner/logout")
@owner_required
def owner_logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================================================
# Owner Session
# =========================================================

@app.get("/api/owner/me")
def owner_me():

    authenticated = (
        session.get("owner_authenticated")
        is True
    )

    return jsonify({
        "authenticated": authenticated
    })


# =========================================================
# Categories — Public
# =========================================================

@app.get("/api/categories")
def get_categories():

    conn = get_db()

    try:

        rows = conn.execute(
            """
            SELECT
                id,
                name,
                is_default,
                created_at
            FROM categories
            ORDER BY
                is_default DESC,
                name COLLATE NOCASE ASC
            """
        ).fetchall()

        categories = [
            {
                "id": row["id"],
                "name": row["name"],
                "is_default": bool(
                    row["is_default"]
                ),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

        return jsonify(categories)

    finally:
        conn.close()


# =========================================================
# Create Category — Owner
# =========================================================

@app.post("/api/owner/categories")
@owner_required
def create_category():

    data = request.get_json(
        silent=True
    ) or {}

    name = clean_text(
        data.get("name"),
        100
    )

    if not name:
        return jsonify({
            "error": "اكتب اسم التصنيف."
        }), 400

    conn = get_db()

    try:

        existing = conn.execute(
            """
            SELECT id
            FROM categories
            WHERE LOWER(name) = LOWER(?)
            """,
            (name,)
        ).fetchone()

        if existing:
            return jsonify({
                "error": "هذا التصنيف موجود بالفعل."
            }), 409

        cursor = conn.execute(
            """
            INSERT INTO categories
            (name, is_default)
            VALUES (?, 0)
            """,
            (name,)
        )

        conn.commit()

        category_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "category": {
                "id": category_id,
                "name": name,
                "is_default": False,
            }
        }), 201

    finally:
        conn.close()


# =========================================================
# Delete Category — Owner
# =========================================================

@app.delete("/api/owner/categories/<int:category_id>")
@owner_required
def delete_category(category_id):

    conn = get_db()

    try:

        category = conn.execute(
            """
            SELECT *
            FROM categories
            WHERE id = ?
            """,
            (category_id,)
        ).fetchone()

        if not category:
            return jsonify({
                "error": "التصنيف غير موجود."
            }), 404

        if category["is_default"]:
            return jsonify({
                "error": "لا يمكن حذف التصنيفات الأساسية."
            }), 400

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM scripts
            WHERE LOWER(TRIM(category))
                = LOWER(TRIM(?))
            """,
            (category["name"],)
        ).fetchone()[0]

        if count > 0:
            return jsonify({
                "error": (
                    "لا يمكن حذف التصنيف لأنه يحتوي "
                    "على سكربتات. انقل السكربتات أولاً."
                )
            }), 400

        conn.execute(
            """
            DELETE FROM categories
            WHERE id = ?
            """,
            (category_id,)
        )

        conn.commit()

        return jsonify({
            "success": True
        })

    finally:
        conn.close()


# =========================================================
# Public Scripts
# =========================================================

@app.get("/api/scripts")
def get_scripts():

    conn = get_db()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM scripts
            ORDER BY
                featured DESC,
                id DESC
            """
        ).fetchall()

        return jsonify([
            row_to_script(row)
            for row in rows
        ])

    finally:
        conn.close()


# =========================================================
# Single Script
# =========================================================

@app.get("/api/scripts/<int:script_id>")
def get_script(script_id):

    conn = get_db()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM scripts
            WHERE id = ?
            """,
            (script_id,)
        ).fetchone()

        if not row:
            return jsonify({
                "error": "السكربت غير موجود."
            }), 404

        return jsonify(
            row_to_script(row)
        )

    finally:
        conn.close()


# =========================================================
# Create Script — Owner
# =========================================================

@app.post("/api/owner/scripts")
@owner_required
def create_script():

    data = request.get_json(
        silent=True
    ) or {}

    title = clean_title(
        data.get("title")
    )

    if not title:
        return jsonify({
            "error": "اكتب اسم السكربت."
        }), 400

    description = clean_text(
        data.get("description"),
        10000
    )

    game = clean_text(
        data.get("game"),
        200
    )

    code = clean_text(
        data.get("code"),
        500000
    )

    image = valid_image_url(
        data.get("image")
    )

    # =====================================================
    # التصنيف اختياري
    #
    # إذا كان فاضي نحفظه كـ ""
    # ولا نرفض عملية النشر.
    # =====================================================

    category = clean_text(
        data.get("category"),
        100
    )

    featured = bool(
        data.get("featured", False)
    )

    conn = get_db()

    try:

        # إذا تم اختيار تصنيف، نتأكد أنه موجود.
        # أما إذا كان فارغاً فنسمح به.
        if category:

            category_exists = conn.execute(
                """
                SELECT id
                FROM categories
                WHERE LOWER(name) = LOWER(?)
                """,
                (category,)
            ).fetchone()

            if not category_exists:
                return jsonify({
                    "error": "التصنيف المحدد غير موجود."
                }), 400

            # نحفظ الاسم الرسمي الموجود في DB
            category = category_exists["name"]

        cursor = conn.execute(
            """
            INSERT INTO scripts
            (
                title,
                description,
                category,
                game,
                code,
                image,
                featured,
                author
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                category,
                game,
                code,
                image,
                1 if featured else 0,
                "Fime",
            )
        )

        conn.commit()

        script_id = cursor.lastrowid

        row = conn.execute(
            """
            SELECT *
            FROM scripts
            WHERE id = ?
            """,
            (script_id,)
        ).fetchone()

        return jsonify({
            "success": True,
            "script": row_to_script(row)
        }), 201

    finally:
        conn.close()


# =========================================================
# Update Script — Owner
# =========================================================

@app.put("/api/owner/scripts/<int:script_id>")
@owner_required
def update_script(script_id):

    data = request.get_json(
        silent=True
    ) or {}

    title = clean_title(
        data.get("title")
    )

    if not title:
        return jsonify({
            "error": "اسم السكربت مطلوب."
        }), 400

    description = clean_text(
        data.get("description"),
        10000
    )

    game = clean_text(
        data.get("game"),
        200
    )

    code = clean_text(
        data.get("code"),
        500000
    )

    image = valid_image_url(
        data.get("image")
    )

    category = clean_text(
        data.get("category"),
        100
    )

    featured = bool(
        data.get("featured", False)
    )

    conn = get_db()

    try:

        existing = conn.execute(
            """
            SELECT id
            FROM scripts
            WHERE id = ?
            """,
            (script_id,)
        ).fetchone()

        if not existing:
            return jsonify({
                "error": "السكربت غير موجود."
            }), 404


        # التصنيف اختياري حتى عند التعديل
        if category:

            category_exists = conn.execute(
                """
                SELECT id, name
                FROM categories
                WHERE LOWER(name) = LOWER(?)
                """,
                (category,)
            ).fetchone()

            if not category_exists:
                return jsonify({
                    "error": "التصنيف المحدد غير موجود."
                }), 400

            category = category_exists["name"]


        conn.execute(
            """
            UPDATE scripts
            SET
                title = ?,
                description = ?,
                category = ?,
                game = ?,
                code = ?,
                image = ?,
                featured = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                title,
                description,
                category,
                game,
                code,
                image,
                1 if featured else 0,
                script_id,
            )
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM scripts
            WHERE id = ?
            """,
            (script_id,)
        ).fetchone()

        return jsonify({
            "success": True,
            "script": row_to_script(row)
        })

    finally:
        conn.close()


# =========================================================
# Delete Script — Owner
# =========================================================

@app.delete("/api/owner/scripts/<int:script_id>")
@owner_required
def delete_script(script_id):

    conn = get_db()

    try:

        existing = conn.execute(
            """
            SELECT id
            FROM scripts
            WHERE id = ?
            """,
            (script_id,)
        ).fetchone()

        if not existing:
            return jsonify({
                "error": "السكربت غير موجود."
            }), 404

        conn.execute(
            """
            DELETE FROM scripts
            WHERE id = ?
            """,
            (script_id,)
        )

        conn.commit()

        return jsonify({
            "success": True
        })

    finally:
        conn.close()


# =========================================================
# Initialize Database
# =========================================================

init_db()


# =========================================================
# Local Development
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )