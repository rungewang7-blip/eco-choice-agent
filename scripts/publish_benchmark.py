"""Publish an immutable approved candidate file; never write eco.db or benchmark.json."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime
from .validate_benchmark import validate_records


def publish(report_path, approval_path, output_dir):
    raw = Path(report_path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    report = json.loads(raw)
    approval = json.loads(Path(approval_path).read_text(encoding='utf-8-sig'))
    if approval.get('report_sha256') != digest or approval.get('run_id') != report['run_id']:
        raise ValueError('Approval must bind to this exact report and run')
    if not str(approval.get('reviewer', '')).strip() or not str(approval.get('reason', '')).strip():
        raise ValueError('Named reviewer and review reason required')
    timestamp = datetime.fromisoformat(approval['approved_at'])
    if timestamp.tzinfo is None:
        raise ValueError('Approval timestamp must include timezone')
    ids = approval.get('record_ids', [])
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Explicit unique record IDs required')
    records = {row['record_id']: row for row in validate_records(report['records'])}
    if any(key not in records for key in ids):
        raise ValueError('Unknown record ID')
    chosen = [records[key] for key in ids]
    if report.get('demo') or any(r.get('demo') or r['status'] != 'PASS' for r in chosen):
        raise ValueError('Only non-demo PASS candidates can be approved')
    for row in chosen:
        if hashlib.sha256(Path(row['raw_file']).read_bytes()).hexdigest() != row['raw_sha256']:
            raise ValueError('Raw evidence hash mismatch')
        row['human_approved'] = True
    result = {'kind': 'approved_benchmark_candidates', 'nationalBenchmarkReady': False,
              'approval': approval, 'records': chosen}
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('approved-' + digest + '.json')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data' / 'approved')
    args = parser.parse_args()
    print(publish(args.report, args.approval, args.output))
