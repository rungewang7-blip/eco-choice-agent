import argparse
import sqlite3
from reference import import_csv

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import an immutable factor CSV version')
    parser.add_argument('csv')
    parser.add_argument('--db', default='eco.db')
    args = parser.parse_args()
    try:
        print('Imported version:', import_csv(args.csv, args.db))
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, 'Import rejected: check CSV fields, file access, database schema and unique version.\n')
