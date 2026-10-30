-- Provisional streaming persistence contract; see docs/streaming-persistence.md.
-- Extends SUR-8 without changing its account/profile schema or identity boundary.
DO $$
DECLARE role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['app_streaming_service', 'app_streaming_retention'] LOOP
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS', role_name);
        END IF;
        IF EXISTS (SELECT FROM pg_roles WHERE rolname = role_name AND
            (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolinherit OR rolbypassrls)) THEN
            RAISE EXCEPTION 'Unsafe existing role: %', role_name;
        END IF;
    END LOOP;
END $$;
CREATE SCHEMA streaming_private AUTHORIZATION app_owner;
SET LOCAL ROLE app_owner;
REVOKE ALL ON SCHEMA streaming_private FROM PUBLIC;
GRANT USAGE ON SCHEMA app_private, streaming_private TO app_streaming_service;
GRANT EXECUTE ON FUNCTION app_private.current_account() TO app_streaming_service;
GRANT USAGE ON SCHEMA streaming_private TO app_runtime;

CREATE TABLE streaming_private.connections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id uuid NOT NULL DEFAULT app_private.current_account()
        REFERENCES app_private.profiles(account_id) ON DELETE CASCADE,
    provider text COLLATE "C" NOT NULL CHECK (provider ~ '^[a-z][a-z0-9_-]{0,63}$'),
    -- Opaque provider account/profile identifiers, never email or credentials.
    provider_account_key text COLLATE "C" NOT NULL CHECK (length(provider_account_key) BETWEEN 1 AND 512),
    provider_profile_key text COLLATE "C" NOT NULL DEFAULT '' CHECK (length(provider_profile_key) <= 512),
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'connected', 'revoked', 'disconnected')),
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    UNIQUE (account_id, id)
);
-- Each connection ID is one authorization generation. Reconnect creates a new
-- row; stale jobs remain attached to the terminal generation and cannot revive it.
CREATE UNIQUE INDEX one_live_provider_binding ON streaming_private.connections
    (account_id, provider, provider_account_key, provider_profile_key)
    WHERE state IN ('pending', 'connected');
CREATE FUNCTION streaming_private.enforce_connection_generation()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF (OLD.state IN ('revoked', 'disconnected') AND NEW.state IN ('pending', 'connected'))
       OR (OLD.state = 'connected' AND NEW.state = 'pending') THEN
        RAISE EXCEPTION 'CONNECTION_GENERATION_ENDED' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER connection_generation BEFORE UPDATE ON streaming_private.connections
    FOR EACH ROW EXECUTE FUNCTION streaming_private.enforce_connection_generation();

-- Locks order: session/account first, then connection. A completed disconnect
-- prevents further writes; in-flight writes finish before disconnect commits.
CREATE FUNCTION streaming_private.can_import(p_account uuid, p_connection uuid)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    IF p_account IS DISTINCT FROM app_private.current_account() THEN RETURN false; END IF;
    PERFORM 1 FROM streaming_private.connections
    WHERE account_id = p_account AND id = p_connection AND state = 'connected' FOR SHARE;
    RETURN FOUND;
END $$;
GRANT EXECUTE ON FUNCTION streaming_private.can_import(uuid, uuid) TO app_streaming_service, app_runtime;

CREATE TABLE streaming_private.subscriptions (
    account_id uuid NOT NULL DEFAULT app_private.current_account(),
    connection_id uuid NOT NULL,
    -- NULL means no observation, never inactive. Unsupported fields stay NULL.
    supported_fields text[] NOT NULL DEFAULT '{}' CHECK (
        supported_fields <@ ARRAY['status', 'plan_name', 'renews_at']::text[]
        AND array_position(supported_fields, NULL) IS NULL),
    status text CHECK (status IN ('active', 'trial', 'paused', 'canceled', 'inactive', 'unknown')),
    plan_name text CHECK (length(plan_name) BETWEEN 1 AND 200),
    renews_at timestamptz,
    observed_at timestamptz NOT NULL,
    PRIMARY KEY (account_id, connection_id),
    FOREIGN KEY (account_id, connection_id) REFERENCES streaming_private.connections(account_id, id) ON DELETE CASCADE,
    CHECK (status IS NULL OR 'status' = ANY(supported_fields)),
    CHECK (plan_name IS NULL OR 'plan_name' = ANY(supported_fields)),
    CHECK (renews_at IS NULL OR 'renews_at' = ANY(supported_fields))
);

