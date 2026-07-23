\set ON_ERROR_STOP on

-- Deletion fencing across the tables added after migration 002: bumping the
-- account epoch must fence Previews and memory items exactly as it fences the
-- original tables, and the deletion runtime sweep must erase everything.

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
VALUES ('acct-fence-owner-a', 3, 'active');

INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
VALUES ('job-fence-a', 'acct-fence-owner-a', 3, 'preview_building', 'ios_files');

INSERT INTO memory_os.preview_ready (
  id, owner_account_id, account_epoch, job_id, spool_id, commit_key,
  source_object_key, source_object_version_id, source_content_length,
  source_checksum_sha256, adapter_id, adapter_version, adapter_artifact_sha256,
  options_sha256, source_row_count, spool_byte_length,
  accepted_record_format, accepted_count, accepted_byte_length, accepted_sha256,
  rejected_record_format, rejected_count, rejected_byte_length, rejected_sha256,
  preview_hash_sha256, sealed_created_at, sealed_expires_at
) VALUES (
  'prv_fenceowner00001', 'acct-fence-owner-a', 3, 'job-fence-a',
  'spl_fenceowner00001', repeat('a', 64),
  'quarantine/job-fence-a/upl-fence-1', 'version-fence-1', 4096,
  repeat('b', 64), 'generic-csv', '1.0.0', repeat('c', 64), repeat('d', 64),
  1, 33,
  'memory-os-preview-candidate-v1-length-prefixed', 1, 33, repeat('e', 64),
  'memory-os-preview-rejection-v1-length-prefixed', 0, 0,
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  repeat('f', 64), now(), now() + interval '1 hour'
);

INSERT INTO memory_os.preview_candidate
  (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
VALUES ('prv_fenceowner00001', 'acct-fence-owner-a', 3, 1, 1, repeat('1', 64),
        '{"fingerprint":"fp-fence-1","title":"kept"}'::jsonb);

INSERT INTO memory_os.memory_item
  (id, owner_account_id, account_epoch, fingerprint, source_preview_id, canonical_record)
VALUES ('mem_' || repeat('a', 32), 'acct-fence-owner-a', 3, 'fp-fence-1',
        'prv_fenceowner00001', '{"title":"kept"}'::jsonb);

-- Sessions live behind SECURITY DEFINER functions, so they are seeded here
-- directly and must be erased by the sweep like every other owned row.
INSERT INTO memory_os.account_session
  (id, token_digest, owner_account_id, account_epoch, authority, state, created_at, expires_at)
VALUES ('ses_fenceowner000001', repeat('9', 64), 'acct-fence-owner-a', 3,
        'ios_user_access_token', 'active', now(), now() + interval '1 hour');

-- A live account's sessions cannot be purged, even by the deletion runtime.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '3', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT memory_os.purge_account_sessions()$$,
  'session purge against a live account'
);
ROLLBACK;

-- Before the fence: the owner sees its own Preview and memory item.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '3', true);
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM memory_os.preview_ready WHERE id = 'prv_fenceowner00001') THEN
    RAISE EXCEPTION 'active owner cannot see its own preview';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM memory_os.memory_item) THEN
    RAISE EXCEPTION 'active owner cannot see its own memory item';
  END IF;
END
$$;
COMMIT;

-- Bump the epoch exactly as account deletion does.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '3', true);
SELECT memory_os.begin_account_deletion();
COMMIT;

-- After the fence: neither the old nor the new epoch can reach the data.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '3', true);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.preview_ready) THEN
    RAISE EXCEPTION 'stale epoch still sees previews';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.preview_candidate) THEN
    RAISE EXCEPTION 'stale epoch still sees preview candidates';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.memory_item) THEN
    RAISE EXCEPTION 'stale epoch still sees memory items';
  END IF;
END
$$;
ROLLBACK;

BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '4', true);
DO $$
BEGIN
  IF memory_os.account_epoch_is_authorized() THEN
    RAISE EXCEPTION 'API is authorized while the account is deleting';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.preview_ready) THEN
    RAISE EXCEPTION 'deleting account still exposes previews to the API role';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.memory_item) THEN
    RAISE EXCEPTION 'deleting account still exposes memory items to the API role';
  END IF;
END
$$;
ROLLBACK;

-- The deletion runtime, and only it, may sweep the fenced rows.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '4', true);
DO $$
DECLARE
  swept record;
  memory_removed bigint := -1;
  preview_removed bigint := -1;
  job_removed bigint := -1;
  session_removed bigint := -1;
BEGIN
  FOR swept IN SELECT * FROM memory_os.sweep_deleted_account()
  LOOP
    IF swept.table_name = 'memory_item' THEN memory_removed := swept.removed; END IF;
    IF swept.table_name = 'preview_ready' THEN preview_removed := swept.removed; END IF;
    IF swept.table_name = 'import_job' THEN job_removed := swept.removed; END IF;
    IF swept.table_name = 'account_session' THEN session_removed := swept.removed; END IF;
  END LOOP;
  IF memory_removed <> 1 OR preview_removed <> 1 OR job_removed <> 1
     OR session_removed <> 1 THEN
    RAISE EXCEPTION 'sweep removed unexpected counts: memory=% preview=% job=% session=%',
      memory_removed, preview_removed, job_removed, session_removed;
  END IF;
END
$$;
COMMIT;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.memory_item) THEN
    RAISE EXCEPTION 'memory items survived the sweep';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.preview_ready) THEN
    RAISE EXCEPTION 'previews survived the sweep';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.import_job) THEN
    RAISE EXCEPTION 'import jobs survived the sweep';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.account_session) THEN
    RAISE EXCEPTION 'sessions survived the sweep';
  END IF;
END
$$;

-- Non-deletion roles cannot run the sweep at all.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-fence-owner-a', true);
SELECT set_config('app.current_account_epoch', '4', true);
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT * FROM memory_os.sweep_deleted_account()$$,
  'api role sweep'
);
ROLLBACK;

SELECT 'Memory OS deletion fencing integration tests PASS' AS result;
