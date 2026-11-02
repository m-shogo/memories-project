# Supplemental OPS learning — original-source SHA provenance guard, indentation failure (2026-11-02)

Append-only subordinate to `docs/operations/AUTONOMOUS-OPS-LEARNING.md` and mandatory `contracts/operations/autonomous-learning-system.json`. This synthetic, read-only learning is **not** production, backup/restore, RPO/RTO/skew, drill, credential, traffic, readiness, environment generation, recovery objective, executable reviewed drill request, request-bound recovery evidence, typed eight-domain non-resurrection coverage, independent review, final recovery candidate, or human production promotion.

## Material failures

- **symptom:** The new original-source SHA provenance negative incorrectly rejected the unchanged, reviewed saturation publisher step. The first exact-source CI failed.
- **observed evidence:** [Autonomous Learning Guard #41451915606](https://github.com/m-shogo/memories-project/actions/runs/41451915606) completed **FAILURE** at `prove_saturation_source_sha_provenance`, reporting `saturation source SHA provenance drift`. Workflow source blob `1f4b20c0` has the `git pull --rebase origin so` and following `verify_critical_source` nested at **12 spaces**, not the 10-space top-level shell indentation.
- **verified root cause:** The initial [`7f562275`](https://github.com/m-shogo/memories-project/commit/7f5622759705088d2095ce56444c706615d644b4) fixture assumed the wrong nested indentation. Its lexical source boundary could not match the real reviewed step.
- **failed approach:** Treating a visually indented workflow shell snippet as an exact string without first counting the actual leading spaces.
- **correction:** [`f75785d1`](https://github.com/m-shogo/memories-project/commit/f75785d116e54f3f992dde3e73030ae0c714ba67) corrected the nested `git pull` and `verify_critical_source` binding.
- **recurrence guard:** A second local exact-source check found that `value.count("          verify_critical_source\\n")` also counts a 12-space line as a 10-space substring. [`7157d6db`](https://github.com/m-shogo/memories-project/commit/7157d6dbe790f63a975113fa0444641834e047f9) uses exact `splitlines()` / `lines.count(...)` comparisons instead. A source-derived JavaScript equivalent accepted the unmodified publisher and rejected eight tested SHA-rebinding/guard-removal mutants. This is **local diagnostic validation**, not a claim of exact-source CI success.
- **retry condition:** Revisit if the corrected exact-source CI fails, the publisher step indentation/control flow changes, or a new assignment bypass is demonstrated. Never repeat the 10-space post-rebase assumption or substring-based indentation counting without a changed precondition.

## Material safe progress

- **outcome:** Three scoped code commits added and corrected the source-SHA provenance negative; the last commit is `7157d6db`. The corrected CI was in progress when this record was written.
- **evidence:** Current `so` source re-read confirmed the original `source_sha="${GITHUB_SHA}"` assignment, exactly one original binding, both guard invocations, the nested rebase adjacency, and mutation controls for HEAD/remote-tip substitution, empty source, late assignment, GitHub SHA overwrite, append, unset, read, eval, and removed post-rebase guard.
- **why safe:** Only `scripts/validate-autonomous-learning-system-negative.py` was modified. No write-capable workflow or publisher was edited or invoked; no real remote Git publication, production evidence, credential, traffic, readiness, or promotion was attempted.
- **reusable mechanism:** Bind a shell guard's compared SHA to its original workflow source, test rebinding mutations, and compare complete shell lines rather than indentation-overlapping substrings.
- **protected-authority check:** After each code change, all ten protected blob SHAs were unchanged: production status `d677a1c9` (`NO_GO`), OPS-P0-007 snapshot `dbaa36b0` (`PREREQUISITES_BLOCKED`), environment generations `bfd1b045`, recovery objectives `f4d74f33`, drill requests `acebcd02`, generation evidence `ae7e57ef`, typed non-resurrection `26bb1cc7`, promotion review `99cb895f`, canonical learning `b809c69d`, mandatory contract `87712ea9`.

## Next safe target

Confirm corrected exact-source read-only CI, then audit the three separately blocked soak publishers' post-rebase source leases without changing write-capable workflows or reusing an unchanged permission blocker. Maintain `productionDecision=NO_GO` and separate human promotion review.
