-- Memory OS Round 9 deletion fencing completion.
-- Apply after 005_memory_os_apply_memory.sql.
--
-- Migration 002_memory_os_account_control.sql introduced the canonical
-- account_control row, the account_epoch_is_authorized() predicate and the
-- deletion epoch bump, and reinforced every table that existed at that time.
-- The Preview domain (003) and Apply/Memory persistence (005) landed later,
-- so their policies never carried the predicate: an account whose epoch had
-- been bumped for deletion could still reach committed Previews and applied
-- memory items. This migration closes that gap and adds the sweep the
-- deletion runtime uses to erase fenced data.

BEGIN;

CREATE OR REPLACE FUNCTION memory_os._reinforce_owner_policy(target_table regclass)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  relation_name text;
  predicate text;
  policy_name text;
  policy_kind text;
BEGIN
  SELECT relation.relname INTO STRICT relation_name
  FROM pg_class AS relation WHERE relation.oid = target_table;

  predicate := '(owner_account_id = memory_os.current_account_id()'
    || ' AND account_epoch = memory_os.current_account_epoch()'
    || ' AND memory_os.account_epoch_is_authorized())';

  FOREACH policy_kind IN ARRAY ARRAY['select', 'insert', 'update', 'delete']
  LOOP
    policy_name := relation_name || '_tenant_' || policy_kind;
    IF NOT EXISTS (
      SELECT 1 FROM pg_policy WHERE polrelid = target_table AND polname = policy_name
    ) THEN
      CONTINUE;
    END IF;
    IF policy_kind = 'insert' THEN
      EXECUTE format('ALTER POLICY %I ON %s WITH CHECK %s', policy_name, target_table, predicate);
    ELSIF policy_kind = 'update' THEN
      EXECUTE format('ALTER POLICY %I ON %s USING %s WITH CHECK %s',
                     policy_name, target_table, predicate, predicate);
    ELSE
      EXECUTE format('ALTER POLICY %I ON %s USING %s', policy_name, target_table, predicate);
    END IF;
  END LOOP;
END
$function$;

ALTER FUNCTION memory_os._reinforce_owner_policy(regclass) OWNER TO memory_migration_owner;

SELECT memory_os._reinforce_owner_policy('memory_os.preview_ready'::regclass);
SELECT memory_os._reinforce_owner_policy('memory_os.preview_candidate'::regclass);
SELECT memory_os._reinforce_owner_policy('memory_os.preview_rejection'::regclass);
SELECT memory_os._reinforce_owner_policy('memory_os.memory_item'::regclass);

DROP FUNCTION memory_os._reinforce_owner_policy(regclass);

-- FINDING: the tenant policy requires row.account_epoch = current epoch, but a
-- deletion bump moves the account to a NEW epoch while every existing row keeps
-- the OLD one. The deletion runtime therefore could not see a single row it was
-- supposed to erase — a sweep would silently remove nothing. (The pre-existing
-- account_control test asserted "count = 0 after delete", which passed only
-- because the rows were invisible, not because they were deleted.)
--
-- deletion_sweep_authorized() closes that gap without widening tenant access:
-- it is true only for the deletion runtime, only while the account is in state
-- 'deleting', and the policies below still require owner_account_id to match.
-- Row epoch is deliberately not compared, because erasing an account means
-- erasing every epoch it ever wrote.
CREATE OR REPLACE FUNCTION memory_os.deletion_sweep_authorized()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY INVOKER
PARALLEL UNSAFE
SET search_path = pg_catalog, memory_os
AS $function$
  SELECT current_user = 'memory_deletion_runtime'
    AND EXISTS (
      SELECT 1 FROM memory_os.account_control AS account
      WHERE account.account_id = memory_os.current_account_id()
        AND account.state = 'deleting'
    )
$function$;

ALTER FUNCTION memory_os.deletion_sweep_authorized() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.deletion_sweep_authorized() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.deletion_sweep_authorized() TO memory_deletion_runtime;

GRANT DELETE ON TABLE
  memory_os.memory_item,
  memory_os.apply_confirmation,
  memory_os.preview_candidate,
  memory_os.preview_rejection,
  memory_os.preview_ready,
  memory_os.upload_authorization,
  memory_os.quarantine_object,
  memory_os.import_job