CREATE TABLE streaming_private.imports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id uuid NOT NULL DEFAULT app_private.current_account(),
    connection_id uuid NOT NULL,
    request_key text COLLATE "C" NOT NULL CHECK (length(request_key) BETWEEN 1 AND 512),
    state text NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'running', 'partial', 'completed', 'failed', 'canceled')),
    checkpoint text CHECK (octet_length(checkpoint) <= 16384),
    checkpoint_expires_at timestamptz,
    processed_count bigint NOT NULL DEFAULT 0 CHECK (processed_count >= 0),
    -- Explicit coverage supplied by adapter; completion does not mean all-time history.
    coverage_start timestamptz,
    coverage_end timestamptz,
    error_code text CHECK (error_code ~ '^[A-Z][A-Z0-9_]{0,63}$'),
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    finished_at timestamptz,
    UNIQUE (account_id, connection_id, id),
    UNIQUE (account_id, connection_id, request_key),
    FOREIGN KEY (account_id, connection_id) REFERENCES streaming_private.connections(account_id, id) ON DELETE CASCADE,
    CHECK (checkpoint IS NULL OR checkpoint_expires_at IS NOT NULL),
    CHECK ((state IN ('completed', 'failed', 'canceled')) = (finished_at IS NOT NULL)),
    CHECK (coverage_start IS NULL OR coverage_end IS NULL OR coverage_end >= coverage_start)
);
CREATE UNIQUE INDEX one_open_import_per_connection ON streaming_private.imports(account_id, connection_id)
    WHERE state IN ('queued', 'running', 'partial');

CREATE TABLE streaming_private.source_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id uuid NOT NULL DEFAULT app_private.current_account(),
    connection_id uuid NOT NULL,
    import_id uuid NOT NULL,
    -- Stable occurrence identity assigned by the adapter, not a title/time hash.
    source_key text COLLATE "C" NOT NULL CHECK (length(source_key) BETWEEN 1 AND 512),
    identity_basis text NOT NULL CHECK (identity_basis IN ('provider_event_id', 'stable_source_locator')),
    provider_title_key text COLLATE "C" CHECK (length(provider_title_key) BETWEEN 1 AND 512),
    occurred_at timestamptz,
    occurred_on date,
    time_precision text NOT NULL CHECK (time_precision IN ('instant', 'date', 'unknown')),
    raw_payload jsonb CHECK (jsonb_typeof(raw_payload) = 'object'),
    raw_expires_at timestamptz,
    received_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    UNIQUE (account_id, connection_id, id),
    UNIQUE (account_id, connection_id, source_key),
    FOREIGN KEY (account_id, connection_id) REFERENCES streaming_private.connections(account_id, id) ON DELETE CASCADE,
    FOREIGN KEY (account_id, connection_id, import_id) REFERENCES streaming_private.imports(account_id, connection_id, id),
    CHECK ((time_precision = 'instant' AND occurred_at IS NOT NULL AND occurred_on IS NULL)
        OR (time_precision = 'date' AND occurred_at IS NULL AND occurred_on IS NOT NULL)
        OR (time_precision = 'unknown' AND occurred_at IS NULL AND occurred_on IS NULL)),
    CHECK (raw_payload IS NULL OR raw_expires_at IS NOT NULL)
);
CREATE INDEX source_events_import_idx ON streaming_private.source_events(account_id, connection_id, import_id);
CREATE INDEX source_events_expiry_idx ON streaming_private.source_events(raw_expires_at) WHERE raw_payload IS NOT NULL;

CREATE TABLE streaming_private.viewing_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id uuid NOT NULL DEFAULT app_private.current_account(),
    connection_id uuid NOT NULL,
    source_event_id uuid NOT NULL,
    media_kind text NOT NULL CHECK (media_kind IN ('movie', 'episode')),
    match_state text NOT NULL CHECK (match_state IN ('matched', 'unmatched', 'ambiguous')),
    catalog_namespace text CHECK (catalog_namespace ~ '^[a-z][a-z0-9_-]{0,63}$'),
    catalog_title_id text COLLATE "C" CHECK (length(catalog_title_id) BETWEEN 1 AND 512),
    -- For episodes, catalog_title_id identifies the episode, not its series.
    normalization_version text NOT NULL CHECK (length(normalization_version) BETWEEN 1 AND 100),
    normalized_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    UNIQUE (account_id, connection_id, source_event_id),
    FOREIGN KEY (account_id, connection_id) REFERENCES streaming_private.connections(account_id, id) ON DELETE CASCADE,
    FOREIGN KEY (account_id, connection_id, source_event_id)
        REFERENCES streaming_private.source_events(account_id, connection_id, id) ON DELETE CASCADE,
    CHECK ((match_state = 'matched') = (catalog_namespace IS NOT NULL AND catalog_title_id IS NOT NULL)),
    CHECK ((catalog_namespace IS NULL) = (catalog_title_id IS NULL))
);
-- Timestamp and source provenance are read by joining source_events, so they
-- cannot disagree with a second copied timestamp on the normalized event.

