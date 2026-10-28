# Supplemental OPS learning — lease diagnostic publisher permission correction (2026-10-29)

Append-only supplemental learning only; not canonical learning, production/backup/restore/RPO/RTO/skew evidence, reviewed drill authority, credentials, traffic, readiness or human promotion.

## Material failure
- **Symptom:** [Deletion Lease Recovery Diagnostic Source Negative #40743778652](https://github.com/m-shogo/memories-project/actions/runs/40743778652) FAILED on exact source `70e10b4e`; the independent CI reached the new validator and raised `AssertionError: lease-diagnostic publisher permission leaf shadow drift`.
- **Observed evidence:** The CI log shows checkout and exact clean source steps SUCCESS, then failure in `validate_yaml_root_permission`. The reviewed publisher `.github/workflows/deletion-lease-recovery.yml` has root `permissions: contents: write` (Git blob `12129252904c15d5a9c335fd0b529319d1f0b71a`), while the independent source-negative workflow has `contents: read` (Git blob `f76d9a92924355358d005d5b49c73d30c4be4b3b`).
- **Verified root cause:** The new semantic guard incorrectly assumed both workflows had read-only root permission; the reviewed publisher is an existing writer authority. This is a test-fixture assumption error, not an authorization to reduce publisher write permissions or promote production.
- **Failed approach:** Reusing the sibling read-only workflow `contents: read` expected leaf and negative fixture for a publisher with a different reviewed permission.
- **Correction:** [9fe847a3](https://github.com/m-shogo/memories-project/commit/9fe847a3829196b215691c46feacee10d85cb3d3) pins `contents: write` for the publisher and `contents: read` for independent CI, and chooses the opposite leaf for each shadow mutation. Adds direct permission replacement negatives for both workflows (14 total), without editing either workflow.
- **Executable recurrence guard:** A pre-write exact target-source permission inventory check must establish each workflow's reviewed root leaf independently; the corrected validator now asserts both distinct leaves and 14 exact-diagnostic negative mutations.
- **Retry condition:** Retry exact-source CI only for corrected code `9fe847a3` or on changed reviewed permission topology; do not rerun the known failing `70e10b4e` unchanged.

## Material success / protected authority
- **Observed outcome/evidence:** GitHub compare `ba8d4a98...9fe847a3` shows only the CI-reachable read-only validator changed (+12/-9). [Corrected exact-source CI #40743921290](https://github.com/m-shogo/memories-project/actions/runs/40743921290) was QUEUED when observed; SUCCESS is not claimed yet.
- **Why safe:** The correction matches existing publisher write authority without changing permissions, workflow files, production evidence, credentials, traffic or promotion. The independent CI remains read-only.
- **Reusable mechanism:** Derive semantic negative fixture expectations from the specific reviewed publisher and independent workflow rather than assuming a common permission value.
- **Protected-authority check:** Eleven protected production/OPS-P0-007/registry/learning-contract/canonical-learning blob SHAs unchanged. `productionDecision=NO_GO`; OPS-P0-007=`PREREQUISITES_BLOCKED`; registered/semantically eligible generations, approved objectives, executable reviewed requests, generation evidence, typed eight-domain records and final candidates remain zero. Human promotion remains separate/non-automatic.
- **Next safe target:** Verify corrected CI, then audit SIGKILL and pre-fence diagnostic source-negative workflows with explicit per-workflow permission inventory.
