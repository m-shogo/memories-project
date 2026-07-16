\set ON_ERROR_STOP on

CREATE OR REPLACE FUNCTION memory_os_test.expect_failure(
  statement text,
  message text
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
AS $function$
DECLARE
  failed boolean := false;
BEGIN
  BEGIN
    EXECUTE statement;
  EXCEPTION
    WHEN OTHERS THEN
      failed := true;
  END;

  IF failed IS NOT true THEN
    RAISE EXCEPTION 'expected failure but statement succeeded: %', message;
  END IF;
END
$function$;

GRANT EXECUTE ON FUNCTION memory_os_test.expect_failure(text, text) TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;

TRUNCATE TABLE memory_os.account_control, memory_os.import_job;

INSERT INTO memory_os.account_control (account_id, account_epoch, state)
VALUES
  ('acct-a', 7, 'active'),
  ('acct-b', 7, 'active');

INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
VALUES
  ('job-a', 'acct-a', 7),
  ('job-b', 'acct-b', 7);

-- Current active account and epoch can access its tenant rows.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.assert_true(
  memory_os.account_epoch_is_authorized(),
  'active current epoch must be authorized'
);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.import_job WHERE id = 'job-a'),
  'active account row must be visible'
);
ROLLBACK;

-- Deletion begins without a client-supplied account ID and atomically increments epoch.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.assert_true(
  memory_os.begin_account_deletion() = 8,
  'deletion must increment canonical epoch'
);
SELECT memory_os_test.assert_true(
  (SELECT account_epoch = 8 AND state = 'deleting'
   FROM memory_os.account_control WHERE account_id = 'acct-a'),
  'account must enter deleting state at the new epoch'
);
SELECT memory_os_test.assert_true(
  NOT memory_os.account_epoch_is_authorized(),
  'old API epoch must become unauthorized immediately'
);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_job WHERE id = 'job-a'),
  'old API transaction must lose tenant-row visibility immediately'
);
SELECT memory_os_test.expect_insufficient_privilege(
  $$INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
    VALUES ('job-after-delete-start', 'acct-a', 7)$$,
  'old API epoch insert after deletion start'
);
SELECT memory_os_test.assert_true(
  (WITH changed AS (
     UPDATE memory_os.import_job SET state = 'changed' WHERE id = 'job-a' RETURNING 1
   ) SELECT count(*) = 0 FROM changed),
  'old API epoch must not update hidden rows'
);
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT account_epoch = 8 AND state = 'deleting'
   FROM memory_os.account_control WHERE account_id = 'acct-a'),
  'deletion epoch must persist'
);
SELECT memory_os_test.assert_true(
  (SELECT state = 'active' FROM memory_os.import_job WHERE id = 'job-a'),
  'stale update must not mutate the row'
);

-- Even a new API/worker context at deletion epoch cannot access ordinary tenant work.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
SELECT memory_os_test.assert_true(
  NOT memory_os.account_epoch_is_authorized(),
  'API is not authorized while account is deleting'
);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_job WHERE id = 'job-a'),
  'API cannot read tenant work while deleting'
);
SELECT memory_os_test.expect_insufficient_privilege(
  $$INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
    VALUES ('job-api-deleting', 'acct-a', 8)$$,
  'API insert while deleting'
);
ROLLBACK;

BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
SELECT memory_os_test.assert_true(
  NOT memory_os.account_epoch_is_authorized(),
  'worker is not authorized while account is deleting'
);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_job WHERE id = 'job-a'),
  'worker cannot read tenant work while deleting'
);
ROLLBACK;

-- Deletion runtime at the new epoch may clean the account's rows.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
SELECT memory_os_test.assert_true(
  memory_os.account_epoch_is_authorized(),
  'deletion runtime must be authorized for deleting account cleanup'
);
DELETE FROM memory_os.import_job WHERE id = 'job-a';
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_job WHERE id = 'job-a'),
  'deletion runtime must delete scoped tenant rows'
);
ROLLBACK;

-- Completion is deletion-runtime-only and keeps the tombstone row.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
SELECT memory_os.complete_account_deletion();
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT account_epoch = 8
      AND state = 'deleted'
      AND deletion_started_at IS NOT NULL
      AND deletion_completed_at IS NOT NULL
   FROM memory_os.account_control WHERE account_id = 'acct-a'),
  'deleted account tombstone must remain at deletion epoch'
);

BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
SELECT memory_os_test.assert_true(
  NOT memory_os.account_epoch_is_authorized(),
  'completed deletion must close deletion-runtime tenant access'
);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_job WHERE id = 'job-a'),
  'deleted account tenant rows must remain hidden'
);
ROLLBACK;

-- Repeating deletion or completing with stale context fails closed.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
SELECT memory_os_test.expect_failure(
  $$SELECT memory_os.begin_account_deletion()$$,
  'repeat deletion start'
);
ROLLBACK;

BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_failure(
  $$SELECT memory_os.complete_account_deletion()$$,
  'stale deletion completion'
);
ROLLBACK;

SELECT 'Memory OS account epoch and deletion RLS tests PASS' AS result;