DO $$
DECLARE relation text;
BEGIN
    FOREACH relation IN ARRAY ARRAY['connections', 'subscriptions', 'imports', 'source_events', 'viewing_events'] LOOP
        EXECUTE format('ALTER TABLE streaming_private.%I ENABLE ROW LEVEL SECURITY', relation);
        IF relation = 'connections' THEN
            EXECUTE format('CREATE POLICY own_read ON streaming_private.%I FOR SELECT TO app_runtime, app_streaming_service USING (account_id = (SELECT app_private.current_account()))', relation);
            EXECUTE format('CREATE POLICY own_write ON streaming_private.%I FOR ALL TO app_streaming_service USING (account_id = (SELECT app_private.current_account())) WITH CHECK (account_id = (SELECT app_private.current_account()))', relation);
        ELSE
            EXECUTE format('CREATE POLICY own_read ON streaming_private.%I FOR SELECT TO app_runtime, app_streaming_service USING (streaming_private.can_import(account_id, connection_id))', relation);
            EXECUTE format('CREATE POLICY connected_insert ON streaming_private.%I FOR INSERT TO app_streaming_service WITH CHECK (streaming_private.can_import(account_id, connection_id))', relation);
            EXECUTE format('CREATE POLICY connected_update ON streaming_private.%I FOR UPDATE TO app_streaming_service USING (streaming_private.can_import(account_id, connection_id)) WITH CHECK (streaming_private.can_import(account_id, connection_id))', relation);
            EXECUTE format('CREATE POLICY own_delete ON streaming_private.%I FOR DELETE TO app_streaming_service USING (account_id = (SELECT app_private.current_account()))', relation);
        END IF;
        EXECUTE format('GRANT SELECT, DELETE ON streaming_private.%I TO app_streaming_service', relation);
    END LOOP;
END $$;
-- Column grants prevent moving records between owners/parents or changing their
-- idempotency keys. No feature role can set account_id, IDs or creation timestamps.
GRANT INSERT (provider, provider_account_key, provider_profile_key, state), UPDATE (state)
    ON streaming_private.connections TO app_streaming_service;
GRANT INSERT (connection_id, supported_fields, status, plan_name, renews_at, observed_at),
    UPDATE (supported_fields, status, plan_name, renews_at, observed_at)
    ON streaming_private.subscriptions TO app_streaming_service;
GRANT INSERT (connection_id, request_key, coverage_start, coverage_end),
    UPDATE (state, checkpoint, checkpoint_expires_at, processed_count, coverage_start, coverage_end, error_code, finished_at)
    ON streaming_private.imports TO app_streaming_service;
GRANT INSERT (connection_id, import_id, source_key, identity_basis, provider_title_key, occurred_at, occurred_on, time_precision, raw_payload, raw_expires_at),
    UPDATE (raw_payload, raw_expires_at)
    ON streaming_private.source_events TO app_streaming_service;
GRANT INSERT (connection_id, source_event_id, media_kind, match_state, catalog_namespace, catalog_title_id, normalization_version),
    UPDATE (media_kind, match_state, catalog_namespace, catalog_title_id, normalization_version, normalized_at)
    ON streaming_private.viewing_events TO app_streaming_service;

GRANT SELECT (id, account_id, provider, state, created_at) ON streaming_private.connections TO app_runtime;
GRANT SELECT ON streaming_private.subscriptions, streaming_private.viewing_events TO app_runtime;
GRANT SELECT (id, account_id, connection_id, state, processed_count, coverage_start, coverage_end, error_code, created_at, finished_at)
    ON streaming_private.imports TO app_runtime;
GRANT SELECT (id, account_id, connection_id, import_id, occurred_at, occurred_on, time_precision, received_at)
    ON streaming_private.source_events TO app_runtime;

-- Erase transient material while retaining occurrence keys/provenance needed to
-- avoid replay duplicates. A separate cleanup role can only erase expired
-- material, including for restricted owners; it cannot read records or set deadlines.
CREATE FUNCTION streaming_private.purge_expired_material()
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
BEGIN
    UPDATE streaming_private.source_events SET raw_payload = NULL
    WHERE raw_expires_at <= statement_timestamp() AND raw_payload IS NOT NULL;
    UPDATE streaming_private.imports SET checkpoint = NULL
    WHERE checkpoint_expires_at <= statement_timestamp() AND checkpoint IS NOT NULL;
END $$;
GRANT USAGE ON SCHEMA streaming_private TO app_streaming_retention;
GRANT EXECUTE ON FUNCTION streaming_private.purge_expired_material() TO app_streaming_retention;
RESET ROLE;
