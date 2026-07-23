-- Memory OS Round 9 account-session store.
-- Apply after 003_memory_os_preview_domain.sql.
--
-- Sessions authenticate requests BEFORE a verified principal (and therefore
-- the owner/epoch RLS context) exists, so this table cannot use the standard
-- tenant policy. Instead the table is reachable exclusively through
-- SECURITY DEFINER functions: no runtime role holds any table privilege, the
-- table stores only SHA-256 token digests (never raw tokens), and the
-- dedicated memory_auth_runtime role is granted EXECUTE on the three
-- functions and nothing else.

BEGIN;

DO $roles$
BEGIN
  BEGIN
    CREATE ROLE memory_auth_runtime NOLOGIN NOINHERIT NOBYPASSRLS;
  EXCEPTION
    WHEN duplicate_object OR unique_violation THEN NULL;
  END;
  ALTER ROLE memory_auth_runtime NOLOGIN NOINHERIT NOBYPASSRLS;
END
$roles$;

GRANT USAGE ON SCHEMA memory_os TO memory_auth_runtime;

CREATE TABLE IF NOT EXISTS memory_os.account_session (
  id text PRIMARY KEY
    CONSTRAINT account_session_id_check CHECK (id ~ '^ses_[A-Za-z0-9_-]{12,120}$'),
  token_digest text NOT NULL
    CONSTRAINT account_session_digest_check CHECK (token_digest ~ '^[a-f0-9]{64}$'),
  owner_account_id text NOT NULL
    CONSTRAINT account_session_owner_check
    CHECK (length(owner_account_id) BETWEEN 16 AND 128),
  account_epoch bigint NOT NULL CHECK (account_epoch >= 0),
  authority text NOT NULL
    CONSTRAINT account_session_authority_check
    CHECK (authority IN ('ios_user_access_token', 'ios_device_session', 'browser_pairing_token')),
  state text NOT NULL DEFAULT 'active'
    CONSTRAINT account_session_state_check CHECK (state IN ('active', 'revoked')),
  created_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  CONSTRAINT account_session_ttl_check CHECK (
    expires_at > created_at
    AND expires_at - created_at <= interval '30 days'
  )
);

ALTER TABLE memory_os.account_session OWNER TO memory_migration_owner;
REVOKE ALL ON TABLE memory_os.account_session FROM PUBLIC;
REVOKE ALL ON TABLE memory_os.account_session FROM
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime,
  memory_readonly_observer, memory_auth_runtime;

CREATE UNIQUE INDEX IF NOT EXISTS account_session_token_digest_uidx
  ON memory_os.account_session (token_digest);

CREATE INDEX IF NOT EXISTS account_session_expiry_idx
  ON memory_os.account_session (expires_at)
  WHERE state = 'active';

CREATE OR REPLACE FUNCTION memory_os.issue_account_session(
  p_id text,
  p_token_digest text,
  p_owner_account_id text,
  p_account_epoch bigint,
  p_authority text,
  p_created_at timestamptz,
  p_expires_at timestamptz
)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $$
  INSERT INTO memory_os.account_session
    (id, token_digest, owner_account_id, account_epoch, authority, state, created_at, expires_at)
  VALUES
    (p_id, p_token_digest, p_owner_account_id, p_account_epoch, p_authority, 'active', p_created_at, p_expires_at);
$$;

CREATE OR REPLACE FUNCTION memory_os.resolve_account_session(p_token_digest text)
RETURNS TABLE (owner_account_id text, account_epoch bigint, authority text)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = pg_catalog, memory_os
AS $$
  SELECT s.owner_account_id, s.account_epoch, s.authority
  FROM memory_os.account_session s
  WHERE s.token_digest = p_token_digest
    AND s.state = 'active'
    AND now() < s.expires_at;
$$;

CREATE OR REPLACE FUNCTION memory_os.revoke_account_session(p_token_digest text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
BEGIN
  UPDATE memory_os.account_session
  SET state = 'revoked'
  WHERE token_digest = p_token_digest AND state = 'active';
  RETURN FOUND;
END
$function$;

ALTER FUNCTION memory_os.issue_account_session(text, text, text, bigint, text, timestamptz, timestamptz)
  OWNER TO memory_migration_owner;
ALTER FUNCTION memory_os.resolve_account_session(text) OWNER TO memory_migration_owner;
ALTER FUNCTION memory_os.revoke_account_session(text) OWNER TO memory_migration_owner;

REVOKE ALL ON FUNCTION memory_os.issue_account_session(text, text, text, bigint, text, timestamptz, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION memory_os.resolve_account_session(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION memory_os.revoke_account_session(text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION memory_os.issue_account_session(text, text, text, bigint, text, timestamptz, timestamptz)
  TO memory_auth_runtime;
GRANT EXECUTE ON FUNCTION memory_os.resolve_account_session(text) TO memory_auth_runtime;
GRANT EXECUTE ON FUNCTION memory_os.revoke_account_session(text) TO memory_auth_runtime;

COMMIT;
