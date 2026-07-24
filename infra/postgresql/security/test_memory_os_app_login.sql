\set ON_ERROR_STOP on

-- Attribute and membership proof for the deployment login principal. What this
-- file cannot show is the connection itself — psql is already connected as the
-- migration superuser — so the live Go suite carries the other half: it opens a
-- real connection as memory_app_login and proves FORCE RLS binds it.

DO $attributes$
DECLARE
  role_record record;
BEGIN
  SELECT rolcanlogin, rolinherit, rolbypassrls, rolsuper, rolcreaterole, rolcreatedb
  INTO STRICT role_record
  FROM pg_roles WHERE rolname = 'memory_app_login';

  IF NOT role_record.rolcanlogin THEN
    RAISE EXCEPTION 'the deployment principal must be able to log in';
  END IF;
  -- NOINHERIT is the load-bearing attribute: with INHERIT the connection would
  -- hold every runtime role's privileges before any SET ROLE, and the scoped
  -- executor's role discipline would become decorative.
  IF role_record.rolinherit THEN
    RAISE EXCEPTION 'the deployment principal must not inherit runtime privileges';
  END IF;
  IF role_record.rolbypassrls THEN
    RAISE EXCEPTION 'the deployment principal must not bypass row-level security';
  END IF;
  IF role_record.rolsuper OR role_record.rolcreaterole OR role_record.rolcreatedb THEN
    RAISE EXCEPTION 'the deployment principal must hold no cluster-level power';
  END IF;
END
$attributes$;

DO $membership$
DECLARE
  granted text;
BEGIN
  FOREACH granted IN ARRAY ARRAY[
    'memory_api_runtime', 'memory_worker_runtime',
    'memory_deletion_runtime', 'memory_auth_runtime'
  ]
  LOOP
    IF NOT pg_has_role('memory_app_login', granted, 'MEMBER') THEN
      RAISE EXCEPTION 'the deployment principal cannot assume %', granted;
    END IF;
  END LOOP;

  -- The owner of the tables and policies is the one role it must never reach.
  IF pg_has_role('memory_app_login', 'memory_migration_owner', 'MEMBER') THEN
    RAISE EXCEPTION 'the deployment principal can become the migration owner';
  END IF;
END
$membership$;

-- No direct object privileges: everything must go through SET ROLE.
DO $privileges$
DECLARE
  offending text;
BEGIN
  SELECT string_agg(table_name, ', ') INTO offending
  FROM information_schema.table_privileges
  WHERE grantee = 'memory_app_login' AND table_schema = 'memory_os';
  IF offending IS NOT NULL THEN
    RAISE EXCEPTION 'the deployment principal holds direct table privileges on: %', offending;
  END IF;

  IF has_schema_privilege('memory_app_login', 'memory_os', 'USAGE') THEN
    RAISE EXCEPTION 'the deployment principal holds schema usage without SET ROLE';
  END IF;
END
$privileges$;

SELECT 'Memory OS deployment login principal tests PASS' AS result;
