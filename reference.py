"""Immutable reference sets; atomic CSV import."""
import csv
import json
import math
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ['id', 'category', 'activity', 'unit', 'kgCO2ePerUnit', 'source', 'sourceYear', 'sourceUrl', 'factorVersion']
UNITS = {'kg', 'kWh', 'km', 'passenger.km', 'count', 'day'}
DATA = Path(__file__).parent / 'data'


def validate(row):
    if set(row) != set(FIELDS) or any(v is None or str(v).strip() == '' for v in row.values()):
        raise ValueError('All factor fields including source are required')
    result = {k: str(v).strip() for k, v in row.items()}
    if result['unit'] not in UNITS or result['category'] not in {'transport', 'food', 'home', 'items'}:
        raise ValueError('Unknown unit or category')
    try:
        value = float(result['kgCO2ePerUnit'])
        year = int(result['sourceYear'])
    except (ValueError, OverflowError):
        raise ValueError('Invalid numeric factor or source year') from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Factor must be finite and positive')
    if not 1900 <= year <= 2100:
        raise ValueError('Invalid source year')
    url = urlparse(result['sourceUrl'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Source URL must be HTTPS')
    result.update(kgCO2ePerUnit=value, sourceYear=year)
    return result


def import_csv(csv_path, db_path):
    with open(csv_path, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or len(reader.fieldnames) != len(FIELDS) or set(reader.fieldnames) != set(FIELDS):
            raise ValueError('CSV header must contain exactly the nine factor fields')
        rows = [validate(row) for row in reader]
    if not rows or len({r['factorVersion'] for r in rows}) != 1:
        raise ValueError('Import exactly one non-empty version')
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate factor ID')
    version = rows[0]['factorVersion']
    with sqlite3.connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS factor_sets (sequence INTEGER PRIMARY KEY, version TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')
        # Preserve the original single-version table before enabling versioned IDs.
        columns = conn.execute('PRAGMA table_info(carbon_factors)').fetchall()
        old_rows = []
        if columns and [c[1] for c in columns if c[5]] == ['id']:
            if [c[1] for c in columns] != FIELDS:
                raise ValueError('Unexpected legacy factor schema')
            old_rows = [validate(dict(zip(FIELDS, row))) for row in
                        conn.execute('SELECT ' + ','.join(FIELDS) + ' FROM carbon_factors')]
            conn.execute('ALTER TABLE carbon_factors RENAME TO carbon_factors_legacy')
        conn.execute('''CREATE TABLE IF NOT EXISTS carbon_factors (
            id TEXT NOT NULL, category TEXT NOT NULL, activity TEXT NOT NULL,
            unit TEXT NOT NULL, kgCO2ePerUnit REAL NOT NULL CHECK(kgCO2ePerUnit > 0),
            source TEXT NOT NULL CHECK(length(trim(source)) > 0),
            sourceYear INTEGER NOT NULL, sourceUrl TEXT NOT NULL,
            factorVersion TEXT NOT NULL, PRIMARY KEY(factorVersion,id))''')
        for old_version in sorted({r['factorVersion'] for r in old_rows}):
            batch = [r for r in old_rows if r['factorVersion'] == old_version]
            conn.execute('INSERT INTO factor_sets(version,payload) VALUES (?,?)',
                         (old_version, json.dumps(batch)))
        # Migrate existing immutable JSON sets inside the same transaction.
        for old_version, payload in conn.execute('SELECT version,payload FROM factor_sets').fetchall():
            old_rows = [validate(r) for r in json.loads(payload)]
            if not old_rows or any(r['factorVersion'] != old_version for r in old_rows):
                raise ValueError('Invalid legacy factor set')
            conn.executemany('INSERT OR IGNORE INTO carbon_factors VALUES (?,?,?,?,?,?,?,?,?)',
                             [tuple(r[k] for k in FIELDS) for r in old_rows])
        conn.execute('INSERT INTO factor_sets(version,payload) VALUES (?,?)', (version, json.dumps(rows)))
        conn.executemany('INSERT INTO carbon_factors VALUES (?,?,?,?,?,?,?,?,?)',
                         [tuple(r[k] for k in FIELDS) for r in rows])
    return version


def factors(db_path, version=None):
    with sqlite3.connect(f'file:{Path(db_path).resolve().as_posix()}?mode=ro', uri=True) as conn:
        if version is None:
            row = conn.execute('SELECT version FROM factor_sets ORDER BY sequence DESC LIMIT 1').fetchone()
        else:
            row = conn.execute('SELECT version FROM factor_sets WHERE version=?', (version,)).fetchone()
        if row is None:
            raise LookupError('Factor version not found')
        rows = conn.execute('SELECT ' + ','.join(FIELDS) + ' FROM carbon_factors WHERE factorVersion=? ORDER BY id', (row[0],)).fetchall()
    if not rows:
        raise sqlite3.DatabaseError('Factor set has no rows')
    return [validate(dict(zip(FIELDS, r))) for r in rows]
