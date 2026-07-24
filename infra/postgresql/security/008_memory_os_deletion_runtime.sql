-- Memory OS Round 9 background deletion runtime.
-- Apply after 007_memory_os_app_login.sql.
--
-- Deletion used to run inside the HTTP request that asked for it. That made
-- erasure hostage to one connection: a timeout, a deploy or a crash mid-sweep
-- left the account fenced in 'deleting' forever, because nothing else ever
-- looked for it again. The user had been told deletion started, and it had —
-- but nothing would finish it.
--
-- This migration adds the claim the worker needs to find such accounts and
-- resume them, with a lease so two workers cannot sweep the same account at
-- once.

BEGIN;

ALTER TABLE memory_os.account_control
  ADD COLUMN IF NOT EXISTS deletion_lease_until timestamptz,
  -- Attempt count only. A failure reason would be free text derived from
  -- runtime state, and this table must never accumulate anything that could
  -- carry a fragment of the user's own content.
  ADD COLUMN IF NOT EXISTS deletion_attempts integer NOT NULL DEFAULT 0;

DO $lease_check$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'account_control_lease_check'
  ) THEN
    ALTER TABLE memory_os.account_control
      ADD CONSTRAINT account_control_lease_check CHECK (
        deletion_attempts >= 0
        AND (deletion_lease_until IS NULL OR state = 'deleting')
      );
  END IF;
END
$lease_check$;

CREATE INDEX IF NOT EXISTS account_control_deleting_idx
  ON memory_os.account_control (deletion_lease_until NULLS FIRST)
  WHERE state = 'deleting';

-- The claim has to scan for work before it knows which account it will get, so
-- it cannot run under the ordinary account-scoped policy. This narrow policy
-- lets the table owner — which only the SECURITY DEFINER bodies below ever
-- run as, since no login role is a member of memory_migration_owner — reach
-- rows that are already committed to deletion, and nothing else.
DROP POLICY IF EXISTS account_control_deletion_claim ON memory_os.account_control;
CREATE POLICY account_control_deletion_claim
  ON memory_os.account_control
  AS PERMISSIVE
  FOR ALL
  TO memory_migration_owner
  USING (state = 'deleting')
  WITH CHECK (state IN ('deleting', 'deleted'));

-- claim_deletion_work leases one account that is committed to deletion and not
-- currently held by another worker. SKIP LOCKED means concurrent workers take
-- different accounts instead of blocking on each other.
CREATE OR REPLACE FUNCTION memory_os.claim_deletion_work(p_lease_seconds integer)
RETURNS TABLE (account_id text, account_epoch bigint, attempts integer)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  claimed record;
BEGIN
  -- The role check lives in the EXECUTE grant below, not here: inside a
  -- SECURITY DEFINER body current_user is the function owner, so testing it
  -- would reject the very caller the grant admits.
  IF p_lease_seconds < 1 OR p_lease_seconds > 3600 THEN
    RAISE EXCEPTION 'lease seconds out of range' USING ERRCODE = '22023';
  END IF;

  SELECT candidate.account_id, candidate.account_epoch, candidate.deletion_attempts
  INTO claimed
  FROM memory_os.account_control AS candidate
  WHERE candidate.state = 'deleting'
    AND (candidate.deletion_lease_until IS NULL OR candidate.deletion_lease_until < now())
  ORDER BY candidate.deletion_started_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  UPDATE memory_os.account_control
  SET deletion_lease_until = now() + make_interval(secs => p_lease_seconds),
      deletion_attempts = memory_os.account_control.deletion_attempts + 1,
      updated_at = now()
  WHERE memory_os.account_control.account_id = claimed.account_id;

  account_id := claimed.account_id;
  account_epoch := claimed.account_epoch;
  attempts := claimed.deletion_attempts + 1;
  RETURN NEXT;
END
$function$;

ALTER FUNCTION memory_os.claim_deletion_work(integer) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.claim_deletion_work(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.claim_deletion_work(integer) TO memory_deletion_runtime;

-- release_deletion_lease hands a claim back immediately after a failed attempt
-- so the next worker can retry without waiting out the lease. It deliberately
-- cannot mark anything deleted; only complete_account_deletion() does that,
-- and only after the sweep.
CREATE OR REPLACE FUNCTION memory_os.release_deletion_lease()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  verified_account_id text := memory_os.current_account_id();
BEGIN
  -- As above: only memory_deletion_runtime holds EXECUTE on this function.
  IF verified_account_id IS NULL THEN
    RAISE EXCEPTION 'verified account context is required' USING ERRCODE = '42501';
  END IF;

  UPDATE memory_os.account_control
  SET deletion_lease_until = NULL, updated_at = now()
  WHERE memory_os.account_control.account_id = verified_account_id
    AND memory_os.account_control.state = 'deleting';
END
$function$;

ALTER FUNCTION memory_os.release_deletion_lease() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.release_deletion_lease() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.release_deletion_lease() TO memory_deletion_runtime;

-- Completion must also clear the lease, or a completed account would keep a
-- lease column set in a state the constraint forbids.
CREATE OR REPLACE FUNCTION memory_os.complete_account_deletion()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  verified_account_id text := memory_os.current_account_id();
BEGIN
  IF verified_account_id IS NULL OR memory_os.current_account_epoch() IS NULL THEN
    RAISE EXCEPTION 'verified account and epoch context are required'
      USING ERRCODE = '42501';
  END IF;

  UPDATE memory_os.account_control
  SET state = 'deleted',
      deletion_completed_at = now(),
      deletion_lease_until = NULL,
      updated_at = now()
  WHERE memory_os.account_control.account_id = verified_account_id
    AND memory_os.account_control.account_epoch = memory_os.current_account_epoch()
    AND memory_os.account_control.state = 'deleting';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'account deletion cannot be completed'
      USING ERRCODE = '55000';
  END IF;
END
$function$;

ALTER FUNCTION memory_os.complete_account_deletion() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.complete_account_deletion() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.complete_account_deletion() TO memory_deletion_runtime;

COMMIT;
