-- Memory OS canonical account state and deletion-epoch enforcement.
-- Apply after 001_memory_os_import_rls.sql.

BEGIN;

CREATE TABLE IF NOT EXISTS memory_os.account_control (
  account_id text PRIMARY KEY,
  account_epoch bigint NOT NULL CHECK (account_epoch >= 0),
  state text NOT NULL CHECK (state IN ('active', 'deleting', 'deleted', 'suspended')),
  deletion_started_at timestamptz,
  deletion_completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (state IN ('active', 'suspended')
      AND deletion_started_at IS NULL
      AND deletion_completed_at IS NULL)
    OR (state = 'deleting'
      AND deletion_started_at IS NOT NULL
      AND deletion_completed_at IS NULL)
    OR (state = 'deleted'
      AND deletion_started_at IS NOT NULL
      AND deletion_completed_at IS NOT NULL)
  )
);

ALTER TABLE memory_os.account_control OWNER TO memory_migration_owner;
REVOKE ALL ON TABLE memory_os.account_control FROM PUBLIC;
REVOKE ALL ON TABLE memory_os.account_control FROM
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime,
  memory_readonly_observer;

ALTER TABLE memory_os.account_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_os.account_control FORCE ROW LEVEL SECURITY;

GRANT SELECT ON TABLE memory_os.account_control TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;
GRANT INSERT ON TABLE memory_os.account_control TO memory_api_runtime;

DROP POLICY IF EXISTS account_control_select ON memory_os.account_control;
CREATE POLICY account_control_select
  ON memory_os.account_control
  FOR SELECT
  TO memory_api_runtime, memory_worker_runtime, memory_deletion_runtime, memory_migration_owner
  USING (account_id = memory_os.current_account_id());

DROP POLICY IF EXISTS account_control_insert ON memory_os.account_control;
CREATE POLICY account_control_insert
  ON memory_os.account_control
  FOR INSERT
  TO memory_api_runtime, memory_migration_owner
  WITH CHECK (
    account_id = memory_os.current_account_id()
    AND account_epoch = memory_os.current_account_epoch()
    AND state = 'active'
    AND deletion_started_at IS NULL
    AND deletion_completed_at IS NULL
  );

DROP POLICY IF EXISTS account_control_internal_update ON memory_os.account_control;
CREATE POLICY account_control_internal_update
  ON memory_os.account_control
  FOR UPDATE
  TO memory_migration_owner
  USING (account_id = memory_os.current_account_id())
  WITH CHECK (account_id = memory_os.current_account_id());

CREATE OR REPLACE FUNCTION memory_os.account_epoch_is_authorized()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY INVOKER
PARALLEL UNSAFE
SET search_path = pg_catalog, memory_os
AS $function$
  SELECT EXISTS (
    SELECT 1
    FROM memory_os.account_control AS account
    WHERE account.account_id = memory_os.current_account_id()
      AND account.account_epoch = memory_os.current_account_epoch()
      AND (
        account.state = 'active'
        OR (
          current_user = 'memory_deletion_runtime'
          AND account.state = 'deleting'
        )
      )
  )
$function$;

ALTER FUNCTION memory_os.account_epoch_is_authorized()
  OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.account_epoch_is_authorized() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.account_epoch_is_authorized() TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;

CREATE OR REPLACE FUNCTION memory_os.begin_account_deletion()
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  verified_account_id text := memory_os.current_account_id();
  next_epoch bigint;
BEGIN
  IF verified_account_id IS NULL THEN
    RAISE EXCEPTION 'verified account context is required'
      USING ERRCODE = '42501';
  END IF;

  UPDATE memory_os.account_control
  SET account_epoch = account_epoch + 1,
      state = 'deleting',
      deletion_started_at = now(),
      deletion_completed_at = NULL,
      updated_at = now()
  WHERE account_id = verified_account_id
    AND account_epoch = memory_os.current_account_epoch()
    AND state IN ('active', 'suspended')
  RETURNING account_epoch INTO next_epoch;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'account cannot enter deletion state'
      USING ERRCODE = '55000';
  END IF;

  RETURN next_epoch;
