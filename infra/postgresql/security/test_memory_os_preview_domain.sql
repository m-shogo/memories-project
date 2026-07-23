\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS memory_os_preview_test;

CREATE OR REPLACE FUNCTION memory_os_preview_test.expect_sqlstate(
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

CREATE OR REPLACE FUNCTION memory_os_preview_test.insert_ready(
  p_id text,
  p_job_id text DEFAULT 'job-preview-a',
  p_owner text DEFAULT 'acct-a',
  p_epoch bigint DEFAULT 7,
  p_spool_id text DEFAULT NULL,
  p_commit_key text DEFAULT NULL,
  p_object_key text DEFAULT NULL,
  p_state text DEFAULT 'ready',
  p_accepted_count integer DEFAULT 2,
  p_rejected_count integer DEFAULT 1,
  p_accepted_bytes bigint DEFAULT 66,
  p_rejected_bytes bigint DEFAULT 33,
  p_source_rows integer DEFAULT NULL,
  p_spool_bytes bigint DEFAULT NULL,
  p_rejected_sha text DEFAULT NULL,
  p_accepted_format text DEFAULT 'memory-os-preview-candidate-v1-length-prefixed',
  p_rejected_format text DEFAULT 'memory-os-preview-rejection-v1-length-prefixed',
  p_ttl interval DEFAULT interval '1 hour'
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
AS $function$
BEGIN
  INSERT INTO memory_os.preview_ready (
    id, owner_account_id, account_epoch, job_id, spool_id, commit_key, state,
    source_object_key, source_object_version_id, source_content_length,
    source_checksum_sha256, adapter_id, adapter_version, adapter_artifact_sha256,
    options_sha256, source_row_count, spool_byte_length,
    accepted_record_format, accepted_count, accepted_byte_length, accepted_sha256,
    rejected_record_format, rejected_count, rejected_byte_length, rejected_sha256,
    preview_hash_sha256, sealed_created_at, sealed_expires_at
  )
  VALUES (
    p_id,
    p_owner,
    p_epoch,
    p_job_id,
    COALESCE(p_spool_id, 'spl_' || substr(md5(p_id), 1, 16)),
    COALESCE(p_commit_key, md5(p_id) || md5(p_id || ':commit')),
    p_state,
    COALESCE(p_object_key, 'quarantine/' || p_job_id || '/upl-' || substr(md5(p_id), 1, 12)),
    'version-' || substr(md5(p_id), 1, 12),
    4096,
    md5(p_id || ':source') || md5(p_id || ':source2'),
    'generic-csv',
    '1.0.0',
    md5(p_id || ':artifact') || md5(p_id || ':artifact2'),
    md5(p_id || ':options') || md5(p_id || ':options2'),
    COALESCE(p_source_rows, p_accepted_count + p_rejected_count),
    COALESCE(p_spool_bytes, p_accepted_bytes + p_rejected_bytes),
    p_accepted_format,
    p_accepted_count,
    p_accepted_bytes,
    md5(p_id || ':accepted') || md5(p_id || ':accepted2'),
    p_rejected_format,
    p_rejected_count,
    p_rejected_bytes,
    COALESCE(p_rejected_sha, md5(p_id || ':rejected') || md5(p_id || ':rejected2')),
    md5(p_id || ':preview') || md5(p_id || ':preview2'),
    now(),
    now() + p_ttl
  );
END
$function$;

GRANT USAGE ON SCHEMA memory_os_preview_test TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os_preview_test.expect_sqlstate(text, text[], text) TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os_preview_test.insert_ready(
  text, text, text, bigint, text, text, text, text, integer, integer,
  bigint, bigint, integer, bigint, text, text, text, interval
) TO
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
  memory_os.upload_authorization,
  memory_os.import_job;

INSERT INTO memory_os.import_job (id, owner_account_id, account_epoch, state, source_surface)
VALUES
  ('job-preview-a',  'acct-a', 7, 'preview_building', 'ios_files'),
  ('job-preview-a2', 'acct-a', 7, 'preview_building', 'ios_files'),
  ('job-preview-a3', 'acct-a', 7, 'preview_building', 'ios_files'),
  ('job-preview-b',  'acct-b', 7, 'preview_building', 'desktop_portal');

-- Worker commits one complete ready Preview atomically.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.insert_ready(
  'prv_valid0000001',
  p_commit_key := repeat('a', 64)
);
INSERT INTO memory_os.preview_candidate
  (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
VALUES
  ('prv_valid0000001', 'acct-a', 7, 1, 1, repeat('1', 64), '{"title":"one"}'::jsonb),
  ('prv_valid0000001', 'acct-a', 7, 2, 3, repeat('2', 64), '{"title":"two"}'::jsonb);
INSERT INTO memory_os.preview_rejection
  (preview_id, owner_account_id, account_epoch, ordinal, source_row, issue_codes)
VALUES
  ('prv_valid0000001', 'acct-a', 7, 1, 2, ARRAY['IMPORT_ROW_EMPTY']);
SELECT memory_os.assert_preview_complete('prv_valid0000001');
COMMIT;

-- API authority cannot create ready Previews.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_apiwrite0001', p_job_id := 'job-preview-a2')$$,
  ARRAY['42501'],
  'api role ready preview insert'
);
ROLLBACK;

-- Cross-tenant job binding is rejected by the composite FK.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_crossjob0001', p_job_id := 'job-preview-b')$$,
  ARRAY['23503'],
  'cross-tenant job binding'
);
ROLLBACK;

-- A commit key can be claimed exactly once.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_commitdup001', p_job_id := 'job-preview-a2', p_commit_key := repeat('a', 64))$$,
  ARRAY['23505'],
  'duplicate deterministic commit key'
);
ROLLBACK;

