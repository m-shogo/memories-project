-- Memory OS Round 9 Apply confirmation and minimal Memory persistence.
-- Apply after 004_memory_os_account_session.sql.
--
-- apply_confirmation gains the idempotency-claim state machine the Apply
-- service requires (in_progress → applied). The original stub kept the table
-- update-free; this migration deliberately narrows that stance to one
-- owner-scoped UPDATE policy for the API role because the claim pattern
-- cannot exist without it. The legacy 'active' state stays allowed for rows
-- the RLS security tests create.

BEGIN;

ALTER TABLE memory_os.apply_confirmation
  ADD COLUMN IF NOT EXISTS preview_id text,
  ADD COLUMN IF NOT EXISTS preview_sha256 text,
  ADD COLUMN IF NOT EXISTS idempotency_key text,
  ADD COLUMN IF NOT EXISTS request_sha256 text,
  ADD COLUMN IF NOT EXISTS duplicate_policy text,
  ADD COLUMN IF NOT EXISTS created_count integer,
  ADD COLUMN IF NOT EXISTS updated_count integer,
  ADD COLUMN IF NOT EXISTS skipped_count integer,
  ADD COLUMN IF NOT EXISTS completed_at timestamptz;

DO $constraints$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'apply_confirmation_state_check'
      AND conrelid = 'memory_os.apply_confirmation'::regclass
  ) THEN
    ALTER TABLE memory_os.apply_confirmation
      ADD CONSTRAINT apply_confirmation_state_check
      CHECK (state IN ('active', 'in_progress', 'applied'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'apply_confirmation_policy_check'
      AND conrelid = 'memory_os.apply_confirmation'::regclass
  ) THEN
    ALTER TABLE memory_os.apply_confirmation
      ADD CONSTRAINT apply_confirmation_policy_check
      CHECK (duplicate_policy IS NULL
             OR duplicate_policy IN ('skip_existing', 'keep_both', 'update_safe_fields'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'apply_confirmation_hash_check'
      AND conrelid = 'memory_os.apply_confirmation'::regclass
  ) THEN
    ALTER TABLE memory_os.apply_confirmation
      ADD CONSTRAINT apply_confirmation_hash_check
      CHECK ((preview_sha256 IS NULL OR preview_sha256 ~ '^[a-f0-9]{64}$')
             AND (request_sha256 IS NULL OR request_sha256 ~ '^[a-f0-9]{64}$'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'apply_confirmation_counts_check'
      AND conrelid = 'memory_os.apply_confirmation'::regclass
  ) THEN
    ALTER TABLE memory_os.apply_confirmation
      ADD CONSTRAINT apply_confirmation_counts_check
      CHECK ((created_count IS NULL OR created_count >= 0)
             AND (updated_count IS NULL OR updated_count >= 0)
             AND (skipped_count IS NULL OR skipped_count >= 0));
  END IF;
END
$constraints$;

CREATE UNIQUE INDEX IF NOT EXISTS apply_confirmation_idempotency_uidx
  ON memory_os.apply_confirmation (owner_account_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

GRANT UPDATE ON TABLE memory_os.apply_confirmation TO memory_api_runtime;
DROP POLICY IF EXISTS apply_confirmation_tenant_update ON memory_os.apply_confirmation;
CREATE POLICY apply_confirmation_tenant_update ON memory_os.apply_confirmation
  FOR UPDATE TO memory_api_runtime
  USING (owner_account_id = memory_os.current_account_id()
         AND account_epoch = memory_os.current_account_epoch())
  WITH CHECK (owner_account_id = memory_os.current_account_id()
              AND account_epoch = memory_os.current_account_epoch());

-- memory_item is the minimal applied-memory persistence: one row per applied
-- candidate, carrying the canonical record and its dedupe fingerprint. The
-- richer Memory domain model remains future work; this table exists so Apply
-- can account for every candidate with real durable writes.
CREATE TABLE IF NOT EXISTS memory_os.memory_item (
  id text PRIMARY KEY
    CONSTRAINT memory_item_id_check CHECK (id ~ '^mem_[a-z0-9]{16,64}$'),
  owner_account_id text NOT NULL
    CONSTRAINT memory_item_owner_check CHECK (length(owner_account_id) BETWEEN 16 AND 128),
  account_epoch bigint NOT NULL CHECK (account_epoch >= 0),
  fingerprint text NOT NULL
    CONSTRAINT memory_item_fingerprint_check CHECK (length(fingerprint) BETWEEN 8 AND 128),
  source_preview_id text NOT NULL
    CONSTRAINT memory_item_preview_check CHECK (source_preview_id ~ '^prv_[A-Za-z0-9_-]{12,120}$'),
  canonical_record jsonb NOT NULL
    CONSTRAINT memory_item_record_object_check CHECK (jsonb_typeof(canonical_record) = 'object'),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE memory_os.memory_item OWNER TO memory_migration_owner;
REVOKE ALL ON TABLE memory_os.memory_item FROM PUBLIC;
REVOKE ALL ON TABLE memory_os.memory_item FROM
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime, memory_readonly_observer;
ALTER TABLE memory_os.memory_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_os.memory_item FORCE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS memory_item_owner_fingerprint_idx
  ON memory_os.memory_item (owner_account_id, account_epoch, fingerprint);

GRANT SELECT, INSERT, UPDATE ON TABLE memory_os.memory_item TO memory_api_runtime;
GRANT SELECT ON TABLE memory_os.memory_item TO memory_deletion_runtime;
GRANT DELETE ON TABLE memory_os.memory_item TO memory_deletion_runtime;

DROP POLICY IF EXISTS memory_item_tenant_select ON memory_os.memory_item;
CREATE POLICY memory_item_tenant_select ON memory_os.memory_item
  FOR SELECT TO memory_api_runtime, memory_deletion_runtime
  USING (owner_account_id = memory_os.current_account_id()
         AND account_epoch = memory_os.current_account_epoch());

DROP POLICY IF EXISTS memory_item_tenant_insert ON memory_os.memory_item;
CREATE POLICY memory_item_tenant_insert ON memory_os.memory_item
  FOR INSERT TO memory_api_runtime
  WITH CHECK (owner_account_id = memory_os.current_account_id()
              AND account_epoch = memory_os.current_account_epoch());

DROP POLICY IF EXISTS memory_item_tenant_update ON memory_os.memory_item;
CREATE POLICY memory_item_tenant_update ON memory_os.memory_item
  FOR UPDATE TO memory_api_runtime
  USING (owner_account_id = memory_os.current_account_id()
         AND account_epoch = memory_os.current_account_epoch())
  WITH CHECK (owner_account_id = memory_os.current_account_id()
              AND account_epoch = memory_os.current_account_epoch());

DROP POLICY IF EXISTS memory_item_tenant_delete ON memory_os.memory_item;
CREATE POLICY memory_item_tenant_delete ON memory_os.memory_item
  FOR DELETE TO memory_deletion_runtime
  USING (owner_account_id = memory_os.current_account_id()
         AND account_epoch = memory_os.current_account_epoch());

COMMIT;
