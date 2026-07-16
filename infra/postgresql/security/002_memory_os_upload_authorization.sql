-- Memory OS Round 9 signed-upload persistence fields.
-- Apply after 001_memory_os_import_rls.sql.

BEGIN;

ALTER TABLE memory_os.import_job
  ADD COLUMN IF NOT EXISTS source_surface text;

CREATE UNIQUE INDEX IF NOT EXISTS import_job_tenant_identity_uidx
  ON memory_os.import_job (id, owner_account_id, account_epoch);

ALTER TABLE memory_os.upload_authorization
  ADD COLUMN IF NOT EXISTS job_id text,
  ADD COLUMN IF NOT EXISTS object_key text,
  ADD COLUMN IF NOT EXISTS content_length bigint,
  ADD COLUMN IF NOT EXISTS checksum_sha256 text,
  ADD COLUMN IF NOT EXISTS declared_content_type text,
  ADD COLUMN IF NOT EXISTS source_surface text,
  ADD COLUMN IF NOT EXISTS expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS failure_reason text;

DO $constraints$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'upload_authorization_content_length_check'
      AND conrelid = 'memory_os.upload_authorization'::regclass
  ) THEN
    ALTER TABLE memory_os.upload_authorization
      ADD CONSTRAINT upload_authorization_content_length_check
      CHECK (content_length > 0 AND content_length <= 268435456);
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'upload_authorization_checksum_check'
      AND conrelid = 'memory_os.upload_authorization'::regclass
  ) THEN
    ALTER TABLE memory_os.upload_authorization
      ADD CONSTRAINT upload_authorization_checksum_check
      CHECK (checksum_sha256 ~ '^[a-f0-9]{64}$');
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'upload_authorization_object_key_check'
      AND conrelid = 'memory_os.upload_authorization'::regclass
  ) THEN
    ALTER TABLE memory_os.upload_authorization
      ADD CONSTRAINT upload_authorization_object_key_check
      CHECK (object_key ~ '^quarantine/[A-Za-z0-9._:-]+/[A-Za-z0-9._:-]+$');
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'upload_authorization_state_check'
      AND conrelid = 'memory_os.upload_authorization'::regclass
  ) THEN
    ALTER TABLE memory_os.upload_authorization
      ADD CONSTRAINT upload_authorization_state_check
      CHECK (state IN ('issuing', 'issued', 'failed', 'consumed', 'revoked', 'expired'));
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'upload_authorization_job_tenant_fk'
      AND conrelid = 'memory_os.upload_authorization'::regclass
  ) THEN
    ALTER TABLE memory_os.upload_authorization
      ADD CONSTRAINT upload_authorization_job_tenant_fk
      FOREIGN KEY (job_id, owner_account_id, account_epoch)
      REFERENCES memory_os.import_job (id, owner_account_id, account_epoch)
      ON UPDATE RESTRICT
      ON DELETE RESTRICT;
  END IF;
END
$constraints$;

DO $not_null$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM memory_os.upload_authorization
    WHERE job_id IS NULL
       OR object_key IS NULL
       OR content_length IS NULL
       OR checksum_sha256 IS NULL
       OR declared_content_type IS NULL
       OR source_surface IS NULL
       OR expires_at IS NULL
  ) THEN
    RAISE EXCEPTION 'cannot enforce upload authorization NOT NULL fields: backfill required';
  END IF;
END
$not_null$;

ALTER TABLE memory_os.upload_authorization
  ALTER COLUMN job_id SET NOT NULL,
  ALTER COLUMN object_key SET NOT NULL,
  ALTER COLUMN content_length SET NOT NULL,
  ALTER COLUMN checksum_sha256 SET NOT NULL,
  ALTER COLUMN declared_content_type SET NOT NULL,
  ALTER COLUMN source_surface SET NOT NULL,
  ALTER COLUMN expires_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS upload_authorization_object_key_uidx
  ON memory_os.upload_authorization (object_key);

CREATE INDEX IF NOT EXISTS upload_authorization_job_idx
  ON memory_os.upload_authorization (owner_account_id, account_epoch, job_id);

CREATE INDEX IF NOT EXISTS upload_authorization_expiry_idx
  ON memory_os.upload_authorization (expires_at)
  WHERE state IN ('issuing', 'issued');

COMMIT;
