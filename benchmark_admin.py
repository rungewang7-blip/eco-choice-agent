"""Small admin API. File lock serializes configuration changes and collection across workers."""
import hmac
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from scripts.collect_benchmark import run
from source_security import secure_fetch, validate_url

LEGACY_CATEGORIES = {'cso_transport_2019': 'transport', 'seai_energy': 'home_energy',
                     'diet': 'diet', 'consumer_items': 'consumer_items'}


class Source(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[A-Za-z0-9_-]+$', min_length=1, max_length=80)
    category: Literal['transport', 'diet', 'home_energy', 'consumer_items']
    url: str | None = Field(default=None, max_length=2048)
    format: Literal['html', 'csv', 'json']
    enabled: StrictBool = False

    @model_validator(mode='after')
    def check_url(self):
        if self.enabled and not self.url:
            raise ValueError('Enabled sources need a URL')
        if self.url:
            validate_url(self.url)
        return self


def authorize(authorization: str | None = Header(default=None)):
    token = os.getenv('ECO_ADMIN_TOKEN', '')
    if len(token) < 32:
        raise HTTPException(503, 'Admin access disabled: configure ECO_ADMIN_TOKEN with at least 32 characters')
    if not authorization or not hmac.compare_digest(authorization.encode(), ('Bearer ' + token).encode()):
        raise HTTPException(401, 'Administrator token required', headers={'WWW-Authenticate': 'Bearer'})


def router(data_dir=None):
    root = Path(data_dir or Path(__file__).parent / 'data')
    config = root / 'sources.json'
    api = APIRouter(prefix='/admin/benchmark', dependencies=[Depends(authorize)])

    @contextmanager
    def locked():
        root.mkdir(parents=True, exist_ok=True)
        lock = root / '.source-manager.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise HTTPException(409, 'Collection or source update already running') from None
        try:
            os.close(fd)
            yield
        except (OSError, ValueError, KeyError, TypeError):
            raise HTTPException(503, 'Source storage or pipeline unavailable; check server files') from None
        finally:
            lock.unlink(missing_ok=True)

    def read():
        document = json.loads(config.read_text(encoding='utf-8-sig'))
        sources = document['sources']
        if not isinstance(sources, list) or any(not isinstance(s, dict) or 'id' not in s for s in sources):
            raise ValueError('Invalid source configuration')
        return document

    def save(document):
        # Keep all existing advanced extraction fields and top-level metadata.
        fd, name = tempfile.mkstemp(dir=root, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as output:
                json.dump(document, output, ensure_ascii=False, indent=2, allow_nan=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, config)
        finally:
            Path(name).unlink(missing_ok=True)

    @api.get('/sources')
    def list_sources():
        with locked():
            return {'sources': [dict(s, category=s.get('category', LEGACY_CATEGORIES.get(s['id'])))
                                for s in read()['sources']]}

    @api.post('/sources', status_code=201)
    def add(source: Source):
        with locked():
            document = read()
            if any(s['id'] == source.id for s in document['sources']):
                raise HTTPException(409, 'Source ID already exists')
            if len(document['sources']) >= 32:
                raise HTTPException(422, 'Maximum 32 sources')
            document['sources'].append(source.model_dump())
            save(document)
            return source

    @api.put('/sources/{source_id}')
    def update(source_id: str, source: Source):
        if source_id != source.id:
            raise HTTPException(422, 'Source ID cannot be changed')
        with locked():
            document = read()
            for item in document['sources']:
                if item['id'] == source_id:
                    item.update(source.model_dump())
                    save(document)
                    return item
            raise HTTPException(404, 'Source not found')

    @api.delete('/sources/{source_id}', status_code=204)
    def delete(source_id: str):
        with locked():
            document = read()
            items = document['sources']
            document['sources'] = [s for s in items if s['id'] != source_id]
            if len(items) == len(document['sources']):
                raise HTTPException(404, 'Source not found')
            save(document)

    @api.post('/collect')
    def collect():
        with locked():
            document = read()
            if len(document['sources']) > 32:
                raise HTTPException(422, 'Maximum 32 sources per run')
            _, report = run(config, root / 'reports', fetcher=secure_fetch)
            return report

    @api.get('/report')
    def report():
        with locked():
            reports = sorted((root / 'reports').glob('*/quality_report.json'))
            if not reports:
                raise HTTPException(404, 'No quality report yet')
            return json.loads(reports[-1].read_text(encoding='utf-8'))

    return api
