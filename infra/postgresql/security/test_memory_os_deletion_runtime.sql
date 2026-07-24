\set ON_ERROR_STOP on

-- The claim/lease contract the background deletion worker depends on.

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

INSERT INTO memory_os.account_control (account_id, account_epoch, state)
VALUES ('acct-runtime-active-01', 2, 'active');

INSERT INTO memory_os.account_control
  (account_id, account_epoch, state, deletion_started_at)
VALUES
  ('acct-runtime-pending-1', 5, 'deleting', now() - interval '2 minutes'),
  ('acct-runtime-pending-2', 9, 'deleting', now() - interval '1 minute');

INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
VALUES ('job-runtime-1', 'acct-runtime-pending-1', 4);

-- Only the deletion runtime may claim work at all.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT * FROM memory_os.claim_deletion_work(60)$$,
  'api role claiming deletion work'
);
ROLLBACK;

-- The claim takes the oldest pending account, never an active one, and leaves
-- the second account for the next worker.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
DO $claim$
DECLARE
  first_claim record;
  second_claim record;
  third_claim record;
BEGIN
  SELECT * INTO first_claim FROM memory_os.claim_deletion_work(60);
  IF first_claim.account_id <> 'acct-runtime-pending-1'
     OR first_claim.account_epoch <> 5
     OR first_claim.attempts <> 1 THEN
    RAISE EXCEPTION 'first claim was % at epoch % (attempt %)',
      first_claim.account_id, first_claim.account_epoch, first_claim.attempts;
  END IF;

  -- A leased account must not be handed out again.
  SELECT * INTO second_claim FROM memory_os.claim_deletion_work(60);
  IF second_claim.account_id <> 'acct-runtime-pending-2' THEN
    RAISE EXCEPTION 'second claim was %, expected the other pending account',
      second_claim.account_id;
  END IF;

  -- Nothing else is claimable: the active account is not deletion work.
  SELECT * INTO third_claim FROM memory_os.claim_deletion_work(60);
  IF third_claim.account_id IS NOT NULL THEN
    RAISE EXCEPTION 'claimed % which is not pending deletion', third_claim.account_id;
  END IF;
END
$claim$;
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT count(*) = 2 FROM memory_os.account_control
   WHERE state = 'deleting' AND deletion_lease_until IS NOT NULL),
  'both pending accounts must hold a lease'
);
SELECT memory_os_test.assert_true(
  (SELECT deletion_lease_until IS NULL AND deletion_attempts = 0
   FROM memory_os.account_control WHERE account_id = 'acct-runtime-active-01'),
  'an active account must never be leased'
);

-- A released lease makes the account claimable again, and the attempt count
-- keeps rising so a poisoned account is visible to operators.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-runtime-pending-1', true);
SELECT set_config('app.current_account_epoch', '5', true);
SELECT memory_os.release_deletion_lease();
DO $reclaim$
DECLARE
  reclaimed record;
BEGIN
  SELECT * INTO reclaimed FROM memory_os.claim_deletion_work(60);
  IF reclaimed.account_id <> 'acct-runtime-pending-1' OR reclaimed.attempts <> 2 THEN
    RAISE EXCEPTION 'reclaim was % on attempt %', reclaimed.account_id, reclaimed.attempts;
  END IF;
END
$reclaim$;
COMMIT;

-- Releasing a lease must not be able to finish a deletion.
SELECT memory_os_test.assert_true(
  (SELECT state = 'deleting' FROM memory_os.account_control
   WHERE account_id = 'acct-runtime-pending-1'),
  'release must never mark an account deleted'
);

-- Completion clears the lease so the tombstone satisfies the state constraint.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-runtime-pending-1', true);
SELECT set_config('app.current_account_epoch', '5', true);
SELECT memory_os.complete_account_deletion();
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT state = 'deleted' AND deletion_lease_until IS NULL AND deletion_attempts = 2
   FROM memory_os.account_control WHERE account_id = 'acct-runtime-pending-1'),
  'completed deletion must clear the lease and keep the attempt count'
);

-- A completed account is no longer claimable work.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
DO $after_completion$
DECLARE
  claimed record;
BEGIN
  SELECT * INTO claimed FROM memory_os.claim_deletion_work(60);
  IF claimed.account_id = 'acct-runtime-pending-1' THEN
    RAISE EXCEPTION 'a completed account was claimed again';
  END IF;
END
$after_completion$;
ROLLBACK;

SELECT 'Memory OS deletion runtime claim tests PASS' AS result;
