-- Memory OS Round 9 PostgreSQL tenant-isolation foundation.
-- Privilege roles are NOLOGIN / NOINHERIT / NOBYPASSRLS.
-- Deployment login principals must SET ROLE only after verified server auth
-- and must set app.current_account_id / app.current_account_epoch with SET LOCAL.

BEGIN;

DO $roles$
DECLARE
  role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY[
    'memory_api_runtime',
    'memory_worker_runtime',
    'memory_migration_owner',
    'memory_deletion_runtime',
    'memory_readonly_observer'
  ]
  LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN NOINHERIT NOBYPASSRLS', role_name);
    END IF;
    EXECUTE format('ALTER ROLE %I NOLOGIN NOINHERIT NOBYPASSRLS', role_name);
  END LOOP;
END
$roles$;

CREATE SCHEMA IF NOT EXISTS memory_os;
ALTER SCHEMA memory_os OWNER TO memory_migration_owner;
REVOKE ALL ON SCHEMA memory_os FROM PUBLIC;
GRANT USAGE ON SCHEMA memory_os TO
  memory_api_runtime,
  memory_worker_runtime,
  memory_deletion_runtime;

CREATE OR REPLACE FUNCTION memory_os.current_account_id()
RETURNS text
LANGUAGE sql
STABLE
PARALLEL SAFE
SET search_path = pg_catalog
AS $$
  SELECT NULLIF(current_setting('app.current_account_id', true), '')
$$;

CREATE OR REPLACE FUNCTION memory_os.current_account_epoch()
RETURNS bigint
LANGUAGE sql
STABLE
PARALLEL SAFE
SET search_path = pg_catalog
AS $$
  SELECT CASE
    WHEN NULLIF(current_setting('app.current_account_epoch', true), '') ~ '^[0-9]+$'
      THEN current_setting('app.current_account_epoch', true)::bigint
    ELSE NULL
  END
$$;

ALTER FUNCTION memory_os.current_account_id() OWNER TO memory_migration_owner;
ALTER FUNCTION memory_os.current_account_epoch() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.current_account_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION memory_os.current_account_epoch() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.current_account_id() TO
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime;
GRANT EXECUTE ON FUNCTION memory_os.current_account_epoch() TO
  memory_api_runtime, memory_worker_runtime, memory_deletion_runtime;

CREATE OR REPLACE FUNCTION memory_os._ensure_security_table(
  p_table name,
  p_epoch_column name
)
RETURNS regclass
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  qualified_name text := format('memory_os.%I', p_table);
BEGIN
  IF p_epoch_column NOT IN ('account_epoch', 'deletion_epoch') THEN
    RAISE EXCEPTION 'unsupported epoch column: %', p_epoch_column;
  END IF;

  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %s (' ||
    'id text PRIMARY KEY,' ||
    'owner_account_id text NOT NULL,' ||
    '%I bigint NOT NULL CHECK (%I >= 0),' ||
    'state text NOT NULL DEFAULT ''active'',' ||
    'safe_metadata jsonb NOT NULL DEFAULT ''{}''::jsonb,' ||
    'created_at timestamptz NOT NULL DEFAULT now(),' ||
    'updated_at timestamptz NOT NULL DEFAULT now()' ||
    ')',
    qualified_name,
    p_epoch_column,
    p_epoch_column
  );
  EXECUTE format('ALTER TABLE %s OWNER TO memory_migration_owner', qualified_name);
  RETURN qualified_name::regclass;
END
$function$;

ALTER FUNCTION memory_os._ensure_security_table(name, name)
  OWNER TO memory_migration_owner;

CREATE OR REPLACE FUNCTION memory_os._install_tenant_rls(
  p_table regclass,
  p_epoch_column name,
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
  owner_epoch_expression := format(
    '(owner_account_id = memory_os.current_account_id() AND %I = memory_os.current_account_epoch())',
    p_epoch_column
  );

  EXECUTE format('REVOKE ALL ON TABLE %s FROM PUBLIC', p_table);
  EXECUTE format(
    'REVOKE ALL ON TABLE %s FROM memory_api_runtime, memory_worker_runtime, memory_deletion_runtime, memory_readonly_observer',
    p_table
  );
  EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', p_table);
  EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', p_table);

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_select', p_table);
  SELECT string_agg(format('%I', role_name), ', ')
    INTO roles_sql FROM unnest(p_select_roles) AS role_name;
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT SELECT ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR SELECT TO %s USING %s',
      rel_name || '_tenant_select', p_table, roles_sql, owner_epoch_expression
    );
  END IF;

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_insert', p_table);
  SELECT string_agg(format('%I', role_name), ', ')
    INTO roles_sql FROM unnest(p_insert_roles) AS role_name;
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT INSERT ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR INSERT TO %s WITH CHECK %s',
      rel_name || '_tenant_insert', p_table, roles_sql, owner_epoch_expression
    );
  END IF;

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_update', p_table);
  SELECT string_agg(format('%I', role_name), ', ')
    INTO roles_sql FROM unnest(p_update_roles) AS role_name;
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT UPDATE ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR UPDATE TO %s USING %s WITH CHECK %s',
      rel_name || '_tenant_update', p_table, roles_sql,
      owner_epoch_expression, owner_epoch_expression
    );
  END IF;

  EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rel_name || '_tenant_delete', p_table);
  SELECT string_agg(format('%I', role_name), ', ')
    INTO roles_sql FROM unnest(p_delete_roles) AS role_name;
  IF roles_sql IS NOT NULL THEN
    EXECUTE format('GRANT DELETE ON TABLE %s TO %s', p_table, roles_sql);
    EXECUTE format(
      'CREATE POLICY %I ON %s FOR DELETE TO %s USING %s',
      rel_name || '_tenant_delete', p_table, roles_sql, owner_epoch_expression
    );
  END IF;
END
$function$;

ALTER FUNCTION memory_os._install_tenant_rls(
  regclass, name, name[], name[], name[], name[]
) OWNER TO memory_migration_owner;

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('import_job', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_api_runtime','memory_worker_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('pairing_session', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('upload_authorization', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('quarantine_object', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime','memory_worker_runtime']::name[],
  ARRAY['memory_api_runtime','memory_worker_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('import_preview', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_worker_runtime']::name[],
  ARRAY[]::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('apply_confirmation', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY[]::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('import_report', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_worker_runtime']::name[],
  ARRAY[]::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('export_job', 'account_epoch'),
  'account_epoch',
  ARRAY['memory_api_runtime','memory_worker_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_worker_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

SELECT memory_os._install_tenant_rls(
  memory_os._ensure_security_table('deletion_fence', 'deletion_epoch'),
  'deletion_epoch',
  ARRAY['memory_api_runtime','memory_deletion_runtime']::name[],
  ARRAY['memory_api_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[],
  ARRAY['memory_deletion_runtime']::name[]
);

DROP FUNCTION memory_os._install_tenant_rls(
  regclass, name, name[], name[], name[], name[]
);
DROP FUNCTION memory_os._ensure_security_table(name, name);

COMMIT;
