-- Memory OS Round 9 deployment login principal.
-- Apply after 006_memory_os_deletion_fencing.sql.
--
-- Every runtime role is NOLOGIN by design, so something must actually connect.
-- Until now that was the superuser in dev and CI, which meant FORCE RLS was
-- proven for the runtime roles but never for the principal a deployment would
-- really use — a superuser bypasses row-level security outright, so a
-- misconfigured deployment would have silently disabled every tenant policy.
--
-- memory_app_login is that principal, and it is deliberately powerless on its
-- own: no table privileges, no schema usage, NOBYPASSRLS, and NOINHERIT so
-- membership in the runtime roles grants nothing until the connection issues
-- an explicit SET ROLE. It is not a member of memory_migration_owner, so it
-- can never reach the policies themselves.
--
-- No password is set here. Credentials belong to deployment configuration,
-- never to a migration in version control.

BEGIN;

DO $login_role$
BEGIN
  BEGIN
    CREATE ROLE memory_app_login LOGIN NOINHERIT NOBYPASSRLS
      NOCREATEDB NOCREATEROLE NOSUPERUSER NOREPLICATION;
  EXCEPTION
    WHEN duplicate_object OR unique_violation THEN NULL;
  END;
  -- Re-assert on every apply: an operator who loosened the role by hand gets
  -- it tightened again rather than keeping a quiet privilege escalation.
  ALTER ROLE memory_app_login LOGIN NOINHERIT NOBYPASSRLS
    NOCREATEDB NOCREATEROLE NOSUPERUSER NOREPLICATION;
END
$login_role$;

-- Membership is what SET ROLE checks. With NOINHERIT it conveys no privilege
-- by itself, so an un-scoped connection can still read nothing.
GRANT memory_api_runtime TO memory_app_login;
GRANT memory_worker_runtime TO memory_app_login;
GRANT memory_deletion_runtime TO memory_app_login;
GRANT memory_auth_runtime TO memory_app_login;

-- Explicitly not granted: memory_migration_owner. The application principal
-- must never be able to become the owner of the tables and policies that
-- constrain it. The revoke is conditional only to keep a clean apply; the
-- point is that an operator who granted it by hand loses it again here.
DO $owner_membership$
BEGIN
  IF pg_has_role('memory_app_login', 'memory_migration_owner', 'MEMBER') THEN
    REVOKE memory_migration_owner FROM memory_app_login;
  END IF;
END
$owner_membership$;

REVOKE ALL ON SCHEMA memory_os FROM memory_app_login;
REVOKE ALL ON ALL TABLES IN SCHEMA memory_os FROM memory_app_login;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA memory_os FROM memory_app_login;

-- PUBLIC keeps CREATE on the public schema in older clusters; a login
-- principal with no legitimate need to create objects should not have it.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

DO $connect$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO memory_app_login', current_database());
END
$connect$;

COMMIT;
