# Supplemental OPS learning — writer mid-read parent swaps and writable parents (2026-11-02)

Append-only learning under `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. It is not production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, generation/objective, reviewed-request, request-bound recovery, typed eight-domain non-resurrection, independent review, final candidate or human-promotion evidence.

## Material failure class

- **symptom:** Existing recovery-objective and generation-evidence pinned writer tests proved only after-capture pathname swaps; they did not independently exercise a parent swap during an owned-FD source read, nor reject a group/other-writable parent in the synthetic harness. This is a verified negative-proof coverage gap, not an observed production failure.
- **evidence:** Before [9d0dba8b](https://github.com/m-shogo/memories-project/commit/9d0dba8b947a33548f27ef52da8ff2e29b66a1e1), the two `prove_pinned_writer_import` functions had positive source and after-capture swap controls but no `os.read` interception to trigger a mid-read parent rename/symlink substitution and no writable-parent mode case.
- **rootCauseOrUnknown:** Verified missing synthetic coverage of parent metadata validation during source acquisition; whether a real concurrent parent swap or writable parent was present on any CI runner is unknown.
- **failedApproach:** Treating an after-capture-only swap negative as sufficient proof for the earlier read/identity-check interval.
- **correction:** [9d0dba8b](https://github.com/m-shogo/memories-project/commit/9d0dba8b947a33548f27ef52da8ff2e29b66a1e1) adds writable writer leaf/parent controls and intercepts the first owned-FD `os.read` to rename the original parent and substitute a redirected symlink. Both loaders must reject before source acceptance, then pass a positive control after the original parent is restored.
- **recurrenceGuard:** CI-reachable recovery-objective and generation-evidence reconcile negative suites now independently assert writable-parent rejection, mid-read parent-swap rejection, exercised swap injection, restored source identity and after-capture canary non-execution.
- **retryCondition:** Revalidate if the pinned writer source reader, parent metadata check, fixture lifecycle or CI entrypoint changes. Do not retry unchanged Quay MinIO HTTP 401, workflow-write permission or human approval blockers.

## Material success

- **outcome:** Exact-source [Recovery Objectives Reconcile Negative #41372939556](https://github.com/m-shogo/memories-project/actions/runs/41372939556) and [Generation Evidence Reconcile Negative #41372939555](https://github.com/m-shogo/memories-project/actions/runs/41372939555) completed **SUCCESS** on `9d0dba8b`. Their logs explicitly show `PASS reject: mid-read objective writer parent swap`, `PASS reject: mid-read generation writer parent swap`, and both reconcile negative suites PASS. [Recovery Objectives Admission #41372939637](https://github.com/m-shogo/memories-project/actions/runs/41372939637) also completed SUCCESS.
- **evidence:** Observed exact-source GitHub Actions run conclusions and negative-job logs. These are synthetic tests, not production backup/restore or readiness evidence.
- **whySafe:** Only two existing read-only negative harness scripts changed. No production registry, approved objective, reviewed request, request-bound recovery evidence, typed non-resurrection, credential, traffic or promotion authority was changed.
- **reusableMechanism:** Test both sides of a source-capture boundary: mutate the parent during the pinned read to prove metadata revalidation and after the capture to prove execution uses immutable bytes. Require a restored positive control and no canary execution.
- **protectedAuthorityCheck:** Protected Production Status `d677a1c9` remains `NO_GO`; OPS-P0-007 snapshot `dbaa36b0` remains `PREREQUISITES_BLOCKED`; generation registry `bfd1b045`, objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, binding contract `cf965325`, evidence contract `57e5e7e5`, objectives admission contract `be0b4604`, typed non-resurrection registry `26bb1cc7`, promotion registry `99cb895f`, and learning contract `87712ea9` remain unchanged. Registered and semantically eligible unsuperseded generations remain distinct, current human-approved objective and executable reviewed request remain required, final candidates require complete typed eight-domain coverage and independent review, and human production promotion is separate and non-automatic.

## Next safe target

Close the generation-evidence reconciler's remaining reviewed post-validator subprocess pathname reopen by reusing pinned source and a CI-reachable exact-bootstrap/stdin negative, without weakening reviewed label/path allowlists.
