"""Run with python -m scripts.collect_benchmark; stdlib-only, no API/DB imports."""
import argparse
import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from .clean_benchmark import clean_record
from .validate_benchmark import https_url, validate_records
from .generate_quality_report import generate_report, write_json

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 10 * 1024 * 1024


class Tables(HTMLParser):
    """Conservative rectangular tables only; refuse merged/nested cells."""
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.table is not None:
                raise ValueError('Nested HTML table needs a source-specific adapter')
            self.table = []
        elif self.table is not None and tag == 'tr':
            self.row = []
        elif self.row is not None and tag in ('td', 'th'):
            if any(k in ('rowspan', 'colspan') and v != '1' for k, v in attrs):
                raise ValueError('Merged HTML cells need a source-specific adapter')
            self.cell = ''

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def table_records(rows, location):
    if len(rows) < 2:
        raise ValueError('No data rows')
    header = rows[0]
    if any(not h for h in header) or len(set(header)) != len(header):
        raise ValueError('Blank or duplicate headers')
    result = []
    for index, values in enumerate(rows[1:], 2):
        if len(values) != len(header):
            raise ValueError('Ragged table at row ' + str(index))
        result.append((dict(zip(header, values)), dict(location, row=index, columns=header)))
    return result


def extract(payload, source):
    text = payload.decode(source.get('encoding', 'utf-8-sig'))
    kind = source['format']
    if kind == 'csv':
        return table_records(list(csv.reader(io.StringIO(text))), {'format': 'csv'})
    if kind == 'json':
        data = json.loads(text, parse_float=str, parse_constant=str)
        path = source.get('json_path', [])
        for key in path:
            data = data[key]
        if not isinstance(data, list) or not data or not all(isinstance(x, dict) for x in data):
            raise ValueError('JSON path must select a non-empty array of objects')
        return [(row, {'format': 'json', 'path': path + [index]}) for index, row in enumerate(data)]
    if kind == 'html':
        parser = Tables()
        parser.feed(text)
        selected = source.get('table_index', 0)
        if not parser.tables or not 0 <= selected < len(parser.tables):
            raise ValueError('Selected HTML table missing (dynamic charts are unsupported)')
        return table_records(parser.tables[selected], {'format': 'html', 'table_index': selected})
    raise ValueError('Unsupported format: ' + str(kind))


def fetch(source):
    request = Request(source['url'], headers={'User-Agent': 'EcoChoice-DataQuality/1.0'})
    with urlopen(request, timeout=25) as response:
        final_url = response.geturl()
        if not https_url(final_url):
            raise ValueError('Non-HTTPS response URL')
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError('Response exceeds 10 MiB')
        return payload, final_url


def run(config, output, fixture_dir=None, fetcher=fetch):
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:10]
    directory = Path(output) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'run_id': run_id, 'created_at': datetime.now(timezone.utc).isoformat(),
              'demo': fixture_dir is not None, 'nationalBenchmarkReady': False,
              'sources': [], 'records': []}
    try:
        config = json.loads(Path(config).read_text(encoding='utf-8-sig'))
        sources = config['sources']
        if not isinstance(sources, list):
            raise ValueError('sources must be an array')
        ids = [s['id'] for s in sources]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in ids):
            raise ValueError('Source IDs must be unique safe filenames')
        write_json(directory / 'sources.snapshot.json', config)
        for source in sources:
            outcome = {'source_id': source['id'], 'status': 'SKIPPED'}
            report['sources'].append(outcome)
            if not source.get('enabled', True):
                continue
            try:
                if not https_url(source.get('url')):
                    raise ValueError('Source URL must be configured HTTPS')
                if fixture_dir is not None:
                    base = Path(fixture_dir).resolve()
                    path = (base / source['fixture']).resolve()
                    if base not in path.parents:
                        raise ValueError('Fixture must be inside fixture directory')
                    payload, final_url = path.read_bytes(), source['url']
                else:
                    if source.get('demo'):
                        raise ValueError('Demo source requires --fixtures')
                    payload, final_url = fetcher(source)
                raw_file = directory / 'raw' / (source['id'] + '.bin')
                raw_file.parent.mkdir(exist_ok=True)
                raw_file.write_bytes(payload)
                provenance = {'raw_file': str(raw_file.resolve()),
                    'raw_sha256': hashlib.sha256(payload).hexdigest(),
                    'retrieved_at': datetime.now(timezone.utc).isoformat(), 'response_url': final_url}
                outcome.update(provenance, download_status='SUCCESS')
                extracted = extract(payload, source)
                cleaned = [clean_record(raw, source, loc, provenance) for raw, loc in extracted]
                # Fixture provenance cannot be approved even if its source config omits demo.
                for row in cleaned:
                    row['demo'] = report['demo'] or row['demo']
                report['records'].extend(cleaned)
                outcome.update(status='SUCCESS', record_count=len(cleaned))
            except Exception as error:
                outcome.update(status='FAILED', error=type(error).__name__ + ': ' + str(error))
        report['records'] = validate_records(report['records'])
        write_json(directory / 'cleaned' / 'records.json', report['records'])
    except Exception as error:
        report['sources'].append({'source_id': 'configuration', 'status': 'FAILED',
                                  'error': type(error).__name__ + ': ' + str(error)})
    finally:
        generate_report(report, directory)
    return directory, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, default=ROOT / 'data' / 'sources.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'reports')
    parser.add_argument('--fixtures', type=Path)
    args = parser.parse_args()
    directory, report = run(args.sources, args.output, args.fixtures)
    print(directory / 'quality_report.md')
    return 1 if any(s['status'] == 'FAILED' for s in report['sources']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
