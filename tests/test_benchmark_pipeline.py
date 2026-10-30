import hashlib
import json
from pathlib import Path
import pytest
from scripts.collect_benchmark import run, extract
from scripts.clean_benchmark import clean_record, FIELDS
from scripts.validate_benchmark import validate_records
from scripts.publish_benchmark import publish

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Tests must not access the network')
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('urllib.request.urlopen', forbidden)
    monkeypatch.setattr('scripts.collect_benchmark.urlopen', forbidden)


def source(kind='csv'):
    return {'id': kind, 'url': 'https://example.invalid/fixture', 'format': kind,
            'fixture': 'sample.' + kind, 'json_path': ['observations'],
            'fields': {k: k for k in FIELDS if k not in ('methodology_url', 'license')},
            'metadata': {'methodology_url': 'https://example.invalid/method', 'license': 'TEST ONLY'}}


def config(tmp_path, sources):
    path = tmp_path / 'sources.json'
    path.write_text(json.dumps({'sources': sources}), encoding='utf-8')
    return path


def test_all_formats_report_and_provenance(tmp_path):
    directory, report = run(config(tmp_path, [source(k) for k in ('csv', 'html', 'json')]),
                            tmp_path / 'reports', FIXTURES)
    assert report['counts'] == {'PASS': 1, 'REVIEW': 2, 'REJECT': 2}
    assert len(list((directory / 'raw').glob('*.bin'))) == 3
    assert (directory / 'quality_report.md').exists()
    assert (directory / 'quality_report.json').exists()
    for row in report['records']:
        assert row['source_url'] and row['original_location'] and row['raw_record']
        assert row['raw_sha256'] == hashlib.sha256(Path(row['raw_file']).read_bytes()).hexdigest()
        assert row['human_approved'] is False
    assert report['records'][1]['extraction_valid'] is True
    assert report['records'][1]['benchmark_candidate'] is False


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', 'abc', '', None, '1e999'])
def test_bad_values_rejected(value):
    raw = dict(extract((FIXTURES / 'sample.csv').read_bytes(), source())[0][0], value=value)
    row = clean_record(raw, source(), {'row': 2}, {})
    assert validate_records([row])[0]['status'] == 'REJECT'


def test_duplicates_all_review():
    raw, loc = extract((FIXTURES / 'sample.csv').read_bytes(), source())[0]
    row = clean_record(raw, source(), loc, {})
    assert [r['status'] for r in validate_records([row, row])] == ['REVIEW', 'REVIEW']


def test_failures_still_generate_report(tmp_path):
    bad = dict(source(), id='broken', fixture='missing.csv')
    directory, report = run(config(tmp_path, [bad, source('html')]), tmp_path / 'out', FIXTURES)
    assert [s['status'] for s in report['sources']] == ['FAILED', 'SUCCESS']
    assert (directory / 'quality_report.md').exists()


def test_bad_config_report(tmp_path):
    directory, report = run(config(tmp_path, [source(), source()]), tmp_path / 'out')
    assert report['sources'][0]['status'] == 'FAILED'
    assert (directory / 'quality_report.json').exists()


@pytest.mark.parametrize('payload', [b'<html>No tables</html>', b'<table><tr><td colspan="2">x</td></tr></table>'])
def test_unsupported_html_fails_closed(payload):
    with pytest.raises(ValueError):
        extract(payload, source('html'))


def test_fetch_failure_preserved(tmp_path):
    def fail(_):
        raise TimeoutError('offline')
    directory, report = run(config(tmp_path, [source()]), tmp_path / 'out', fetcher=fail)
    assert 'TimeoutError' in report['sources'][0]['error']
    assert (directory / 'quality_report.md').exists()


def make_approval(tmp_path, directory, report, ids=None):
    path = tmp_path / 'approval.json'
    path.write_text(json.dumps({'run_id': report['run_id'], 'reviewer': 'Test reviewer',
        'reason': 'Test only', 'approved_at': '2026-10-30T10:00:00+08:00',
        'report_sha256': hashlib.sha256((directory / 'quality_report.json').read_bytes()).hexdigest(),
        'record_ids': ids or [report['records'][0]['record_id']]}), encoding='utf-8')
    return path


def test_demo_cannot_publish(tmp_path):
    directory, report = run(config(tmp_path, [source()]), tmp_path / 'out', FIXTURES)
    with pytest.raises(ValueError, match='non-demo'):
        publish(directory / 'quality_report.json', make_approval(tmp_path, directory, report), tmp_path / 'approved')


def test_approval_binding_and_immutable_publish(tmp_path):
    directory, report = run(config(tmp_path, [source()]), tmp_path / 'out',
        fetcher=lambda s: ((FIXTURES / 'sample.csv').read_bytes(), s['url']))
    approval = make_approval(tmp_path, directory, report)
    destination = publish(directory / 'quality_report.json', approval, tmp_path / 'approved')
    result = json.loads(destination.read_text(encoding='utf-8'))
    assert len(result['records']) == 1 and result['nationalBenchmarkReady'] is False
    with pytest.raises(FileExistsError):
        publish(directory / 'quality_report.json', approval, tmp_path / 'approved')
    (directory / 'quality_report.json').write_bytes((directory / 'quality_report.json').read_bytes() + b' ')
    with pytest.raises(ValueError, match='exact report'):
        publish(directory / 'quality_report.json', approval, tmp_path / 'approved')


def test_review_cannot_publish(tmp_path):
    directory, report = run(config(tmp_path, [source()]), tmp_path / 'out',
        fetcher=lambda s: ((FIXTURES / 'sample.csv').read_bytes(), s['url']))
    approval = make_approval(tmp_path, directory, report, [report['records'][1]['record_id']])
    with pytest.raises(ValueError, match='non-demo PASS'):
        publish(directory / 'quality_report.json', approval, tmp_path / 'approved')


def test_changed_raw_evidence_blocks_publication(tmp_path):
    directory, report = run(config(tmp_path, [source()]), tmp_path / 'out',
        fetcher=lambda s: ((FIXTURES / 'sample.csv').read_bytes(), s['url']))
    approval = make_approval(tmp_path, directory, report)
    Path(report['records'][0]['raw_file']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash mismatch'):
        publish(directory / 'quality_report.json', approval, tmp_path / 'approved')


def test_json_nonfinite_numeric_preserved_for_rejection():
    raw, location = extract(b'{"observations":[{"value":NaN}]}', source('json'))[0]
    row = clean_record(raw, source('json'), location, {})
    assert row['raw_value'] == 'NaN'
    assert validate_records([row])[0]['status'] == 'REJECT'


def test_missing_method_needs_review():
    raw, location = extract((FIXTURES / 'sample.csv').read_bytes(), source())[0]
    spec = source()
    spec['metadata'] = {}
    row = validate_records([clean_record(raw, spec, location, {})])[0]
    assert row['status'] == 'REVIEW'
    assert 'methodology_evidence_required' in row['reasons']


def test_unmapped_or_changed_header_not_inferred():
    raw, location = extract((FIXTURES / 'sample.csv').read_bytes(), source())[0]
    raw['RenamedUnit'] = raw.pop('unit')
    row = validate_records([clean_record(raw, source(), location, {})])[0]
    assert row['status'] == 'REJECT'
    assert 'missing:unit' in row['reasons']
