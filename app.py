import os
import re
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


# =========================================================
# Fime Scripts — app.py
# Turso / libSQL ONLY
# =========================================================

try:
    import libsql
except ImportError:
    libsql = None


BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# Environment
# =========================================================

SESSION_SECRET = os.getenv("SESSION_SECRET")

OWNER_USERNAME = os.getenv("OWNER_USERNAME")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD")

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


# =========================================================
# Environment Validation
# =========================================================

if libsql is None:
    raise RuntimeError(
        "❌ مكتبة libsql غير مثبتة. "
        "أضف libsql إلى requirements.txt."
    )


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


if not TURSO_DATABASE_URL:
    raise RuntimeError(
        "❌ TURSO_DATABASE_URL غير موجود في Environment Variables."
    )


if not TURSO_AUTH_TOKEN:
    raise RuntimeError(
        "❌ TURSO_AUTH_TOKEN غير موجود في Environment Variables."
    )


# =========================================================
# Flask
# =========================================================

app = Flask(
    __name__,
    static_folder=None,
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
# Turso Row Helper
# =========================================================

class Row(dict):
    """
    يحول نتائج libSQL إلى كائن يسمح بالوصول هكذا:

        row["title"]

    بدل الاعتماد على dict_row الخاص بـ psycopg.
    """

    def __getattr__(self, key):

        try:
            return self[key]

        except KeyError:
            raise AttributeError(key)


# =========================================================
# Cursor Helpers
# =========================================================

def cursor_rows(cursor):
    """
    يحول نتائج libSQL إلى Rows بأسماء الأعمدة.
    """

    rows = cursor.fetchall()

    description = cursor.description or []

    columns = [
        column[0]
        for column in description
    ]

    result = []

    for raw_row in rows:

        if isinstance(raw_row, dict):
            result.append(
                Row(raw_row)
            )
            continue

        result.append(
            Row(
                zip(
                    columns,
                    raw_row
                )
            )
        )

    return result


def cursor_one(cursor):
    """
    يرجع صفًا واحدًا كـ Row.
    """

    raw_row = cursor.fetchone()

    if raw_row is None:
        return None

    description = cursor.description or []

    columns = [
        column[0]
        for column in description
    ]

    if isinstance(raw_row, dict):
        return Row(raw_row)

    return Row(
        zip(
            columns,
            raw_row
        )
    )


# =========================================================
# Database Connection
# =========================================================

@contextmanager
def get_db():

    conn = None

    try:

        conn = libsql.connect(
            database=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )

        yield conn

        if hasattr(conn, "commit"):
            conn.commit()

    except Exception:

        if conn is not None:

            try:

                if hasattr(conn, "rollback"):
                    conn.rollback()

            except Exception:
                pass

        raise

    finally:

        if conn is not None:

            try:
                conn.close()

            except Exception:
                pass


# =========================================================
# Database Helpers
# =========================================================

def fetchall(
    conn,
    query,
    params=(),
):

    cursor = conn.execute(
        query,
        params,
    )

    return cursor_rows(cursor)


def fetchone(
    conn,
    query,
    params=(),
):

    cursor = conn.execute(
        query,
        params,
    )

    return cursor_one(cursor)


def last_insert_id(conn):

    row = fetchone(
        conn,
        """
        SELECT last_insert_rowid() AS id
        """
    )

    if not row:
        return None

    return row["id"]


# =========================================================
# Database Type
# =========================================================

def database_error_name():

    return "Turso / libSQL"


# =========================================================
# Schema Helpers
# =========================================================

def get_table_columns(
    conn,
    table_name,
):

    rows = fetchall(
        conn,
        f"""
        PRAGMA table_info({table_name})
        """
    )

    return {
        row["name"]
        for row in rows
    }


def add_column_if_missing(
    conn,
    table_name,
    columns,
    column_name,
    definition,
):

    if column_name not in columns:

        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )

        columns.add(column_name)


