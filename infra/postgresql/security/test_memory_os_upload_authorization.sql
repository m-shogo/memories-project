\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS memory_os_upload_test;

CREATE OR REPLACE FUNCTION memory_os_upload_test.expect_sqlstate(
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

GRANT USAGE ON SCHEMA memory_os_upload_test TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os_upload_test.expect_sqlstate(text, text[], text) TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;

TRUNCATE TABLE
  memory_os.preview_candidate,
  memory_os.preview_rejection,
  memory_os.preview_ready,
  memory_os.upload_authorization,
  memory_os.import_job;

INSERT INTO memory_os.import_job (
  id,
  owner_account_id,
  account_epoch,
  state,
  source_surface
)
VALUES
  ('job-upload-a', 'acct-a', 7, 'awaiting_upload', 'ios_files'),
  ('job-upload-b', 'acct-b', 7, 'awaiting_upload', 'desktop_portal');

-- Same-owner, same-epoch authorization succeeds.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
INSERT INTO memory_os.upload_authorization (
  id,
  owner_account_id,
  account_epoch,
  state,
  job_id,
  object_key,
  content_length,
  checksum_sha256,
  declared_content_type,
  source_surface,
  expires_at
)
VALUES (
  'upa-valid-a',
  'acct-a',
  7,
  'issuing',
  'job-upload-a',
  'quarantine/job-upload-a/obj-valid-a',
  1024,
  repeat('a', 64),
  'application/zip',
  'ios_files',
  now() + interval '10 minutes'
);
UPDATE memory_os.upload_authorization
SET state = 'issued'
WHERE id = 'upa-valid-a' AND state = 'issuing';
COMMIT;

-- Cross-tenant job reference is rejected by the composite FK.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_upload_test.expect_sqlstate(
  $$INSERT INTO memory_os.upload_authorization (
      id, owner_account_id, account_epoch, state, job_id, object_key,
      content_length, checksum_sha256, declared_content_type, source_surface, expires_at
    ) VALUES (
      'upa-cross-job', 'acct-a', 7, 'issuing', 'job-upload-b',
      'quarantine/job-upload-b/obj-cross', 1024, repeat('b', 64),
      'application/zip', 'ios_files', now() + interval '10 minutes'
    )$$,
  ARRAY['23503'],
  'cross-tenant import job foreign key'
);
ROLLBACK;

-- Oversized payload is rejected by the database even if API validation regresses.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_upload_test.expect_sqlstate(
  $$INSERT INTO memory_os.upload_authorization (
      id, owner_account_id, account_epoch, state, job_id, object_key,
      content_length, checksum_sha256, declared_content_type, source_surface, expires_at
    ) VALUES (
      'upa-too-large', 'acct-a', 7, 'issuing', 'job-upload-a',
      'quarantine/job-upload-a/obj-large', 268435457, repeat('c', 64),
      'application/zip', 'ios_files', now() + interval '10 minutes'
    )$$,
  ARRAY['23514'],
  'content length limit'
);
ROLLBACK;

-- Invalid checksum is rejected.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_upload_test.expect_sqlstate(
  $$INSERT INTO memory_os.upload_authorization (
      id, owner_account_id, account_epoch, state, job_id, object_key,
      content_length, checksum_sha256, declared_content_type, source_surface, expires_at
    ) VALUES (
      'upa-bad-checksum', 'acct-a', 7, 'issuing', 'job-upload-a',
      'quarantine/job-upload-a/obj-checksum', 1024, 'NOT-A-SHA256',
      'application/zip', 'ios_files', now() + interval '10 minutes'
    )$$,
  ARRAY['23514'],
  'checksum format'
);
ROLLBACK;

-- Object keys cannot be reused across authorizations.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_upload_test.expect_sqlstate(
  $$INSERT INTO memory_os.upload_authorization (
      id, owner_account_id, account_epoch, state, job_id, object_key,
      content_length, checksum_sha256, declared_content_type, source_surface, expires_at
    ) VALUES (
      'upa-duplicate-key', 'acct-a', 7, 'issuing', 'job-upload-a',
      'quarantine/job-upload-a/obj-valid-a', 1024, repeat('d', 64),
      'application/zip', 'ios_files', now() + interval '10 minutes'
    )$$,
  ARRAY['23505'],
  'duplicate quarantine object key'
);
ROLLBACK;

-- Worker cannot issue upload authorizations.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_upload_test.expect_sqlstate(
  $$INSERT INTO memory_os.upload_authorization (
      id, owner_account_id, account_epoch, state, job_id, object_key,
      content_length, checksum_sha256, declared_content_type, source_surface, expires_at
    ) VALUES (
      'upa-worker', 'acct-a', 7, 'issuing', 'job-upload-a',
      'quarantine/job-upload-a/obj-worker', 1024, repeat('e', 64),
      'application/zip', 'ios_files', now() + interval '10 minutes'
    )$$,
  ARRAY['42501'],
  'worker upload authorization insert'
);
ROLLBACK;

SELECT 'Memory OS upload authorization integration tests PASS' AS result;
