import json
import socket
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from main import create_app
from source_security import public_addresses, secure_fetch, validate_url

TOKEN = 'test-secret-' * 4
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
PREFIX = '/admin/benchmark'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ECO_ADMIN_TOKEN', TOKEN)
    monkeypatch.setenv('BENCHMARK_ALLOWED_HOSTS', 'www.cso.ie')
    (tmp_path / 'sources.json').write_text(json.dumps({'version': 1, 'sources': []}))
    return TestClient(create_app(admin_data_dir=tmp_path))


def source(**kwargs):
    return dict({'id': 'test', 'category': 'transport', 'url': 'https://www.cso.ie/data.csv',
                 'format': 'csv', 'enabled': False}, **kwargs)


@pytest.mark.parametrize('method,path', [('get','/sources'),('post','/sources'),
    ('put','/sources/test'),('delete','/sources/test'),('post','/collect'),('get','/report')])
def test_admin_required(client, method, path):
    response = getattr(client, method)(PREFIX + path)
    assert response.status_code == 401
    assert getattr(client, method)(PREFIX + path, headers={'Authorization': 'Bearer wrong'}).status_code == 401


def test_disabled_without_configuration(client, monkeypatch):
    monkeypatch.delenv('ECO_ADMIN_TOKEN')
    assert client.get(PREFIX + '/sources', headers=HEADERS).status_code == 503


def test_crud_preserves_advanced_config(client, tmp_path):
    path = tmp_path / 'sources.json'
    original = source()
    original.update(fields={'value': 'Distance'}, metadata={'unit': 'km'}, note='Keep me')
    path.write_text(json.dumps({'version': 7, 'sources': [original]}))
    assert client.get(PREFIX+'/sources', headers=HEADERS).json()['sources'][0]['note'] == 'Keep me'
    assert client.post(PREFIX+'/sources', headers=HEADERS, json=source()).status_code == 409
    assert client.put(PREFIX+'/sources/test', headers=HEADERS, json=source(enabled=True)).status_code == 200
    saved = json.loads(path.read_text())
    assert saved['version'] == 7
    assert saved['sources'][0]['fields'] == {'value': 'Distance'}
    assert saved['sources'][0]['metadata'] == {'unit': 'km'}
    assert client.put(PREFIX+'/sources/test', headers=HEADERS, json=source(enabled=False)).status_code == 200
    assert client.delete(PREFIX+'/sources/test', headers=HEADERS).status_code == 204
    assert client.delete(PREFIX+'/sources/test', headers=HEADERS).status_code == 404
    assert client.post(PREFIX+'/sources', headers=HEADERS, json=source()).status_code == 201


def test_read_preserves_disabled_legacy_sources(client, tmp_path):
    path = tmp_path / 'sources.json'
    legacy = [{'id': key, 'enabled': False, 'url': None, 'format': 'csv',
               'fields': {}, 'metadata': {}}
              for key in ('cso_transport_2019', 'seai_energy', 'diet', 'consumer_items')]
    path.write_text(json.dumps({'sources': legacy}))
    before = path.read_bytes()
    response = client.get(PREFIX+'/sources', headers=HEADERS)
    assert response.status_code == 200
    assert [s['category'] for s in response.json()['sources']] == [
        'transport', 'home_energy', 'diet', 'consumer_items']
    assert all(s['enabled'] is False for s in response.json()['sources'])
    assert path.read_bytes() == before


@pytest.mark.parametrize('method,path', [('post', '/sources'), ('put', '/sources/test')])
def test_failed_disk_write_never_returns_success(client, tmp_path, monkeypatch, method, path):
    config = tmp_path / 'sources.json'
    config.write_text(json.dumps({'sources': [source()] if method == 'put' else []}))
    before = config.read_bytes()
    monkeypatch.setattr('benchmark_admin.os.replace', Mock(side_effect=OSError('Disk unavailable')))
    response = getattr(client, method)(PREFIX+path, headers=HEADERS, json=source(enabled=True))
    assert response.status_code == 503
    assert config.read_bytes() == before
    assert not (tmp_path / '.source-manager.lock').exists()
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('change', [dict(id='../x'),dict(category='other'),dict(format='xml'),
    dict(enabled='false'),dict(enabled=True,url=None),dict(url='http://www.cso.ie/'),
    dict(url='https://www.cso.ie.evil.com/'),dict(url='https://user@www.cso.ie/'),
    dict(url='https://www.cso.ie:8443/'),dict(url='https://127.0.0.1/'),dict(extra='x')])
