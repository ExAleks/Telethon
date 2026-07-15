"""
database.py — Лёгкая SQLite-обёртка: настройки, логи.
"""
import os
import sqlite3
import threading
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'telethon.db')
_lock = threading.Lock()


def _open():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    with _lock:
        conn = _open()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            );
            CREATE TABLE IF NOT EXISTS parser_config (
                id INTEGER PRIMARY KEY CHECK (id=1),
                enabled INTEGER DEFAULT 0,
                api_id INTEGER,
                api_hash TEXT,
                phone TEXT,
                session_string TEXT,
                phone_code_hash TEXT,
                last_parse TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT, message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        conn.close()


def get_setting(key: str, default: str = '') -> str:
    with _lock:
        conn = _open()
        row = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        conn.close()
    return row[0] if row else default


def set_setting(key: str, value):
    with _lock:
        conn = _open()
        conn.execute(
            'INSERT INTO settings(key,value) VALUES(?,?) '
            'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (key, str(value)),
        )
        conn.commit()
        conn.close()


def add_log(level: str, message: str):
    with _lock:
        conn = _open()
        conn.execute('INSERT INTO logs(level,message) VALUES(?,?)', (level, message))
        conn.commit()
        conn.close()


def get_config() -> dict:
    with _lock:
        conn = _open()
        row = conn.execute('SELECT * FROM parser_config WHERE id=1').fetchone()
        conn.close()
    if row:
        return {
            'enabled': bool(row[1]), 'api_id': row[2], 'api_hash': row[3],
            'phone': row[4], 'session_string': row[5], 'phone_code_hash': row[6],
            'last_parse': row[7],
        }
    return {k: None for k in ('enabled', 'api_id', 'api_hash', 'phone',
                               'session_string', 'phone_code_hash', 'last_parse')}


def update_config(**kwargs):
    cols = {'enabled', 'api_id', 'api_hash', 'phone', 'session_string',
            'phone_code_hash', 'last_parse'}
    safe = {k: v for k, v in kwargs.items() if k in cols}
    if not safe:
        return
    with _lock:
        conn = _open()
        clause = ', '.join(f'{k}=?' for k in safe)
        conn.execute(f'UPDATE parser_config SET {clause} WHERE id=1', list(safe.values()))
        conn.commit()
        conn.close()
