-- Memory OS Round 9 Sign in with Apple identity binding and replay store.
-- Apply after 009_memory_os_deletion_visibility.sql.
--
-- Two definer-only surfaces, reachable only by memory_auth_runtime through the
-- SECURITY DEFINER functions below — never by table grant:
--
--   apple_identity  the canonical binding (issuer, subject) -> account. This is
--                   the account holder's Apple identity, so it is account-owned
--                   PII and is erased with the account.
--   apple_replay    single-use nonce and authorization-code digests, with a
--                   TTL. These are anti-replay records, not account data: the
--                   digest reveals nothing and is consumed before an account is
--                   even resolved, so it is cleaned by TTL, not by the account
--                   sweep.
--
-- The canonical identity key is (issuer, subject), matching the Apple auth
-- contract. Email is never an identity key and never auto-links an account.

BEGIN;

CREATE TABLE IF NOT EXISTS memory_os.apple_identity (
  issuer text NOT NULL
    CONSTRAINT apple_identity_issuer_check CHECK (length(issuer) BETWEEN 1 AND 255),
  subject text NOT NULL
    CONSTRAINT apple_identity_subject_check CHECK (length(subject) BETWEEN 1 AND 255),
  account_id text NOT NULL
    CONSTRAINT apple_identity_account_check CHECK (length(account_id) BETWEEN 16 AND 128),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (issuer, subject)
);

ALTER TABLE memory_os.apple_identity OWNER TO memory_migration_owner;
REVOKE ALL ON TABLE memory_os.apple_identity FROM PUBLIC;
REVOKE ALL ON TABLE memory_os.apple_identity FROM
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime,
  memory_readonly_observer, memory_auth_runtime;

-- One Apple identity maps to exactly one account, and one account is created by
-- exactly one Apple identity: the reverse uniqueness stops a second identity
-- from quietly attaching to an existing account.
CREATE UNIQUE INDEX IF NOT EXISTS apple_identity_account_uidx
  ON memory_os.apple_identity (account_id);

CREATE TABLE IF NOT EXISTS memory_os.apple_replay (
  scope text NOT NULL CONSTRAINT apple_replay_scope_check CHECK (scope IN ('nonce', 'code')),
  digest text NOT NULL CONSTRAINT apple_replay_digest_check CHECK (digest ~ '^[a-f0-9]{64}$'),
  consumed_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (scope, digest),
  CONSTRAINT apple_replay_ttl_check CHECK (expires_at > consumed_at)
);

ALTER TABLE memory_os.apple_replay OWNER TO memory_migration_owner;
REVOKE ALL ON TABLE memory_os.apple_replay FROM PUBLIC;
REVOKE ALL ON TABLE memory_os.apple_replay FROM
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime,
  memory_readonly_observer, memory_auth_runtime;

CREATE INDEX IF NOT EXISTS apple_replay_expiry_idx ON memory_os.apple_replay (expires_at);