def test_validation(client, change):
    assert client.post(PREFIX+'/sources', headers=HEADERS, json=source(**change)).status_code == 422


def test_lock_and_corrupt_storage(client, tmp_path):
    lock = tmp_path / '.source-manager.lock'
    lock.touch()
    assert client.post(PREFIX+'/collect', headers=HEADERS).status_code == 409
    assert client.post(PREFIX+'/sources', headers=HEADERS, json=source()).status_code == 409
    lock.unlink()
    (tmp_path/'sources.json').write_text('invalid')
    assert client.get(PREFIX+'/sources', headers=HEADERS).status_code == 503
    assert not lock.exists()


def test_real_pipeline_with_fixture_transport(client, tmp_path, monkeypatch):
    fixtures = Path(__file__).parent/'fixtures'
    document = json.loads((Path(__file__).parents[1]/'data/sources.demo.json').read_text(encoding='utf-8'))
    for s in document['sources']:
        s['demo'] = False
    (tmp_path/'sources.json').write_text(json.dumps(document))
    monkeypatch.setattr('benchmark_admin.secure_fetch', lambda s: ((fixtures/s['fixture']).read_bytes(), s['url']))
    assert client.get(PREFIX+'/report', headers=HEADERS).status_code == 404
    result = client.post(PREFIX+'/collect', headers=HEADERS)
    assert result.status_code == 200
    report = result.json()
    assert all(report['counts'][s] > 0 for s in ('PASS','REVIEW','REJECT'))
    assert client.get(PREFIX+'/report', headers=HEADERS).json() == report
    assert len(list((tmp_path/'reports').glob('*/quality_report.md'))) == 1


def test_failure_is_reported(client, tmp_path, monkeypatch):
    (tmp_path/'sources.json').write_text(json.dumps({'sources':[source(enabled=True)]}))
    monkeypatch.setattr('benchmark_admin.secure_fetch', Mock(side_effect=ValueError('Blocked address')))
    report = client.post(PREFIX+'/collect', headers=HEADERS).json()
    assert report['sources'][0]['status'] == 'FAILED'
    assert 'Blocked address' in report['sources'][0]['error']
    assert report['counts'] == {'PASS':0,'REVIEW':0,'REJECT':0}


@pytest.mark.parametrize('ip', ['127.0.0.1','10.0.0.1','169.254.169.254','::1','fc00::1','::ffff:127.0.0.1'])
def test_private_dns_blocked(monkeypatch, ip):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(0,0,0,'',(ip,443))])
    with pytest.raises(ValueError):
        public_addresses('www.cso.ie')


def test_redirect_never_followed(monkeypatch):
    monkeypatch.setattr('source_security.public_addresses', lambda host: ['93.184.216.34'])
    conn = Mock()
    conn.getresponse.return_value.status = 302
    factory = Mock(return_value=conn)
    monkeypatch.setattr('source_security.PinnedHTTPS', factory)
    with pytest.raises(ValueError, match='redirects'):
        secure_fetch(source())
    factory.assert_called_once_with('www.cso.ie', '93.184.216.34')
    conn.request.assert_called_once()
    conn.close.assert_called_once()


def test_connection_pins_ip_but_checks_hostname(monkeypatch):
    from source_security import PinnedHTTPS
    sock, context = Mock(), Mock()
    monkeypatch.setattr(socket, 'socket', Mock(return_value=sock))
    monkeypatch.setattr('ssl.create_default_context', Mock(return_value=context))
    connection = PinnedHTTPS('www.cso.ie', '93.184.216.34')
    connection.connect()
    sock.connect.assert_called_once_with(('93.184.216.34',443))
    context.wrap_socket.assert_called_once_with(sock, server_hostname='www.cso.ie')
