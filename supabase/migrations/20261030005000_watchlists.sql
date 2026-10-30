-- Server-only persistence API. Catalog ingestion owns identity resolution; runtime
-- callers cannot mint titles or supply account IDs. No provider calls on this path.
SET LOCAL ROLE app_owner;
CREATE TABLE app_private.watchlist_catalog_titles (
    catalog_entity_id uuid PRIMARY KEY,
    media_kind text NOT NULL CHECK (media_kind IN ('movie', 'series')),
    display_title text NOT NULL CHECK (char_length(btrim(display_title)) BETWEEN 1 AND 500),
    release_year integer CHECK (release_year BETWEEN 1 AND 9999)
);
-- This minimal catalog projection is populated by the trusted catalog integration,
-- not by browsers or the auth service. Keep stable IDs even when offers disappear.
ALTER TABLE app_private.watchlist_catalog_titles ENABLE ROW LEVEL SECURITY;

CREATE TABLE app_private.watchlist_entries (
    account_id uuid NOT NULL REFERENCES app_private.accounts(id) ON DELETE CASCADE,
    catalog_entity_id uuid NOT NULL REFERENCES app_private.watchlist_catalog_titles(catalog_entity_id) ON DELETE RESTRICT,
    media_kind text NOT NULL CHECK (media_kind IN ('movie', 'series')),
    display_title text NOT NULL,
    release_year integer,
    saved_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    PRIMARY KEY (account_id, catalog_entity_id)
);
CREATE INDEX watchlist_entries_order_idx
    ON app_private.watchlist_entries(account_id, saved_at DESC, catalog_entity_id DESC);
ALTER TABLE app_private.watchlist_entries ENABLE ROW LEVEL SECURITY;
-- No runtime table grants: every operation goes through an owner-scoped function.

CREATE FUNCTION app_private.watchlist_actor()
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid;
BEGIN
    actor := app_private.current_account();
    IF actor IS NULL THEN
        RAISE EXCEPTION 'UNAUTHENTICATED' USING ERRCODE = '28000';
    END IF;
    IF NOT EXISTS (SELECT FROM app_private.profiles WHERE account_id = actor AND display_name IS NOT NULL) THEN
        RAISE EXCEPTION 'PROFILE_INCOMPLETE' USING ERRCODE = '42501';
    END IF;
    RETURN actor;
END;
$$;

CREATE FUNCTION app_api.save_watchlist_title(p_catalog_entity_id uuid)
RETURNS TABLE (catalog_entity_id uuid, media_kind text, display_title text, release_year integer, saved_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid;
BEGIN
    actor := app_private.watchlist_actor();
    IF p_catalog_entity_id IS NULL THEN
        RAISE EXCEPTION 'VALIDATION_FAILED' USING ERRCODE = '22023';
    END IF;
    RETURN QUERY
    INSERT INTO app_private.watchlist_entries AS saved
        (account_id, catalog_entity_id, media_kind, display_title, release_year)
    SELECT actor, c.catalog_entity_id, c.media_kind, c.display_title, c.release_year
    FROM app_private.watchlist_catalog_titles c WHERE c.catalog_entity_id = p_catalog_entity_id
    ON CONFLICT ON CONSTRAINT watchlist_entries_pkey DO UPDATE
        SET catalog_entity_id = EXCLUDED.catalog_entity_id
    RETURNING saved.catalog_entity_id, saved.media_kind, saved.display_title, saved.release_year, saved.saved_at;
    -- The no-op update returns the original snapshot/time even for concurrent saves.
    IF NOT FOUND THEN
        RAISE EXCEPTION 'NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
END;
$$;

CREATE FUNCTION app_api.list_watchlist(
    p_limit integer DEFAULT 50,
    p_before_saved_at timestamptz DEFAULT NULL,
    p_before_catalog_entity_id uuid DEFAULT NULL
)
RETURNS TABLE (catalog_entity_id uuid, media_kind text, display_title text, release_year integer, saved_at timestamptz)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid;
BEGIN
    actor := app_private.watchlist_actor();
    IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100
       OR (p_before_saved_at IS NULL) <> (p_before_catalog_entity_id IS NULL) THEN
        RAISE EXCEPTION 'VALIDATION_FAILED' USING ERRCODE = '22023';
    END IF;
    RETURN QUERY
    SELECT w.catalog_entity_id, w.media_kind, w.display_title, w.release_year, w.saved_at
    FROM app_private.watchlist_entries w
    WHERE w.account_id = actor
      AND (p_before_saved_at IS NULL OR
           (w.saved_at, w.catalog_entity_id) < (p_before_saved_at, p_before_catalog_entity_id))
    ORDER BY w.saved_at DESC, w.catalog_entity_id DESC LIMIT p_limit;
END;
$$;

CREATE FUNCTION app_api.remove_watchlist_title(p_catalog_entity_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid;
BEGIN
    actor := app_private.watchlist_actor();
    IF p_catalog_entity_id IS NULL THEN
        RAISE EXCEPTION 'VALIDATION_FAILED' USING ERRCODE = '22023';
    END IF;
    DELETE FROM app_private.watchlist_entries
    WHERE account_id = actor AND catalog_entity_id = p_catalog_entity_id;
END;
$$;

REVOKE ALL ON FUNCTION app_private.watchlist_actor() FROM PUBLIC;
REVOKE ALL ON FUNCTION app_api.save_watchlist_title(uuid),
    app_api.list_watchlist(integer, timestamptz, uuid), app_api.remove_watchlist_title(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_api.save_watchlist_title(uuid),
    app_api.list_watchlist(integer, timestamptz, uuid), app_api.remove_watchlist_title(uuid) TO app_runtime;
RESET ROLE;