-- One job holds at most one ready Preview.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_jobdup000001', p_job_id := 'job-preview-a')$$,
  ARRAY['23505'],
  'second ready preview for one job'
);
ROLLBACK;

-- Only the immutable ready state exists; partial states cannot be stored.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_building0001', p_job_id := 'job-preview-a2', p_state := 'building')$$,
  ARRAY['23514'],
  'building preview state'
);
ROLLBACK;

-- Aggregate row and byte totals are database-enforced.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_rowtotals001', p_job_id := 'job-preview-a2', p_source_rows := 5)$$,
  ARRAY['23514'],
  'row totals mismatch'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_bytelimit001', p_job_id := 'job-preview-a2', p_accepted_bytes := 536870912, p_rejected_bytes := 1)$$,
  ARRAY['23514'],
  'spool byte limit'
);
ROLLBACK;

-- Empty rejected streams must use the exact empty representation.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_emptybad0001', p_job_id := 'job-preview-a2', p_rejected_count := 0, p_rejected_bytes := 0, p_rejected_sha := repeat('d', 64))$$,
  ARRAY['23514'],
  'empty rejection stream hash'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_emptybad0002', p_job_id := 'job-preview-a2', p_rejected_count := 0, p_rejected_bytes := 12)$$,
  ARRAY['23514'],
  'empty rejection stream bytes'
);
ROLLBACK;

-- Source object keys must bind the exact job.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_foreignkey01', p_job_id := 'job-preview-a2', p_object_key := 'quarantine/job-preview-a/upl-foreign')$$,
  ARRAY['23514'],
  'object key job binding'
);
ROLLBACK;

-- TTL and record format literals are database-enforced.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_longttl00001', p_job_id := 'job-preview-a2', p_ttl := interval '25 hours')$$,
  ARRAY['23514'],
  'sealed TTL limit'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os_preview_test.insert_ready('prv_badformat001', p_job_id := 'job-preview-a2', p_accepted_format := 'memory-os-preview-candidate-v2')$$,
  ARRAY['23514'],
  'accepted record format literal'
);
ROLLBACK;

-- No runtime role may mutate a committed Preview.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$UPDATE memory_os.preview_ready SET preview_hash_sha256 = repeat('f', 64) WHERE id = 'prv_valid0000001'$$,
  ARRAY['42501'],
  'worker ready preview update'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$UPDATE memory_os.preview_candidate SET record_sha256 = repeat('f', 64) WHERE preview_id = 'prv_valid0000001'$$,
  ARRAY['42501'],
  'worker candidate update'
);
ROLLBACK;

