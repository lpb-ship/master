#!/usr/bin/env python3
"""Watchlist integration checks against disposable PostgreSQL; no provider access."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from verify import IMAGE, NAME, ROOT, actor, check, run, sql

MOVIE, SERIES, REMAKE = [str(uuid.UUID(int=i)) for i in (1, 2, 3)]
UNKNOWN = str(uuid.UUID(int=999))


def value(query, token='a'):
    return actor(query, token).splitlines()[-2]


def entries(token='a', args=''):
    return json.loads(value(f"SELECT coalesce(jsonb_agg(w), '[]') FROM app_api.list_watchlist({args}) w", token))


def save(title=MOVIE, token='a'):
    return json.loads(value(f"SELECT row_to_json(w) FROM app_api.save_watchlist_title('{title}') w", token))


def ready():
    for _ in range(60):
        result = subprocess.run(['docker', 'exec', NAME, 'pg_isready', '-U', 'postgres'], capture_output=True)
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise AssertionError('PostgreSQL did not become ready')


def main():
    with tempfile.TemporaryDirectory(prefix='watchlist-test-') as folder:
        try:
            run(['docker', 'run', '--detach', '--rm', '--name', NAME,
                 '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', IMAGE])
            ready()
            sql('CREATE DATABASE baseline', db='postgres')
            wrapper = Path(folder) / 'psql'
            wrapper.write_text(f'#!/bin/sh\nexec docker exec -i {NAME} psql -U postgres -d baseline "$@"\n')
            wrapper.chmod(0o700)

            def migrate(*args):
                run(['python3', str(ROOT / 'scripts/migrate.py'), *args],
                    env=dict(os.environ, PSQL=str(wrapper)))

            migrate('--through', '20261030000200')
            users = []
            for name, token in [('alice', 'a'), ('bob', 'b'), ('incomplete', 'c')]:
                user = sql(f"SET ROLE app_auth_service; SELECT app_api.provision_account('https://auth.test', '{name}')").splitlines()[-1]
                users.append(user)
                sql(f"SET ROLE app_auth_service; INSERT INTO app_private.sessions(token_hash, account_id, expires_at) VALUES ('{token*64}', '{user}', statement_timestamp() + interval '1 hour')")
                if name != 'incomplete':
                    actor(f"SELECT app_api.update_own_profile('{name}', 0)", token)
            alice, bob, _ = users
            migrate()
            migrate()
            check(entries() == [], 'Existing account has an empty watchlist after upgrade')
            sql(f"""INSERT INTO app_private.watchlist_catalog_titles VALUES
                ('{MOVIE}', 'movie', 'The Return', 2000),
                ('{SERIES}', 'series', 'The Return', NULL),
                ('{REMAKE}', 'movie', 'The Return', 2020)""")
            first = save()
            check(save() == first, 'Repeated save returns original timestamp and snapshot')
            # Distinct titles with identical names must never be collapsed by labels.
            save(SERIES)
            save(REMAKE)
            check(len(entries()) == 3, 'Movie, series and remake identities stay distinct')
            with ThreadPoolExecutor(max_workers=12) as pool:
                results = list(pool.map(lambda _: save(), range(12)))
            check(all(row == first for row in results), 'Concurrent retries preserve the original entry')
            # Also race the first save, rather than only retries of an existing row.
            with ThreadPoolExecutor(max_workers=12) as pool:
                results = list(pool.map(lambda _: save(token='b'), range(12)))
            check(all(row == results[0] for row in results), 'Concurrent first saves are idempotent')
            check(len(entries('b')) == 1, 'Exactly one row survives concurrent first saves')
            print('PASS upgrade, repeated/concurrent saves, and distinct canonical titles')

            # Lists and deletes have no owner parameter. Even a known title/cursor
            # can only affect the current account; direct table access is denied.
            actor(f"SELECT app_api.remove_watchlist_title('{SERIES}')", 'b')
            check(len(entries()) == 3, 'Bob cannot remove a title saved only by Alice')
            actor(f"SELECT app_api.remove_watchlist_title('{MOVIE}')", 'b')
            check(entries('b') == [] and len(entries()) == 3, 'Removal is isolated even for a shared title')
            check(entries('b', f"50, '{first['saved_at']}', '{MOVIE}'") == [], 'Another owner cursor cannot expose data')
            for query in [
                'TABLE app_private.watchlist_entries',
                f"SELECT * FROM app_private.watchlist_entries WHERE account_id = '{alice}'",
                f"DELETE FROM app_private.watchlist_entries WHERE account_id = '{alice}'",
                f"UPDATE app_private.watchlist_entries SET account_id = '{bob}'",
                f"INSERT INTO app_private.watchlist_entries(account_id, catalog_entity_id, media_kind, display_title) VALUES ('{bob}', '{MOVIE}', 'movie', 'forged')",
                'TABLE app_private.watchlist_catalog_titles',
                f"INSERT INTO app_private.watchlist_catalog_titles VALUES ('{UNKNOWN}', 'movie', 'forged', NULL)",
                'SELECT app_private.watchlist_actor()',
            ]:
                check('permission denied' in actor(query, 'b', ok=False), 'Runtime cannot bypass API: ' + query)
            for role in ['anon', 'authenticated', 'service_role', 'untrusted']:
                sql(f"CREATE ROLE {role} NOLOGIN {'BYPASSRLS' if role == 'service_role' else ''}")
            operations = [f"SELECT app_api.save_watchlist_title('{MOVIE}')",
                          'SELECT * FROM app_api.list_watchlist()',
                          f"SELECT app_api.remove_watchlist_title('{MOVIE}')"]
            for role in ['anon', 'authenticated', 'service_role', 'untrusted', 'app_auth_service']:
                for query in operations + ['TABLE app_private.watchlist_entries']:
                    check('permission denied' in sql(f'SET ROLE {role}; {query}', ok=False), 'Non-runtime role denied')
            for query in operations:
                check('UNAUTHENTICATED' in actor(query, 'f', ok=False), 'Unknown session denied')
                check('UNAUTHENTICATED' in sql('SET ROLE app_runtime; ' + query, ok=False), 'Absent context denied')
                check('PROFILE_INCOMPLETE' in actor(query, 'c', ok=False), 'Incomplete profile denied')
            for status in ['restricted', 'deletion_pending']:
                sql(f"UPDATE app_private.accounts SET status = '{status}' WHERE id = '{alice}'")
                for query in operations:
                    check('UNAUTHENTICATED' in actor(query, ok=False), 'Inactive account denied')
            sql(f"UPDATE app_private.accounts SET status = 'active' WHERE id = '{alice}'")
            for assignment in [
                'revoked_at = statement_timestamp()',
                "created_at = statement_timestamp() - interval '2 days', last_active_at = statement_timestamp() - interval '25 hours', expires_at = statement_timestamp() + interval '1 hour'",
                "created_at = statement_timestamp() - interval '2 hours', last_active_at = statement_timestamp() - interval '1 hour', expires_at = statement_timestamp() - interval '1 minute'",
            ]:
                sql(f"UPDATE app_private.sessions SET {assignment} WHERE token_hash = '{'a'*64}'")
                for query in operations:
                    check('UNAUTHENTICATED' in actor(query, ok=False), 'Revoked/expired session denied')
                sql(f"UPDATE app_private.sessions SET revoked_at = NULL, created_at = statement_timestamp(), last_active_at = statement_timestamp(), expires_at = statement_timestamp() + interval '1 hour' WHERE token_hash = '{'a'*64}'")
            check(len(entries()) == 3, 'Denied operations leave all entries intact')
            print('PASS cross-user isolation, role denial, profile/session/account authorization')

            # A fresh application session and a database restart both retain saves.
            sql(f"SET ROLE app_auth_service; UPDATE app_private.sessions SET revoked_at = statement_timestamp() WHERE token_hash = '{'a'*64}'; INSERT INTO app_private.sessions(token_hash, account_id, expires_at) VALUES ('{'d'*64}', '{alice}', statement_timestamp() + interval '1 hour')")
            before = entries('d')
            run(['docker', 'restart', NAME])
            ready()
            check(entries('d') == before, 'Saves persist across database restart and new session')
            for query in operations:
                check('UNAUTHENTICATED' in actor(query, ok=False), 'Old session stays revoked')
            # Provider offers are not stored or required by these operations. Even
            # catalog metadata changes do not rewrite the saved display snapshot.
            sql("UPDATE app_private.watchlist_catalog_titles SET display_title = 'Updated catalog label', release_year = NULL")
            check(entries('d') == before and save(token='d') == first, 'Metadata changes retain saved entries')
            check('foreign key constraint' in sql(f"DELETE FROM app_private.watchlist_catalog_titles WHERE catalog_entity_id = '{MOVIE}'", ok=False), 'Catalog eviction cannot cascade saved entries')
            print('PASS new sessions, restart durability, stable snapshots and catalog retention')

            for query in [
                'SELECT app_api.save_watchlist_title(NULL)',
                'SELECT app_api.remove_watchlist_title(NULL)',
                'SELECT * FROM app_api.list_watchlist(0)',
                'SELECT * FROM app_api.list_watchlist(101)',
                'SELECT * FROM app_api.list_watchlist(NULL)',
                "SELECT * FROM app_api.list_watchlist(1, now(), NULL)",
                f"SELECT * FROM app_api.list_watchlist(1, NULL, '{MOVIE}')",
            ]:
                check('VALIDATION_FAILED' in actor(query, 'd', ok=False), 'Malformed input denied')
            check('NOT_FOUND' in actor(f"SELECT app_api.save_watchlist_title('{UNKNOWN}')", 'd', ok=False), 'Unresolved title cannot be saved')
            check('invalid input syntax for type uuid' in actor("SELECT app_api.save_watchlist_title('provider:movie:1')", 'd', ok=False), 'Provider IDs are not canonical IDs')
            # Equal timestamps exercise the stable tie breaker and every page boundary.
            sql(f"UPDATE app_private.watchlist_entries SET saved_at = '2026-01-01Z' WHERE account_id = '{alice}'")
            expected = entries('d')
            paged, args = [], '1'
            while page := entries('d', args):
                paged.extend(page)
                last = page[-1]
                args = f"1, '{last['saved_at']}', '{last['catalog_entity_id']}'"
                check(len(paged) <= 3, 'Pagination must make progress')
            check(paged == expected and len(paged) == 3, 'Keyset pages have no omissions or duplicates')
            for _ in range(2):
                actor(f"SELECT app_api.remove_watchlist_title('{MOVIE}')", 'd')
                actor(f"SELECT app_api.remove_watchlist_title('{UNKNOWN}')", 'd')
            check(len(entries('d')) == 2, 'Removal persists and missing removals are idempotent')
            check(save(token='d')['display_title'] == 'Updated catalog label', 'Re-save after removal takes a fresh snapshot')
            save(token='b')
            sql(f"DELETE FROM app_private.accounts WHERE id = '{alice}'")
            check(sql(f"SELECT count(*) FROM app_private.watchlist_entries WHERE account_id = '{alice}'") == '0', 'Final account deletion cascades only owned entries')
            check(len(entries('b')) == 1, 'Other account survives deletion')
            print('PASS validation, pagination, removal/re-save and account deletion')
        finally:
            subprocess.run(['docker', 'rm', '--force', NAME], capture_output=True)


if __name__ == '__main__':
    main()
