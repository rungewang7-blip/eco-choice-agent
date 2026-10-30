"""Seed the reference database; fail visibly on corruption or changed versions."""
import csv
import os
import sqlite3
from pathlib import Path
from reference import DATA, factors, import_csv, validate


def bootstrap(db_path=None):
    path = db_path or os.getenv('ECO_DB', str(Path(__file__).parent / 'eco.db'))
    try:
        return import_csv(DATA / 'factors.csv', path)
    except sqlite3.IntegrityError:
        # Only an identical, already imported version is an acceptable no-op.
        with (DATA / 'factors.csv').open(encoding='utf-8-sig', newline='') as stream:
            expected = [validate(row) for row in csv.DictReader(stream)]
        version = expected[0]['factorVersion']
        if factors(path, version) != sorted(expected, key=lambda row: row['id']):
            raise ValueError('Existing version differs from the supplied CSV') from None
        return version


if __name__ == '__main__':
    print('Reference version:', bootstrap())
