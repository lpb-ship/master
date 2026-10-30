#!/usr/bin/env python3
"""Apply immutable SQL migrations using psql and standard PG* connection settings."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT / 'supabase/migrations')
    parser.add_argument('--through', help='Apply through this 14-digit version (local upgrade tests)')
    args = parser.parse_args()
    migrations = sorted(args.directory.glob('*.sql'))
    if not migrations:
        parser.error('No migrations found')
    versions = []
    for path in migrations:
        if not re.fullmatch(r'\d{14}_[a-z0-9_]+\.sql', path.name):
            parser.error(f'Invalid migration filename: {path.name}')
        versions.append(path.name[:14])
    if len(set(versions)) != len(versions):
        parser.error('Duplicate migration version')
    if args.through and args.through not in versions:
        parser.error('Unknown target version')
    # One connection and transaction: lock, checks, SQL and ledger commit together.
    sql = ["""BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
SELECT pg_advisory_xact_lock(830008);
CREATE SCHEMA IF NOT EXISTS app_migrations;
REVOKE ALL ON SCHEMA app_migrations FROM PUBLIC;
CREATE TABLE IF NOT EXISTS app_migrations.history (
    version text PRIMARY KEY, checksum text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT statement_timestamp()
);
REVOKE ALL ON app_migrations.history FROM PUBLIC;
"""]
    known = ','.join("'" + v + "'" for v in versions)
    sql.append(f"""DO $$ BEGIN
IF EXISTS (SELECT FROM app_migrations.history WHERE version NOT IN ({known})) THEN
    RAISE EXCEPTION 'Database has migrations absent from this checkout';
END IF; END $$;""")
    for path, version in zip(migrations, versions):
        content = path.read_text()
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        sql.append(f"""DO $$ BEGIN
IF EXISTS (SELECT FROM app_migrations.history WHERE version = '{version}' AND checksum <> '{checksum}') THEN
    RAISE EXCEPTION 'Applied migration {version} was modified';
END IF; END $$;""")
        if args.through and version > args.through:
            continue
        sql.append(f"SELECT NOT EXISTS (SELECT FROM app_migrations.history WHERE version = '{version}') AS apply_migration \\gset")
        sql.extend(['\\if :apply_migration', f"""DO $$ BEGIN
IF EXISTS (SELECT FROM app_migrations.history WHERE version > '{version}') THEN
    RAISE EXCEPTION 'Migration {version} would apply out of order';
END IF; END $$;""", content,
                    f"INSERT INTO app_migrations.history(version, checksum) VALUES ('{version}', '{checksum}');",
                    '\\endif'])
    sql.append('COMMIT;')
    subprocess.run([os.environ.get('PSQL', 'psql'), '-X', '--no-password',
                    '--set=ON_ERROR_STOP=1', '--file=-'],
                   input='\n'.join(sql), text=True, check=True)


if __name__ == '__main__':
    main()