-- consume_apple_replay atomically claims both the nonce and the code digest.
-- Either one already present is a replay, and the whole call fails closed: the
-- two inserts share one statement's implicit transaction, so a duplicate on
-- either rolls back both and nothing is half-consumed.
CREATE OR REPLACE FUNCTION memory_os.consume_apple_replay(
  p_nonce_digest text,
  p_code_digest text,
  p_ttl_seconds integer
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  expiry timestamptz;
BEGIN
  IF p_nonce_digest !~ '^[a-f0-9]{64}$' OR p_code_digest !~ '^[a-f0-9]{64}$' THEN
    RAISE EXCEPTION 'replay digests must be hex sha-256' USING ERRCODE = '22023';
  END IF;
  IF p_ttl_seconds < 1 OR p_ttl_seconds > 3600 THEN
    RAISE EXCEPTION 'replay ttl out of range' USING ERRCODE = '22023';
  END IF;
  expiry := now() + make_interval(secs => p_ttl_seconds);

  -- Opportunistic TTL cleanup so the table cannot grow without bound; scoped to
  -- already-expired rows, so it never removes a live guard.
  DELETE FROM memory_os.apple_replay WHERE expires_at < now();

  INSERT INTO memory_os.apple_replay (scope, digest, expires_at)
  VALUES ('nonce', p_nonce_digest, expiry), ('code', p_code_digest, expiry);
END
$function$;

ALTER FUNCTION memory_os.consume_apple_replay(text, text, integer) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.consume_apple_replay(text, text, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.consume_apple_replay(text, text, integer) TO memory_auth_runtime;

-- provision_apple_identity resolves (issuer, subject) to an account, creating a
-- fresh active account on first sight and returning the existing one otherwise.
-- p_candidate_account_id is used only when a new account is created; on a
-- returning identity it is ignored, so a caller cannot redirect an existing
-- binding by supplying a different id.
--
-- Concurrency: two simultaneous first logins race on the (issuer, subject)
-- primary key. The loser's INSERT does nothing, and the following SELECT reads
-- the winner's row, so exactly one account is ever created.
--
-- A returning identity whose account is not 'active' is refused rather than
-- revived: a deleted tombstone is never unconditionally brought back, and the
-- binding conflict decision from the contract is deny-and-require-recovery.
CREATE OR REPLACE FUNCTION memory_os.provision_apple_identity(
  p_issuer text,
  p_subject text,
  p_candidate_account_id text
)
RETURNS TABLE (account_id text, account_epoch bigint, created boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  bound_account_id text;
  bound_epoch bigint;
  bound_state text;
  did_create boolean := false;
BEGIN
  IF length(coalesce(p_issuer, '')) = 0 OR length(coalesce(p_subject, '')) = 0 THEN
    RAISE EXCEPTION 'issuer and subject are required' USING ERRCODE = '22023';
  END IF;
  IF length(coalesce(p_candidate_account_id, '')) NOT BETWEEN 16 AND 128 THEN
    RAISE EXCEPTION 'candidate account id is invalid' USING ERRCODE = '22023';
  END IF;

  -- Claim the identity if it is new. ON CONFLICT DO NOTHING makes this safe
  -- under concurrent first logins; only the winner inserts.
  INSERT INTO memory_os.apple_identity (issuer, subject, account_id)
  VALUES (p_issuer, p_subject, p_candidate_account_id)
  ON CONFLICT (issuer, subject) DO NOTHING;

  SELECT identity.account_id INTO bound_account_id
  FROM memory_os.apple_identity AS identity
  WHERE identity.issuer = p_issuer AND identity.subject = p_subject;

  -- account_control has FORCE row-level security, which binds even this definer
  -- function's owner: both its SELECT and INSERT policies are scoped to
  -- current_account_id(). The transaction context is therefore set to the
  -- resolved account so the reads and the create below can see exactly that one
  -- account and nothing else. This is the one place a brand-new account's own
  -- context can legitimately be asserted.
  PERFORM set_config('app.current_account_id', bound_account_id, true);
  PERFORM set_config('app.current_account_epoch', '0', true);

  IF bound_account_id = p_candidate_account_id THEN
    -- We won the race (or are the sole caller). Create the control row in the
    -- same transaction, so an identity binding never exists without its account.
    -- If control creation fails, the whole call rolls back.
    INSERT INTO memory_os.account_control (account_id, account_epoch, state)
    VALUES (p_candidate_account_id, 0, 'active');
    did_create := true;
  END IF;

  SELECT control.account_epoch, control.state
  INTO bound_epoch, bound_state
  FROM memory_os.account_control AS control
  WHERE control.account_id = bound_account_id;

  IF bound_state IS NULL THEN
    RAISE EXCEPTION 'identity resolved to an account with no control row'
      USING ERRCODE = 'internal_error';
  END IF;
  IF bound_state <> 'active' THEN
    -- A returning identity whose account is deleting, deleted or suspended is
    -- refused. Revival is a recovery flow, not a side effect of signing in.
    RAISE EXCEPTION 'account is not active and will not be revived by sign-in'
      USING ERRCODE = 'raise_exception';
  END IF;

  account_id := bound_account_id;
  account_epoch := bound_epoch;
  created := did_create;
  RETURN NEXT;
END
$function$;

ALTER FUNCTION memory_os.provision_apple_identity(text, text, text) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.provision_apple_identity(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.provision_apple_identity(text, text, text) TO memory_auth_runtime;

-- purge_apple_identity removes the account holder's Apple binding on deletion,
-- keeping the definer-only access path rather than granting the deletion
-- runtime a table privilege. Gated on the deleting state exactly like
-- purge_account_sessions in migration 006.
CREATE OR REPLACE FUNCTION memory_os.purge_apple_identity()
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  removed_count bigint;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM memory_os.account_control AS account
    WHERE account.account_id = memory_os.current_account_id()
      AND account.state = 'deleting'
  ) THEN
    RAISE EXCEPTION 'identity purge requires an account in deleting state'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  DELETE FROM memory_os.apple_identity
  WHERE account_id = memory_os.current_account_id();
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  RETURN removed_count;
END
$function$;

ALTER FUNCTION memory_os.purge_apple_identity() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.purge_apple_identity() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.purge_apple_identity() TO memory_deletion_runtime;

-- Extend the account sweep to erase the Apple identity binding. This replaces
-- the function body from migration 006 rather than editing that migration;
-- appending 'apple_identity' keeps every deleted account free of its Apple PII.
CREATE OR REPLACE FUNCTION memory_os.sweep_deleted_account()
RETURNS TABLE (table_name text, removed bigint)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  removed_count bigint;
BEGIN
  IF memory_os.current_account_id() IS NULL OR memory_os.current_account_epoch() IS NULL THEN
    RAISE EXCEPTION 'verified account and epoch context are required'
      USING ERRCODE = 'insufficient_privilege';
  END IF;

  DELETE FROM memory_os.memory_item;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'memory_item'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.preview_candidate;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'preview_candidate'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.preview_rejection;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'preview_rejection'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.preview_ready;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'preview_ready'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.apply_confirmation;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'apply_confirmation'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.quarantine_object;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'quarantine_object'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.upload_authorization;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'upload_authorization'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.import_job;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'import_job'; removed := removed_count; RETURN NEXT;

  table_name := 'account_session';
  removed := memory_os.purge_account_sessions();
  RETURN NEXT;

  table_name := 'apple_identity';
  removed := memory_os.purge_apple_identity();
  RETURN NEXT;

  RETURN;
END
$function$;

ALTER FUNCTION memory_os.sweep_deleted_account() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.sweep_deleted_account() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.sweep_deleted_account() TO memory_deletion_runtime;

COMMIT;
