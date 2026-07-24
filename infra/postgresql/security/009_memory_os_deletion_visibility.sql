-- Memory OS Round 9 deletion backlog visibility.
-- Apply after 008_memory_os_deletion_runtime.sql.
--
-- Migration 008 made deletion resumable and counted attempts so a poisoned
-- account would be visible to an operator. Nobody was looking. An account
-- whose erasure fails every time would retry forever in silence, and the user
-- who asked to be deleted would never be — with no signal anywhere.
--
-- Two surfaces, deliberately different in what they reveal:
--
--   deletion_backlog()  aggregate counts only, no identifiers. This is what a
--                       dashboard or alert consumes, so watching the health of
--                       deletion can never become a way to enumerate accounts.
--   stuck_deletions()   account identifiers, for the runtime that already has
--                       to know them in order to act.
--
-- Neither returns anything derived from user content. The tables they read
-- hold none, and that is a property to preserve, not an accident.

BEGIN;

-- The observer role held no schema usage at all, which is why it could not so
-- much as name a function here. Usage alone grants nothing: every table in the
-- schema revokes all privileges from this role, and that stays true.
GRANT USAGE ON SCHEMA memory_os TO memory_readonly_observer;

CREATE OR REPLACE FUNCTION memory_os.deletion_backlog(p_stuck_attempts integer DEFAULT 3)
RETURNS TABLE (
  pending_count bigint,
  stuck_count bigint,
  max_attempts integer,
  oldest_pending_seconds bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
  SELECT
    count(*) FILTER (WHERE account.state = 'deleting'),
    count(*) FILTER (WHERE account.state = 'deleting'
                       AND account.deletion_attempts >= greatest(p_stuck_attempts, 1)),
    coalesce(max(account.deletion_attempts) FILTER (WHERE account.state = 'deleting'), 0),
    coalesce(
      max(extract(epoch FROM now() - account.deletion_started_at))
        FILTER (WHERE account.state = 'deleting'),
      0
    )::bigint
  FROM memory_os.account_control AS account
$function$;

ALTER FUNCTION memory_os.deletion_backlog(integer) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.deletion_backlog(integer) FROM PUBLIC;
-- The observer role holds no table privileges anywhere; this aggregate is the
-- one thing it may read, precisely because it cannot identify anyone.
GRANT EXECUTE ON FUNCTION memory_os.deletion_backlog(integer) TO
  memory_deletion_runtime,
  memory_readonly_observer;

CREATE OR REPLACE FUNCTION memory_os.stuck_deletions(
  p_min_attempts integer DEFAULT 3,
  p_limit integer DEFAULT 50
)
RETURNS TABLE (
  account_id text,
  attempts integer,
  deletion_started_at timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
  SELECT account.account_id, account.deletion_attempts, account.deletion_started_at
  FROM memory_os.account_control AS account
  WHERE account.state = 'deleting'
    AND account.deletion_attempts >= greatest(p_min_attempts, 1)
  ORDER BY account.deletion_attempts DESC, account.deletion_started_at
  LIMIT least(greatest(p_limit, 1), 500)
$function$;

ALTER FUNCTION memory_os.stuck_deletions(integer, integer) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.stuck_deletions(integer, integer) FROM PUBLIC;
-- Identifiers go only to the runtime that must act on them. The observer role
-- is deliberately excluded: alerting needs a number, not a list of people.
GRANT EXECUTE ON FUNCTION memory_os.stuck_deletions(integer, integer) TO
  memory_deletion_runtime;

COMMIT;
