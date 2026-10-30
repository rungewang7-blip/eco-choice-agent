import json
from collections import Counter
from pathlib import Path


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n', encoding='utf-8')


def generate_report(report, directory):
    directory = Path(directory)
    report['counts'] = {s: Counter(r['status'] for r in report['records'])[s]
                        for s in ('PASS', 'REVIEW', 'REJECT')}
    write_json(directory / 'quality_report.json', report)
    lines = ['# Benchmark Data Quality Report', '', 'Run: ' + report['run_id'],
             '', '**PASS means candidate checks passed, not human approval or a complete national benchmark.**',
             '', 'Counts: ' + json.dumps(report['counts']), '', '## Source collection results']
    for source in report['sources']:
        lines.append('- ' + source['source_id'] + ': ' + source['status'] +
                     ' — ' + source.get('error', str(source.get('record_count', 0)) + ' records'))
    lines += ['', '## Record results']
    for row in report['records']:
        lines += ['', '### ' + str(row.get('indicator')) + ' — ' + row['status'],
                  '- Value / unit / year: ' + str(row['value']) + ' / ' + str(row['unit']) + ' / ' + str(row['year']),
                  '- Source: ' + row['source_url'],
                  '- Original location: ' + json.dumps(row['original_location'], ensure_ascii=False),
                  '- Raw file: ' + row['raw_file'],
                  '- Statistical basis: ' + ' / '.join(str(row.get(k)) for k in
                      ('geography', 'population_basis', 'period', 'statistic', 'scope')),
                  '- Reasons: ' + (', '.join(row['reasons']) or 'Defined checks passed; verify methodology, representativeness and terms of use.'),
                  '- Next step: ' + ('Correct missing fields or formatting, then collect again.' if row['status'] == 'REJECT' else
                      'Verify source and statistical basis; document any conversion separately before approval.' if row['status'] == 'REVIEW' else
                      'Review the evidence, then approve using this report hash and record_id.'),
                  '- Record ID: ' + row['record_id']]
    (directory / 'quality_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
