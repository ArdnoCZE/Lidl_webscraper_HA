"""
Jednoduchá SQLite vrstva - žádné ORM, ať je to čitelné a snadno laditelné.
"""
import os
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

# V HA add-onu je /data perzistentní úložiště (přežije restart i update
# add-onu). Mimo add-on (např. lokální vývoj) padá zpátky na ./data.
DB_DIR = Path(os.environ.get("DB_DIR", Path(__file__).resolve().parent.parent / "data"))
DB_PATH = DB_DIR / "lidl.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS watch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,            -- 'keyword' nebo 'category'
    value TEXT NOT NULL,           -- hledaný text / interní klíč kategorie
    label TEXT NOT NULL,           -- lidsky čitelný název
    watch_shop INTEGER NOT NULL DEFAULT 1,
    watch_leaflet INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_key TEXT PRIMARY KEY,  -- stabilní klíč (např. URL nebo slug)
    watch_item_id INTEGER,
    name TEXT NOT NULL,
    url TEXT,
    image_url TEXT,
    latest_price REAL,
    currency TEXT DEFAULT 'CZK',
    latest_seen REAL,
    FOREIGN KEY(watch_item_id) REFERENCES watch_items(id)
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_key TEXT NOT NULL,
    price REAL,
    currency TEXT DEFAULT 'CZK',
    scraped_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS leaflet_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_item_id INTEGER,
    flyer_name TEXT,
    page_number INTEGER,
    matched_text TEXT,
    image_url TEXT,
    valid_from TEXT,
    valid_to TEXT,
    found_at REAL NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------- watch items ----------

def add_watch_item(kind: str, value: str, label: str, watch_shop=True, watch_leaflet=True):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO watch_items (kind, value, label, watch_shop, watch_leaflet, active, created_at) "
            "VALUES (?,?,?,?,?,1,?)",
            (kind, value, label, int(watch_shop), int(watch_leaflet), time.time()),
        )


def list_watch_items(active_only=True):
    with get_conn() as conn:
        q = "SELECT * FROM watch_items"
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY created_at DESC"
        return [dict(r) for r in conn.execute(q).fetchall()]


def set_watch_item_active(item_id: int, active: bool):
    with get_conn() as conn:
        conn.execute("UPDATE watch_items SET active=? WHERE id=?", (int(active), item_id))


def delete_watch_item(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM watch_items WHERE id=?", (item_id,))


# ---------- products / prices ----------

def upsert_product_price(product_key, watch_item_id, name, url, image_url, price, currency="CZK"):
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO products (product_key, watch_item_id, name, url, image_url, latest_price, currency, latest_seen)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(product_key) DO UPDATE SET
                name=excluded.name,
                url=excluded.url,
                image_url=excluded.image_url,
                latest_price=excluded.latest_price,
                currency=excluded.currency,
                latest_seen=excluded.latest_seen
            """,
            (product_key, watch_item_id, name, url, image_url, price, currency, now),
        )
        conn.execute(
            "INSERT INTO price_history (product_key, price, currency, scraped_at) VALUES (?,?,?,?)",
            (product_key, price, currency, now),
        )


def list_products():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM products ORDER BY latest_seen DESC"
        ).fetchall()]


def price_history_for(product_key, limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT price, currency, scraped_at FROM price_history "
            "WHERE product_key=? ORDER BY scraped_at DESC LIMIT ?",
            (product_key, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- leaflet matches ----------

def add_leaflet_match(watch_item_id, flyer_name, page_number, matched_text, image_url, valid_from, valid_to):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO leaflet_matches
               (watch_item_id, flyer_name, page_number, matched_text, image_url, valid_from, valid_to, found_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (watch_item_id, flyer_name, page_number, matched_text, image_url, valid_from, valid_to, time.time()),
        )


def clear_leaflet_matches():
    """Volá se před každým novým scrapem letáku, ať se nehromadí staré nálezy."""
    with get_conn() as conn:
        conn.execute("DELETE FROM leaflet_matches")


def list_leaflet_matches():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT lm.*, wi.label as watch_label FROM leaflet_matches lm "
            "LEFT JOIN watch_items wi ON wi.id = lm.watch_item_id "
            "ORDER BY lm.found_at DESC"
        ).fetchall()]
