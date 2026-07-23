\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS memory_os_session_test;

CREATE OR REPLACE FUNCTION memory_os_session_test.expect_sqlstate(
  statement text,
  accepted_codes text[],
  message text
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
AS $function$
BEGIN
  BEGIN
    EXECUTE statement;
    RAISE EXCEPTION 'expected statement failure: %', message;
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLSTATE = 'P0001' THEN
        RAISE;
      END IF;
      IF NOT (SQLSTATE = ANY(accepted_codes)) THEN
        RAISE EXCEPTION 'unexpected SQLSTATE % for %: %', SQLSTATE, message, SQLERRM;
      END IF;
  END;
END
$function$;

GRANT USAGE ON SCHEMA memory_os_session_test TO
  memory_auth_runtime, memory_api_runtime;
GRANT EXECUTE ON FUNCTION memory_os_session_test.expect_sqlstate(text, text[], text) TO
  memory_auth_runtime, memory_api_runtime;

TRUNCATE TABLE memory_os.account_session;

-- The auth role issues and resolves sessions exclusively through the
-- definer functions.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os.issue_account_session(
  'ses_active000000001', repeat('a', 64), 'acct-session-owner-a', 3,
  'ios_user_access_token', now(), now() + interval '1 hour'
);
DO $$
DECLARE
  resolved record;
BEGIN
  SELECT * INTO STRICT resolved FROM memory_os.resolve_account_session(repeat('a', 64));
  IF resolved.owner_account_id <> 'acct-session-owner-a'
     OR resolved.account_epoch <> 3
     OR resolved.authority <> 'ios_user_access_token' THEN
    RAISE EXCEPTION 'resolved session carries wrong identity: %', resolved;
  END IF;
END
$$;
COMMIT;

-- Direct table access is denied even to the auth role.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os_session_test.expect_sqlstate(
  $$SELECT count(*) FROM memory_os.account_session$$,
  ARRAY['42501'],
  'auth role direct table select'
);
ROLLBACK;

-- Other runtime roles cannot execute the session functions at all.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT memory_os_session_test.expect_sqlstate(
  $$SELECT * FROM memory_os.resolve_account_session(repeat('a', 64))$$,
  ARRAY['42501'],
  'api role session resolution'
);
ROLLBACK;

-- Unknown, expired and revoked sessions all resolve to nothing.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os.issue_account_session(
  'ses_expired00000001', repeat('b', 64), 'acct-session-owner-a', 3,
  'ios_user_access_token', now() - interval '2 hours', now() - interval '1 hour'
);
SELECT memory_os.issue_account_session(
  'ses_revoked00000001', repeat('c', 64), 'acct-session-owner-a', 3,
  'browser_pairing_token', now(), now() + interval '1 hour'
);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.resolve_account_session(repeat('f', 64))) THEN
    RAISE EXCEPTION 'unknown digest resolved';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.resolve_account_session(repeat('b', 64))) THEN
    RAISE EXCEPTION 'expired session resolved';
  END IF;
  IF NOT memory_os.revoke_account_session(repeat('c', 64)) THEN
    RAISE EXCEPTION 'active session revocation reported nothing';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.resolve_account_session(repeat('c', 64))) THEN
    RAISE EXCEPTION 'revoked session resolved';
  END IF;
  IF memory_os.revoke_account_session(repeat('c', 64)) THEN
    RAISE EXCEPTION 'double revocation reported success';
  END IF;
END
$$;
COMMIT;

-- Structural rejections: duplicate digests, bad authority, oversized TTL.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os_session_test.expect_sqlstate(
  $$SELECT memory_os.issue_account_session(
      'ses_duplicate000001', repeat('a', 64), 'acct-session-owner-a', 3,
      'ios_user_access_token', now(), now() + interval '1 hour')$$,
  ARRAY['23505'],
  'duplicate token digest'
);
SELECT memory_os_session_test.expect_sqlstate(
  $$SELECT memory_os.issue_account_session(
      'ses_badauthority01', repeat('d', 64), 'acct-session-owner-a', 3,
      'worker_lease', now(), now() + interval '1 hour')$$,
  ARRAY['23514'],
  'non-interactive authority session'
);
SELECT memory_os_session_test.expect_sqlstate(
  $$SELECT memory_os.issue_account_session(
      'ses_longttl0000001', repeat('e', 64), 'acct-session-owner-a', 3,
      'ios_user_access_token', now(), now() + interval '31 days')$$,
  ARRAY['23514'],
  'session TTL limit'
);
ROLLBACK;

SELECT 'Memory OS account session integration tests PASS' AS result;
