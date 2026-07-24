\set ON_ERROR_STOP on

-- The observer makes negative assertions here, so it needs the test helper.
GRANT EXECUTE ON FUNCTION memory_os_test.expect_insufficient_privilege(text, text)
  TO memory_readonly_observer;
GRANT USAGE ON SCHEMA memory_os_test TO memory_readonly_observer;

TRUNCATE TABLE
  memory_os.memory_item,
  memory_os.apply_confirmation,
  memory_os.preview_candidate,
  memory_os.preview_rejection,
  memory_os.preview_ready,
  memory_os.quarantine_object,
  memory_os.upload_authorization,
  memory_os.import_job,
  memory_os.account_session,
  memory_os.account_control;

INSERT INTO memory_os.account_control
  (account_id, account_epoch, state, deletion_started_at, deletion_completed_at, deletion_attempts)
VALUES
  ('acct-visible-active-01', 1, 'active', NULL, NULL, 0),
  ('acct-visible-fresh-001', 2, 'deleting', now() - interval '30 seconds', NULL, 1),
  ('acct-visible-stuck-001', 3, 'deleting', now() - interval '6 hours', NULL, 9),
  ('acct-visible-stuck-002', 4, 'deleting', now() - interval '2 hours', NULL, 4),
  ('acct-visible-done-0001', 5, 'deleted', now() - interval '1 day', now(), 2);

-- The observer sees numbers and nothing that identifies anyone.
BEGIN;
SET LOCAL ROLE memory_readonly_observer;
DO $backlog$
DECLARE
  backlog record;
BEGIN
  SELECT * INTO backlog FROM memory_os.deletion_backlog(3);
  IF backlog.pending_count <> 3 THEN
    RAISE EXCEPTION 'pending count was %, expected the three deleting accounts', backlog.pending_count;
  END IF;
  IF backlog.stuck_count <> 2 THEN
    RAISE EXCEPTION 'stuck count was %, expected the two at or above 3 attempts', backlog.stuck_count;
  END IF;
  IF backlog.max_attempts <> 9 THEN
    RAISE EXCEPTION 'max attempts was %, expected 9', backlog.max_attempts;
  END IF;
  -- The oldest pending deletion is six hours old; a completed one is a day old
  -- and must not be counted as backlog.
  IF backlog.oldest_pending_seconds < 21000 OR backlog.oldest_pending_seconds > 22200 THEN
    RAISE EXCEPTION 'oldest pending age was % seconds, expected about 6 hours',
      backlog.oldest_pending_seconds;
  END IF;
END
$backlog$;

-- Alerting needs a number, not a list of people: the observer must not be able
-- to turn deletion health into an account enumeration.
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT * FROM memory_os.stuck_deletions(1, 50)$$,
  'observer listing stuck deletions'
);
-- And it still holds no direct access to the table itself.
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT count(*) FROM memory_os.account_control$$,
  'observer reading account_control directly'
);
ROLLBACK;

-- The runtime, which must act, gets the identifiers.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
DO $stuck$
DECLARE
  listed record;
  seen integer := 0;
  first_account text;
BEGIN
  FOR listed IN SELECT * FROM memory_os.stuck_deletions(3, 50)
  LOOP
    seen := seen + 1;
    IF seen = 1 THEN
      first_account := listed.account_id;
    END IF;
    IF listed.attempts < 3 THEN
      RAISE EXCEPTION '% was listed with only % attempts', listed.account_id, listed.attempts;
    END IF;
  END LOOP;
  IF seen <> 2 THEN
    RAISE EXCEPTION 'listed % stuck accounts, expected 2', seen;
  END IF;
  -- Worst first, so an operator reads the most damaged account at the top.
  IF first_account <> 'acct-visible-stuck-001' THEN
    RAISE EXCEPTION 'worst account was %, expected the one with 9 attempts', first_account;
  END IF;
END
$stuck$;
ROLLBACK;

-- The API runtime is not an operator surface.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT * FROM memory_os.deletion_backlog(3)$$,
  'api role reading deletion backlog'
);
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT * FROM memory_os.stuck_deletions(3, 50)$$,
  'api role listing stuck deletions'
);
ROLLBACK;

-- The threshold floors at one attempt, so a zero cannot widen the listing to
-- accounts that have not been attempted at all.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
DO $floor$
DECLARE
  seen integer;
BEGIN
  SELECT count(*) INTO seen FROM memory_os.stuck_deletions(0, 500);
  IF seen <> 3 THEN
    RAISE EXCEPTION 'a zero threshold listed % accounts, expected the three with at least one attempt', seen;
  END IF;
END
$floor$;
ROLLBACK;

SELECT 'Memory OS deletion visibility tests PASS' AS result;