END
$function$;

ALTER FUNCTION memory_os.begin_account_deletion()
  OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.begin_account_deletion() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.begin_account_deletion() TO memory_api_runtime;

CREATE OR REPLACE FUNCTION memory_os.complete_account_deletion()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  verified_account_id text := memory_os.current_account_id();
BEGIN
  IF verified_account_id IS NULL OR memory_os.current_account_epoch() IS NULL THEN
    RAISE EXCEPTION 'verified account and epoch context are required'
      USING ERRCODE = '42501';
  END IF;

  UPDATE memory_os.account_control
  SET state = 'deleted',
      deletion_completed_at = now(),
      updated_at = now()
  WHERE account_id = verified_account_id
    AND account_epoch = memory_os.current_account_epoch()
    AND state = 'deleting';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'account deletion cannot be completed'
      USING ERRCODE = '55000';
  END IF;
END
$function$;

ALTER FUNCTION memory_os.complete_account_deletion()
  OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.complete_account_deletion() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.complete_account_deletion() TO memory_deletion_runtime;

CREATE OR REPLACE FUNCTION memory_os._reinforce_tenant_policy(
  target_table regclass,
  epoch_column name
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  relation_name text;
  owner_epoch_expression text;
BEGIN
  IF epoch_column NOT IN ('account_epoch', 'deletion_epoch') THEN
    RAISE EXCEPTION 'unsupported epoch column: %', epoch_column;
  END IF;

  SELECT relation.relname
  INTO STRICT relation_name
  FROM pg_class AS relation
  WHERE relation.oid = target_table;

  owner_epoch_expression := format(
    '(owner_account_id = memory_os.current_account_id()'
    ' AND %I = memory_os.current_account_epoch()'
    ' AND memory_os.account_epoch_is_authorized())',
    epoch_column
  );

  IF EXISTS (
    SELECT 1 FROM pg_policy
    WHERE polrelid = target_table
      AND polname = relation_name || '_tenant_select'
  ) THEN
    EXECUTE format(
      'ALTER POLICY %I ON %s USING %s',
      relation_name || '_tenant_select',
      target_table,
      owner_epoch_expression
    );
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_policy
    WHERE polrelid = target_table
      AND polname = relation_name || '_tenant_insert'
  ) THEN
    EXECUTE format(
      'ALTER POLICY %I ON %s WITH CHECK %s',
      relation_name || '_tenant_insert',
      target_table,
      owner_epoch_expression
    );
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_policy
    WHERE polrelid = target_table
      AND polname = relation_name || '_tenant_update'
  ) THEN
    EXECUTE format(
      'ALTER POLICY %I ON %s USING %s WITH CHECK %s',
      relation_name || '_tenant_update',
      target_table,
      owner_epoch_expression,
      owner_epoch_expression
    );
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_policy
    WHERE polrelid = target_table
      AND polname = relation_name || '_tenant_delete'
  ) THEN
    EXECUTE format(
      'ALTER POLICY %I ON %s USING %s',
      relation_name || '_tenant_delete',
      target_table,
      owner_epoch_expression
    );
  END IF;
END
$function$;

ALTER FUNCTION memory_os._reinforce_tenant_policy(regclass, name)
  OWNER TO memory_migration_owner;

SELECT memory_os._reinforce_tenant_policy('memory_os.import_job', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.pairing_session', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.upload_authorization', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.quarantine_object', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.import_preview', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.apply_confirmation', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.import_report', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.export_job', 'account_epoch');
SELECT memory_os._reinforce_tenant_policy('memory_os.deletion_fence', 'deletion_epoch');

DROP FUNCTION memory_os._reinforce_tenant_policy(regclass, name);

COMMIT;
