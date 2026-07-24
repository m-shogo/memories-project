\set ON_ERROR_STOP on

-- Apple identity binding, replay store and deletion coverage.

TRUNCATE TABLE
  memory_os.apple_identity, memory_os.apple_replay,
  memory_os.memory_item, memory_os.apply_confirmation,
  memory_os.preview_candidate, memory_os.preview_rejection, memory_os.preview_ready,
  memory_os.quarantine_object, memory_os.upload_authorization, memory_os.import_job,
  memory_os.account_session, memory_os.account_control;

GRANT USAGE ON SCHEMA memory_os_test TO memory_auth_runtime;
GRANT EXECUTE ON FUNCTION memory_os_test.expect_failure(text, text) TO memory_auth_runtime;
GRANT EXECUTE ON FUNCTION memory_os_test.expect_insufficient_privilege(text, text) TO memory_auth_runtime;
GRANT EXECUTE ON FUNCTION memory_os_test.assert_true(boolean, text) TO memory_auth_runtime;

-- No runtime role may touch either table directly; everything goes through the
-- definer functions.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT count(*) FROM memory_os.apple_identity$$,
  'auth role reading apple_identity directly');
SELECT memory_os_test.expect_insufficient_privilege(
  $$SELECT count(*) FROM memory_os.apple_replay$$,
  'auth role reading apple_replay directly');
ROLLBACK;

-- First login creates one active account at epoch 0.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
DO $first$
DECLARE
  provisioned record;
BEGIN
  SELECT * INTO provisioned FROM memory_os.provision_apple_identity(
    'https://appleid.apple.com', 'apple-subject-0001', 'acct_appleprov00000001');
  IF NOT provisioned.created OR provisioned.account_id <> 'acct_appleprov00000001'
     OR provisioned.account_epoch <> 0 THEN
    RAISE EXCEPTION 'first login gave %', provisioned;
  END IF;
END
$first$;
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT state = 'active' AND account_epoch = 0
   FROM memory_os.account_control WHERE account_id = 'acct_appleprov00000001'),
  'first login must leave an active account at epoch 0');

-- Returning login resolves the same account and never creates a second one, and
-- a different candidate id is ignored rather than redirecting the binding.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
DO $returning$
DECLARE
  provisioned record;
BEGIN
  SELECT * INTO provisioned FROM memory_os.provision_apple_identity(
    'https://appleid.apple.com', 'apple-subject-0001', 'acct_differentcandidate1');
  IF provisioned.created OR provisioned.account_id <> 'acct_appleprov00000001' THEN
    RAISE EXCEPTION 'returning login gave %', provisioned;
  END IF;
END
$returning$;
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.account_control),
  'a returning login must not create a second account');
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.apple_identity),
  'a returning login must not create a second identity');

-- A different Apple subject is a different account.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
DO $second$
DECLARE
  provisioned record;
BEGIN
  SELECT * INTO provisioned FROM memory_os.provision_apple_identity(
    'https://appleid.apple.com', 'apple-subject-0002', 'acct_appleprov00000002');
  IF NOT provisioned.created OR provisioned.account_id <> 'acct_appleprov00000002' THEN
    RAISE EXCEPTION 'second subject gave %', provisioned;
  END IF;
END
$second$;
COMMIT;

-- The replay guard consumes a nonce and a code once; either reused is rejected.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os.consume_apple_replay(repeat('a', 64), repeat('b', 64), 600);
COMMIT;

BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os_test.expect_failure(
  $$SELECT memory_os.consume_apple_replay(repeat('a', 64), repeat('c', 64), 600)$$,
  'reused nonce must be rejected');
SELECT memory_os_test.expect_failure(
  $$SELECT memory_os.consume_apple_replay(repeat('d', 64), repeat('b', 64), 600)$$,
  'reused code must be rejected');
ROLLBACK;

-- A fresh nonce and code still pass, proving the rejection above was specific.
BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os.consume_apple_replay(repeat('e', 64), repeat('f', 64), 600);
COMMIT;

-- Deletion refuses to revive: mark the first account deleting, and a returning
-- login is refused rather than resurrecting it.
BEGIN;
SET LOCAL ROLE memory_api_runtime;
SELECT set_config('app.current_account_id', 'acct_appleprov00000001', true);
SELECT set_config('app.current_account_epoch', '0', true);
SELECT memory_os.begin_account_deletion();
COMMIT;

BEGIN;
SET LOCAL ROLE memory_auth_runtime;
SELECT memory_os_test.expect_failure(
  $$SELECT * FROM memory_os.provision_apple_identity(
      'https://appleid.apple.com', 'apple-subject-0001', 'acct_wouldrevive00000001')$$,
  'a deleting account must not be revived by sign-in');
ROLLBACK;

-- The deletion sweep erases the Apple identity binding along with everything
-- else, and reports it in its accounting.
BEGIN;
SET LOCAL ROLE memory_deletion_runtime;
SELECT set_config('app.current_account_id', 'acct_appleprov00000001', true);
SELECT set_config('app.current_account_epoch', '1', true);
DO $sweep$
DECLARE
  swept record;
  identity_removed bigint := -1;
BEGIN
  FOR swept IN SELECT * FROM memory_os.sweep_deleted_account()
  LOOP
    IF swept.table_name = 'apple_identity' THEN identity_removed := swept.removed; END IF;
  END LOOP;
  IF identity_removed <> 1 THEN
    RAISE EXCEPTION 'sweep removed % apple_identity rows, expected 1', identity_removed;
  END IF;
END
$sweep$;
COMMIT;

SELECT memory_os_test.assert_true(
  (SELECT count(*) = 0 FROM memory_os.apple_identity WHERE account_id = 'acct_appleprov00000001'),
  'the deleted account must keep no Apple identity binding');

-- The second account's identity is untouched by the first account's deletion.
SELECT memory_os_test.assert_true(
  (SELECT count(*) = 1 FROM memory_os.apple_identity WHERE account_id = 'acct_appleprov00000002'),
  'another account''s identity must survive');

SELECT 'Memory OS Apple identity binding tests PASS' AS result;