# =========================================================
# Scripts Migration
# =========================================================

def migrate_scripts_table(conn):

    columns = get_table_columns(
        conn,
        "scripts",
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


    # -----------------------------------------------------
    # title from old name column if available
    # -----------------------------------------------------

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
        "TEXT DEFAULT ''",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "category",
        "TEXT DEFAULT ''",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "game",
        "TEXT DEFAULT ''",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "code",
        "TEXT DEFAULT ''",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "image",
        "TEXT DEFAULT ''",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "featured",
        "INTEGER NOT NULL DEFAULT 0",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "author",
        "TEXT DEFAULT 'Fime'",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "created_at",
        "TEXT DEFAULT ''",
    )

    add_column_if_missing(
        conn,
        "scripts",
        columns,
        "updated_at",
        "TEXT DEFAULT ''",
    )


    # -----------------------------------------------------
    # Clean old values
    # -----------------------------------------------------

    conn.execute(
        """
        UPDATE scripts
        SET title = 'بدون عنوان'
        WHERE title IS NULL
           OR TRIM(title) = ''
        """
    )

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
# Turso Database Initialization
# =========================================================

def init_db():

    print(
        "🟢 Fime Scripts Database: Turso / libSQL"
    )

    with get_db() as conn:

        # =================================================
        # Categories
        # =================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT
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
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                game TEXT NOT NULL DEFAULT '',
                code TEXT NOT NULL DEFAULT '',
                image TEXT NOT NULL DEFAULT '',
                featured INTEGER NOT NULL DEFAULT 0,
                author TEXT NOT NULL DEFAULT 'Fime',
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # =================================================
        # Migration
        # =================================================

        migrate_scripts_table(conn)


        # =================================================
        # Category Index
        # =================================================

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            categories_name_lower_unique
            ON categories (LOWER(name))
            """
        )


        # =================================================
        # Script Indexes
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
            (
                name,
                is_default
            )
            SELECT
                ?,
                1
            WHERE NOT EXISTS (
                SELECT 1
                FROM categories
                WHERE LOWER(name) = LOWER(?)
            )
            """,
            (
                "Scripts",
                "Scripts",
            ),
        )


        conn.execute(
            """
            INSERT INTO categories
            (
                name,
                is_default
            )
            SELECT
                ?,
                1
            WHERE NOT EXISTS (
                SELECT 1
                FROM categories
                WHERE LOWER(name) = LOWER(?)
            )
            """,
            (
                "Hacks",
                "Hacks",
            ),
        )


        # =================================================
        # Import categories already used by scripts
        # =================================================

        old_categories = fetchall(
            conn,
            """
            SELECT DISTINCT category
            FROM scripts
            WHERE category IS NOT NULL
              AND TRIM(category) != ''
            """
        )


        for row in old_categories:

            category_name = str(
                row["category"]
            ).strip()

            if not category_name:
                continue

            conn.execute(
                """
                INSERT INTO categories
                (
                    name,
                    is_default
                )
                SELECT
                    ?,
                    0
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM categories
                    WHERE LOWER(name) = LOWER(?)
                )
                """,
                (
                    category_name,
                    category_name,
                ),
            )


        if hasattr(conn, "commit"):
            conn.commit()


# =========================================================
# Utility Helpers
# =========================================================

def clean_text(
    value,
    max_length=10000,
):

    if value is None:
        return ""

    value = str(value).strip()

    return value[:max_length]


def clean_title(value):

    return clean_text(
        value,
        200,
    )


def valid_image_url(value):

    value = clean_text(
        value,
        2000,
    )

    if not value:
        return ""

    # Local image
    if value.startswith("/"):
        return value

    # HTTPS
    if re.match(
        r"^https://",
        value,
        re.IGNORECASE,
    ):
        return value

    # HTTP
    if re.match(
        r"^http://",
        value,
        re.IGNORECASE,
    ):
        return value

    return ""


