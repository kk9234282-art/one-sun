import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from flask import current_app, g


def now():
    return datetime.now(timezone.utc).isoformat()


def connect(path):
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    from .locality import derive
    db.create_function('pin_district',2,derive,deterministic=True)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    return db


def get_db():
    if 'db' not in g:
        g.db = connect(current_app.config['DATABASE'])
    return g.db


def init_db(db):
    from .sources import SOURCES
    db.executescript(Path(__file__).with_name('schema.sql').read_text())
    columns = {r['name'] for r in db.execute('PRAGMA table_info(companies)')}
    for column in ('roc','postal_code','subcategory','registered_class'):
        if column not in columns:
            db.execute(f'ALTER TABLE companies ADD COLUMN {column} TEXT')
    for key, value in SOURCES.items():
        db.execute('INSERT OR IGNORE INTO sources(id,name,url,mode) VALUES(?,?,?,?)',
                   (key, value['name'], value['url'], value['mode']))
    db.commit()
