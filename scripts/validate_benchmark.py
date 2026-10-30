"""PASS is a candidate under these rules, never a publication approval."""
import math
from datetime import datetime, timezone
from urllib.parse import urlparse


def https_url(value):
    parsed = urlparse(str(value or ''))
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username


def validate_records(records):
    seen = set()
    results = []
    for original in records:
        row = dict(original)
        reject, review = [], []
        for field in ('indicator', 'unit', 'year', 'source_url', 'original_location',
                      'geography', 'population_basis', 'period', 'statistic', 'scope'):
            if not row.get(field):
                reject.append('missing:' + field)
        if not https_url(row.get('source_url')):
            reject.append('invalid_source_url')
        value = row.get('value')
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            reject.append('invalid_nonnegative_value')
        year = str(row.get('year', ''))
        if not (year.isdigit() and 1900 <= int(year) <= datetime.now(timezone.utc).year):
            reject.append('invalid_year')
        key = tuple(str(row.get(k)) for k in ('indicator', 'year', 'geography',
                    'unit', 'population_basis', 'period', 'statistic', 'scope'))
        if key in seen:
            review.append('duplicate_or_conflicting_observation')
        seen.add(key)
        requirements = {'geography': 'Ireland', 'population_basis': 'person',
                        'period': 'year', 'statistic': 'mean', 'scope': 'national'}
        for field, expected in requirements.items():
            if row.get(field) != expected:
                review.append('benchmark_requires:' + field + '=' + expected)
        if row.get('unit') not in ('km/person/year', 'kWh/person/year',
                                   'kg/person/year', 'kgCO2e/person/year'):
            review.append('unit_needs_review_or_documented_conversion')
        if not https_url(row.get('methodology_url')):
            review.append('methodology_evidence_required')
        if not row.get('license'):
            review.append('reuse_terms_required')
        row.update(status='REJECT' if reject else 'REVIEW' if review else 'PASS',
                   reasons=reject + review, extraction_valid=not bool(reject),
                   benchmark_candidate=not bool(reject or review),
                   human_approved=False)
        results.append(row)
    # All members of a duplicate group require review, including the first row.
    duplicate_keys = {}
    for row in results:
        key = tuple(str(row.get(k)) for k in ('indicator', 'year', 'geography',
                    'unit', 'population_basis', 'period', 'statistic', 'scope'))
        duplicate_keys.setdefault(key, []).append(row)
    for group in duplicate_keys.values():
        if len(group) > 1:
            for row in group:
                reason = 'duplicate_or_conflicting_observation'
                if reason not in row['reasons']:
                    row['reasons'].append(reason)
                if row['status'] == 'PASS':
                    row['status'] = 'REVIEW'
                row['benchmark_candidate'] = False
    return results
