-- Additive upgrade: existing identities, shells and sessions remain intact.
SET LOCAL ROLE app_owner;
CREATE FUNCTION app_api.update_own_profile(p_display_name text, p_expected_version bigint)
RETURNS app_private.profiles LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor uuid; saved app_private.profiles; canonical_name text;
BEGIN
    actor := app_private.current_account();
    IF actor IS NULL THEN
        RAISE EXCEPTION 'UNAUTHENTICATED' USING ERRCODE = '28000';
    END IF;
    canonical_name := normalize(btrim(p_display_name, U&'\0009\000A\000B\000C\000D\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'), NFC);
    IF canonical_name IS NULL OR char_length(canonical_name) NOT BETWEEN 1 AND 80
       OR canonical_name ~ U&'[\0001-\001F\007F-\009F]'
       OR p_expected_version IS NULL OR p_expected_version < 0 THEN
        RAISE EXCEPTION 'VALIDATION_FAILED' USING ERRCODE = '22023';
    END IF;
    UPDATE app_private.profiles SET display_name = canonical_name,
        version = version + 1, updated_at = statement_timestamp()
    WHERE account_id = actor AND version = p_expected_version
    RETURNING * INTO saved;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'CONFLICT' USING ERRCODE = '40001';
    END IF;
    RETURN saved;
END;
$$;
REVOKE ALL ON FUNCTION app_api.update_own_profile(text, bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_api.update_own_profile(text, bigint) TO app_runtime;
RESET ROLE;
