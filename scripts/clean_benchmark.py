"""Explicit field mapping; never infer units, years or population denominators."""
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation

FIELDS = ('indicator', 'value', 'unit', 'year', 'geography', 'population_basis',
          'period', 'statistic', 'scope', 'methodology_url', 'license')


def clean_record(raw, source, location, provenance):
    mapping = source.get('fields', {})
    metadata = source.get('metadata', {})
    record = {}
    origins = {}
    for field in FIELDS:
        if field in mapping:
            record[field] = raw.get(mapping[field])
            origins[field] = {'column': mapping[field]}
        else:
            record[field] = metadata.get(field)
            origins[field] = {'configured_metadata': True}
        if isinstance(record[field], str):
            record[field] = record[field].strip()
    record['raw_value'] = record['value']
    try:
        # Decimal convention is explicitly configured; no guessed comma removal.
        value = str(record['value'])
        separator = source.get('thousands_separator')
        if separator:
            value = value.replace(separator, '')
        number = Decimal(value)
        record['value'] = float(number) if number.is_finite() else None
        if record['value'] is not None and not math.isfinite(record['value']):
            record['value'] = None
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        record['value'] = None
    record.update(provenance)
    record.update(source_id=source['id'], source_url=source['url'],
                  original_location=location, raw_record=raw, field_origins=origins,
                  demo=source.get('demo', False))
    record['record_id'] = hashlib.sha256(json.dumps(record, sort_keys=True,
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    return record
