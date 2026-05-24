from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collectibles (
            id TEXT PRIMARY KEY,
            slug TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'ruin',
            location_style TEXT NOT NULL DEFAULT 'terracotta',
            title TEXT NOT NULL DEFAULT '',
            subtitle TEXT NOT NULL DEFAULT '',
            short_description TEXT NOT NULL DEFAULT '',
            site_name TEXT NOT NULL DEFAULT '',
            province TEXT NOT NULL DEFAULT '',
            district TEXT NOT NULL DEFAULT '',
            era_label TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            hero_url TEXT NOT NULL DEFAULT '',
            thumbnail_url TEXT NOT NULL DEFAULT '',
            share_url TEXT NOT NULL DEFAULT '',
            image_alt TEXT NOT NULL DEFAULT '',
            story TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            material_keywords TEXT NOT NULL DEFAULT '[]',
            collector_note TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            is_featured INTEGER NOT NULL DEFAULT 0,
            generation_status TEXT NOT NULL DEFAULT 'idle',
            related_ids TEXT NOT NULL DEFAULT '[]',
            latitude REAL NOT NULL DEFAULT 0,
            longitude REAL NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL DEFAULT '',
            weather_condition TEXT NOT NULL DEFAULT '',
            temperature REAL NOT NULL DEFAULT 0,
            wind_direction TEXT NOT NULL DEFAULT '',
            wind_level INTEGER NOT NULL DEFAULT 0,
            aqi INTEGER NOT NULL DEFAULT 0,
            aqi_level TEXT NOT NULL DEFAULT '',
            location_name TEXT NOT NULL DEFAULT '',
            mint_number INTEGER NOT NULL DEFAULT 0,
            earliest_imprint TEXT NOT NULL DEFAULT '',
            golden_line TEXT NOT NULL DEFAULT '',
            call_to_action TEXT NOT NULL DEFAULT '',
            view_count INTEGER NOT NULL DEFAULT 0,
            share_count INTEGER NOT NULL DEFAULT 0,
            save_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    # Migration: add call_to_action column for existing databases
    try:
        conn.execute("ALTER TABLE collectibles ADD COLUMN call_to_action TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.execute("""
        CREATE TABLE IF NOT EXISTS location_counters (
            location_hash TEXT PRIMARY KEY,
            location_name TEXT NOT NULL DEFAULT '',
            province TEXT NOT NULL DEFAULT '',
            district TEXT NOT NULL DEFAULT '',
            counter INTEGER NOT NULL DEFAULT 0,
            earliest_imprint TEXT NOT NULL DEFAULT '',
            era_label TEXT NOT NULL DEFAULT '',
            location_style TEXT NOT NULL DEFAULT 'terracotta',
            suggested_kind TEXT NOT NULL DEFAULT 'ruin'
        )
    """)
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("tags", "material_keywords", "related_ids"):
        if key in d and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    d["is_favorite"] = bool(d.get("is_favorite", False))
    d["is_featured"] = bool(d.get("is_featured", False))
    return d


def insert_collectible(data: dict) -> dict:
    conn = get_db()
    data.setdefault("id", str(uuid.uuid4()))
    now = datetime.now(timezone.utc).isoformat()
    data.setdefault("created_at", now)
    data.setdefault("updated_at", now)
    data.setdefault("generation_status", "idle")
    data.setdefault("slug", "")
    data.setdefault("kind", "ruin")
    data.setdefault("location_style", "terracotta")
    data.setdefault("title", "")
    data.setdefault("subtitle", "")
    data.setdefault("short_description", "")
    data.setdefault("site_name", "")
    data.setdefault("province", "")
    data.setdefault("district", "")
    data.setdefault("era_label", "")
    data.setdefault("hero_url", "")
    data.setdefault("thumbnail_url", "")
    data.setdefault("share_url", "")
    data.setdefault("image_alt", "")
    data.setdefault("story", "")
    data.setdefault("collector_note", None)
    data.setdefault("is_favorite", False)
    data.setdefault("is_featured", False)
    data.setdefault("view_count", 0)
    data.setdefault("share_count", 0)
    data.setdefault("save_count", 0)
    data.setdefault("related_ids", [])
    data.setdefault("latitude", 0.0)
    data.setdefault("longitude", 0.0)
    data.setdefault("timestamp", "")
    data.setdefault("weather_condition", "")
    data.setdefault("temperature", 0.0)
    data.setdefault("wind_direction", "")
    data.setdefault("wind_level", 0)
    data.setdefault("aqi", 0)
    data.setdefault("aqi_level", "")
    data.setdefault("location_name", "")
    data.setdefault("mint_number", 0)
    data.setdefault("earliest_imprint", "")
    data.setdefault("golden_line", "")
    data.setdefault("call_to_action", "")

    for k in ("tags", "material_keywords", "related_ids"):
        if isinstance(data.get(k), list):
            data[k] = json.dumps(data[k], ensure_ascii=False)
    data["is_favorite"] = 1 if data["is_favorite"] else 0
    data["is_featured"] = 1 if data["is_featured"] else 0

    columns = [
        "id", "slug", "kind", "location_style", "title", "subtitle",
        "short_description", "site_name", "province", "district", "era_label",
        "created_at", "updated_at", "hero_url", "thumbnail_url", "share_url",
        "image_alt", "story", "tags", "material_keywords", "collector_note",
        "is_favorite", "is_featured", "generation_status", "related_ids",
        "latitude", "longitude", "timestamp", "weather_condition", "temperature",
        "wind_direction", "wind_level", "aqi", "aqi_level", "location_name",
        "mint_number", "earliest_imprint", "golden_line", "call_to_action",
        "view_count", "share_count", "save_count",
    ]
    placeholders = ", ".join(f":{c}" for c in columns)
    conn.execute(
        f"INSERT INTO collectibles ({', '.join(columns)}) VALUES ({placeholders})",
        {c: data.get(c) for c in columns},
    )
    conn.commit()
    conn.close()
    return data


def update_collectible(collectible_id: str, data: dict) -> Optional[dict]:
    conn = get_db()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    for k in ("tags", "material_keywords", "related_ids"):
        if k in data and isinstance(data[k], list):
            data[k] = json.dumps(data[k], ensure_ascii=False)
    if "is_favorite" in data:
        data["is_favorite"] = 1 if data["is_favorite"] else 0
    if "is_featured" in data:
        data["is_featured"] = 1 if data["is_featured"] else 0

    set_clauses = [f"{k} = :{k}" for k in data.keys()]
    data["id"] = collectible_id
    conn.execute(
        f"UPDATE collectibles SET {', '.join(set_clauses)} WHERE id = :id",
        data,
    )
    conn.commit()
    conn.close()
    return get_collectible_by_id(collectible_id)


def get_collectible_by_id(collectible_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM collectibles WHERE id = ?", (collectible_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def list_collectibles(
    kind: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conn = get_db()
    conditions = []
    params: list = []
    if kind and kind != "all":
        conditions.append("kind = ?")
        params.append(kind)
    if status and status != "all":
        conditions.append("generation_status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    order = "ORDER BY created_at DESC" if sort == "newest" else "ORDER BY created_at ASC"
    rows = conn.execute(
        f"SELECT * FROM collectibles {where} {order} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def delete_collectible(collectible_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM collectibles WHERE id = ?", (collectible_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ── Location counter ──────────────────────────────────────────

def _hash_location(lat: float, lng: float) -> str:
    return f"{round(lat, 3)}_{round(lng, 3)}"


def get_or_create_location_counter(lat: float, lng: float) -> dict:
    conn = get_db()
    loc_hash = _hash_location(lat, lng)
    row = conn.execute(
        "SELECT * FROM location_counters WHERE location_hash = ?", (loc_hash,)
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO location_counters (location_hash, counter, earliest_imprint) VALUES (?, 0, ?)",
            (loc_hash, datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        )
        conn.commit()
        conn.close()
        return {
            "location_hash": loc_hash,
            "location_name": "",
            "province": "",
            "district": "",
            "counter": 0,
            "earliest_imprint": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "era_label": "",
            "location_style": "terracotta",
            "suggested_kind": "ruin",
        }
    conn.close()
    return dict(row)


def increment_location_counter(lat: float, lng: float, location_name: str = "", province: str = "", district: str = "", era_label: str = "", location_style: str = "terracotta", suggested_kind: str = "ruin") -> dict:
    conn = get_db()
    loc_hash = _hash_location(lat, lng)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT * FROM location_counters WHERE location_hash = ?", (loc_hash,)
    ).fetchone()
    if not row:
        conn.execute(
            """INSERT INTO location_counters
               (location_hash, location_name, province, district, counter, earliest_imprint, era_label, location_style, suggested_kind)
               VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
            (loc_hash, location_name, province, district, now_str, era_label, location_style, suggested_kind),
        )
    else:
        conn.execute(
            """UPDATE location_counters SET
               counter = counter + 1,
               location_name = CASE WHEN location_name = '' AND ? != '' THEN ? ELSE location_name END,
               province = CASE WHEN province = '' AND ? != '' THEN ? ELSE province END
               WHERE location_hash = ?""",
            (location_name, location_name, province, province, loc_hash),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM location_counters WHERE location_hash = ?", (loc_hash,)).fetchone()
    conn.close()
    return dict(row)


def get_location_counter(lat: float, lng: float) -> dict:
    return get_or_create_location_counter(lat, lng)


def update_location_counter_meta(lat: float, lng: float, location_name: str = "", province: str = "", district: str = "", era_label: str = "", location_style: str = "terracotta", suggested_kind: str = "ruin") -> dict:
    """Update location metadata on counter WITHOUT incrementing."""
    conn = get_db()
    loc_hash = _hash_location(lat, lng)
    row = conn.execute("SELECT * FROM location_counters WHERE location_hash = ?", (loc_hash,)).fetchone()
    if not row:
        conn.execute(
            """INSERT INTO location_counters
               (location_hash, location_name, province, district, counter, earliest_imprint, era_label, location_style, suggested_kind)
               VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (loc_hash, location_name, province, district,
             datetime.now(timezone.utc).strftime("%Y-%m-%d"),
             era_label, location_style, suggested_kind),
        )
    else:
        conn.execute(
            """UPDATE location_counters SET
               location_name = CASE WHEN location_name = '' AND ? != '' THEN ? ELSE location_name END,
               province = CASE WHEN province = '' AND ? != '' THEN ? ELSE province END,
               district = CASE WHEN district = '' AND ? != '' THEN ? ELSE district END,
               era_label = CASE WHEN era_label = '' AND ? != '' THEN ? ELSE era_label END,
               location_style = CASE WHEN location_style = 'terracotta' AND ? != 'terracotta' THEN ? ELSE location_style END,
               suggested_kind = CASE WHEN suggested_kind = 'ruin' AND ? != 'ruin' THEN ? ELSE suggested_kind END
               WHERE location_hash = ?""",
            (location_name, location_name, province, province,
             district, district, era_label, era_label,
             location_style, location_style, suggested_kind, suggested_kind,
             loc_hash),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM location_counters WHERE location_hash = ?", (loc_hash,)).fetchone()
    conn.close()
    return dict(row)


def increment_view_count(collectible_id: str) -> None:
    """Increment view_count WITHOUT updating updated_at timestamp."""
    conn = get_db()
    conn.execute(
        "UPDATE collectibles SET view_count = view_count + 1 WHERE id = ?",
        (collectible_id,),
    )
    conn.commit()
    conn.close()


def toggle_favorite(collectible_id: str) -> Optional[bool]:
    """Toggle is_favorite. Returns new state or None if not found."""
    conn = get_db()
    row = conn.execute(
        "SELECT is_favorite FROM collectibles WHERE id = ?", (collectible_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    new_val = 0 if row[0] else 1
    conn.execute(
        "UPDATE collectibles SET is_favorite = ? WHERE id = ?",
        (new_val, collectible_id),
    )
    conn.commit()
    conn.close()
    return bool(new_val)


def count_collectibles(kind: Optional[str] = None, status: Optional[str] = None) -> int:
    """Count collectibles matching filters."""
    conn = get_db()
    conditions = []
    params: list = []
    if kind and kind != "all":
        conditions.append("kind = ?")
        params.append(kind)
    if status and status != "all":
        conditions.append("generation_status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    row = conn.execute(f"SELECT COUNT(*) FROM collectibles {where}", params).fetchone()
    conn.close()
    return row[0] if row else 0


def get_all_location_counters() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM location_counters WHERE counter > 0 ORDER BY counter DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