-- Candidate integrity: ordinals, source rows and tenant binding.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$INSERT INTO memory_os.preview_candidate
      (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
    VALUES ('prv_valid0000001', 'acct-a', 7, 1, 9, repeat('3', 64), '{"title":"dup"}'::jsonb)$$,
  ARRAY['23505'],
  'duplicate candidate ordinal'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$INSERT INTO memory_os.preview_candidate
      (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
    VALUES ('prv_valid0000001', 'acct-a', 7, 3, 1, repeat('3', 64), '{"title":"dup"}'::jsonb)$$,
  ARRAY['23505'],
  'duplicate candidate source row'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$INSERT INTO memory_os.preview_candidate
      (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
    VALUES ('prv_valid0000001', 'acct-a', 7, 0, 9, repeat('3', 64), '{"title":"zero"}'::jsonb)$$,
  ARRAY['23514'],
  'zero candidate ordinal'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$INSERT INTO memory_os.preview_candidate
      (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
    VALUES ('prv_valid0000001', 'acct-a', 8, 3, 9, repeat('3', 64), '{"title":"epoch"}'::jsonb)$$,
  ARRAY['42501', '23503'],
  'stale-epoch candidate insert'
);
ROLLBACK;

-- Rejections cannot carry free-form content or invalid codes.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$INSERT INTO memory_os.preview_rejection
      (preview_id, owner_account_id, account_epoch, ordinal, source_row, issue_codes)
    VALUES ('prv_valid0000001', 'acct-a', 7, 2, 9, ARRAY['user@example.com'])$$,
  ARRAY['23514'],
  'free-form rejection code'
);
SELECT memory_os_preview_test.expect_sqlstate(
  $$INSERT INTO memory_os.preview_rejection
      (preview_id, owner_account_id, account_epoch, ordinal, source_row, issue_codes)
    VALUES ('prv_valid0000001', 'acct-a', 7, 2, 9, ARRAY[]::text[])$$,
  ARRAY['23514'],
  'empty rejection code list'
);
ROLLBACK;

-- Completeness assertion rejects missing rows and ordinal gaps.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.insert_ready(
  'prv_incomplete01',
  p_job_id := 'job-preview-a3',
  p_rejected_count := 0,
  p_rejected_bytes := 0,
  p_rejected_sha := 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
);
INSERT INTO memory_os.preview_candidate
  (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
VALUES
  ('prv_incomplete01', 'acct-a', 7, 1, 1, repeat('4', 64), '{"title":"only"}'::jsonb);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os.assert_preview_complete('prv_incomplete01')$$,
  ARRAY['P0002'],
  'missing candidate rows'
);
INSERT INTO memory_os.preview_candidate
  (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
VALUES
  ('prv_incomplete01', 'acct-a', 7, 3, 3, repeat('5', 64), '{"title":"gap"}'::jsonb);
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os.assert_preview_complete('prv_incomplete01')$$,
  ARRAY['P0002'],
  'candidate ordinal gap'
);
ROLLBACK;

-- Empty rejected streams commit with the exact empty representation.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.insert_ready(
  'prv_emptyok00001',
  p_job_id := 'job-preview-a2',
  p_accepted_count := 1,
  p_accepted_bytes := 33,
  p_rejected_count := 0,
  p_rejected_bytes := 0,
  p_rejected_sha := 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
);
INSERT INTO memory_os.preview_candidate
  (preview_id, owner_account_id, account_epoch, ordinal, source_row, record_sha256, canonical_record)
VALUES
  ('prv_emptyok00001', 'acct-a', 7, 1, 1, repeat('6', 64), '{"title":"solo"}'::jsonb);
SELECT memory_os.assert_preview_complete('prv_emptyok00001');
COMMIT;

-- Cross-tenant readers see nothing and cannot probe completeness.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-b', true);
SELECT set_config('app.current_account_epoch', '7', true);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.preview_ready) THEN
    RAISE EXCEPTION 'cross-tenant ready preview visible';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.preview_candidate) THEN
    RAISE EXCEPTION 'cross-tenant candidate visible';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.preview_rejection) THEN
    RAISE EXCEPTION 'cross-tenant rejection visible';
  END IF;
END
$$;
SELECT memory_os_preview_test.expect_sqlstate(
  $$SELECT memory_os.assert_preview_complete('prv_valid0000001')$$,
  ARRAY['P0002'],
  'foreign preview completeness probe'
);
ROLLBACK;

-- Stale-epoch context cannot read its old previews.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '8', true);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.preview_ready) THEN
    RAISE EXCEPTION 'stale-epoch ready preview visible';
  END IF;
END
$$;
ROLLBACK;

-- A job cannot be deleted while its ready Preview exists.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
SELECT memory_os_preview_test.expect_sqlstate(
  $$DELETE FROM memory_os.import_job WHERE id = 'job-preview-a'$$,
  ARRAY['23503'],
  'job deletion under existing preview'
);
ROLLBACK;

-- Deletion runtime removes the whole Preview atomically (children cascade).
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct-a', true);
SELECT set_config('app.current_account_epoch', '7', true);
DELETE FROM memory_os.preview_ready WHERE id = 'prv_valid0000001';
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.preview_candidate WHERE preview_id = 'prv_valid0000001') THEN
    RAISE EXCEPTION 'candidates survived preview deletion';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.preview_rejection WHERE preview_id = 'prv_valid0000001') THEN
    RAISE EXCEPTION 'rejections survived preview deletion';
  END IF;
END
$$;
COMMIT;

SELECT 'Memory OS preview domain integration tests PASS' AS result;
