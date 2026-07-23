\set ON_ERROR_STOP on

CREATE SCHEMA IF NOT EXISTS memory_os_apply_test;

CREATE OR REPLACE FUNCTION memory_os_apply_test.expect_sqlstate(
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

GRANT USAGE ON SCHEMA memory_os_apply_test TO
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os_apply_test.expect_sqlstate(text, text[], text) TO
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime;

-- Deletion fencing requires an active account_control row at the exact epoch
-- for every tenant these blocks act as. Provisioned as the migration superuser
-- because the API insert policy itself depends on this row existing.
INSERT INTO memory_os.account_control (account_id, account_epoch, state)
VALUES
  ('acct-apply-owner-a', 2, 'active'),
  ('acct-apply-owner-b', 2, 'active'),
  ('acct-apply-intruder', 2, 'active')
ON CONFLICT (account_id) DO UPDATE
SET account_epoch = EXCLUDED.account_epoch,
    state = 'active',
    deletion_started_at = NULL,
    deletion_completed_at = NULL;

TRUNCATE TABLE memory_os.memory_item, memory_os.apply_confirmation;

-- API role claims, completes and re-reads an apply confirmation for its own
-- tenant, and stores memory items.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-apply-owner-a', true);
SELECT set_config('app.current_account_epoch', '2', true);
INSERT INTO memory_os.apply_confirmation (
  id, owner_account_id, account_epoch, state, preview_id, preview_sha256,
  idempotency_key, request_sha256, duplicate_policy, created_at, updated_at
) VALUES (
  'apl-claim-a-000001', 'acct-apply-owner-a', 2, 'in_progress', 'prv-apply-a-000001',
  repeat('a', 64), 'idem-key-a-000001', repeat('b', 64), 'skip_existing', now(), now()
);
UPDATE memory_os.apply_confirmation
SET state = 'applied', created_count = 2, updated_count = 0, skipped_count = 1,
    completed_at = now(), updated_at = now()
WHERE id = 'apl-claim-a-000001' AND state = 'in_progress';
INSERT INTO memory_os.memory_item (
  id, owner_account_id, account_epoch, fingerprint, source_preview_id, canonical_record
) VALUES (
  'mem_' || repeat('a', 32), 'acct-apply-owner-a', 2, 'fingerprint-one',
  'prv_applymemitem0001', '{"title":"one"}'::jsonb
);
DO $$
DECLARE
  confirmed record;
BEGIN
  SELECT state, created_count INTO STRICT confirmed
  FROM memory_os.apply_confirmation WHERE id = 'apl-claim-a-000001';
  IF confirmed.state <> 'applied' OR confirmed.created_count <> 2 THEN
    RAISE EXCEPTION 'apply completion not persisted: %', confirmed;
  END IF;
END
$$;
COMMIT;

-- Idempotency keys are unique per owner.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-apply-owner-a', true);
SELECT set_config('app.current_account_epoch', '2', true);
SELECT memory_os_apply_test.expect_sqlstate(
  $$INSERT INTO memory_os.apply_confirmation (
      id, owner_account_id, account_epoch, state, preview_id, preview_sha256,
      idempotency_key, request_sha256, duplicate_policy, created_at, updated_at
    ) VALUES (
      'apl-claim-a-000002', 'acct-apply-owner-a', 2, 'in_progress', 'prv-apply-a-000002',
      repeat('a', 64), 'idem-key-a-000001', repeat('b', 64), 'keep_both', now(), now()
    )$$,
  ARRAY['23505'],
  'duplicate idempotency key'
);
ROLLBACK;

-- Cross-tenant confirmations and memory items are invisible and immutable.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-apply-owner-b', true);
SELECT set_config('app.current_account_epoch', '2', true);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM memory_os.apply_confirmation WHERE id = 'apl-claim-a-000001') THEN
    RAISE EXCEPTION 'cross-tenant apply confirmation visible';
  END IF;
  IF EXISTS (SELECT 1 FROM memory_os.memory_item) THEN
    RAISE EXCEPTION 'cross-tenant memory item visible';
  END IF;
END
$$;
UPDATE memory_os.apply_confirmation SET state = 'applied' WHERE id = 'apl-claim-a-000001';
DO $$
BEGIN
  IF FOUND THEN
    RAISE EXCEPTION 'cross-tenant apply update matched a row';
  END IF;
END
$$;
ROLLBACK;

-- Worker role cannot touch apply confirmations or memory items.
BEGIN;
SET LOCAL ROLE memory_worker_runtime;
SELECT set_config('app.current_account_id', 'acct-apply-owner-a', true);
SELECT set_config('app.current_account_epoch', '2', true);
SELECT memory_os_apply_test.expect_sqlstate(
  $$UPDATE memory_os.apply_confirmation SET state = 'applied' WHERE id = 'apl-claim-a-000001'$$,
  ARRAY['42501'],
  'worker apply confirmation update'
);
SELECT memory_os_apply_test.expect_sqlstate(
  $$SELECT count(*) FROM memory_os.memory_item$$,
  ARRAY['42501'],
  'worker memory item select'
);
ROLLBACK;

-- Structural rejections on memory items.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct-apply-owner-a', true);
SELECT set_config('app.current_account_epoch', '2', true);
SELECT memory_os_apply_test.expect_sqlstate(
  $$INSERT INTO memory_os.memory_item (
      id, owner_account_id, account_epoch, fingerprint, source_preview_id, canonical_record
    ) VALUES (
      'mem_' || repeat('b', 32), 'acct-apply-owner-a', 2, 'short',
      'prv_applymemitem0001', '{"title":"bad"}'::jsonb
    )$$,
  ARRAY['23514'],
  'undersized fingerprint'
);
SELECT memory_os_apply_test.expect_sqlstate(
  $$INSERT INTO memory_os.memory_item (
      id, owner_account_id, account_epoch, fingerprint, source_preview_id, canonical_record
    ) VALUES (
      'mem_' || repeat('c', 32), 'acct-apply-owner-a', 2, 'fingerprint-two',
      'not-a-preview-id-x', '{"title":"bad"}'::jsonb
    )$$,
  ARRAY['23514'],
  'invalid source preview binding'
);
SELECT memory_os_apply_test.expect_sqlstate(
  $$INSERT INTO memory_os.memory_item (
      id, owner_account_id, account_epoch, fingerprint, source_preview_id, canonical_record
    ) VALUES (
      'mem_' || repeat('d', 32), 'acct-apply-intruder', 2, 'fingerprint-three',
      'prv_applymemitem0001', '{"title":"bad"}'::jsonb
    )$$,
  ARRAY['42501'],
  'foreign-owner memory item insert'
);
ROLLBACK;

SELECT 'Memory OS apply and memory integration tests PASS' AS result;
