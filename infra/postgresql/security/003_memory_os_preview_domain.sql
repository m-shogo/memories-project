-- Memory OS Round 9 production Preview domain schema.
-- Apply after 002_memory_os_upload_authorization.sql.
--
-- preview_ready is the immutable "ready Preview": one row per committed spool,
-- inserted only by the commit worker inside the single short commit
-- transaction, never updated, deleted only by the deletion runtime.
-- preview_candidate / preview_rejection are its immutable children.
-- memory_os.import_preview remains the Round 9 RLS security stub and is not
-- part of this production domain.

BEGIN;

CREATE TABLE IF NOT EXISTS memory_os.preview_ready (
  id text PRIMARY KEY
    CONSTRAINT preview_ready_id_check CHECK (id ~ '^prv_[A-Za-z0-9_-]{12,120}$'),
  owner_account_id text NOT NULL,
  account_epoch bigint NOT NULL CHECK (account_epoch >= 0),
  job_id text NOT NULL,
  spool_id text NOT NULL
    CONSTRAINT preview_ready_spool_id_check CHECK (spool_id ~ '^spl_[A-Za-z0-9_-]{12,120}$'),
  commit_key text NOT NULL
    CONSTRAINT preview_ready_commit_key_check CHECK (commit_key ~ '^[a-f0-9]{64}$'),
  state text NOT NULL DEFAULT 'ready'
    CONSTRAINT preview_ready_state_check CHECK (state = 'ready'),
  source_object_key text NOT NULL,
  source_object_version_id text NOT NULL
    CONSTRAINT preview_ready_object_version_check
    CHECK (
      source_object_version_id ~ '^[A-Za-z0-9._~:+/=-]+$'
      AND length(source_object_version_id) BETWEEN 1 AND 256
    ),
  source_content_length bigint NOT NULL
    CONSTRAINT preview_ready_source_length_check
    CHECK (source_content_length > 0 AND source_content_length <= 268435456),
  source_checksum_sha256 text NOT NULL
    CONSTRAINT preview_ready_source_checksum_check
    CHECK (source_checksum_sha256 ~ '^[a-f0-9]{64}$'),
  adapter_id text NOT NULL
    CONSTRAINT preview_ready_adapter_id_check
    CHECK (adapter_id ~ '^[a-z][a-z0-9]*([._:-][a-z0-9]+)*$' AND length(adapter_id) <= 160),
  adapter_version text NOT NULL
    CONSTRAINT preview_ready_adapter_version_check
    CHECK (adapter_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$' AND length(adapter_version) <= 32),
  adapter_artifact_sha256 text NOT NULL
    CONSTRAINT preview_ready_adapter_artifact_check
    CHECK (adapter_artifact_sha256 ~ '^[a-f0-9]{64}$'),
  options_sha256 text NOT NULL
    CONSTRAINT preview_ready_options_check CHECK (options_sha256 ~ '^[a-f0-9]{64}$'),
  source_row_count integer NOT NULL,
  spool_byte_length bigint NOT NULL,
  accepted_record_format text NOT NULL
    CONSTRAINT preview_ready_accepted_format_check
    CHECK (accepted_record_format = 'memory-os-preview-candidate-v1-length-prefixed'),
  accepted_count integer NOT NULL
    CONSTRAINT preview_ready_accepted_count_check CHECK (accepted_count >= 1),
  accepted_byte_length bigint NOT NULL
    CONSTRAINT preview_ready_accepted_bytes_check CHECK (accepted_byte_length >= 1),
  accepted_sha256 text NOT NULL
    CONSTRAINT preview_ready_accepted_sha_check CHECK (accepted_sha256 ~ '^[a-f0-9]{64}$'),
  rejected_record_format text NOT NULL
    CONSTRAINT preview_ready_rejected_format_check
    CHECK (rejected_record_format = 'memory-os-preview-rejection-v1-length-prefixed'),
  rejected_count integer NOT NULL
    CONSTRAINT preview_ready_rejected_count_check CHECK (rejected_count >= 0),
  rejected_byte_length bigint NOT NULL
    CONSTRAINT preview_ready_rejected_bytes_check CHECK (rejected_byte_length >= 0),
  rejected_sha256 text NOT NULL
    CONSTRAINT preview_ready_rejected_sha_check CHECK (rejected_sha256 ~ '^[a-f0-9]{64}$'),
  preview_hash_sha256 text NOT NULL
    CONSTRAINT preview_ready_preview_hash_check CHECK (preview_hash_sha256 ~ '^[a-f0-9]{64}$'),
  sealed_created_at timestamptz NOT NULL,
  sealed_expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT preview_ready_row_totals_check CHECK (
    source_row_count = accepted_count + rejected_count
    AND source_row_count >= 1
    AND source_row_count <= 100000
  ),
  CONSTRAINT preview_ready_byte_totals_check CHECK (
    spool_byte_length = accepted_byte_length + rejected_byte_length
    AND spool_byte_length >= 1
    AND spool_byte_length <= 536870912
  ),
  CONSTRAINT preview_ready_empty_rejection_check CHECK (
    (rejected_count = 0) = (rejected_byte_length = 0)
    AND (
      rejected_count > 0
      OR rejected_sha256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    )
  ),
  CONSTRAINT preview_ready_object_key_check CHECK (
    source_object_key ~ '^quarantine/[A-Za-z0-9._:-]+/[A-Za-z0-9._:-]+$'
    AND split_part(source_object_key, '/', 2) = job_id
  ),
  CONSTRAINT preview_ready_ttl_check CHECK (
    sealed_expires_at > sealed_created_at
    AND sealed_expires_at - sealed_created_at <= interval '24 hours'
  ),
  CONSTRAINT preview_ready_job_tenant_fk
    FOREIGN KEY (job_id, owner_account_id, account_epoch)
    REFERENCES memory_os.import_job (id, owner_account_id, account_epoch)
    ON UPDATE RESTRICT
    ON DELETE RESTRICT
);

ALTER TABLE memory_os.preview_ready OWNER TO memory_migration_owner;

CREATE UNIQUE INDEX IF NOT EXISTS preview_ready_commit_key_uidx
  ON memory_os.preview_ready (commit_key);

CREATE UNIQUE INDEX IF NOT EXISTS preview_ready_job_uidx
  ON memory_os.preview_ready (job_id);

CREATE UNIQUE INDEX IF NOT EXISTS preview_ready_spool_uidx
  ON memory_os.preview_ready (spool_id);

CREATE UNIQUE INDEX IF NOT EXISTS preview_ready_tenant_identity_uidx
  ON memory_os.preview_ready (id, owner_account_id, account_epoch);

CREATE TABLE IF NOT EXISTS memory_os.preview_candidate (
  preview_id text NOT NULL,
  owner_account_id text NOT NULL,
  account_epoch bigint NOT NULL CHECK (account_epoch >= 0),
  ordinal integer NOT NULL
    CONSTRAINT preview_candidate_ordinal_check CHECK (ordinal >= 1 AND ordinal <= 100000),
  source_row bigint NOT NULL
    CONSTRAINT preview_candidate_source_row_check CHECK (source_row >= 1 AND source_row <= 100000),
  record_sha256 text NOT NULL
    CONSTRAINT preview_candidate_record_sha_check CHECK (record_sha256 ~ '^[a-f0-9]{64}$'),
  canonical_record jsonb NOT NULL
    CONSTRAINT preview_candidate_record_object_check
    CHECK (jsonb_typeof(canonical_record) = 'object'),
  CONSTRAINT preview_candidate_pkey PRIMARY KEY (preview_id, ordinal),
  CONSTRAINT preview_candidate_source_row_uniq UNIQUE (preview_id, source_row),
  CONSTRAINT preview_candidate_tenant_fk
    FOREIGN KEY (preview_id, owner_account_id, account_epoch)
    REFERENCES memory_os.preview_ready (id, owner_account_id, account_epoch)
    ON UPDATE RESTRICT
    ON DELETE CASCADE
);

ALTER TABLE memory_os.preview_candidate OWNER TO memory_migration_owner;

CREATE OR REPLACE FUNCTION memory_os.valid_import_issue_codes(codes text[])
RETURNS boolean
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
SET search_path = pg_catalog
AS $$
  SELECT cardinality(codes) BETWEEN 1 AND 16
    AND COALESCE(
      (SELECT bool_and(code IS NOT NULL AND code ~ '^IMPORT_[A-Z0-9_]+$' AND length(code) <= 64)
         FROM unnest(codes) AS u(code)),
      false
    )
$$;

ALTER FUNCTION memory_os.valid_import_issue_codes(text[]) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.valid_import_issue_codes(text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.valid_import_issue_codes(text[]) TO
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime;

-- Safe rejection rows have no free-text columns at all: raw user values are
-- structurally impossible, only the source row number and IMPORT_* codes fit.
CREATE TABLE IF NOT EXISTS memory_os.preview_rejection (
  preview_id text NOT NULL,
  owner_account_id text NOT NULL,
  account_epoch bigint NOT NULL CHECK (account_epoch >= 0),
  ordinal integer NOT NULL
    CONSTRAINT preview_rejection_ordinal_check CHECK (ordinal >= 1 AND ordinal <= 100000),
  source_row bigint NOT NULL
    CONSTRAINT preview_rejection_source_row_check CHECK (source_row >= 1 AND source_row <= 100000),
  issue_codes text[] NOT NULL
    CONSTRAINT preview_rejection_issue_codes_check
    CHECK (memory_os.valid_import_issue_codes(issue_codes)),
  CONSTRAINT preview_rejection_pkey PRIMARY KEY (preview_id, ordinal),
  CONSTRAINT preview_rejection_source_row_uniq UNIQUE (preview_id, source_row),
  CONSTRAINT preview_rejection_tenant_fk
    FOREIGN KEY (preview_id, owner_account_id, account_epoch)
    REFERENCES memory_os.preview_ready (id, owner_account_id, account_epoch)
    ON UPDATE RESTRICT
    ON DELETE CASCADE
);

ALTER TABLE memory_os.preview_rejection OWNER TO memory_migration_owner;

-- assert_preview_complete must be the last statement before COMMIT in the
-- commit transaction: it proves the copied child rows are exactly the sealed
-- counts with contiguous 1..n ordinals. SECURITY INVOKER keeps tenant RLS in
-- force, so a foreign tenant's preview is simply not visible.
CREATE OR REPLACE FUNCTION memory_os.assert_preview_complete(p_preview_id text)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  ready memory_os.preview_ready%ROWTYPE;
  row_count bigint;
  min_ordinal integer;
  max_ordinal integer;
BEGIN
  SELECT * INTO ready FROM memory_os.preview_ready WHERE id = p_preview_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'preview % is not visible', p_preview_id USING ERRCODE = 'P0002';
  END IF;

  SELECT count(*), min(ordinal), max(ordinal)
    INTO row_count, min_ordinal, max_ordinal
    FROM memory_os.preview_candidate
    WHERE preview_id = p_preview_id;
  IF row_count <> ready.accepted_count
     OR min_ordinal IS DISTINCT FROM 1
     OR max_ordinal IS DISTINCT FROM ready.accepted_count THEN
    RAISE EXCEPTION 'preview % candidates are not complete and contiguous', p_preview_id
      USING ERRCODE = 'P0002';
  END IF;

  SELECT count(*), min(ordinal), max(ordinal)
    INTO row_count, min_ordinal, max_ordinal
    FROM memory_os.preview_rejection
    WHERE preview_id = p_preview_id;
  IF row_count <> ready.rejected_count
     OR (ready.rejected_count > 0 AND (
       min_ordinal IS DISTINCT FROM 1
       OR max_ordinal IS DISTINCT FROM ready.rejected_count
     )) THEN
    RAISE EXCEPTION 'preview % rejections are not complete and contiguous', p_preview_id
      USING ERRCODE = 'P0002';
  END IF;
END
$function$;

ALTER FUNCTION memory_os.assert_preview_complete(text) OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.assert_preview_complete(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.assert_preview_complete(text) TO
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime;

CREATE OR REPLACE FUNCTION memory_os._install_preview_tenant_rls(
  p_table regclass,
  p_select_roles name[],
  p_insert_roles name[],
  p_update_roles name[],
  p_delete_roles name[]
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  rel_name text;
  owner_epoch_expression text;
  roles_sql text;
BEGIN
  SELECT c.relname INTO STRICT rel_name FROM pg_class c WHERE c.oid = p_table;
  owner_epoch_expression :=
    '(owner_account_id = memory_os.current_account_id() AND account_epoch = memory_os.current_account_epoch())';

  EXECUTE format('REVOKE ALL ON TABLE %s FROM PUBLIC', p_table);
  EXECUTE format(
    'REVOKE ALL ON TABLE %s FROM memory_api_runtime, memory_worker_runtime, memory_deletion_runtime, memory_readonly_observer',
    p_table
  );
  EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', p_table);
  EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', p_table);

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_select', p_table);
  SELECT string_agg(format('%I', r.role_name), ', ')
    INTO roles_sql FROM unnest(p_select_roles) AS r(role_name);
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT SELECT ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR SELECT TO %s USING %s',
      rel_name || '_tenant_select', p_table, roles_sql, owner_epoch_expression
    );
  END IF;

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_insert', p_table);
  SELECT string_agg(format('%I', r.role_name), ', ')
    INTO roles_sql FROM unnest(p_insert_roles) AS r(role_name);
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT INSERT ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR INSERT TO %s WITH CHECK %s',
      rel_name || '_tenant_insert', p_table, roles_sql, owner_epoch_expression
    );
  END IF;

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_update', p_table);
  SELECT string_agg(format('%I', r.role_name), ', ')
    INTO roles_sql FROM unnest(p_update_roles) AS r(role_name);
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT UPDATE ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR UPDATE TO %s USING %s WITH CHECK %s',
      rel_name || '_tenant_update', p_table, roles_sql,
      owner_epoch_expression, owner_epoch_expression
    );
  END IF;

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_delete', p_table);
  SELECT string_agg(format('%I', r.role_name), ', ')
    INTO roles_sql FROM unnest(p_delete_roles) AS r(role_name);
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT DELETE ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR DELETE TO %s USING %s',
      rel_name || '_tenant_delete', p_table, roles_sql, owner_epoch_expression
    );
  END IF;
END
$function$;

ALTER FUNCTION memory_os._install_preview_tenant_rls(
  regclass, name[], name[], name[], name[]
) OWNER TO memory_migration_owner;

SELECT memory_os._install_preview_tenant_rls(
  'memory_os.preview_ready'::regclass,
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_worker_runtime']::name[],
  ARRAY[]::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_preview_tenant_rls(
  'memory_os.preview_candidate'::regclass,
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_worker_runtime']::name[],
  ARRAY[]::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_preview_tenant_rls(
  'memory_os.preview_rejection'::regclass,
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_worker_runtime']::name[],
  ARRAY[]::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

DROP FUNCTION memory_os._install_preview_tenant_rls(
  regclass, name[], name[], name[], name[]
);

COMMIT;
