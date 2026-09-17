import os
import re
import sqlite3
from functools import wraps
from pathlib import Path
from contextlib import contextmanager

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

# PostgreSQL
try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


# =========================================================
# Fime Scripts — app.py
# PostgreSQL + SQLite Fallback
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# PostgreSQL on Render
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLite fallback for local development
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

    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=()"
    )

    response.headers["Content-Security-Policy"] = (
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
# Database Type
# =========================================================

def using_postgres():
    """
    إذا كان DATABASE_URL موجودًا نستخدم PostgreSQL.
    على Render يجب أن يكون DATABASE_URL مربوطًا بقاعدة PostgreSQL.
    """

    return bool(DATABASE_URL)


# =========================================================
# Database Connection
# =========================================================

@contextmanager
def get_db():

    # =====================================================
    # PostgreSQL
    # =====================================================

    if using_postgres():

        if psycopg is None:
            raise RuntimeError(
                "❌ مكتبة psycopg غير مثبتة. "
                "تأكد من requirements.txt."
            )

        conn = None

        try:

            conn = psycopg.connect(
                DATABASE_URL,
                row_factory=dict_row,
                connect_timeout=15,
            )

            yield conn

            conn.commit()

        except Exception:

            if conn:
                conn.rollback()

            raise

        finally:

            if conn:
                conn.close()

        return

    # =====================================================
    # SQLite fallback
    # =====================================================

    conn = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    try:

        yield conn

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# =========================================================
# Database Cursor Helper
# =========================================================

def fetchall(conn, query, params=()):

    cursor = conn.execute(
        query,
        params
    )

    return cursor.fetchall()


def fetchone(conn, query, params=()):

    cursor = conn.execute(
        query,
        params
    )

    return cursor.fetchone()


# =========================================================
# SQLite Migration Helpers
# =========================================================

def get_table_columns(conn, table_name):

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {
        row["name"]
        for row in rows
    }


def add_column_if_missing(
    conn,
    table_name,
    columns,
    column_name,
    definition
):

    if column_name not in columns:

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )

        columns.add(column_name)


def migrate_scripts_table_sqlite(conn):

    columns = get_table_columns(
        conn,
        "scripts"
    )

    # -----------------------------------------------------
    # title
    # -----------------------------------------------------

    if "title" not in columns:

        conn.execute(
            """
            ALTER TABLE scripts
            ADD COLUMN title TEXT DEFAULT ''
            """
        )

        columns.add("title")

    if "name" in columns:

        conn.execute(
            """
            UPDATE scripts
            SET title = COALESCE(
                NULLIF(TRIM(title), ''),
                name,
                'بدون عنوان'
            )
            WHERE title IS NULL
               OR TRIM(title) = ''
            """
        )

    else:

        conn.execute(
            """
            UPDATE scripts
            SET title = 'بدون عنوان'
            WHERE title IS NULL
               OR TRIM(title) = ''
            """
        )

    # -----------------------------------------------------
    # Other columns
    # -----------------------------------------------------

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "description",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "category",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "game",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "code",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "image",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "featured",
        "INTEGER NOT NULL DEFAULT 0"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "author",
        "TEXT DEFAULT 'Fime'"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "created_at",
        "TEXT DEFAULT ''"
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "updated_at",
        "TEXT DEFAULT ''"
    )

    # -----------------------------------------------------
    # Clean old data
    # -----------------------------------------------------

    conn.execute(
        """
        UPDATE scripts
        SET description = ''
        WHERE description IS NULL
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET category = ''
        WHERE category IS NULL
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET game = ''
        WHERE game IS NULL
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET code = ''
        WHERE code IS NULL
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET image = ''
        WHERE image IS NULL
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET featured = 0
        WHERE featured IS NULL
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET author = 'Fime'
        WHERE author IS NULL
           OR TRIM(author) = ''
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
           OR TRIM(created_at) = ''
        """
    )

    conn.execute(
        """
        UPDATE scripts
        SET updated_at = CURRENT_TIMESTAMP
        WHERE updated_at IS NULL
           OR TRIM(updated_at) = ''
        """
    )


# =========================================================
# PostgreSQL Database Initialization
# =========================================================

