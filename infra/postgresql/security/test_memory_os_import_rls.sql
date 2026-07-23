\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS memory_os_test;

CREATE OR REPLACE FUNCTION memory_os_test.assert_true(
  condition boolean,
  message text
)
RETURNS void
LANGUAGE plpgsql
AS $function$
BEGIN
  IF condition IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'assertion failed: %', message;
  END IF;
END
$function$;

CREATE OR REPLACE FUNCTION memory_os_test.expect_insufficient_privilege(
  statement text,
  message text
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
AS $function$
BEGIN
  BEGIN
    EXECUTE statement;
    RAISE EXCEPTION 'expected denial but statement succeeded: %', message;
  EXCEPTION
    WHEN insufficient_privilege THEN
      NULL;
  END;
END
$function$;

GRANT USAGE ON SCHEMA memory_os_test TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os_test.assert_true(boolean, text) TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os_test.expect_insufficient_privilege(text, text) TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;

-- Deletion fencing requires an active account_control row at the exact epoch
-- for every tenant these blocks act as. Provisioned as the migration superuser
-- because the API insert policy itself depends on this row existing.
INSERT INTO memory_os.account_control (account_id, account_epoch, state)
VALUES
  ('acct-a', 7, 'active'),
  ('acct-b', 7, 'active')
ON CONFLICT (account_id) DO UPDATE
SET account_epoch = EXCLUDED.account_epoch,
    state = 'active',
    deletion_started_at = NULL,
    deletion_completed_at = NULL;

TRUNCATE TABLE
  memory_os.preview_candidate,
  memory_os.preview_rejection,
  memory_os.preview_ready,
  memory_os.import_job,
  memory_os.pairing_session,
  memory_os.upload_authorization,
  memory_os.quarantine_object,
  memory_os.import_preview,
  memory_os.apply_confirmation,
  memory_os.import_report,
  memory_os.export_job,
  memory_os.deletion_fence;

INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
VALUES
  ('job-a', 'acct-a', 7),
  ('job-b', 'acct-b', 7);
INSERT INTO memory_os.quarantine_object (id, owner_account_id, account_epoch)
VALUES ('object-a', 'acct-a', 7);
INSERT INTO memory_os.import_preview (id, owner_account_id, account_epoch)
VALUES ('preview-a', 'acct-a', 7);
INSERT INTO memory_os.apply_confirmation (id, owner_account_id, account_epoch)
VALUES ('apply-a', 'acct-a', 7);
INSERT INTO memory_os.deletion_fence (id, owner_account_id, deletion_epoch)
VALUES ('deletion-a', 'acct-a', 8);

DO $checks$
DECLARE
  role_row record;
  table_name text;
  rls_enabled boolean;
  force_rls boolean;
BEGIN
  FOR role_row IN
    SELECT rolname, rolcanlogin, rolinherit, rolbypassrls
    FROM pg_roles
    WHERE rolname IN (
      'memory_api_runtime',
      'memory_worker_runtime',
      'memory_migration_owner',
      'memory_deletion_runtime',
      'memory_readonly_observer'
    )
  LOOP
    IF role_row.rolcanlogin OR role_row.rolinherit OR role_row.rolbypassrls THEN
      RAISE EXCEPTION 'unsafe role attributes: %', role_row.rolname;
    END IF;
  END LOOP;

  FOREACH table_name IN ARRAY ARRAY[
    'import_job', 'pairing_session', 'upload_authorization',
    'quarantine_object', 'import_preview', 'apply_confirmation',
    'import_report', 'export_job', 'deletion_fence'
  ]
  LOOP
    SELECT c.relrowsecurity, c.relforcerowsecurity
      INTO rls_enabled, force_rls
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'memory_os' AND c.relname = table_name;
    IF rls_enabled IS DISTINCT FROM true OR force_rls IS DISTINCT FROM true THEN
      RAISE EXCEPTION 'RLS/FORCE RLS missing: %', table_name;
    END IF;
  END LOOP;
END
$checks$;

-- Same owner and epoch can read its row.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.import_job WHERE id = 'job-a'),
  'same-owner row must be visible'
);
ROLLBACK;

-- Cross-user row is hidden, not returned with a different body.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-b', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_job WHERE id = 'job-a'),
  'cross-user row must be hidden'
);
ROLLBACK;

-- A stale epoch cannot see a current Preview.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '6', true);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.import_preview WHERE id = 'preview-a'),
  'stale epoch must be hidden'
);
ROLLBACK;

-- Missing session context fails closed.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.quarantine_object),
  'missing session context must return zero rows'
);
ROLLBACK;

-- Same-owner insert is allowed.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
VALUES ('job-a-2', 'acct-a', 7);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.import_job WHERE id = 'job-a-2'),
  'same-owner insert must succeed'
);
ROLLBACK;

-- Foreign-owner insert is rejected by WITH CHECK.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch)
    VALUES ('job-foreign', 'acct-b', 7)$$,
  'foreign-owner insert'
);
ROLLBACK;

-- Owner mutation is rejected even when UPDATE is otherwise allowed.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$UPDATE memory_os.import_job
    SET owner_account_id = 'acct-b'
    WHERE id = 'job-a'$$,
  'owner mutation'
);
ROLLBACK;

-- Epoch downgrade is rejected by WITH CHECK.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$UPDATE memory_os.import_job
    SET account_epoch = 6
    WHERE id = 'job-a'$$,
  'epoch downgrade'
);
ROLLBACK;

-- Worker may read a scoped quarantine object.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.quarantine_object WHERE id = 'object-a'),
  'worker scoped read must succeed'
);
ROLLBACK;

-- API and worker cannot delete quarantine objects.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$DELETE FROM memory_os.quarantine_object WHERE id = 'object-a'$$,
  'API quarantine delete'
);
ROLLBACK;

BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$DELETE FROM memory_os.quarantine_object WHERE id = 'object-a'$$,
  'worker quarantine delete'
);
ROLLBACK;

-- Materialized Preview and Apply confirmation are immutable to API/worker UPDATE.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$UPDATE memory_os.import_preview SET state = 'changed' WHERE id = 'preview-a'$$,
  'Preview update'
);
ROLLBACK;

BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$INSERT INTO memory_os.apply_confirmation (id, owner_account_id, account_epoch)
    VALUES ('apply-worker', 'acct-a', 7)$$,
  'worker Apply confirmation insert'
);
ROLLBACK;

-- Only the deletion runtime can delete a same-owner, same-epoch fence.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
DELETE FROM memory_os.deletion_fence WHERE id = 'deletion-a';
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.deletion_fence WHERE id = 'deletion-a'),
  'deletion runtime delete must succeed'
);
ROLLBACK;

SELECT 'Memory OS PostgreSQL RLS integration tests PASS' AS result;