TO memory_deletion_runtime;

DO $policies$
DECLARE
  table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'memory_item', 'apply_confirmation', 'preview_candidate', 'preview_rejection',
    'preview_ready', 'upload_authorization', 'quarantine_object', 'import_job'
  ]
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON memory_os.%I',
                   table_name || '_deletion_sweep', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON memory_os.%I AS PERMISSIVE FOR DELETE TO memory_deletion_runtime'
      ' USING (owner_account_id = memory_os.current_account_id()'
      ' AND memory_os.deletion_sweep_authorized())',
      table_name || '_deletion_sweep', table_name);
    -- The sweep also needs to see the rows it deletes.
    EXECUTE format('GRANT SELECT ON TABLE memory_os.%I TO memory_deletion_runtime', table_name);
    EXECUTE format('DROP POLICY IF EXISTS %I ON memory_os.%I',
                   table_name || '_deletion_sweep_select', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON memory_os.%I AS PERMISSIVE FOR SELECT TO memory_deletion_runtime'
      ' USING (owner_account_id = memory_os.current_account_id()'
      ' AND memory_os.deletion_sweep_authorized())',
      table_name || '_deletion_sweep_select', table_name);
  END LOOP;
END
$policies$;

-- account_session (004) is deliberately unreachable by table grants: the auth
-- runtime touches it only through SECURITY DEFINER functions. Erasure keeps
-- that invariant instead of breaking it with a DELETE grant, so the sweep goes
-- through a definer function that is itself gated on deletion_sweep_authorized().
CREATE OR REPLACE FUNCTION memory_os.purge_account_sessions()
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  removed_count bigint;
BEGIN
  -- deletion_sweep_authorized() cannot be reused here: inside a SECURITY
  -- DEFINER body current_user is the function owner, so its role test would
  -- never hold. The role half is enforced by the EXECUTE grant below (only
  -- memory_deletion_runtime has it); the state half is re-checked here so an
  -- authorized runtime still cannot purge sessions of a live account.
  IF NOT EXISTS (
    SELECT 1 FROM memory_os.account_control AS account
    WHERE account.account_id = memory_os.current_account_id()
      AND account.state = 'deleting'
  ) THEN
    RAISE EXCEPTION 'session purge requires an account in deleting state'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  DELETE FROM memory_os.account_session
  WHERE owner_account_id = memory_os.current_account_id();
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  RETURN removed_count;
END
$function$;

ALTER FUNCTION memory_os.purge_account_sessions() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.purge_account_sessions() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.purge_account_sessions() TO memory_deletion_runtime;

-- sweep_deleted_account erases every owned row for the account currently in
-- context. It is SECURITY INVOKER on purpose: the deletion-sweep policies above
-- still scope every DELETE to this owner and require state='deleting', so the
-- sweep can never reach another tenant or run against a live account.
CREATE OR REPLACE FUNCTION memory_os.sweep_deleted_account()
RETURNS TABLE (table_name text, removed bigint)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, memory_os
AS $function$
DECLARE
  removed_count bigint;
BEGIN
  IF memory_os.current_account_id() IS NULL OR memory_os.current_account_epoch() IS NULL THEN
    RAISE EXCEPTION 'verified account and epoch context are required'
      USING ERRCODE = 'insufficient_privilege';
  END IF;

  DELETE FROM memory_os.memory_item;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'memory_item'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.preview_candidate;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'preview_candidate'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.preview_rejection;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'preview_rejection'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.preview_ready;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'preview_ready'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.apply_confirmation;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'apply_confirmation'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.quarantine_object;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'quarantine_object'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.upload_authorization;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'upload_authorization'; removed := removed_count; RETURN NEXT;

  DELETE FROM memory_os.import_job;
  GET DIAGNOSTICS removed_count = ROW_COUNT;
  table_name := 'import_job'; removed := removed_count; RETURN NEXT;

  table_name := 'account_session';
  removed := memory_os.purge_account_sessions();
  RETURN NEXT;

  RETURN;
END
$function$;

ALTER FUNCTION memory_os.sweep_deleted_account() OWNER TO memory_migration_owner;
REVOKE ALL ON FUNCTION memory_os.sweep_deleted_account() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION memory_os.sweep_deleted_account() TO memory_deletion_runtime;

COMMIT;
