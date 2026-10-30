-- PostgreSQL 17. Apply as the migration administrator, never the runtime role.
-- Roles are cluster-wide; isolate environments in separate clusters/projects.
DO $$
DECLARE role_name text;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['app_owner', 'app_runtime', 'app_auth_service'] LOOP
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS', role_name);
        END IF;
        IF EXISTS (SELECT FROM pg_roles WHERE rolname = role_name AND
            (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolinherit OR rolbypassrls)) THEN
            RAISE EXCEPTION 'Unsafe existing role: %', role_name;
        END IF;
    END LOOP;
END;
$$;
-- Supabase's migration administrator must be able to SET ROLE to the object owner.
GRANT app_owner TO CURRENT_USER;
CREATE SCHEMA app_private AUTHORIZATION app_owner;
CREATE SCHEMA app_api AUTHORIZATION app_owner;
SET LOCAL ROLE app_owner;
REVOKE ALL ON SCHEMA app_private, app_api FROM PUBLIC;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES REVOKE ALL ON TABLES FROM PUBLIC;

CREATE TABLE app_private.accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'restricted', 'deletion_pending')),
    created_at timestamptz NOT NULL DEFAULT statement_timestamp()
);
CREATE TABLE app_private.identities (
    issuer text COLLATE "C" NOT NULL CHECK (octet_length(issuer) BETWEEN 1 AND 1024),
    subject text COLLATE "C" NOT NULL CHECK (length(subject) BETWEEN 1 AND 255),
    account_id uuid NOT NULL UNIQUE REFERENCES app_private.accounts(id) ON DELETE CASCADE,
    PRIMARY KEY (issuer, subject)
);
-- No provider credentials, email, name inferred from email, or feature data.
CREATE TABLE app_private.profiles (
    account_id uuid PRIMARY KEY REFERENCES app_private.accounts(id) ON DELETE CASCADE,
    display_name text,
    version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    CHECK (display_name IS NULL OR (
        char_length(display_name) BETWEEN 1 AND 80
        AND display_name = normalize(display_name, NFC)
        AND display_name !~ U&'[\0001-\001F\007F-\009F]'
        AND display_name = btrim(display_name, U&'\0009\000A\000B\000C\000D\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000')
    ))
);
-- Auth adapter stores SHA-256 of a random >=256-bit opaque cookie, never the cookie.
-- Provider token storage/refresh and provider-session validation belong to SUR-9.
CREATE TABLE app_private.sessions (
    token_hash text COLLATE "C" PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    account_id uuid NOT NULL REFERENCES app_private.accounts(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    last_active_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > created_at AND expires_at <= created_at + interval '7 days'),
    CHECK (last_active_at >= created_at)
);
CREATE INDEX sessions_account_id_idx ON app_private.sessions(account_id);
ALTER TABLE app_private.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_private.identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_private.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_private.sessions ENABLE ROW LEVEL SECURITY;

-- The trusted auth adapter calls this only after verifying the provider identity
-- and email verification. It must allowlist the exact environment-specific issuer.
CREATE FUNCTION app_api.provision_account(p_issuer text, p_subject text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid; account_status text;
BEGIN
    IF p_issuer IS NULL OR p_subject IS NULL THEN
        RAISE EXCEPTION 'VALIDATION_FAILED' USING ERRCODE = '22023';
    END IF;
    -- Serialize retries of this mapping, including concurrent first sign-ins.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_issuer || ':' || p_subject, 0));
    SELECT i.account_id, a.status INTO actor, account_status
    FROM app_private.identities i JOIN app_private.accounts a ON a.id = i.account_id
    WHERE i.issuer = p_issuer AND i.subject = p_subject FOR SHARE OF a;
    IF FOUND THEN
        IF account_status <> 'active' THEN
            RAISE EXCEPTION 'FORBIDDEN' USING ERRCODE = '42501';
        END IF;
        RETURN actor;
    END IF;
    INSERT INTO app_private.accounts DEFAULT VALUES RETURNING id INTO actor;
    INSERT INTO app_private.identities VALUES (p_issuer, p_subject, actor);
    INSERT INTO app_private.profiles(account_id) VALUES (actor);
    RETURN actor;
END;
$$;

-- The context is set by the server inside the same transaction as the query.
-- Missing/unknown/revoked/expired context yields no actor. Locks serialize protected
-- operations with revocation/restriction until transaction end (READ COMMITTED).
CREATE FUNCTION app_private.current_account()
RETURNS uuid LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid;
BEGIN
    SELECT s.account_id INTO actor
    FROM app_private.sessions s JOIN app_private.accounts a ON a.id = s.account_id
    WHERE s.token_hash = current_setting('app.session_hash', true)
      AND s.revoked_at IS NULL AND a.status = 'active'
      AND s.created_at <= statement_timestamp()
      AND s.last_active_at <= statement_timestamp()
      AND s.expires_at > statement_timestamp()
      AND s.last_active_at + interval '24 hours' > statement_timestamp()
    FOR SHARE OF s, a;
    RETURN actor;
END;
$$;
CREATE POLICY own_profile ON app_private.profiles FOR SELECT TO app_runtime
    USING (account_id = (SELECT app_private.current_account()));
-- No direct Data API grants, including authenticated and service_role. These
-- schemas must remain outside Supabase's exposed schemas. Owner bypass is only
-- available through the narrowly granted SECURITY DEFINER functions below.
GRANT USAGE ON SCHEMA app_private, app_api TO app_runtime;
GRANT SELECT ON app_private.profiles TO app_runtime;
GRANT EXECUTE ON FUNCTION app_private.current_account() TO app_runtime;
GRANT USAGE ON SCHEMA app_private, app_api TO app_auth_service;
GRANT EXECUTE ON FUNCTION app_api.provision_account(text, text) TO app_auth_service;
-- The auth adapter needs all-session revocation and action-based idle renewal.
-- It cannot change account IDs, creation time, or absolute expiry on an issued session.
GRANT SELECT, INSERT ON app_private.sessions TO app_auth_service;
GRANT UPDATE (last_active_at, revoked_at) ON app_private.sessions TO app_auth_service;
CREATE POLICY auth_sessions ON app_private.sessions TO app_auth_service
    USING (true) WITH CHECK (true);
RESET ROLE;
