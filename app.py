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
# SECURITY / SESSION
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


# نحول كلمة المرور إلى Hash عند تشغيل السيرفر.
# كلمة المرور الأصلية لا يتم إرسالها للواجهة.
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

    db.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT NOT NULL,

            category TEXT NOT NULL
                DEFAULT 'scripts',

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


    # إذا command-bar أرسل كلمة المرور فقط،
    # نستخدم اسم المستخدم الموجود في Render.
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


    # إنشاء جلسة جديدة بعد نجاح الدخول.
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
# OWNER SESSION STATUS
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
# PUBLIC — GET ALL SCRIPTS
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

            "id": row["id"],

            "title": row["title"],

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

            # لا يتم إظهار هوية المالك.
            "author": "Fime"

        })


    return jsonify(scripts)


# =========================================================
# PUBLIC — GET SINGLE SCRIPT
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
    """, (
        script_id,
    )).fetchone()


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
            "scripts"
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


    if not code:

        return jsonify({
            "success": False,
            "error": "ضع كود السكربت."
        }), 400


    if category not in (
        "scripts",
        "hacks"
    ):

        return jsonify({
            "success": False,
            "error": "تصنيف غير صالح."
        }), 400


    db = get_db()


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
            "scripts"
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


    if not code:

        return jsonify({
            "success": False,
            "error": "كود السكربت مطلوب."
        }), 400


    if category not in (
        "scripts",
        "hacks"
    ):

        return jsonify({
            "success": False,
            "error": "تصنيف غير صالح."
        }), 400


    db = get_db()


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
    """, (
        script_id,
    ))


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

    # منع الملفات الحساسة.
    normalized = path.replace("\\", "/").strip("/")


    blocked_files = {
        "fime.db",
        ".env",
        ".git",
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


    # منع Path Traversal.
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
# STARTUP
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