def init_postgres():

    with get_db() as conn:

        # =================================================
        # Categories
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            categories_name_lower_unique
            ON categories (LOWER(name))
            """
        )

        # =================================================
        # Scripts
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scripts (
                id BIGSERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category VARCHAR(100) NOT NULL DEFAULT '',
                game VARCHAR(200) NOT NULL DEFAULT '',
                code TEXT NOT NULL DEFAULT '',
                image VARCHAR(2000) NOT NULL DEFAULT '',
                featured BOOLEAN NOT NULL DEFAULT FALSE,
                author VARCHAR(200) NOT NULL DEFAULT 'Fime',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # =================================================
        # Indexes
        # =================================================

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            scripts_featured_idx
            ON scripts (featured)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            scripts_game_idx
            ON scripts (LOWER(game))
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            scripts_category_idx
            ON scripts (LOWER(category))
            """
        )

        # =================================================
        # Default Categories
        # =================================================

        conn.execute(
            """
            INSERT INTO categories
            (name, is_default)
            SELECT %s, TRUE
            WHERE NOT EXISTS (
                SELECT 1
                FROM categories
                WHERE LOWER(name) = LOWER(%s)
            )
            """,
            ("Scripts", "Scripts")
        )

        conn.execute(
            """
            INSERT INTO categories
            (name, is_default)
            SELECT %s, TRUE
            WHERE NOT EXISTS (
                SELECT 1
                FROM categories
                WHERE LOWER(name) = LOWER(%s)
            )
            """,
            ("Hacks", "Hacks")
        )


# =========================================================
# SQLite Database Initialization
# =========================================================

def init_sqlite():

    conn = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    try:

        # =================================================
        # Categories
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # =================================================
        # Scripts
        # =================================================

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
                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # =================================================
        # Migration
        # =================================================

        migrate_scripts_table_sqlite(conn)

        # =================================================
        # Default Categories
        # =================================================

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

        # =================================================
        # Import Old Categories
        # =================================================

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
# Initialize Database
# =========================================================

def init_db():

    if using_postgres():

        print(
            "🟢 Fime Scripts Database: PostgreSQL"
        )

        init_postgres()

    else:

        print(
            "🟡 Fime Scripts Database: SQLite fallback"
        )

        init_sqlite()


# =========================================================
# Database Error Helper
# =========================================================

def database_error_name():

    if using_postgres():
        return "PostgreSQL"

    return "SQLite"


# =========================================================
# Database Helpers
# =========================================================

def row_to_script(row):

    if row is None:
        return None

    return {
        "id": row["id"],
        "title": row["title"] or "",
        "description": row["description"] or "",
        "category": row["category"] or "",
        "game": row["game"] or "",
        "code": row["code"] or "",
        "image": row["image"] or "",
        "featured": bool(row["featured"]),
        "author": row["author"] or "Fime",
        "created_at": str(
            row["created_at"] or ""
        ),
        "updated_at": str(
            row["updated_at"] or ""
        ),
    }


def clean_text(value, max_length=10000):

    if value is None:
        return ""

    value = str(value).strip()

    return value[:max_length]


def clean_title(value):

    return clean_text(
        value,
        200
    )


def valid_image_url(value):

    value = clean_text(
        value,
        2000
    )

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

        if session.get(
            "owner_authenticated"
        ) is not True:

            return jsonify({
                "error": "غير مصرح"
            }), 401

        return function(
            *args,
            **kwargs
        )

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


@app.route("/index.html")
def index_html():

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
            or filename_lower.startswith(
                item + "/"
            )
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

    session[
        "owner_authenticated"
    ] = True

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
        session.get(
            "owner_authenticated"
        ) is True
    )

    return jsonify({
        "authenticated": authenticated
    })


# =========================================================
# Categories — Public
# =========================================================

@app.get("/api/categories")
def get_categories():

    with get_db() as conn:

        if using_postgres():

            rows = fetchall(
                conn,
                """
                SELECT
                    id,
                    name,
                    is_default,
                    created_at
                FROM categories
                ORDER BY
                    is_default DESC,
                    LOWER(name) ASC
                """
            )

        else:

            rows = fetchall(
                conn,
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
            )

        categories = [
            {
                "id": row["id"],
                "name": row["name"],
                "is_default": bool(
                    row["is_default"]
                ),
                "created_at": str(
                    row["created_at"]
                ),
            }
            for row in rows
        ]

        return jsonify(categories)


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

    try:

        with get_db() as conn:

            if using_postgres():

                existing = fetchone(
                    conn,
                    """
                    SELECT id
                    FROM categories
                    WHERE LOWER(name) = LOWER(%s)
                    """,
                    (name,)
                )

            else:

                existing = fetchone(
                    conn,
                    """
                    SELECT id
                    FROM categories
                    WHERE LOWER(name) = LOWER(?)
                    """,
                    (name,)
                )

            if existing:

                return jsonify({
                    "error": "هذا التصنيف موجود بالفعل."
                }), 409

            if using_postgres():

                row = fetchone(
                    conn,
                    """
                    INSERT INTO categories
                    (name, is_default)
                    VALUES (%s, FALSE)
                    RETURNING id
                    """,
                    (name,)
                )

                category_id = row["id"]

            else:

                cursor = conn.execute(
                    """
                    INSERT INTO categories
                    (name, is_default)
                    VALUES (?, 0)
                    """,
                    (name,)
                )

                category_id = cursor.lastrowid

            return jsonify({
                "success": True,
                "category": {
                    "id": category_id,
                    "name": name,
                    "is_default": False,
                }
            }), 201

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while creating category:",
            error
        )

        return jsonify({
            "success": False,
            "error": "حدث خطأ في قاعدة البيانات."
        }), 500


