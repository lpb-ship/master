#!/usr/bin/env python3
"""Disposable PostgreSQL integration and recovery rehearsal; synthetic data only."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
NAME = 'account-baseline-' + uuid.uuid4().hex[:10]
IMAGE = os.environ.get('POSTGRES_TEST_IMAGE', 'postgres:17')


def run(args, *, data=None, ok=True, env=None):
    result = subprocess.run(args, input=data, text=True, capture_output=True, env=env)
    if (result.returncode == 0) != ok:
        raise AssertionError(f'{args[0]} unexpected exit {result.returncode}: {result.stderr}\n{result.stdout}')
    return result.stdout.strip() if ok else result.stderr


def sql(query, *, db='baseline', ok=True):
    return run(['docker', 'exec', '-i', NAME, 'psql', '-XAt', '-v', 'ON_ERROR_STOP=1',
                '-U', 'postgres', '-d', db], data=query, ok=ok)


def actor(query, token='a', *, ok=True):
    return sql(f"BEGIN; SET LOCAL ROLE app_runtime; SET LOCAL app.session_hash = '{token * 64}'; {query}; COMMIT;", ok=ok)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory(prefix='account-db-test-') as folder:
        folder = Path(folder)
        try:
            run(['docker', 'run', '--detach', '--rm', '--name', NAME,
                 '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', IMAGE])
            for _ in range(60):
                ready = subprocess.run(['docker', 'exec', NAME, 'pg_isready', '-U', 'postgres'], capture_output=True)
                if ready.returncode == 0:
                    break
                time.sleep(0.5)
            else:
                raise AssertionError('PostgreSQL did not become ready')
            sql('CREATE DATABASE baseline', db='postgres')
            wrapper = folder / 'psql'
            wrapper.write_text(f'#!/bin/sh\nexec docker exec -i {NAME} psql -U postgres -d "${{TEST_DATABASE:-baseline}}" "$@"\n')
            wrapper.chmod(0o700)
            env = dict(os.environ, PSQL=str(wrapper))

            def migrate(*args, ok=True, db='baseline'):
                return run(['python3', str(ROOT / 'scripts/migrate.py'), *args],
                           env=dict(env, TEST_DATABASE=db), ok=ok)

            migrate('--through', '20261030000100')
            alice = sql("SET ROLE app_auth_service; SELECT app_api.provision_account('https://auth.test/issuer', 'alice');").splitlines()[-1]
            bob = sql("SET ROLE app_auth_service; SELECT app_api.provision_account('https://auth.test/issuer', 'bob');").splitlines()[-1]
            check(alice != bob, 'Independent application UUIDs')
            sql(f"SET ROLE app_auth_service; INSERT INTO app_private.sessions(token_hash, account_id, expires_at) VALUES ('{'a'*64}', '{alice}', statement_timestamp() + interval '1 hour'), ('{'b'*64}', '{bob}', statement_timestamp() + interval '1 hour');")
            migrate()
            migrate()
            check(sql('SELECT count(*) FROM app_migrations.history') == str(len(list((ROOT / 'supabase/migrations').glob('*.sql')))), 'Migration replay')
            check(sql(f"SELECT display_name IS NULL AND version = 0 FROM app_private.profiles WHERE account_id = '{alice}'") == 't', 'Upgrade preserves shell')
            print('PASS clean baseline, upgrade with existing rows, and migration replay')

            with ThreadPoolExecutor(max_workers=2) as pool:
                ids = list(pool.map(lambda _: sql("SET ROLE app_auth_service; SELECT app_api.provision_account('https://auth.test/issuer', 'race');").splitlines()[-1], range(2)))
            check(ids[0] == ids[1], 'Concurrent provisioning must be idempotent')
            other = sql("SET ROLE app_auth_service; SELECT app_api.provision_account('https://other.test/issuer', 'alice');").splitlines()[-1]
            check(other != alice, 'Issuer namespaces must not merge')
            before = sql('SELECT count(*) FROM app_private.accounts')
            sql("SET ROLE app_auth_service; SELECT app_api.provision_account('', 'invalid');", ok=False)
            check(before == sql('SELECT count(*) FROM app_private.accounts'), 'Invalid provisioning rolls back')
            sql(f"INSERT INTO app_private.identities VALUES ('https://auth.test/issuer', 'alice', '{bob}')", ok=False)
            sql("INSERT INTO app_private.profiles(account_id) VALUES (gen_random_uuid())", ok=False)
            print('PASS identity isolation, atomic/concurrent provisioning, uniqueness and foreign keys')

            check('\n1\n' in actor('SELECT count(*) FROM app_private.profiles'), 'Owner sees exactly one profile')
            check('\n0\n' in actor(f"SELECT count(*) FROM app_private.profiles WHERE account_id = '{bob}'"), 'Cross-owner read denied')
            check('\n0\n' in actor('SELECT count(*) FROM app_private.profiles', token='c'), 'Unknown session denied')
            check('\n0\n' in sql('BEGIN; SET LOCAL ROLE app_runtime; SELECT count(*) FROM app_private.profiles; COMMIT;'), 'Pool context does not persist')
            for query in ["SELECT * FROM app_private.identities", "SELECT * FROM app_private.sessions",
                          "SELECT * FROM app_private.accounts", "UPDATE app_private.profiles SET display_name = 'bypass'",
                          "DELETE FROM app_private.profiles", "INSERT INTO app_private.profiles(account_id) VALUES (gen_random_uuid())",
                          "SELECT app_api.provision_account('evil', 'evil')"]:
                actor(query, ok=False)
            for query in ["SELECT * FROM app_private.profiles", "SELECT app_api.update_own_profile('bad', 0)"]:
                sql('SET ROLE app_auth_service; ' + query, ok=False)
            # SET ROLE escalation must be tested from a real non-superuser login.
            sql('CREATE ROLE test_runtime LOGIN NOINHERIT IN ROLE app_runtime')
            denied = run(['docker', 'exec', NAME, 'psql', '-XAt', '-U', 'test_runtime', '-d', 'baseline',
                          '-v', 'ON_ERROR_STOP=1', '-c', 'SET ROLE app_owner'], ok=False)
            check('permission denied' in denied, 'Runtime cannot become owner')
            # Simulate pre-existing Supabase roles, including the BYPASSRLS service role.
            for role in ['anon', 'authenticated', 'service_role']:
                sql(f"CREATE ROLE {role} NOLOGIN {'BYPASSRLS' if role == 'service_role' else ''}")
                sql(f'SET ROLE {role}; SELECT * FROM app_private.profiles', ok=False)
                sql(f"SET ROLE {role}; SELECT app_api.update_own_profile('bad', 0)", ok=False)
            print('PASS runtime least privilege, owner-only RLS, no context, and Data API denial')

            actor("SELECT app_api.update_own_profile(U&'  Jose\\0301  ', 0)")
            check(sql(f"SELECT display_name = 'José' AND version = 1 FROM app_private.profiles WHERE account_id = '{alice}'") == 't', 'Canonical Unicode and managed version')
            check('CONFLICT' in actor("SELECT app_api.update_own_profile('stale', 0)", ok=False), 'Stale version rejected')
            for value in ["NULL", "''", "'   '", "repeat('🙂', 81)", "E'bad\\nname'", "U&'bad\\0085name'"]:
                check('VALIDATION_FAILED' in actor(f'SELECT app_api.update_own_profile({value}, 1)', ok=False), 'Name validation')
            actor("SELECT app_api.update_own_profile(repeat('🙂', 80), 1)")
            with ThreadPoolExecutor(max_workers=2) as pool:
                def save(_):
                    try:
                        return actor("SELECT app_api.update_own_profile('winner', 2)")
                    except AssertionError as error:
                        check('CONFLICT' in str(error), 'Only stale version may fail')
                        return 'conflict'
                saves = list(pool.map(save, range(2)))
            check(saves.count('conflict') == 1, 'Exactly one concurrent edit wins')
            for status in ['restricted', 'deletion_pending']:
                sql(f"UPDATE app_private.accounts SET status = '{status}' WHERE id = '{alice}'")
                check('\n0\n' in actor('SELECT count(*) FROM app_private.profiles'), 'Inactive account read denied')
                actor("SELECT app_api.update_own_profile('denied', 3)", ok=False)
                sql("SET ROLE app_auth_service; SELECT app_api.provision_account('https://auth.test/issuer', 'alice')", ok=False)
            sql(f"UPDATE app_private.accounts SET status = 'active' WHERE id = '{alice}'")
            for assignment in ["revoked_at = statement_timestamp()", "created_at = statement_timestamp() - interval '2 days', last_active_at = statement_timestamp() - interval '25 hours', expires_at = statement_timestamp() + interval '1 hour'", "created_at = statement_timestamp() - interval '2 hours', last_active_at = statement_timestamp() - interval '1 hour', expires_at = statement_timestamp() - interval '1 minute'"]:
                sql(f"UPDATE app_private.sessions SET {assignment} WHERE token_hash = '{'a'*64}'")
                check('\n0\n' in actor('SELECT count(*) FROM app_private.profiles'), 'Revoked/expired session denied')
                actor("SELECT app_api.update_own_profile('denied', 3)", ok=False)
                sql(f"UPDATE app_private.sessions SET revoked_at = NULL, created_at = statement_timestamp(), last_active_at = statement_timestamp(), expires_at = statement_timestamp() + interval '1 hour' WHERE token_hash = '{'a'*64}'")
            print('PASS Unicode validation, concurrent edits, restriction, deletion pending, revocation and expiry')

            modified = folder / 'migrations'
            shutil.copytree(ROOT / 'supabase/migrations', modified)
            first = sorted(modified.glob('*.sql'))[0]
            first.write_text(first.read_text() + '\n-- tampered\n')
            check('was modified' in migrate('--directory', str(modified), ok=False), 'Checksum drift rejected')
            shutil.rmtree(modified)
            shutil.copytree(ROOT / 'supabase/migrations', modified)
            (modified / '20981231000000_failure.sql').write_text('CREATE TABLE public.must_rollback(id int); SELECT 1/0;')
            migrate('--directory', str(modified), ok=False)
            check(sql("SELECT to_regclass('public.must_rollback') IS NULL") == 't', 'Failed migration DDL rolled back')
            check(sql('SELECT count(*) FROM app_migrations.history') == str(len(list((ROOT / 'supabase/migrations').glob('*.sql')))), 'Failed migration not recorded')
            (modified / '20981231000000_failure.sql').unlink()
            (modified / '20261030000150_late.sql').write_text('SELECT 1;')
            check('out of order' in migrate('--directory', str(modified), ok=False), 'Out-of-order migration rejected')
            sql("INSERT INTO app_migrations.history(version, checksum) VALUES ('20990101000000', 'unknown')")
            check('absent from this checkout' in migrate(ok=False), 'Unknown history rejected')
            sql("DELETE FROM app_migrations.history WHERE version = '20990101000000'")
            sql('CREATE DATABASE clean', db='postgres')
            migrate(db='clean')
            check(sql('SELECT count(*) FROM app_migrations.history', db='clean') == str(len(list((ROOT / 'supabase/migrations').glob('*.sql')))), 'All migrations from empty')
            print('PASS immutable history, failed migration rollback, and full clean initialization')

            # A custom-format logical backup contains the application and migration ledger.
            run(['docker', 'exec', NAME, 'pg_dump', '-U', 'postgres', '-d', 'baseline', '-Fc', '-f', '/tmp/baseline.dump'])
            sql('CREATE DATABASE restored', db='postgres')
            run(['docker', 'exec', NAME, 'pg_restore', '-U', 'postgres', '-d', 'restored', '--exit-on-error', '/tmp/baseline.dump'])
            fingerprint = "SELECT account_id, coalesce(display_name, ''), version FROM app_private.profiles ORDER BY account_id"
            check(sql(fingerprint) == sql(fingerprint, db='restored'), 'Restore preserves profiles and IDs')
            check(sql('TABLE app_private.identities') == sql('TABLE app_private.identities', db='restored'), 'Restore preserves mappings')
            sql('UPDATE app_private.sessions SET revoked_at = statement_timestamp()', db='restored')
            check('\n0\n' in sql(f"BEGIN; SET LOCAL ROLE app_runtime; SET LOCAL app.session_hash = '{'a'*64}'; SELECT count(*) FROM app_private.profiles; COMMIT;", db='restored'), 'Restored sessions invalidated')
            check(sql("SELECT relrowsecurity FROM pg_class WHERE oid = 'app_private.profiles'::regclass", db='restored') == 't', 'RLS restored')
            migrate(db='restored')
            print('PASS backup/restore, stable identity mapping, restored grants/RLS and session invalidation')

            # Demonstrate certificate-verified TLS against the disposable database.
            run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                 '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                 '-keyout', str(folder / 'server.key'), '-out', str(folder / 'server.crt')])
            for name in ['server.key', 'server.crt']:
                run(['docker', 'cp', str(folder / name), f'{NAME}:/tmp/{name}'])
            run(['docker', 'exec', '-u', 'root', NAME, 'chown', 'postgres:postgres', '/tmp/server.key'])
            run(['docker', 'exec', '-u', 'root', NAME, 'chmod', '600', '/tmp/server.key'])
            sql("ALTER SYSTEM SET ssl = on", db='postgres')
            sql("ALTER SYSTEM SET ssl_cert_file = '/tmp/server.crt'", db='postgres')
            sql("ALTER SYSTEM SET ssl_key_file = '/tmp/server.key'", db='postgres')
            sql('SELECT pg_reload_conf()', db='postgres')
            time.sleep(0.5)
            connect = ['docker', 'exec', NAME, 'psql', '-XAt',
                       'host=localhost hostaddr=127.0.0.1 user=postgres dbname=baseline sslmode=verify-full sslrootcert=/tmp/server.crt',
                       '-c', 'SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()']
            check(run(connect) == 't', 'Verified TLS connection')
            connect[-3] = connect[-3].replace('host=localhost ', 'host=wrong.test ')
            check('does not match host name' in run(connect, ok=False), 'Wrong certificate hostname rejected')
            print('PASS verified TLS and certificate hostname rejection')
        finally:
            subprocess.run(['docker', 'rm', '--force', NAME], capture_output=True)


if __name__ == '__main__':
    main()