# =========================================================
# Script Row Conversion
# =========================================================

def row_to_script(row):

    if row is None:
        return None

    return {
        "id": row["id"],

        "title": (
            row["title"] or ""
        ),

        "description": (
            row["description"] or ""
        ),

        "category": (
            row["category"] or ""
        ),

        "game": (
            row["game"] or ""
        ),

        "code": (
            row["code"] or ""
        ),

        "image": (
            row["image"] or ""
        ),

        "featured": bool(
            row["featured"]
        ),

        "author": (
            row["author"]
            or "Fime"
        ),

        "created_at": str(
            row["created_at"]
            or ""
        ),

        "updated_at": str(
            row["updated_at"]
            or ""
        ),
    }


# =========================================================
# Owner Authentication
# =========================================================

def owner_required(function):

    @wraps(function)
    def wrapper(
        *args,
        **kwargs,
    ):

        if (
            session.get(
                "owner_authenticated"
            )
            is not True
        ):

            return jsonify({
                "error": "غير مصرح"
            }), 401

        return function(
            *args,
            **kwargs,
        )

    return wrapper


# =========================================================
# Public Pages
# =========================================================

@app.route("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "index.html",
    )


@app.route("/index.html")
def index_html():

    return send_from_directory(
        BASE_DIR,
        "index.html",
    )


@app.route("/scripts")
def scripts_page():

    return send_from_directory(
        BASE_DIR,
        "scripts.html",
    )


@app.route("/hacks")
def hacks_page():

    return send_from_directory(
        BASE_DIR,
        "hacks.html",
    )


@app.route("/script")
def script_page():

    return send_from_directory(
        BASE_DIR,
        "script.html",
    )


@app.route("/owner")
def owner_page():

    return send_from_directory(
        BASE_DIR,
        "owner.html",
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
        filename,
    )


@app.route("/js/<path:filename>")
def js_files(filename):

    if ".." in filename:
        abort(404)

    return send_from_directory(
        BASE_DIR / "js",
        filename,
    )


@app.route("/assets/<path:filename>")
def asset_files(filename):

    if ".." in filename:
        abort(404)

    return send_from_directory(
        BASE_DIR / "assets",
        filename,
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
        "app2.py",
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
        200,
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
            "error": "بيانات الدخول غير صحيحة.",
        }), 401


    if not check_password_hash(
        OWNER_PASSWORD_HASH,
        password,
    ):

        return jsonify({
            "success": False,
            "error": "بيانات الدخول غير صحيحة.",
        }), 401


    session.clear()

    session.permanent = True

    session[
        "owner_authenticated"
    ] = True


    return jsonify({
        "success": True,
        "message": "تم تسجيل الدخول بنجاح.",
    })


# =========================================================
# Owner Logout
# =========================================================

@app.post("/api/owner/logout")
@owner_required
def owner_logout():

    session.clear()

    return jsonify({
        "success": True,
    })


# =========================================================
# Owner Session
# =========================================================

@app.get("/api/owner/me")
def owner_me():

    authenticated = (
        session.get(
            "owner_authenticated"
        )
        is True
    )

    return jsonify({
        "authenticated": authenticated,
    })


# =========================================================
# Categories — Public
# =========================================================

@app.get("/api/categories")
def get_categories():

    try:

        with get_db() as conn:

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
                        or ""
                    ),
                }

                for row in rows

            ]


            return jsonify(
                categories
            )


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while loading categories:",
            error,
        )

        return jsonify({
            "error": "تعذر تحميل التصنيفات.",
        }), 500


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
        100,
    )


    if not name:

        return jsonify({
            "error": "اكتب اسم التصنيف.",
        }), 400


    try:

        with get_db() as conn:

            existing = fetchone(
                conn,
                """
                SELECT id
                FROM categories
                WHERE LOWER(name) = LOWER(?)
                """,
                (name,),
            )


            if existing:

                return jsonify({
                    "error": (
                        "هذا التصنيف موجود بالفعل."
                    ),
                }), 409


            cursor = conn.execute(
                """
                INSERT INTO categories
                (
                    name,
                    is_default
                )
                VALUES (?, 0)
                """,
                (name,),
            )


            category_id = (
                getattr(
                    cursor,
                    "lastrowid",
                    None,
                )
            )


            if category_id is None:

                category_id = last_insert_id(
                    conn
                )


            return jsonify({

                "success": True,

                "category": {
                    "id": category_id,
                    "name": name,
                    "is_default": False,
                },

            }), 201


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while creating category:",
            error,
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات."
            ),
        }), 500