# =========================================================
# Delete Category — Owner
# =========================================================

@app.delete(
    "/api/owner/categories/<int:category_id>"
)
@owner_required
def delete_category(category_id):

    try:

        with get_db() as conn:

            if using_postgres():

                category = fetchone(
                    conn,
                    """
                    SELECT *
                    FROM categories
                    WHERE id = %s
                    """,
                    (category_id,)
                )

            else:

                category = fetchone(
                    conn,
                    """
                    SELECT *
                    FROM categories
                    WHERE id = ?
                    """,
                    (category_id,)
                )

            if not category:

                return jsonify({
                    "error": "التصنيف غير موجود."
                }), 404

            if category["is_default"]:

                return jsonify({
                    "error": (
                        "لا يمكن حذف "
                        "التصنيفات الأساسية."
                    )
                }), 400

            if using_postgres():

                result = fetchone(
                    conn,
                    """
                    SELECT COUNT(*) AS count
                    FROM scripts
                    WHERE LOWER(TRIM(category))
                        = LOWER(TRIM(%s))
                    """,
                    (category["name"],)
                )

            else:

                result = fetchone(
                    conn,
                    """
                    SELECT COUNT(*) AS count
                    FROM scripts
                    WHERE LOWER(TRIM(category))
                        = LOWER(TRIM(?))
                    """,
                    (category["name"],)
                )

            count = int(
                result["count"]
            )

            if count > 0:

                return jsonify({
                    "error": (
                        "لا يمكن حذف التصنيف لأنه يحتوي "
                        "على سكربتات. انقل السكربتات أولاً."
                    )
                }), 400

            if using_postgres():

                conn.execute(
                    """
                    DELETE FROM categories
                    WHERE id = %s
                    """,
                    (category_id,)
                )

            else:

                conn.execute(
                    """
                    DELETE FROM categories
                    WHERE id = ?
                    """,
                    (category_id,)
                )

            return jsonify({
                "success": True
            })

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while deleting category:",
            error
        )

        return jsonify({
            "success": False,
            "error": "حدث خطأ في قاعدة البيانات."
        }), 500


# =========================================================
# Public Scripts
# =========================================================

@app.get("/api/scripts")
def get_scripts():

    try:

        with get_db() as conn:

            rows = fetchall(
                conn,
                """
                SELECT *
                FROM scripts
                ORDER BY
                    featured DESC,
                    id DESC
                """
            )

            return jsonify([
                row_to_script(row)
                for row in rows
            ])

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while loading scripts:",
            error
        )

        return jsonify({
            "error": "تعذر تحميل السكربتات."
        }), 500


# =========================================================
# Single Script
# =========================================================

@app.get(
    "/api/scripts/<int:script_id>"
)
def get_script(script_id):

    try:

        with get_db() as conn:

            if using_postgres():

                row = fetchone(
                    conn,
                    """
                    SELECT *
                    FROM scripts
                    WHERE id = %s
                    """,
                    (script_id,)
                )

            else:

                row = fetchone(
                    conn,
                    """
                    SELECT *
                    FROM scripts
                    WHERE id = ?
                    """,
                    (script_id,)
                )

            if not row:

                return jsonify({
                    "error": "السكربت غير موجود."
                }), 404

            return jsonify(
                row_to_script(row)
            )

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while loading script:",
            error
        )

        return jsonify({
            "error": "تعذر تحميل السكربت."
        }), 500


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

    category = clean_text(
        data.get("category"),
        100
    )

    featured = bool(
        data.get(
            "featured",
            False
        )
    )

    try:

        with get_db() as conn:

            # -------------------------------------------------
            # Optional category
            # -------------------------------------------------

            if category:

                if using_postgres():

                    category_exists = fetchone(
                        conn,
                        """
                        SELECT id, name
                        FROM categories
                        WHERE LOWER(name) = LOWER(%s)
                        """,
                        (category,)
                    )

                else:

                    category_exists = fetchone(
                        conn,
                        """
                        SELECT id, name
                        FROM categories
                        WHERE LOWER(name) = LOWER(?)
                        """,
                        (category,)
                    )

                if not category_exists:

                    return jsonify({
                        "error": (
                            "التصنيف المحدد غير موجود."
                        )
                    }), 400

                category = category_exists["name"]

            # -------------------------------------------------
            # Insert
            # -------------------------------------------------

            if using_postgres():

                row = fetchone(
                    conn,
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
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        title,
                        description,
                        category,
                        game,
                        code,
                        image,
                        featured,
                        "Fime",
                    )
                )

            else:

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

                script_id = cursor.lastrowid

                row = fetchone(
                    conn,
                    """
                    SELECT *
                    FROM scripts
                    WHERE id = ?
                    """,
                    (script_id,)
                )

            return jsonify({
                "success": True,
                "script": row_to_script(row)
            }), 201

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while creating script:",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات "
                "أثناء نشر السكربت."
            )
        }), 500


