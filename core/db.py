# core/db.py
"""
Veritabanı katmanı.

Bu dosyanın görevi:
- SQLite bağlantısını yönetmek
- Temel tabloları (projects, app_settings) garantiye almak
- Aktif proje bilgisini saklayıp okumak
- Genel SELECT / INSERT yardımcı fonksiyonları sağlamak
- Uygulamayı kullanan diğer katmanlar için basit, UI'dan bağımsız bir API sunmak
"""

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

from .utils import DATA_DIR, ensure_dir

# ---------------------------------------------------------------------------
# Temel yollar ve bağlantı ayarları
# ---------------------------------------------------------------------------

# data/ klasörü garanti olsun
ensure_dir(DATA_DIR)

DB_PATH = DATA_DIR / "ArcSys.db"

# Uygulama boyu cache
ACTIVE_PROJECT_ID: Optional[int] = None


def get_connection() -> sqlite3.Connection:
    """
    Yeni bir SQLite bağlantısı döner.

    - foreign_keys = ON
    - row_factory = sqlite3.Row (kolon isimleri ile erişim için)
    - busy_timeout = 5000 ms (5 sn boyunca kilidin açılmasını bekler)
    - journal_mode = WAL (daha az kilitlenme için)
    """
    con = sqlite3.connect(DB_PATH, timeout=5.0)
    con.row_factory = sqlite3.Row

    # Kilit sorunlarını azalt
    con.execute("PRAGMA foreign_keys = ON;")
    con.execute("PRAGMA busy_timeout = 5000;")
    con.execute("PRAGMA journal_mode = WAL;")

    return con


@contextmanager
def db_connection(
    con: Optional[sqlite3.Connection] = None,
) -> Iterator[sqlite3.Connection]:
    """
    Bağlantı context manager'ı.

    - Eğer dışarıdan bir bağlantı verilirse (con != None), onu kullanır ve
      commit/close yapmaz.
    - Eğer bağlantı verilmezse, kendisi açar; context çıkışında commit + close yapar.

    Örnek:

        with db_connection() as con:
            con.execute("INSERT ...")

        dışarıdan bağlantı ile:

        con = get_connection()
        with db_connection(con) as c:
            c.execute("INSERT ...")
        con.commit()
        con.close()
    """
    owns_con = con is None
    if con is None:
        con = get_connection()

    try:
        yield con
        if owns_con:
            con.commit()
    finally:
        if owns_con:
            con.close()


# ---------------------------------------------------------------------------
# Temel tablo kurulumları
# ---------------------------------------------------------------------------


def _ensure_base_tables(con: sqlite3.Connection) -> None:
    """
    projects ve app_settings tabloları yoksa oluşturur.
    Bu fonksiyon, aktif proje ile ilgili fonksiyonlar tarafından kullanılır.
    """
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


# ---------------------------------------------------------------------------
# Aktif proje yönetimi
# ---------------------------------------------------------------------------


def get_active_project_id(
    con: sqlite3.Connection | None = None,
) -> Optional[int]:
    """
    Aktif proje ID'sini döner.

    - Önce RAM'deki ACTIVE_PROJECT_ID'ye bakar.
    - Yoksa app_settings tablosundan okur.
    - app_settings'te de yoksa, projects tablosundaki ilk projeyi aktif kabul eder.
    """
    global ACTIVE_PROJECT_ID

    if ACTIVE_PROJECT_ID is not None:
        return ACTIVE_PROJECT_ID

    with db_connection(con) as c:
        _ensure_base_tables(c)
        cur = c.cursor()

        # app_settings'ten oku
        cur.execute("SELECT active_project_id FROM app_settings WHERE id = 1")
        row = cur.fetchone()

        if row and row["active_project_id"] is not None:
            ACTIVE_PROJECT_ID = int(row["active_project_id"])
            return ACTIVE_PROJECT_ID

        # app_settings yoksa / boşsa ilk projeyi aktif yap
        cur.execute("SELECT id FROM projects ORDER BY id LIMIT 1")
        row = cur.fetchone()
        ACTIVE_PROJECT_ID = int(row["id"]) if row else None

        if ACTIVE_PROJECT_ID is not None:
            cur.execute(
                """
                INSERT INTO app_settings (id, active_project_id)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET active_project_id = excluded.active_project_id
                """,
                (ACTIVE_PROJECT_ID,),
            )

    return ACTIVE_PROJECT_ID


def set_active_project_id(
    project_id: int, con: sqlite3.Connection | None = None
) -> None:
    """
    Aktif projeyi değiştirir.

    - Hem app_settings tablosuna yazar,
    - Hem de module-level cache (ACTIVE_PROJECT_ID) güncellenir.
    """
    global ACTIVE_PROJECT_ID

    with db_connection(con) as c:
        _ensure_base_tables(c)
        cur = c.cursor()
        cur.execute(
            """
            INSERT INTO app_settings (id, active_project_id)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET active_project_id = excluded.active_project_id
            """,
            (project_id,),
        )

    ACTIVE_PROJECT_ID = project_id


# ---------------------------------------------------------------------------
# Genel SQL yardımcıları (SELECT / INSERT / UPDATE)
# ---------------------------------------------------------------------------


def fetch_all(
    sql: str,
    params: Sequence[Any] | None = None,
    con: sqlite3.Connection | None = None,
) -> list[sqlite3.Row]:
    """
    Çoklu satır dönen SELECT sorguları için yardımcı.

    Örnek:
        rows = fetch_all("SELECT * FROM projects WHERE code LIKE ?", ("%T01%",))
    """
    if params is None:
        params = ()

    with db_connection(con) as c:
        cur = c.execute(sql, params)
        return cur.fetchall()


def fetch_one(
    sql: str,
    params: Sequence[Any] | None = None,
    con: sqlite3.Connection | None = None,
) -> Optional[sqlite3.Row]:
    """
    Tek satır dönen SELECT sorguları için yardımcı.
    """
    if params is None:
        params = ()

    with db_connection(con) as c:
        cur = c.execute(sql, params)
        return cur.fetchone()


def execute(
    sql: str,
    params: Sequence[Any] | None = None,
    con: sqlite3.Connection | None = None,
) -> None:
    """
    INSERT / UPDATE / DELETE gibi, geriye sonuç dönmeyen sorgular için.

    Örnek:
        execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, pid))
    """
    if params is None:
        params = ()

    with db_connection(con) as c:
        c.execute(sql, params)


def execute_and_get_id(
    sql: str,
    params: Sequence[Any] | None = None,
    con: sqlite3.Connection | None = None,
) -> int:
    """
    INSERT + lastrowid ihtiyacı için yardımcı.

    Örnek:
        project_id = execute_and_get_id(
            "INSERT INTO projects (code, name) VALUES (?, ?)",
            (code, name),
        )
    """
    if params is None:
        params = ()

    with db_connection(con) as c:
        cur = c.execute(sql, params)
        return int(cur.lastrowid)