# =========================================================
# Delete Category — Owner
# =========================================================

@app.delete(
    "/api/owner/categories/<int:category_id>"
)
@owner_required
def delete_category(
    category_id,
):

    try:

        with get_db() as conn:

            category = fetchone(
                conn,
                """
                SELECT *
                FROM categories
                WHERE id = ?
                """,
                (category_id,),
            )


            if not category:

                return jsonify({
                    "error": "التصنيف غير موجود.",
                }), 404


            if category["is_default"]:

                return jsonify({
                    "error": (
                        "لا يمكن حذف "
                        "التصنيفات الأساسية."
                    ),
                }), 400


            result = fetchone(
                conn,
                """
                SELECT COUNT(*) AS count
                FROM scripts
                WHERE LOWER(TRIM(category))
                    = LOWER(TRIM(?))
                """,
                (category["name"],),
            )


            count = int(
                result["count"]
            )


            if count > 0:

                return jsonify({
                    "error": (
                        "لا يمكن حذف التصنيف لأنه يحتوي "
                        "على سكربتات. انقل السكربتات أولاً."
                    ),
                }), 400


            conn.execute(
                """
                DELETE FROM categories
                WHERE id = ?
                """,
                (category_id,),
            )


            return jsonify({
                "success": True,
            })


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while deleting category:",
            error,
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات."
            ),
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
            "❌ Turso / libSQL "
            "error while loading scripts:",
            error,
        )

        return jsonify({
            "error": "تعذر تحميل السكربتات.",
        }), 500


# =========================================================
# Single Script
# =========================================================

@app.get(
    "/api/scripts/<int:script_id>"
)
def get_script(
    script_id,
):

    try:

        with get_db() as conn:

            row = fetchone(
                conn,
                """
                SELECT *
                FROM scripts
                WHERE id = ?
                """,
                (script_id,),
            )


            if not row:

                return jsonify({
                    "error": "السكربت غير موجود.",
                }), 404


            return jsonify(
                row_to_script(row)
            )


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while loading script:",
            error,
        )

        return jsonify({
            "error": "تعذر تحميل السكربت.",
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
            "error": "اكتب اسم السكربت.",
        }), 400


    description = clean_text(
        data.get("description"),
        10000,
    )


    game = clean_text(
        data.get("game"),
        200,
    )


    code = clean_text(
        data.get("code"),
        500000,
    )


    image = valid_image_url(
        data.get("image")
    )


    category = clean_text(
        data.get("category"),
        100,
    )


    featured = bool(
        data.get(
            "featured",
            False,
        )
    )


    try:

        with get_db() as conn:

            # -------------------------------------------------
            # Category
            # -------------------------------------------------

            if category:

                category_exists = fetchone(
                    conn,
                    """
                    SELECT
                        id,
                        name
                    FROM categories
                    WHERE LOWER(name)
                        = LOWER(?)
                    """,
                    (category,),
                )


                if not category_exists:

                    return jsonify({
                        "error": (
                            "التصنيف المحدد غير موجود."
                        ),
                    }), 400


                category = (
                    category_exists["name"]
                )


            # -------------------------------------------------
            # Insert
            # -------------------------------------------------

            conn.execute(
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
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
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
                ),
            )


            script_id = last_insert_id(
                conn
            )


            row = fetchone(
                conn,
                """
                SELECT *
                FROM scripts
                WHERE id = ?
                """,
                (script_id,),
            )


            return jsonify({

                "success": True,

                "script": row_to_script(
                    row
                ),

            }), 201


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while creating script:",
            error,
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات "
                "أثناء نشر السكربت."
            ),
        }), 500