# =========================================================
# Update Script — Owner
# =========================================================

@app.put(
    "/api/owner/scripts/<int:script_id>"
)
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
        data.get(
            "featured",
            False
        )
    )

    try:

        with get_db() as conn:

            # -------------------------------------------------
            # Existing script
            # -------------------------------------------------

            if using_postgres():

                existing = fetchone(
                    conn,
                    """
                    SELECT id
                    FROM scripts
                    WHERE id = %s
                    """,
                    (script_id,)
                )

            else:

                existing = fetchone(
                    conn,
                    """
                    SELECT id
                    FROM scripts
                    WHERE id = ?
                    """,
                    (script_id,)
                )

            if not existing:

                return jsonify({
                    "error": "السكربت غير موجود."
                }), 404

            # -------------------------------------------------
            # Optional category
            # -------------------------------------------------

            if category:

                if using_postgres():

                    category_exists = fetchone(
                        conn,
                        """
                        SELECT id, name
                        FROM categories
                        WHERE LOWER(name) = LOWER(%s)
                        """,
                        (category,)
                    )

                else:

                    category_exists = fetchone(
                        conn,
                        """
                        SELECT id, name
                        FROM categories
                        WHERE LOWER(name) = LOWER(?)
                        """,
                        (category,)
                    )

                if not category_exists:

                    return jsonify({
                        "error": (
                            "التصنيف المحدد غير موجود."
                        )
                    }), 400

                category = category_exists["name"]

            # -------------------------------------------------
            # Update
            # -------------------------------------------------

            if using_postgres():

                row = fetchone(
                    conn,
                    """
                    UPDATE scripts
                    SET
                        title = %s,
                        description = %s,
                        category = %s,
                        game = %s,
                        code = %s,
                        image = %s,
                        featured = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        title,
                        description,
                        category,
                        game,
                        code,
                        image,
                        featured,
                        script_id,
                    )
                )

            else:

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

                row = fetchone(
                    conn,
                    """
                    SELECT *
                    FROM scripts
                    WHERE id = ?
                    """,
                    (script_id,)
                )

            return jsonify({
                "success": True,
                "script": row_to_script(row)
            })

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while updating script:",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات "
                "أثناء تعديل السكربت."
            )
        }), 500


# =========================================================
# Delete Script — Owner
# =========================================================

@app.delete(
    "/api/owner/scripts/<int:script_id>"
)
@owner_required
def delete_script(script_id):

    try:

        with get_db() as conn:

            if using_postgres():

                existing = fetchone(
                    conn,
                    """
                    SELECT id
                    FROM scripts
                    WHERE id = %s
                    """,
                    (script_id,)
                )

            else:

                existing = fetchone(
                    conn,
                    """
                    SELECT id
                    FROM scripts
                    WHERE id = ?
                    """,
                    (script_id,)
                )

            if not existing:

                return jsonify({
                    "error": "السكربت غير موجود."
                }), 404

            if using_postgres():

                conn.execute(
                    """
                    DELETE FROM scripts
                    WHERE id = %s
                    """,
                    (script_id,)
                )

            else:

                conn.execute(
                    """
                    DELETE FROM scripts
                    WHERE id = ?
                    """,
                    (script_id,)
                )

            return jsonify({
                "success": True
            })

    except Exception as error:

        print(
            f"❌ {database_error_name()} "
            f"error while deleting script:",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات "
                "أثناء حذف السكربت."
            )
        }), 500


# =========================================================
# Health Check
# =========================================================

@app.get("/api/health")
def health():

    try:

        with get_db() as conn:

            if using_postgres():

                fetchone(
                    conn,
                    "SELECT 1"
                )

            else:

                fetchone(
                    conn,
                    "SELECT 1"
                )

        return jsonify({
            "status": "ok",
            "database": (
                "postgresql"
                if using_postgres()
                else "sqlite"
            )
        })

    except Exception as error:

        print(
            "❌ Database health check failed:",
            error
        )

        return jsonify({
            "status": "error"
        }), 500


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