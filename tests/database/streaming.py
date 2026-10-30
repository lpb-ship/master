"""Streaming persistence checks using the baseline's disposable PostgreSQL cluster."""
from concurrent.futures import ThreadPoolExecutor


def verify(sql, check, alice, bob):
    def service(query, token='a', ok=True):
        return sql(f"BEGIN; SET LOCAL ROLE app_streaming_service; SET LOCAL app.session_hash = '{token * 64}'; {query}; COMMIT;", ok=ok)

    def runtime(query, token='a', ok=True):
        return sql(f"BEGIN; SET LOCAL ROLE app_runtime; SET LOCAL app.session_hash = '{token * 64}'; {query}; COMMIT;", ok=ok)

    def value(query, token='a'):
        # psql command tags surround SELECT output; return exactly the selected row.
        return service(query, token).splitlines()[-2]

    def denied(query, fragment):
        check(fragment in service(query, ok=False), f'Expected {fragment}: {query}')

    tables = ['connections', 'subscriptions', 'imports', 'source_events', 'viewing_events']
    check(sql("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'streaming_private' AND c.relkind = 'r' AND c.relrowsecurity") == '5', 'All streaming tables enable RLS')
    service("INSERT INTO streaming_private.connections(provider, provider_account_key, state) VALUES ('fixture', 'alice-provider', 'connected')")
    service("INSERT INTO streaming_private.connections(provider, provider_account_key, state) VALUES ('fixture', 'bob-provider', 'connected')", 'b')
    connection = value('SELECT id FROM streaming_private.connections')
    bob_connection = value('SELECT id FROM streaming_private.connections', 'b')
    denied("INSERT INTO streaming_private.connections(provider, provider_account_key) VALUES ('fixture', 'alice-provider')", 'unique constraint')
    denied(f"UPDATE streaming_private.connections SET account_id = '{bob}'", 'permission denied')
    denied(f"INSERT INTO streaming_private.connections(account_id, provider, provider_account_key) VALUES ('{bob}', 'fixture', 'forged')", 'permission denied')
    # Provider identifiers can coincide across owners; they never merge app identity.
    service("INSERT INTO streaming_private.connections(provider, provider_account_key, provider_profile_key, state) VALUES ('fixture', 'alice-provider', 'child', 'connected')")
    second_connection = value("SELECT id FROM streaming_private.connections WHERE provider_profile_key = 'child'")
    service("INSERT INTO streaming_private.connections(provider, provider_account_key) VALUES ('fixture', 'alice-provider')", 'b')

    service(f"INSERT INTO streaming_private.subscriptions(connection_id, supported_fields, status, observed_at) VALUES ('{connection}', ARRAY['status'], 'active', now())")
    denied(f"INSERT INTO streaming_private.subscriptions(connection_id, plan_name, observed_at) VALUES ('{second_connection}', 'invented', now())", 'check constraint')
    service(f"INSERT INTO streaming_private.subscriptions(connection_id, observed_at) VALUES ('{second_connection}', now())")
    check(value(f"SELECT status IS NULL AND supported_fields = '{{}}'::text[] FROM streaming_private.subscriptions WHERE connection_id = '{second_connection}'") == 't', 'Unavailable subscription is not inactive')

    service(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{connection}', 'request-1')")
    job = value('SELECT id FROM streaming_private.imports')
    service(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{bob_connection}', 'request-1')", 'b')
    bob_job = value('SELECT id FROM streaming_private.imports', 'b')
    denied(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{connection}', 'request-2')", 'unique constraint')
    denied(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{bob_connection}', 'forged')", 'row-level security')
    denied(f"UPDATE streaming_private.imports SET connection_id = '{second_connection}'", 'permission denied')
    denied("UPDATE streaming_private.imports SET state = 'completed'", 'check constraint')
    denied("UPDATE streaming_private.imports SET processed_count = -1", 'check constraint')
    denied("UPDATE streaming_private.imports SET checkpoint = 'cursor'", 'check constraint')

    def source(key, *, job_id=job, parent=connection, stamp="'2026-01-01T00:00:00Z'", precision='instant'):
        return f"INSERT INTO streaming_private.source_events(connection_id, import_id, source_key, identity_basis, provider_title_key, occurred_at, time_precision) VALUES ('{parent}', '{job_id}', '{key}', 'provider_event_id', 'same-title', {stamp}, '{precision}')"

    service(source('watch-1'))
    service(source('watch-2'))  # Same title AND timestamp may still be distinct occurrences.
    service(source('unknown-1', stamp='NULL', precision='unknown'))
    service(source('unknown-2', stamp='NULL', precision='unknown'))
    denied(source('watch-1'), 'unique constraint')
    denied(source('bad-owner', job_id=bob_job), 'foreign key constraint')
    denied(source('bad-connection', parent=second_connection), 'foreign key constraint')
    denied(source('bad-time', stamp='NULL'), 'check constraint')
    denied(source('bad-precision', precision='unknown'), 'check constraint')
    # A date is not stored as an invented midnight instant.
    service(source('date-only', stamp='NULL', precision='date').replace('occurred_at, time_precision)', 'occurred_at, occurred_on, time_precision)').replace("NULL, 'date')", "NULL, '2026-01-01', 'date')"))
    check(value("SELECT occurred_on = '2026-01-01' AND occurred_at IS NULL FROM streaming_private.source_events WHERE source_key = 'date-only'") == 't', 'Date-only precision preserved')
    denied("UPDATE streaming_private.source_events SET source_key = 'changed'", 'permission denied')
    denied("UPDATE streaming_private.source_events SET raw_payload = '{}'", 'check constraint')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service(source('concurrent') + ' ON CONFLICT (account_id, connection_id, source_key) DO NOTHING'), range(2)))
    check(len(results) == 2 and value("SELECT count(*) FROM streaming_private.source_events WHERE source_key = 'concurrent'") == '1', 'Concurrent source replay deduplicates')
    source_id = value("SELECT id FROM streaming_private.source_events WHERE source_key = 'watch-1'")
    source_two = value("SELECT id FROM streaming_private.source_events WHERE source_key = 'watch-2'")
    for source_ref, kind in [(source_id, 'movie'), (source_two, 'episode')]:
        service(f"INSERT INTO streaming_private.viewing_events(connection_id, source_event_id, media_kind, match_state, catalog_namespace, catalog_title_id, normalization_version) VALUES ('{connection}', '{source_ref}', '{kind}', 'matched', 'fixture_catalog', 'same-catalog-id', 'fixture-v1')")
    event = f"INSERT INTO streaming_private.viewing_events(connection_id, source_event_id, media_kind, match_state, normalization_version) VALUES ('{connection}', '{source_id}', 'movie', 'unmatched', 'fixture-v1')"
    denied(event, 'unique constraint')
    denied(event.replace(f"'{connection}'", f"'{second_connection}'"), 'foreign key constraint')
    denied("UPDATE streaming_private.viewing_events SET match_state = 'unmatched'", 'check constraint')
    denied("UPDATE streaming_private.viewing_events SET catalog_title_id = NULL", 'check constraint')
    unknown_id = value("SELECT id FROM streaming_private.source_events WHERE source_key = 'unknown-1'")
    service(event.replace(source_id, unknown_id))
    service("UPDATE streaming_private.viewing_events SET match_state = 'ambiguous' WHERE match_state = 'unmatched'")
    check(value('SELECT count(*) FROM streaming_private.viewing_events') == '3', 'Movie, episode, and unresolved events persist')
    check(value(f"SELECT count(*) FROM streaming_private.viewing_events v JOIN streaming_private.source_events s ON (s.account_id, s.connection_id, s.id) = (v.account_id, v.connection_id, v.source_event_id) JOIN streaming_private.imports i ON (i.account_id, i.connection_id, i.id) = (s.account_id, s.connection_id, s.import_id) WHERE i.id = '{job}'") == '3', 'Complete event/source/import provenance')
    print('PASS streaming ownership constraints, subscriptions, provenance, repeat watches and concurrent replay')

    # Every relation contains Alice's records; Bob cannot discover or mutate them.
    for table in tables:
        query = f"SELECT count(*) FROM streaming_private.{table} WHERE account_id = '{alice}'"
        check('\n0\n' in runtime(query, 'b'), f'Runtime cross-owner read: {table}')
        check(value(query, 'b') == '0', f'Service cross-owner read: {table}')
        check('DELETE 0' in service(f"DELETE FROM streaming_private.{table} WHERE account_id = '{alice}'", 'b'), f'Cross-owner delete: {table}')
        runtime(f'DELETE FROM streaming_private.{table}', ok=False)
        runtime(f"INSERT INTO streaming_private.{table}(account_id) VALUES ('{alice}')", ok=False)
        for role in ['anon', 'authenticated', 'service_role', 'app_auth_service', 'app_streaming_retention']:
            sql(f'SET ROLE {role}; SELECT * FROM streaming_private.{table}', ok=False)
        check('\n0\n' in sql(f'BEGIN; SET LOCAL ROLE app_streaming_service; SELECT count(*) FROM streaming_private.{table}; COMMIT;'), f'Missing context denied: {table}')
        check(value(f'SELECT count(*) FROM streaming_private.{table}', 'c') == '0', f'Unknown context denied: {table}')
    for table, field in [('connections', 'provider_account_key'), ('imports', 'checkpoint'), ('source_events', 'raw_payload')]:
        runtime(f'SELECT {field} FROM streaming_private.{table}', ok=False)
    for table, assignment in [('connections', "state = 'disconnected'"), ('subscriptions', "status = NULL"), ('imports', 'processed_count = 99'), ('source_events', 'raw_payload = NULL'), ('viewing_events', "normalization_version = 'forged'")]:
        check('UPDATE 0' in service(f"UPDATE streaming_private.{table} SET {assignment} WHERE account_id = '{alice}'", 'b'), f'Cross-owner update: {table}')
        runtime(f'UPDATE streaming_private.{table} SET {assignment}', ok=False)
    sql('CREATE ROLE test_streaming LOGIN NOINHERIT IN ROLE app_streaming_service')
    # A role-membership catalog assertion supplements the baseline real-login test.
    check(sql("SELECT pg_has_role('test_streaming', 'app_owner', 'MEMBER') OR pg_has_role('test_streaming', 'app_auth_service', 'MEMBER')") == 'f', 'Streaming login has no elevated memberships')
    for assignment in ["revoked_at = now()", "expires_at = now() - interval '1 second', created_at = now() - interval '1 hour', last_active_at = now() - interval '1 hour'"]:
        sql(f"UPDATE app_private.sessions SET {assignment} WHERE token_hash = '{'a'*64}'")
        for table in tables:
            check(value(f'SELECT count(*) FROM streaming_private.{table}') == '0', f'Invalid session denied: {table}')
        service(source('expired-session'), ok=False)
        sql(f"UPDATE app_private.sessions SET revoked_at = NULL, created_at = now(), last_active_at = now(), expires_at = now() + interval '1 hour' WHERE token_hash = '{'a'*64}'")
    for status in ['restricted', 'deletion_pending']:
        sql(f"UPDATE app_private.accounts SET status = '{status}' WHERE id = '{alice}'")
        for table in tables:
            check(value(f'SELECT count(*) FROM streaming_private.{table}') == '0', f'Inactive owner denied: {table}')
        service(source('inactive-owner'), ok=False)
    sql(f"UPDATE app_private.accounts SET status = 'active' WHERE id = '{alice}'")
    print('PASS all streaming tables deny unauthorized reads/writes and invalid sessions; raw material hidden from runtime')

    # Commit each page and its checkpoint together. An interrupted page is all-or-nothing.
    service("UPDATE streaming_private.imports SET state = 'partial', checkpoint = 'page-1', checkpoint_expires_at = now() + interval '1 day', processed_count = 5")
    service(source('rolled-back') + "; UPDATE streaming_private.imports SET checkpoint = 'page-2', processed_count = 6; SELECT 1/0", ok=False)
    check(value("SELECT count(*) FROM streaming_private.source_events WHERE source_key = 'rolled-back'") == '0', 'Page rollback removes source rows')
    check(value("SELECT checkpoint = 'page-1' AND processed_count = 5 AND state = 'partial' FROM streaming_private.imports") == 't', 'Rollback preserves checkpoint and incompleteness')
    service(source('resumed') + "; UPDATE streaming_private.imports SET checkpoint = 'page-2', processed_count = 6")
    service("UPDATE streaming_private.imports SET state = 'completed', finished_at = now()")
    denied(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{connection}', 'request-1')", 'unique constraint')
    service(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{connection}', 'request-2')")
    new_job = value("SELECT id FROM streaming_private.imports WHERE request_key = 'request-2'")
    denied(source('watch-1', job_id=new_job), 'unique constraint')

    service("UPDATE streaming_private.source_events SET raw_payload = '{\"synthetic\":true}', raw_expires_at = now() - interval '1 second'")
    service("UPDATE streaming_private.imports SET checkpoint_expires_at = now() - interval '1 second'")
    service('SELECT streaming_private.purge_expired_material()', 'b', ok=False)
    check(value('SELECT count(*) FROM streaming_private.source_events WHERE raw_payload IS NOT NULL') == '7', 'Importer cannot run global retention cleanup')
    service("UPDATE streaming_private.source_events SET raw_expires_at = now() + interval '1 day' WHERE source_key = 'unknown-2'")
    sql(f"UPDATE app_private.accounts SET status = 'restricted' WHERE id = '{alice}'")
    sql('SET ROLE app_streaming_retention; SELECT streaming_private.purge_expired_material()')
    sql(f"UPDATE app_private.accounts SET status = 'active' WHERE id = '{alice}'")
    check(value("SELECT count(*) FROM streaming_private.source_events WHERE raw_payload IS NOT NULL AND source_key <> 'unknown-2'") == '0', 'Expired raw material purged for restricted owner')
    check(value("SELECT raw_payload IS NOT NULL FROM streaming_private.source_events WHERE source_key = 'unknown-2'") == 't', 'Cleanup preserves unexpired material')
    check(value('SELECT count(*) FROM streaming_private.imports WHERE checkpoint IS NOT NULL') == '0', 'Expired checkpoints purged')
    denied(source('watch-1', job_id=new_job), 'unique constraint')
    check(value('SELECT count(*) FROM streaming_private.viewing_events') == '3', 'Purge retains normalized history and occurrence identity')
    # A separate provider occurrence remains separate even if title/time coincide.
    service("INSERT INTO streaming_private.connections(provider, provider_account_key, state) VALUES ('other_fixture', 'alice-provider', 'connected')")
    other_connection = value("SELECT id FROM streaming_private.connections WHERE provider = 'other_fixture'")
    service(f"INSERT INTO streaming_private.imports(connection_id, request_key) VALUES ('{other_connection}', 'request-1')")
    other_job = value(f"SELECT id FROM streaming_private.imports WHERE connection_id = '{other_connection}'")
    service(source('watch-1', parent=other_connection, job_id=other_job))
    other_source = value(f"SELECT id FROM streaming_private.source_events WHERE connection_id = '{other_connection}'")
    service(event.replace(connection, other_connection).replace(source_id, other_source))
    check(value('SELECT count(*) FROM streaming_private.viewing_events') == '4', 'No automatic cross-provider watch merging')
    for state in ['revoked', 'disconnected']:
        service(f"UPDATE streaming_private.connections SET state = '{state}' WHERE id = '{connection}'")
        denied(source('after-disconnect'), 'row-level security')
        check('UPDATE 0' in service(f"UPDATE streaming_private.imports SET processed_count = 999 WHERE connection_id = '{connection}'"), 'Disconnected jobs cannot advance')
        for table in ['subscriptions', 'imports', 'source_events', 'viewing_events']:
            check(value(f"SELECT count(*) FROM streaming_private.{table} WHERE connection_id = '{connection}'") == '0', f'Terminal connection immediately hides {table}')
            check('\n0\n' in runtime(f"SELECT count(*) FROM streaming_private.{table} WHERE connection_id = '{connection}'"), f'Runtime hides terminal {table}')
        denied(f"UPDATE streaming_private.connections SET state = 'connected' WHERE id = '{connection}'", 'CONNECTION_GENERATION_ENDED')
    service("INSERT INTO streaming_private.connections(provider, provider_account_key, state) VALUES ('fixture', 'alice-provider', 'connected')")
    check(value(f"SELECT count(*) FROM streaming_private.source_events WHERE connection_id = '{connection}'") == '0', 'Fresh generation does not revive old history')
    # Feature-owned cascades follow operator-authorized final account deletion.
    sql(f"DELETE FROM app_private.accounts WHERE id = '{alice}'")
    for table in tables:
        check(sql(f"SELECT count(*) FROM streaming_private.{table} WHERE account_id = '{alice}'") == '0', f'Account deletion cascades: {table}')
    check(value('SELECT count(*) FROM streaming_private.imports', 'b') == '1', 'Deletion preserves other owner')
    print('PASS atomic import recovery, disconnect/revocation, retention purge, replay after purge and final deletion cascade')