# =========================================================
# Update Script — Owner
# =========================================================

@app.put(
    "/api/owner/scripts/<int:script_id>"
)
@owner_required
def update_script(
    script_id,
):

    data = request.get_json(
        silent=True
    ) or {}


    title = clean_title(
        data.get("title")
    )


    if not title:

        return jsonify({
            "error": "اسم السكربت مطلوب.",
        }), 400


    description = clean_text(
        data.get("description"),
        10000,
    )


    game = clean_text(
        data.get("game"),
        200,
    )


    code = clean_text(
        data.get("code"),
        500000,
    )


    image = valid_image_url(
        data.get("image")
    )


    category = clean_text(
        data.get("category"),
        100,
    )


    featured = bool(
        data.get(
            "featured",
            False,
        )
    )


    try:

        with get_db() as conn:

            # -------------------------------------------------
            # Existing Script
            # -------------------------------------------------

            existing = fetchone(
                conn,
                """
                SELECT id
                FROM scripts
                WHERE id = ?
                """,
                (script_id,),
            )


            if not existing:

                return jsonify({
                    "error": "السكربت غير موجود.",
                }), 404


            # -------------------------------------------------
            # Category
            # -------------------------------------------------

            if category:

                category_exists = fetchone(
                    conn,
                    """
                    SELECT
                        id,
                        name
                    FROM categories
                    WHERE LOWER(name)
                        = LOWER(?)
                    """,
                    (category,),
                )


                if not category_exists:

                    return jsonify({
                        "error": (
                            "التصنيف المحدد غير موجود."
                        ),
                    }), 400


                category = (
                    category_exists["name"]
                )


            # -------------------------------------------------
            # Update
            # -------------------------------------------------

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
                ),
            )


            row = fetchone(
                conn,
                """
                SELECT *
                FROM scripts
                WHERE id = ?
                """,
                (script_id,),
            )


            return jsonify({

                "success": True,

                "script": row_to_script(
                    row
                ),

            })


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while updating script:",
            error,
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات "
                "أثناء تعديل السكربت."
            ),
        }), 500


# =========================================================
# Delete Script — Owner
# =========================================================

@app.delete(
    "/api/owner/scripts/<int:script_id>"
)
@owner_required
def delete_script(
    script_id,
):

    try:

        with get_db() as conn:

            existing = fetchone(
                conn,
                """
                SELECT id
                FROM scripts
                WHERE id = ?
                """,
                (script_id,),
            )


            if not existing:

                return jsonify({
                    "error": "السكربت غير موجود.",
                }), 404


            conn.execute(
                """
                DELETE FROM scripts
                WHERE id = ?
                """,
                (script_id,),
            )


            return jsonify({
                "success": True,
            })


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "error while deleting script:",
            error,
        )

        return jsonify({
            "success": False,
            "error": (
                "حدث خطأ في قاعدة البيانات "
                "أثناء حذف السكربت."
            ),
        }), 500


# =========================================================
# Health Check
# =========================================================

@app.get("/api/health")
def health():

    try:

        with get_db() as conn:

            fetchone(
                conn,
                "SELECT 1"
            )


        return jsonify({

            "status": "ok",

            "database": "turso/libsql",

        })


    except Exception as error:

        print(
            "❌ Turso / libSQL "
            "health check failed:",
            error,
        )

        return jsonify({

            "status": "error",

            "database": "turso/libsql",

        }), 500


# =========================================================
# Initialize Database
# =========================================================

init_db()


# =========================================================
# Local Development / Render
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "8080",
        )
    )


    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )