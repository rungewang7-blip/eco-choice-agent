"""Public reference API and authenticated source manager. Importing this module does not modify the database."""
import json
import os
import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from reference import DATA, factors


def create_app(db_path=None, admin_data_dir=None):
    app = FastAPI(title='EcoChoice reference API', version='1.0.0')
    database = db_path or os.getenv('ECO_DB', str(Path(__file__).parent / 'eco.db'))
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])
    from benchmark_admin import router
    app.include_router(router(admin_data_dir))

    def read(version):
        try:
            return factors(database, version)
        except LookupError:
            raise HTTPException(404, 'Factor version not found')
        except (sqlite3.Error, ValueError, TypeError):
            raise HTTPException(503, 'Reference data unavailable; run the CSV import')

    @app.get('/factors')
    def get_factors(version: str | None = Query(default=None, max_length=80)):
        rows = read(version)
        return {'factorVersion': rows[0]['factorVersion'], 'factors': rows}

    @app.get('/catalog')
    def get_catalog(version: str | None = Query(default=None, max_length=80)):
        rows = read(version)
        return {'factorVersion': rows[0]['factorVersion'], 'items': [r for r in rows if r['category'] in ('food', 'items')]}

    @app.get('/benchmark')
    def get_benchmark():
        try:
            result = json.loads((DATA / 'benchmark.json').read_text(encoding='utf-8'))
            read(result['factorVersion'])
            return result
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(503, 'Benchmark data unavailable') from None

    @app.get('/health')
    def health():
        read(None)
        return {'status': 'ok'}

    return app


app = create_app()
