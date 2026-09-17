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


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "fime.db"

app = Flask(
    __name__,
    static_folder=".",
    static_url_path=""
)

# مهم:
# لا تضع مفتاحًا حقيقيًا داخل GitHub.
app.secret_key = os.environ.get("SESSION_SECRET")

if not app.secret_key:
    raise RuntimeError("SESSION_SECRET is missing.")


OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "owner")
OWNER_PASSWORD_HASH = os.environ.get("OWNER_PASSWORD_HASH")

if not OWNER_PASSWORD_HASH:
    raise RuntimeError("OWNER_PASSWORD_HASH is missing.")


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'scripts',
            game TEXT NOT NULL DEFAULT '',
            code TEXT NOT NULL,
            image TEXT DEFAULT '',
            featured INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


def owner_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("owner_authenticated"):
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 401

        return func(*args, **kwargs)

    return wrapper


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/scripts")
def scripts_page():
    return send_from_directory(BASE_DIR, "scripts.html")


@app.get("/hacks")
def hacks_page():
    return send_from_directory(BASE_DIR, "hacks.html")


@app.get("/script")
def script_page():
    return send_from_directory(BASE_DIR, "script.html")


@app.get("/owner")
def owner_page():
    return send_from_directory(BASE_DIR, "owner.html")


# =========================
# OWNER LOGIN
# =========================

@app.post("/api/owner/login")
def owner_login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", ""))
    password = str(data.get("password", ""))

    if username != OWNER_USERNAME:
        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة."
        }), 401

    if not check_password_hash(OWNER_PASSWORD_HASH, password):
        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة."
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
    authenticated = bool(
        session.get("owner_authenticated")
    )

    return jsonify({
        "authenticated": authenticated
    })


# =========================
# PUBLIC SCRIPTS
# =========================

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
        ORDER BY featured DESC, id DESC
    """).fetchall()

    db.close()

    scripts = []

    for row in rows:
        scripts.append({
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "game": row["game"],
            "code": row["code"],
            "image": row["image"],
            "featured": bool(row["featured"]),
            "author": "Fime"
        })

    return jsonify(scripts)


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
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "game": row["game"],
        "code": row["code"],
        "image": row["image"],
        "featured": bool(row["featured"]),
        "author": "Fime"
    })


# =========================
# OWNER CRUD
# =========================

@app.post("/api/owner/scripts")
@owner_required
def create_script():
    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    category = str(data.get("category", "scripts")).strip()
    game = str(data.get("game", "")).strip()
    code = str(data.get("code", ""))
    image = str(data.get("image", "")).strip()
    featured = bool(data.get("featured", False))

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

    if category not in ("scripts", "hacks"):
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


@app.put("/api/owner/scripts/<int:script_id>")
@owner_required
def update_script(script_id):
    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    category = str(data.get("category", "scripts")).strip()
    game = str(data.get("game", "")).strip()
    code = str(data.get("code", ""))
    image = str(data.get("image", "")).strip()
    featured = bool(data.get("featured", False))

    if not title or not description or not code:
        return jsonify({
            "success": False,
            "error": "بعض البيانات المطلوبة ناقصة."
        }), 400

    if category not in ("scripts", "hacks"):
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


# =========================
# STATIC FILES
# =========================

@app.get("/<path:path>")
def static_files(path):
    requested = BASE_DIR / path

    if requested.exists() and requested.is_file():
        return send_from_directory(BASE_DIR, path)

    return jsonify({
        "error": "Not found"
    }), 404


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )