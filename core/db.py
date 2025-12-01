# core/db.py
import sqlite3
from typing import Optional

from .utils import DATA_DIR, ensure_dir

# data/ klasörü garanti olsun
ensure_dir(DATA_DIR)

DB_PATH = DATA_DIR / "ArcSys.db"

# Uygulama boyu cache
ACTIVE_PROJECT_ID: Optional[int] = None


def get_connection() -> sqlite3.Connection:
    """Temel bağlantı fonksiyonu."""
    con = sqlite3.connect(DB_PATH)
    return con


def _ensure_base_tables(con: sqlite3.Connection) -> None:
    """projects ve app_settings tabloları yoksa oluştur."""
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            code                 TEXT UNIQUE,
            name                 TEXT,
            center_x             REAL,
            center_y             REAL,
            center_z             REAL,
            coordinate_system_id INTEGER
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            id                INTEGER PRIMARY KEY CHECK (id = 1),
            active_project_id INTEGER
        )
        """
    )

    con.commit()


def get_active_project_id(con: sqlite3.Connection | None = None) -> Optional[int]:
    """
    Bellekte ACTIVE_PROJECT_ID varsa onu döner.
    Yoksa app_settings'ten okur, o da yoksa ilk projeyi aktif sayar.
    """
    global ACTIVE_PROJECT_ID

    if ACTIVE_PROJECT_ID is not None:
        return ACTIVE_PROJECT_ID

    owns_con = con is None
    if con is None:
        con = get_connection()

    _ensure_base_tables(con)

    cur = con.cursor()
    cur.execute("SELECT active_project_id FROM app_settings WHERE id = 1")
    row = cur.fetchone()

    if row and row[0] is not None:
        ACTIVE_PROJECT_ID = int(row[0])
    else:
        cur.execute("SELECT id FROM projects ORDER BY id LIMIT 1")
        row = cur.fetchone()
        ACTIVE_PROJECT_ID = int(row[0]) if row else None

        if ACTIVE_PROJECT_ID is not None:
            cur.execute(
                """
                INSERT INTO app_settings (id, active_project_id)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET active_project_id = excluded.active_project_id
                """,
                (ACTIVE_PROJECT_ID,),
            )
            con.commit()

    if owns_con:
        con.close()

    return ACTIVE_PROJECT_ID


def insert_vector_layer(project_id: int, name: str, geojson: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO vector_layers (project_id, name, geojson)
        VALUES (?, ?, ?)
        """,
        (project_id, name, geojson),
    )
    conn.commit()
    layer_id = cur.lastrowid
    conn.close()
    return layer_id


def set_active_project_id(project_id: int) -> None:
    """Aktif projeyi değiştir."""
    global ACTIVE_PROJECT_ID

    con = get_connection()
    _ensure_base_tables(con)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO app_settings (id, active_project_id)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET active_project_id = excluded.active_project_id
        """,
        (project_id,),
    )
    con.commit()
    con.close()

    ACTIVE_PROJECT_ID = project_id
