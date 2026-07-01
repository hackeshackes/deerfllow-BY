from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

DEFAULT_VOICE_CONFIG = {
    "stt_enabled": True,
    "tts_enabled": True,
    "stt_language": "zh",
    "stt_model_size": "small",
    "tts_voice": "zh-CN-XiaoxiaoNeural",
    "tts_speed": 1.0,
}

_db_path = Path(__file__).resolve().parent / "voice.db"
_db_lock = threading.Lock()


def _get_db() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_lock:
        conn = _get_db()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS voice_configs (
                user_id TEXT PRIMARY KEY,
                stt_enabled INTEGER NOT NULL DEFAULT 1,
                tts_enabled INTEGER NOT NULL DEFAULT 1,
                stt_language TEXT NOT NULL DEFAULT 'zh',
                stt_model_size TEXT NOT NULL DEFAULT 'small',
                tts_voice TEXT NOT NULL DEFAULT 'zh-CN-XiaoxiaoNeural',
                tts_speed REAL NOT NULL DEFAULT 1.0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """
        )
        # Migration: add stt_model_size column if missing (for existing databases)
        cursor = conn.execute("PRAGMA table_info(voice_configs)")
        columns = [row[1] for row in cursor.fetchall()]
        if "stt_model_size" not in columns:
            conn.execute("ALTER TABLE voice_configs ADD COLUMN stt_model_size TEXT NOT NULL DEFAULT 'small'")
        conn.commit()
        conn.close()


_init_db()


def _row_to_config(row: sqlite3.Row | None) -> dict[str, bool | float | str]:
    if row is None:
        return dict(DEFAULT_VOICE_CONFIG)
    return {
        "stt_enabled": bool(row["stt_enabled"]),
        "tts_enabled": bool(row["tts_enabled"]),
        "stt_language": row["stt_language"],
        "stt_model_size": row["stt_model_size"],
        "tts_voice": row["tts_voice"],
        "tts_speed": float(row["tts_speed"]),
    }


def get_voice_config(user_id: str) -> dict[str, bool | float | str]:
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM voice_configs WHERE user_id = ?", (user_id,)).fetchone()
        return _row_to_config(row)
    finally:
        conn.close()


def upsert_voice_config(user_id: str, config: dict[str, bool | float | str]) -> dict[str, bool | float | str]:
    merged = {**DEFAULT_VOICE_CONFIG, **config}
    now = time.time()
    conn = _get_db()
    try:
        with _db_lock:
            existing = conn.execute("SELECT created_at FROM voice_configs WHERE user_id = ?", (user_id,)).fetchone()
            created_at = float(existing["created_at"]) if existing else now
            conn.execute(
                """
                INSERT INTO voice_configs (
                    user_id, stt_enabled, tts_enabled, stt_language, stt_model_size, tts_voice, tts_speed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    stt_enabled = excluded.stt_enabled,
                    tts_enabled = excluded.tts_enabled,
                    stt_language = excluded.stt_language,
                    stt_model_size = excluded.stt_model_size,
                    tts_voice = excluded.tts_voice,
                    tts_speed = excluded.tts_speed,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    1 if bool(merged["stt_enabled"]) else 0,
                    1 if bool(merged["tts_enabled"]) else 0,
                    str(merged["stt_language"]),
                    str(merged["stt_model_size"]),
                    str(merged["tts_voice"]),
                    float(merged["tts_speed"]),
                    created_at,
                    now,
                ),
            )
            conn.commit()
        return get_voice_config(user_id)
    finally:
        conn.close()
