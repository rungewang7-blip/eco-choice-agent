import csv
import sqlite3
import pytest
from fastapi.testclient import TestClient
from main import create_app
from reference import DATA, FIELDS, factors, import_csv


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'test.db'
    import_csv(DATA / 'factors.csv', path)
    return path


def test_endpoints(database):
    client = TestClient(create_app(database))
    result = client.get('/factors').json()
    assert result['factors']
    assert all(set(row) == set(FIELDS) for row in result['factors'])
    assert all(row['factorVersion'] == result['factorVersion'] for row in result['factors'])
    catalog = client.get('/catalog').json()
    assert catalog['items']
    assert all(row['category'] in ('food', 'items') for row in catalog['items'])
    assert client.get('/benchmark').json()['scenario']['inputs']
    assert client.get('/health').status_code == 200
    assert client.get('/factors?version=missing').status_code == 404
    assert client.post('/factors', json={}).status_code == 405


@pytest.mark.parametrize('key,value', [('source',''), ('unit','unknown'), ('kgCO2ePerUnit','0'), ('kgCO2ePerUnit','-1'), ('kgCO2ePerUnit','NaN'), ('kgCO2ePerUnit','inf'), ('category','other'), ('sourceUrl','javascript:alert(1)'), ('sourceYear','wrong')])
def test_invalid_csv_is_atomic(database, tmp_path, key, value):
    before = factors(database)
    rows = [dict(row, factorVersion='invalid') for row in before]
    rows[-1][key] = value
    path = tmp_path / 'invalid.csv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        import_csv(path, database)
    assert factors(database) == before


def test_immutable_versions(database):
    with pytest.raises(sqlite3.IntegrityError):
        import_csv(DATA / 'factors.csv', database)


def test_missing_database(tmp_path):
    assert TestClient(create_app(tmp_path / 'missing.db')).get('/factors').status_code == 503
    assert not (tmp_path / 'missing.db').exists()


def test_cors(database):
    client = TestClient(create_app(database))
    assert client.get('/factors', headers={'Origin': 'http://localhost:5173'}).headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'access-control-allow-origin' not in client.get('/factors', headers={'Origin': 'https://evil.example'}).headers


def write_csv(path, rows, fields=FIELDS):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_relational_storage_and_versions(database, tmp_path):
    before = factors(database)
    rows = [dict(r, factorVersion='second') for r in before]
    rows[0]['kgCO2ePerUnit'] = 123.45
    path = tmp_path / 'second.csv'
    write_csv(path, rows)
    import_csv(path, database)
    assert factors(database)[0]['kgCO2ePerUnit'] == 123.45
    assert factors(database, before[0]['factorVersion']) == before
    with sqlite3.connect(database) as conn:
        assert conn.execute('SELECT COUNT(*) FROM carbon_factors').fetchone()[0] == len(rows)*2
        assert [r[1] for r in conn.execute('PRAGMA table_info(carbon_factors)')] == FIELDS


@pytest.mark.parametrize('kind', ['empty', 'duplicate', 'mixed', 'header', 'duplicate_header'])
def test_invalid_batch(database, tmp_path, kind):
    before = factors(database)
    rows = [dict(r, factorVersion='bad') for r in before]
    fields = FIELDS
    if kind == 'empty': rows = []
    if kind == 'duplicate': rows.append(rows[0])
    if kind == 'mixed': rows[0]['factorVersion'] = 'other'
    if kind == 'header': fields = FIELDS[:-1]; rows = []
    if kind == 'duplicate_header': fields = FIELDS + ['source']
    path = tmp_path / 'bad.csv'
    write_csv(path, rows, fields)
    with pytest.raises(ValueError): import_csv(path, database)
    assert factors(database) == before


def test_legacy_migration_preserves_other_tables(tmp_path):
    import json
    from reference import validate
    path = tmp_path / 'legacy.db'
    with (DATA / 'factors.csv').open(encoding='utf-8') as stream:
        old = [dict(validate(r), factorVersion='legacy') for r in csv.DictReader(stream)]
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE test (name TEXT)')
        conn.execute("INSERT INTO test VALUES ('keep')")
        conn.execute('CREATE TABLE factor_sets (sequence INTEGER PRIMARY KEY, version TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)')
        conn.execute('INSERT INTO factor_sets(version,payload) VALUES (?,?)', ('legacy', json.dumps(old)))
    import_csv(DATA / 'factors.csv', path)
    assert len(factors(path, 'legacy')) == len(old)
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT name FROM test').fetchone()[0] == 'keep'


def test_benchmark_pins_version(database, tmp_path):
    client = TestClient(create_app(database))
    benchmark = client.get('/benchmark').json()
    assert benchmark['nationalBenchmarkReady'] is False
    assert benchmark['annualKgCO2e'] is None
    assert benchmark['assumptions'] and benchmark['sources']
    rows = [dict(r, factorVersion='new') for r in factors(database)]
    path = tmp_path / 'new.csv'
    write_csv(path, rows)
    import_csv(path, database)
    assert client.get('/benchmark').json()['factorVersion'] == benchmark['factorVersion']
    assert client.get('/factors', params={'version': benchmark['factorVersion']}).status_code == 200


def test_corrupt_database_returns_safe_error(database):
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE carbon_factors SET unit='bad'")
    response = TestClient(create_app(database)).get('/factors')
    assert response.status_code == 503
    assert 'Traceback' not in response.text


def test_cli_safe_error(tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(DATA.parent / 'import_factors.py'), str(tmp_path/'secret.csv'), '--db', str(tmp_path/'test.db')], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'secret.csv' not in result.stderr
    assert 'Traceback' not in result.stderr


def test_original_table_migration_preserves_data(tmp_path):
    path = tmp_path / 'original.db'
    from reference import validate
    with (DATA / 'factors.csv').open(encoding='utf-8') as stream:
        old = dict(validate(next(csv.DictReader(stream))), factorVersion='original')
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute("INSERT INTO test(name) VALUES ('keep')")
        conn.execute('''CREATE TABLE carbon_factors (
            id TEXT PRIMARY KEY, category TEXT NOT NULL, activity TEXT NOT NULL,
            unit TEXT NOT NULL, kgCO2ePerUnit REAL NOT NULL CHECK(kgCO2ePerUnit > 0),
            source TEXT NOT NULL, sourceYear INTEGER NOT NULL,
            sourceUrl TEXT NOT NULL, factorVersion TEXT NOT NULL)''')
        conn.execute('INSERT INTO carbon_factors VALUES (?,?,?,?,?,?,?,?,?)', tuple(old[k] for k in FIELDS))
    import_csv(DATA / 'factors.csv', path)
    assert factors(path, 'original') == [old]
    assert factors(path)[0]['factorVersion'] == '2026-10-f1'
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT name FROM test').fetchone()[0] == 'keep'
        assert conn.execute('SELECT COUNT(*) FROM carbon_factors_legacy').fetchone()[0] == 1


def test_bootstrap_is_repeatable_but_rejects_changed_data(database):
    from bootstrap import bootstrap
    assert bootstrap(database) == '2026-10-f1'
    with sqlite3.connect(database) as conn:
        conn.execute('UPDATE carbon_factors SET kgCO2ePerUnit=123')
    with pytest.raises(ValueError, match='differs'):
        bootstrap(database)
