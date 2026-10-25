#!/usr/bin/env python3
"""Prove strict OPS-P0-007 snapshot PR validation is read-only and publication remains source-bound."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import stat
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot-pr.yml"
PUBLISH_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot.yml"

READONLY_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot-readonly.yml"
SNAPSHOT_PERMISSION_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-snapshot-permission-boundary.yml"
REVIEWED_SNAPSHOT_PERMISSION_WORKFLOW_BLOB_SHA = "5f29fdb29280b9e9b46c65c703d6cefa6fee643a"
READONLY_SOURCE_REF = "${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}"


READONLY_HASH_LINE = "printf '%s\\t%s\\t%s\\n' \"$authority\" \"$(sha256sum \"$authority\" | cut -d' ' -f1)\" \"$(stat -c '%a' \"$authority\")\""
READONLY_PROTECTED_AUTHORITIES = (
    "contracts/operations/ops-p0-007-admission-snapshot.v1.json",
    "contracts/operations/operability-admission-inventory.v1.json",
    "contracts/operations/production-operability-status.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/backup-restore-promotion-review-registry.v1.json",
)


FULL_ADMISSION_VALIDATORS = (
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
)

PUBLISH_REVALIDATION_CHAIN = (
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
    "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-negative.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-validator-authority-negative.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-generator-execution-authority-negative.py",
)

# GitHub's write-capable token scopes are not limited to contents:write.
# The snapshot PR job must remain read-only across every recognized scope.
REQUIRED_PR_ADMISSION_CONTRACTS = (
    "production-equivalent-environment-generation-contract.v1.json",
    "production-equivalent-environment-generation-registry.v1.json",
    "production-equivalent-environment-record.v1.schema.json",
    "production-equivalent-environment-generation-record.v1.schema.json",
    "production-equivalent-environment-eligibility-contract.v1.json",
    "recovery-objectives-admission-contract.v1.json",
    "recovery-objectives-registry.v1.json",
    "backup-restore-drill-request-contract.v1.json",
    "backup-restore-drill-request-registry.v1.json",
    "backup-restore-generation-evidence-contract.v1.json",
    "backup-restore-generation-evidence-registry.v1.json",
    "backup-restore-non-resurrection-admission-contract.v1.json",
    "backup-restore-non-resurrection-admission-registry.v1.json",
)


# The reviewed PR compile stage is an executable command boundary, not a
# textual occurrence of py_compile or a substitute for runtime admission.
PR_COMPILE_FILES = (
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
    "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-negative.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-validator-authority-negative.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-generator-execution-authority-negative.py",
    "scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py",
)

GITHUB_PERMISSION_SCOPES = (
    "actions", "attestations", "checks", "contents", "deployments",
    "discussions", "id-token", "issues", "models", "packages", "pages",
    "pull-requests", "repository-projects", "security-events", "statuses",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_canonical_workflow(path: Path, relative: Path, root: Path = ROOT) -> None:
    try:
        lexical = path.relative_to(root)
        resolved = path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"strict snapshot workflow missing or escapes canonical root: {relative}") from exc
    require(
        lexical == relative and resolved == relative and path.is_file() and not path.is_symlink(),
        f"strict snapshot workflow path drift: {relative}",
    )


def prove_symlink_rejected() -> None:
    # Isolated outside the checkout: this proof cannot dirty source-bound CI.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-workflow-path-negative-") as tmp:
        root = Path(tmp)
        target = root / "target.yml"
        alias = root / "alias.yml"
        target.write_text("permissions: contents: read\n", encoding="utf-8")
        alias.symlink_to(target.name)
        require_canonical_workflow(target, Path("target.yml"), root)
        try:
            require_canonical_workflow(alias, Path("alias.yml"), root)
        except Fail as exc:
            require("workflow path drift" in str(exc), f"symlink rejected outside intended path guard: {exc}")
        else:
            raise Fail("strict snapshot workflow symlink alias unexpectedly accepted")



def executable_diagnostic_calls(publish: str) -> tuple[dict[str, ast.Call], list[ast.AST]]:
    # Only the live Python heredoc in the publisher counts. Comments, strings,
    # function definitions, and statically dead branches are not call-site proof.
    match = re.search(r"(?ms)^[ \t]*python[ \t]+-[ \t]*<<'PY'[ \t]*\n(.*?)^[ \t]*PY[ \t]*$", publish)
    require(match is not None, "strict snapshot diagnostic executable Python heredoc missing")
    try:
        tree = ast.parse(textwrap.dedent(match.group(1)))
    except SyntaxError as exc:
        raise Fail(f"strict snapshot diagnostic Python heredoc invalid: {exc}") from exc

    # Evaluate only literal boolean expressions, never arbitrary Python code.
    # A constant-true comparison is as unconditional as a literal True.
    def static_truth(test: ast.AST) -> bool | None:
        if isinstance(test, ast.Constant):
            return bool(test.value)
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            value = static_truth(test.operand)
            return None if value is None else not value
        if (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.left, ast.Constant)
            and isinstance(test.comparators[0], ast.Constant)
        ):
            left, right = test.left.value, test.comparators[0].value
            if isinstance(test.ops[0], ast.Eq):
                return left == right
            if isinstance(test.ops[0], ast.NotEq):
                return left != right
        if isinstance(test, ast.BoolOp):
            values = [static_truth(value) for value in test.values]
            if isinstance(test.op, ast.And):
                if False in values:
                    return False
                if all(value is True for value in values):
                    return True
            if isinstance(test.op, ast.Or):
                if True in values:
                    return True
                if all(value is False for value in values):
                    return False
        return None

    # AST call presence is not proof if the publication heredoc exits
    # unconditionally before reaching its atomic write. Inspect only
    # unconditionally entered statement bodies; exception handlers remain
    # legitimate conditional failure paths.
    def reject_unconditional_termination(statements: list[ast.stmt]) -> None:
        for statement in statements:
            if isinstance(statement, ast.Raise):
                raise Fail("strict snapshot diagnostic unconditional early termination")
            if isinstance(statement, ast.While) and static_truth(statement.test) is True:
                # An unconditional loop can prevent replacement/cleanup even
                # without a syntactically explicit raise or exit.
                raise Fail("strict snapshot diagnostic unconditional early termination")
            if (
                isinstance(statement, ast.Assert)
                and isinstance(statement.test, ast.Constant)
                and not bool(statement.test.value)
            ):
                raise Fail("strict snapshot diagnostic unconditional early termination")
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                target = statement.value.func
                is_exit = (
                    isinstance(target, ast.Name) and target.id in ("exit", "quit")
                ) or (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and (target.value.id, target.attr) in (("sys", "exit"), ("os", "_exit"))
                )
                if is_exit:
                    raise Fail("strict snapshot diagnostic unconditional early termination")
            if isinstance(statement, (ast.With, ast.AsyncWith, ast.Try)):
                reject_unconditional_termination(statement.body)
            if isinstance(statement, ast.Try):
                # finally runs even after a successful atomic replacement.
                # A termination here can skip the required cleanup call.
                reject_unconditional_termination(statement.finalbody)
            if isinstance(statement, ast.If) and static_truth(statement.test) is not None:
                reject_unconditional_termination(
                    statement.body if static_truth(statement.test) else statement.orelse
                )

    reject_unconditional_termination(tree.body)

    def live(node: ast.AST):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(node, ast.If) and static_truth(node.test) is not None:
            yield node
            for child in (node.body if static_truth(node.test) else node.orelse):
                yield from live(child)
            return
        yield node
        for child in ast.iter_child_nodes(node):
            yield from live(child)

    nodes = list(live(tree))
    # Diagnostic records are explicitly non-production metadata. A valid
    # atomic write cannot authorize fabricated evidence or unbounded logs.
    values = [
        node.value for node in nodes
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "value"
    ]
    require(
        len(values) == 1 and isinstance(values[0], ast.Dict),
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    record = values[0]
    require(
        all(isinstance(key, ast.Constant) and isinstance(key.value, str) for key in record.keys),
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    fields = {key.value: value for key, value in zip(record.keys, record.values)}
    require(
        len(fields) == len(record.keys),
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    literals = {
        "schemaVersion": "memory-os-validator-diagnostic.v1",
        "workflow": "ops-p0-007-admission-snapshot",
        "result": "FAIL",
        "containsSecrets": False,
        "generationCreated": False,
        "objectiveCreated": False,
        "requestCreated": False,
        "restoreExecuted": False,
        "productionEvidence": False,
        "productionReady": False,
    }
    require(
        set(fields) == set(literals) | {"sourceCommitSha", "exitCode", "output"}
        and all(
            isinstance(fields[key], ast.Constant)
            and type(fields[key].value) is type(expected)
            and fields[key].value == expected
            for key, expected in literals.items()
        ),
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    expressions = {
        "sourceCommitSha": "os.environ['SOURCE_SHA']",
        "exitCode": "int(os.environ['SNAPSHOT_EXIT_CODE'])",
        "output": "'REDACTED: strict OPS-P0-007 snapshot validation failed; raw output withheld'",
    }
    require(
        all(
            ast.dump(fields[key], include_attributes=False)
            == ast.dump(ast.parse(expression, mode="eval").body, include_attributes=False)
            for key, expression in expressions.items()
        ),
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    path_expression = ast.parse(
        "path = Path('docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json')"
    ).body[0]
    require(
        sum(
            isinstance(node, ast.Assign)
            and ast.dump(node, include_attributes=False)
            == ast.dump(path_expression, include_attributes=False)
            for node in nodes
        ) == 1,
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    # Preserve the complete record through serialization. Valid initial
    # fields are insufficient if later statements rewrite value or payload.
    payload_assignment = ast.parse(
        "payload = (json.dumps(value, indent=2) + '\\n').encode('utf-8')"
    ).body[0]
    payload_writes = [
        node for node in nodes
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "payload" for target in node.targets)
    ]
    require(
        len(payload_writes) == 1
        and ast.dump(payload_writes[0], include_attributes=False)
        == ast.dump(payload_assignment, include_attributes=False),
        "strict snapshot diagnostic non-production evidence boundary drift",
    )
    def touches_record(target: ast.AST) -> bool:
        if isinstance(target, ast.Name):
            return target.id in ("value", "payload")
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            return touches_record(target.value)
        if isinstance(target, (ast.Tuple, ast.List)):
            return any(touches_record(item) for item in target.elts)
        return False

    for node in nodes:
        if isinstance(node, ast.Assign):
            if node in payload_writes or (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "value"
                and node.value is record
            ):
                continue
            require(
                not any(touches_record(target) for target in node.targets),
                "strict snapshot diagnostic non-production evidence boundary drift",
            )
        if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            require(
                not touches_record(node.target),
                "strict snapshot diagnostic non-production evidence boundary drift",
            )
        if isinstance(node, ast.Delete):
            require(
                not any(touches_record(target) for target in node.targets),
                "strict snapshot diagnostic non-production evidence boundary drift",
            )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "value"
            and node.func.attr in ("update", "clear", "pop", "popitem", "setdefault", "__setitem__")
        ):
            raise Fail("strict snapshot diagnostic non-production evidence boundary drift")
    calls = [node for node in nodes if isinstance(node, ast.Call)]
    required = {
        "mkstemp": "tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)",
        "chmod": "os.fchmod(fd, existing_mode)",
        "write": "handle.write(payload)",
        "flush": "handle.flush()",
        "fsync": "os.fsync(handle.fileno())",
        "replace": "os.replace(tmp_name, path)",
        "unlink": "os.unlink(tmp_name)",
    }
    found: dict[str, ast.Call] = {}
    for label, expression in required.items():
        expected = ast.dump(ast.parse(expression, mode="eval").body, include_attributes=False)
        matches = [call for call in calls if ast.dump(call, include_attributes=False) == expected]
        require(len(matches) == 1, f"strict snapshot diagnostic missing executable {label} call or duplicated call")
        found[label] = matches[0]

    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    def enclosing_conditions(call: ast.Call) -> list[ast.AST]:
        conditions: list[ast.AST] = []
        node: ast.AST = call
        while node in parents:
            node = parents[node]
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Match, ast.ExceptHandler)):
                conditions.append(node)
        return conditions

    # Publication calls other than conditional chmod must be unconditionally
    # reached in their enclosing try/with flow. AST walking alone would count
    # a syntactically valid but never-run comparison-dead call.
    for label in ("mkstemp", "write", "flush", "fsync", "replace", "unlink"):
        require(
            not enclosing_conditions(found[label]),
            f"strict snapshot diagnostic executable {label} call hidden in conditional branch",
        )
    mode_guard = ast.dump(ast.parse("existing_mode is not None", mode="eval").body, include_attributes=False)
    chmod_conditions = enclosing_conditions(found["chmod"])
    require(
        len(chmod_conditions) == 1
        and isinstance(chmod_conditions[0], ast.If)
        and ast.dump(chmod_conditions[0].test, include_attributes=False) == mode_guard,
        "strict snapshot diagnostic chmod not bound to existing-mode guard",
    )
    mode_assignment = ast.dump(
        ast.parse("existing_mode = path.stat().st_mode & 0o7777 if path.exists() else None").body[0],
        include_attributes=False,
    )
    require(
        any(isinstance(node, ast.Assign) and ast.dump(node, include_attributes=False) == mode_assignment for node in nodes),
        "strict snapshot diagnostic missing executable existing-mode preservation",
    )
    require(
        found["mkstemp"].lineno < found["chmod"].lineno < found["write"].lineno
        < found["flush"].lineno < found["fsync"].lineno < found["replace"].lineno
        < found["unlink"].lineno,
        "strict snapshot diagnostic executable publication call order drift",
    )
    def has_call(statements: list[ast.stmt], target: ast.Call) -> bool:
        return any(node is target for stmt in statements for node in live(stmt))
    require(
        any(
            isinstance(node, ast.Try)
            and has_call(node.body, found["replace"])
            and has_call(node.finalbody, found["unlink"])
            for node in nodes
        ),
        "strict snapshot diagnostic replace/cleanup not bound to one try/finally",
    )
    return found, nodes


def prove_diagnostic_comment_and_dead_code_rejected(publish: str) -> None:
    validate_atomic_diagnostic_publication(publish)
    mutations = (
        ("comment-only replacement", "os.replace(tmp_name, path)", "# os.replace(tmp_name, path)"),
        ("quoted flush", "handle.flush()", "'handle.flush()'"),
        ("dead fsync", "os.fsync(handle.fileno())", "if False: os.fsync(handle.fileno())"),
        ("comparison-dead fsync", "os.fsync(handle.fileno())", "if 1 == 2: os.fsync(handle.fileno())"),
        ("while-dead fsync", "os.fsync(handle.fileno())", "while False: os.fsync(handle.fileno())"),
        ("empty-for fsync", "os.fsync(handle.fileno())", "for _ in []: os.fsync(handle.fileno())"),
        ("comparison-dead chmod", "os.fchmod(fd, existing_mode)", "if 1 == 2: os.fchmod(fd, existing_mode)"),
        ("comment-only cleanup", "os.unlink(tmp_name)", "pass  # os.unlink(tmp_name)"),
        ("direct-write bypass", "os.replace(tmp_name, path)", "path.write_text('unsafe')  # os.replace(tmp_name, path)"),
    )
    for label, before, after in mutations:
        require(publish.count(before) == 1, f"{label}: expected one canonical mutation site")
        mutated = publish.replace(before, after, 1)
        try:
            validate_atomic_diagnostic_publication(mutated)
        except Fail as exc:
            require(
                "strict snapshot diagnostic" in str(exc),
                f"{label} rejected outside intended diagnostic guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot diagnostic accepted {label}")

def prove_diagnostic_unconditional_exit_rejected(publish: str) -> None:
    validate_atomic_diagnostic_publication(publish)
    mutations = (
        ("module raise", "          import json, os, tempfile",
         "          import json, os, tempfile\n          raise SystemExit(0)"),
        ("module exit", "          import json, os, tempfile",
         "          import json, os, tempfile\n          exit(0)"),
        ("try raise", "              os.replace(tmp_name, path)",
         "              raise SystemExit(0)\n              os.replace(tmp_name, path)"),
        ("try sys exit", "              os.replace(tmp_name, path)",
         "              sys.exit(0)\n              os.replace(tmp_name, path)"),
        ("conditional true raise", "              os.replace(tmp_name, path)",
         "              if True: raise SystemExit(0)\n              os.replace(tmp_name, path)"),
        ("finally raise before cleanup", "                  os.unlink(tmp_name)",
         "                  raise SystemExit(0)\n                  os.unlink(tmp_name)"),
        ("finally exit before cleanup", "                  os.unlink(tmp_name)",
         "                  exit(0)\n                  os.unlink(tmp_name)"),
        ("finally constant-true exit", "                  os.unlink(tmp_name)",
         "                  if True: raise SystemExit(0)\n                  os.unlink(tmp_name)"),
        ("module assert false", "          import json, os, tempfile",
         "          import json, os, tempfile\n          assert False"),
        ("try assert zero", "              os.replace(tmp_name, path)",
         "              assert 0\n              os.replace(tmp_name, path)"),
        ("finally assert false", "                  os.unlink(tmp_name)",
         "                  assert False\n                  os.unlink(tmp_name)"),
        ("comparison-true raise", "              os.replace(tmp_name, path)",
         "              if 1 == 1: raise SystemExit(0)\n              os.replace(tmp_name, path)"),
        ("comparison-true exit", "              os.replace(tmp_name, path)",
         "              if 'a' != 'b': exit(0)\n              os.replace(tmp_name, path)"),
        ("negated-false assert", "              os.replace(tmp_name, path)",
         "              if not False: assert False\n              os.replace(tmp_name, path)"),
        ("boolean-true raise", "              os.replace(tmp_name, path)",
         "              if True and True: raise SystemExit(0)\n              os.replace(tmp_name, path)"),
        ("unbounded while true", "              os.replace(tmp_name, path)",
         "              while True: pass\n              os.replace(tmp_name, path)"),
        ("comparison-true while cleanup", "                  os.unlink(tmp_name)",
         "                  while 1 == 1: pass\n                  os.unlink(tmp_name)"),
        ("short-circuit true raise", "              os.replace(tmp_name, path)",
         "              if True or runtime_unknown: raise SystemExit(0)\n              os.replace(tmp_name, path)"),
        ("short-circuit negated false", "              os.replace(tmp_name, path)",
         "              if not (False and runtime_unknown): raise SystemExit(0)\n              os.replace(tmp_name, path)"),
    )
    for label, before, after in mutations:
        require(publish.count(before) == 1, f"{label}: canonical diagnostic fixture drift")
        mutated = publish.replace(before, after, 1)
        try:
            validate_atomic_diagnostic_publication(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot diagnostic unconditional early termination",
                f"{label} rejected outside exact early-termination guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot diagnostic accepted {label}")
    safe = publish.replace(
        "              os.replace(tmp_name, path)",
        "              if 1 == 2: raise SystemExit(0)\n              os.replace(tmp_name, path)",
        1,
    )
    require(safe != publish, "constant-false positive fixture drift")
    validate_atomic_diagnostic_publication(safe)
    inert_loop = publish.replace(
        "              os.replace(tmp_name, path)",
        "              while False: raise SystemExit(0)\n              os.replace(tmp_name, path)",
        1,
    )
    require(inert_loop != publish, "constant-false while positive fixture drift")
    validate_atomic_diagnostic_publication(inert_loop)
    short_circuit_false = publish.replace(
        "              os.replace(tmp_name, path)",
        "              if False and runtime_unknown: raise SystemExit(0)\n              os.replace(tmp_name, path)",
        1,
    )
    require(short_circuit_false != publish, "short-circuit false positive fixture drift")
    validate_atomic_diagnostic_publication(short_circuit_false)


def prove_diagnostic_privacy_boundary_rejected(publish: str) -> None:
    validate_atomic_diagnostic_publication(publish)
    mutations = (
        ("result", "'result': 'FAIL'", "'result': 'SUCCESS'"),
        ("secrets", "'containsSecrets': False", "'containsSecrets': True"),
        ("generation", "'generationCreated': False", "'generationCreated': True"),
        ("objective", "'objectiveCreated': False", "'objectiveCreated': True"),
        ("request", "'requestCreated': False", "'requestCreated': True"),
        ("restore", "'restoreExecuted': False", "'restoreExecuted': True"),
        ("evidence", "'productionEvidence': False", "'productionEvidence': True"),
        ("readiness", "'productionReady': False", "'productionReady': True"),
        ("source", "'sourceCommitSha': os.environ['SOURCE_SHA']",
         "'sourceCommitSha': 'unbound'"),
        ("exit code", "'exitCode': int(os.environ['SNAPSHOT_EXIT_CODE'])",
         "'exitCode': 0"),
        ("raw diagnostic", "'output': 'REDACTED: strict OPS-P0-007 snapshot validation failed; raw output withheld'", "'output': text"),
        ("diagnostic path",
         "Path('docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json')",
         "Path('docs/evidence/backup-restore/production-evidence.json')"),
        ("record overwrite", "          path = Path(",
         "          value['productionEvidence'] = True\n          path = Path("),
        ("record update", "          path = Path(",
         "          value.update({'productionReady': True})\n          path = Path("),
        ("record deletion", "          path = Path(",
         "          del value['containsSecrets']\n          path = Path("),
        ("payload overwrite", "          existing_mode = path.stat()",
         "          payload = b'forged'\n          existing_mode = path.stat()"),
        ("payload augmentation", "          existing_mode = path.stat()",
         "          payload += b'forged'\n          existing_mode = path.stat()"),
    )
    for label, before, after in mutations:
        require(publish.count(before) == 1, f"{label} diagnostic privacy fixture drift")
        mutated = publish.replace(before, after, 1)
        try:
            validate_atomic_diagnostic_publication(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot diagnostic non-production evidence boundary drift",
                f"{label} diagnostic rejected outside exact privacy guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot diagnostic accepted {label} authority drift")


def validate_atomic_diagnostic_publication(publish: str) -> None:
    required_fragments = (
        "existing_mode = path.stat().st_mode & 0o7777 if path.exists() else None",
        "if path.is_symlink():",
        "tempfile.mkstemp(",
        "dir=path.parent",
        "os.fchmod(fd, existing_mode)",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in publish]
    require(not missing, f"strict snapshot diagnostic publication is not crash-safe/mode-preserving: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in publish,
        "strict snapshot diagnostic publication regressed to direct write_text",
    )
    executable_diagnostic_calls(publish)


def require_exact_checkout_ref(workflow: str, expected: str, label: str) -> None:
    # Require the actual checkout step's with.ref, not a comment, env value,
    # or a later shell assertion mentioning the desired source SHA.
    # An extra checkout with another action version could overwrite the exact
    # source after the legitimate checkout and must not escape this matcher.
    checkout_steps = re.findall(
        # Both legal GitHub Actions step key orders must count. A named step
        # can declare uses: below - name: rather than on the list-item line.
        r"""(?m)^(?:      - uses:|        uses:)[ \t]*['"]?(actions/checkout@[^\s'"#]+)""",
        workflow,
    )
    action = ("actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
              if label in ("strict snapshot publisher", "strict snapshot publication workflow") else "actions/checkout@v4")
    require(
        checkout_steps == [action],
        f"{label} checkout must bind to exact event source SHA",
    )
    matches = re.findall(
        r"(?m)^      - uses: " + re.escape(action) + r"[ \t]*\n        with:[ \t]*\n          ref:[ \t]*(.+?)[ \t]*$",
        workflow,
    )
    require(
        len(matches) == 1 and matches[0].strip() == expected,
        f"{label} checkout must bind to exact event source SHA",
    )


def prove_checkout_comment_bypass_rejected(pr: str, publish: str) -> None:
    fixtures = (
        ("strict snapshot PR", pr, "${{ github.event.pull_request.head.sha }}", "${{ github.sha }}"),
        ("strict snapshot publisher", publish, "${{ github.sha }}", "${{ github.event.pull_request.head.sha }}"),
    )
    for label, workflow, expected, substitute in fixtures:
        require_exact_checkout_ref(workflow, expected, label)
        original = f"ref: {expected}"
        require(workflow.count(original) == 1, f"{label} checkout fixture boundary drift")
        mutated = workflow.replace(original, f"ref: {substitute}  # {expected}", 1)
        try:
            require_exact_checkout_ref(mutated, expected, label)
        except Fail as exc:
            require("checkout must bind" in str(exc), f"{label} rejected outside checkout guard: {exc}")
        else:
            raise Fail(f"{label} accepted substituted checkout with comment-only source")
        for extra_ref in ("actions/checkout@v4", "actions/checkout@v3", "actions/checkout@v4.2.0", "actions/checkout@main", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"):
            duplicate = workflow + f"\n      - uses: {extra_ref}\n        with:\n          ref: {expected}\n"
            try:
                require_exact_checkout_ref(duplicate, expected, label)
            except Fail as exc:
                require("checkout must bind" in str(exc), f"{label} duplicate {extra_ref} rejected outside checkout guard: {exc}")
            else:
                raise Fail(f"{label} accepted ambiguous duplicate checkout: {extra_ref}")
            anchor = "          fetch-depth: 0\n"
            require(workflow.count(anchor) == 1, f"{label} named checkout fixture boundary drift")
            named = workflow.replace(
                anchor,
                anchor + f"      - name: second checkout\n        uses: {extra_ref}\n"
                f"        with:\n          ref: {expected}\n",
                1,
            )
            try:
                require_exact_checkout_ref(named, expected, label)
            except Fail as exc:
                require(
                    "checkout must bind" in str(exc),
                    f"{label} named duplicate {extra_ref} rejected outside checkout guard: {exc}",
                )
            else:
                raise Fail(f"{label} accepted named duplicate checkout: {extra_ref}")


def executable_run_lines(workflow: str) -> list[str]:
    """Count commands only in enabled GitHub Actions run blocks, not YAML data or heredocs."""
    lines = workflow.splitlines()
    executable: list[str] = []
    for index, line in enumerate(lines):
        if line != "        run: |":
            continue
        step_start = index - 1
        while step_start >= 0 and not lines[step_start].startswith("      - "):
            step_start -= 1
        if step_start < 0:
            continue
        header = lines[step_start:index]
        if any(
            re.fullmatch(r"""        if:\s*(?:false|'false'|"false"|\$\{\{\s*false\s*\}\})\s*""", item)
            for item in header
        ):
            continue
        heredoc: str | None = None
        shell_if: list[bool | None] = []
        in_bounded_function = False
        for item in lines[index + 1:]:
            if item.strip() and not item.startswith("          "):
                break
            command = item[10:] if item.startswith("          ") else ""
            if heredoc is not None:
                if command.strip() == heredoc:
                    heredoc = None
                continue
            stripped = command.strip()
            # A function body is parsed at definition time, but its exit does
            # not terminate the outer run step before the function is called.
            # The bounded function has a separate exact early-exit guard.
            if stripped == "revalidate_latest_snapshot() {":
                in_bounded_function = True
            elif stripped == "}" and in_bounded_function:
                in_bounded_function = False
            # A literal-false shell branch is inert even inside a live run step.
            # Track nested if/else/fi blocks so an inner fi cannot revive a
            # dead outer branch. Unknown conditions may execute either side.
            if re.fullmatch(r"if\b.*;\s*then", stripped):
                literal = re.fullmatch(r"if\s+(true|false)\s*;\s*then", stripped)
                shell_if.append(literal.group(1) == "true" if literal else None)
                continue
            if stripped == "else" and shell_if:
                if shell_if[-1] is not None:
                    shell_if[-1] = not shell_if[-1]
                continue
            if stripped == "fi" and shell_if:
                shell_if.pop()
                continue
            if False in shell_if:
                continue
            # An exit in a conditional unknown branch is not unconditional.
            if re.fullmatch(r"exit(?:\s+[0-9]+)?(?:\s*#.*)?", stripped):
                if in_bounded_function:
                    executable.append(command)
                    continue
                if not any(value is None for value in shell_if):
                    break
                continue
            executable.append(command)
            delimiter = re.search(r"""<<-?\s*(['"]?)([A-Za-z_]\w*)\1""", command)
            if delimiter:
                heredoc = delimiter.group(2)
    return executable


def require_full_admission_chain(workflow: str, label: str) -> None:
    commands = [line.strip() for line in executable_run_lines(workflow)]
    for validator in FULL_ADMISSION_VALIDATORS:
        require(validator in workflow, f"{label} missing full admission validator: {validator}")
        command = rf"^python[ \t]+{re.escape(validator)}(?=[ \t]|$)"
        candidates = [line for line in commands if re.match(command, line)]
        allowed = {f"python {validator}", f'python {validator} >> "$log" 2>&1'}
        require(
            bool(candidates) and all(line in allowed for line in candidates),
            f"{label} does not execute full admission validator fail-closed: {validator}",
        )


def require_fail_closed_pr_shell(workflow: str) -> None:
    """Every PR run step must enter fail-closed Bash before any command executes."""
    lines = workflow.splitlines()
    starts = [index for index, line in enumerate(lines) if line == "        run: |"]
    require(len(starts) == 3, "strict snapshot PR shell run-step authority drift")
    for start in starts:
        body: list[str] = []
        for item in lines[start + 1:]:
            if item.strip() and not item.startswith("          "):
                break
            if item.startswith("          "):
                body.append(item[10:].strip())
        active = [command for command in body if command and not command.startswith("#")]
        require(
            bool(active) and active[0] == "set -euo pipefail",
            "strict snapshot PR shell must start fail-closed in every run step",
        )
        # No later shell-option override is part of the reviewed PR command
        # architecture. In particular, set +e would turn validator failure
        # into an apparent successful admission.
        require(
            not any(re.match(r"^set(?:\s|$)", command) for command in active[1:]),
            "strict snapshot PR shell options must remain fail-closed",
        )


def prove_pr_shell_fail_closed_negative(pr: str) -> None:
    require_fail_closed_pr_shell(pr)
    lines = pr.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line == "          set -euo pipefail\n"]
    require(len(starts) == 3, "strict snapshot PR shell fixture boundary drift")
    for start in starts:
        for replacement in (
            "          set -e\n",
            "          # set -euo pipefail\n",
            "          echo 'set -euo pipefail'\n",
        ):
            mutated = lines.copy()
            mutated[start] = replacement
            try:
                require_fail_closed_pr_shell("".join(mutated))
            except Fail as exc:
                require(
                    str(exc) == "strict snapshot PR shell must start fail-closed in every run step",
                    f"PR shell startup mutation rejected outside exact guard: {exc}",
                )
            else:
                raise Fail("strict snapshot PR shell accepted weakened startup")
        for override in ("set +e", "set +u", "set +o pipefail", "set -e +o pipefail"):
            mutated = lines.copy()
            mutated[start] += f"          {override}\n"
            try:
                require_fail_closed_pr_shell("".join(mutated))
            except Fail as exc:
                require(
                    str(exc) == "strict snapshot PR shell options must remain fail-closed",
                    f"PR shell override rejected outside exact guard: {exc}",
                )
            else:
                raise Fail(f"strict snapshot PR shell accepted {override}")


def require_pr_source_verification(workflow: str) -> None:
    """Bind the PR's exact-source assertion to one unconditional reviewed step."""
    lines = workflow.splitlines()
    marker = "      - name: Verify exact pull request source"
    starts = [index for index, line in enumerate(lines) if line == marker]
    require(len(starts) == 1, "strict snapshot PR source verification step authority drift")
    start = starts[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("      - ")),
        len(lines),
    )
    expected = [
        marker,
        "        run: |",
        "          set -euo pipefail",
        '          expected="${{ github.event.pull_request.head.sha }}"',
        '          test -n "$expected"',
        '          test "$(git rev-parse HEAD)" = "$expected"',
        '          test -z "$(git status --porcelain)"',
    ]
    require(
        lines[start:end] == expected,
        "strict snapshot PR source verification step authority drift",
    )


def prove_pr_source_verification_negative(pr: str) -> None:
    require_pr_source_verification(pr)
    substitutions = (
        (
            '          expected="${{ github.event.pull_request.head.sha }}"\n',
            '          expected="${{ github.sha }}"\n',
        ),
        (
            '          test -n "$expected"\n',
            '          # missing nonempty source assertion\n',
        ),
        (
            '          test "$(git rev-parse HEAD)" = "$expected"\n',
            '          # missing checked-out source assertion\n',
        ),
        (
            '          test "$(git rev-parse HEAD)" = "$expected"\n          test -z "$(git status --porcelain)"\n',
            '          test "$(git rev-parse HEAD)" = "$expected"\n          # missing clean-worktree assertion\n',
        ),
        (
            '          test -n "$expected"\n',
            '          exit 0\n          test -n "$expected"\n',
        ),
        (
            "      - name: Verify exact pull request source\n        run: |\n",
            "      - name: Verify exact pull request source\n        if: false\n        run: |\n",
        ),
        (
            "      - name: Verify exact pull request source\n        run: |\n",
            "      - name: Verify exact pull request source\n        continue-on-error: true\n        run: |\n",
        ),
        (
            '          test "$(git rev-parse HEAD)" = "$expected"\n          test -z "$(git status --porcelain)"\n',
            '          test "$(git rev-parse HEAD)" = "$expected"\n          true\n          test -z "$(git status --porcelain)"\n',
        ),
    )
    for original, replacement in substitutions:
        require(pr.count(original) == 1, "strict snapshot PR source verification fixture drift")
        mutated = pr.replace(original, replacement, 1)
        require(mutated != pr, "strict snapshot PR source verification mutation was a no-op")
        try:
            require_pr_source_verification(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR source verification step authority drift",
                f"PR source verification rejected outside exact guard: {exc}",
            )
        else:
            raise Fail("strict snapshot PR accepted weakened source verification")
    duplicate = pr + "\n      - name: Verify exact pull request source\n        run: |\n          exit 0\n"
    try:
        require_pr_source_verification(duplicate)
    except Fail as exc:
        require(
            str(exc) == "strict snapshot PR source verification step authority drift",
            f"duplicate PR source verification rejected outside exact guard: {exc}",
        )
    else:
        raise Fail("strict snapshot PR accepted duplicate source verification")


def publisher_source_capture_expected_lines() -> list[str]:
    return [
        "      - name: Capture exact OPS-P0-007 snapshot source",
        "        run: |",
        "          set -euo pipefail",
        '          EXPECTED_SOURCE_SHA="${{ github.sha }}"',
        '          test -z "$(git status --porcelain)"',
        '          test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"',
        '          echo "SOURCE_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"',
    ]


def require_publisher_source_capture_step(publish: str) -> None:
    """The initial publisher SOURCE_SHA must come from an exact checked-out HEAD."""
    lines = publish.splitlines()
    expected = publisher_source_capture_expected_lines()
    marker = expected[0]
    starts = [index for index, line in enumerate(lines) if line == marker]
    require(len(starts) == 1, "strict snapshot publisher source capture step authority drift")
    start = starts[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("      - ")),
        len(lines),
    )
    require(
        lines[start:end] == expected,
        "strict snapshot publisher source capture step authority drift",
    )


def prove_publisher_source_capture_negative(publish: str) -> None:
    require_publisher_source_capture_step(publish)
    expected = publisher_source_capture_expected_lines()
    block = "\n".join(expected) + "\n"
    require(publish.count(block) == 1, "publisher source capture fixture block drift")
    substitutions = (
        ('EXPECTED_SOURCE_SHA="${{ github.sha }}"', 'EXPECTED_SOURCE_SHA="${{ github.ref }}"'),
        ('test -z "$(git status --porcelain)"', '# skipped clean source assertion'),
        ('test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"', '# skipped HEAD source assertion'),
        ('echo "SOURCE_SHA=$(git rev-parse HEAD)" >> "$GITHUB_ENV"', 'echo "SOURCE_SHA=forged" >> "$GITHUB_ENV"'),
        ("        run: |", "        if: false\n        run: |"),
        ("        run: |", "        continue-on-error: true\n        run: |"),
        ('test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"',
         'exit 0\n          test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"'),
        ('test -z "$(git status --porcelain)"\n          test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"',
         'test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"\n          test -z "$(git status --porcelain)"'),
    )
    for original, replacement in substitutions:
        require(block.count(original) == 1, "publisher source capture fixture mutation anchor drift")
        altered = block.replace(original, replacement, 1)
        mutated = publish.replace(block, altered, 1)
        require(mutated != publish, "publisher source capture mutation was a no-op")
        try:
            require_publisher_source_capture_step(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher source capture step authority drift",
                f"publisher source capture rejected outside exact guard: {exc}",
            )
        else:
            raise Fail("strict snapshot publisher accepted weakened source capture")
    duplicate = publish + "\n      - name: Capture exact OPS-P0-007 snapshot source\n        run: |\n          exit 0\n"
    try:
        require_publisher_source_capture_step(duplicate)
    except Fail as exc:
        require(
            str(exc) == "strict snapshot publisher source capture step authority drift",
            f"duplicate publisher source capture rejected outside exact guard: {exc}",
        )
    else:
        raise Fail("strict snapshot publisher accepted duplicate source capture")


def pr_drift_rejection_expected_lines() -> list[str]:
    return [
        "      - name: Reject deterministic snapshot drift",
        "        run: |",
        "          set -euo pipefail",
        "          git diff --exit-code -- contracts/operations/ops-p0-007-admission-snapshot.v1.json",
        '          test -z "$(git status --porcelain)"',
    ]


def require_pr_drift_rejection_step(pr: str) -> None:
    """The deterministic snapshot drift check must execute as a fatal PR step."""
    lines = pr.splitlines()
    expected = pr_drift_rejection_expected_lines()
    marker = expected[0]
    starts = [index for index, line in enumerate(lines) if line == marker]
    require(len(starts) == 1, "strict snapshot PR drift rejection step authority drift")
    start = starts[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("      - ")),
        len(lines),
    )
    require(
        lines[start:end] == expected,
        "strict snapshot PR drift rejection step authority drift",
    )


def prove_pr_drift_rejection_negative(pr: str) -> None:
    require_pr_drift_rejection_step(pr)
    block = "\n".join(pr_drift_rejection_expected_lines()) + "\n"
    require(pr.count(block) == 1, "strict snapshot PR drift rejection fixture block drift")
    substitutions = (
        ("git diff --exit-code -- contracts/operations/ops-p0-007-admission-snapshot.v1.json",
         "echo 'git diff --exit-code -- contracts/operations/ops-p0-007-admission-snapshot.v1.json'"),
        ('test -z "$(git status --porcelain)"', '# omitted clean-worktree assertion'),
        ("        run: |", "        if: false\n        run: |"),
        ("        run: |", "        continue-on-error: true\n        run: |"),
        ("        run: |", "        shell: pwsh\n        run: |"),
        ("          git diff --exit-code", "          exit 0\n          git diff --exit-code"),
        ("          git diff --exit-code", "          git add -A\n          git diff --exit-code"),
    )
    for original, replacement in substitutions:
        require(block.count(original) == 1, "strict snapshot PR drift rejection fixture mutation anchor drift")
        altered = block.replace(original, replacement, 1)
        mutated = pr.replace(block, altered, 1)
        require(mutated != pr, "strict snapshot PR drift rejection mutation was a no-op")
        try:
            require_pr_drift_rejection_step(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR drift rejection step authority drift",
                f"PR drift rejection mutation rejected outside exact guard: {exc}",
            )
        else:
            raise Fail("strict snapshot PR accepted weakened deterministic drift gate")
    duplicate = pr + "\n      - name: Reject deterministic snapshot drift\n        run: |\n          exit 0\n"
    try:
        require_pr_drift_rejection_step(duplicate)
    except Fail as exc:
        require(
            str(exc) == "strict snapshot PR drift rejection step authority drift",
            f"duplicate PR drift rejection rejected outside exact guard: {exc}",
        )
    else:
        raise Fail("strict snapshot PR accepted duplicate deterministic drift gate")



def require_pr_step_allowlist(pr: str) -> None:
    """No unreviewed Actions step may run before or around PR admission."""
    lines = pr.splitlines()
    starts = [index for index, line in enumerate(lines) if line == "    steps:"]
    require(len(starts) == 1, "strict snapshot PR step allowlist authority drift")
    steps: list[list[str]] = []
    for line in lines[starts[0] + 1:]:
        if line.startswith("      - "):
            steps.append([line])
        elif steps:
            steps[-1].append(line)
        elif line.strip():
            raise Fail("strict snapshot PR step allowlist authority drift")
    require(len(steps) == 5, "strict snapshot PR step allowlist authority drift")
    require(
        steps[0] == [
            "      - uses: actions/checkout@v4",
            "        with:",
            "          ref: ${{ github.event.pull_request.head.sha }}",
            "          fetch-depth: 0",
        ] and steps[1] == [
            "      - uses: actions/setup-python@v5",
            "        with:",
            '          python-version: "3.12"',
        ] and [
            step[:2] for step in steps[2:]
        ] == [
            ["      - name: Verify exact pull request source", "        run: |"],
            ["      - name: Generate and validate strict snapshot read-only", "        run: |"],
            ["      - name: Reject deterministic snapshot drift", "        run: |"],
        ],
        "strict snapshot PR step allowlist authority drift",
    )

    # Keys dedented after a run scalar are executable Actions step metadata,
    # not shell lines. They must not disable or mask the admission gate.
    require(
        all(not line.strip() or line.startswith("          ")
            for step in steps[2:]
            for line in step[step.index("        run: |") + 1:]),
        "strict snapshot PR step allowlist authority drift",
    )


def prove_pr_step_allowlist_negative(pr: str) -> None:
    require_pr_step_allowlist(pr)
    checkout = (
        "      - uses: actions/checkout@v4\n"
        "        with:\n"
        "          ref: ${{ github.event.pull_request.head.sha }}\n"
        "          fetch-depth: 0\n"
    )
    setup = (
        "      - uses: actions/setup-python@v5\n"
        "        with:\n"
        '          python-version: "3.12"\n'
    )
    verify = "      - name: Verify exact pull request source\n"
    require(pr.count(checkout + setup) == pr.count(verify) == 1,
            "strict snapshot PR step allowlist fixture anchor drift")
    for label, mutated in (
        ("nonfatal admission after run", pr.replace(
            "      - name: Reject deterministic snapshot drift\n",
            "        continue-on-error: true\n      - name: Reject deterministic snapshot drift\n", 1)),
        ("disabled admission after run", pr.replace(
            "      - name: Reject deterministic snapshot drift\n",
            "        if: false\n      - name: Reject deterministic snapshot drift\n", 1)),
        ("nonfatal final drift step", pr + "        continue-on-error: true\n"),
    ):
        require(mutated != pr, f"{label} PR trailing metadata fixture was a no-op")
        try:
            require_pr_step_allowlist(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot PR step allowlist authority drift",
                    f"{label} PR trailing metadata rejected outside exact guard: {exc}")
        else:
            raise Fail(f"strict snapshot PR accepted trailing step metadata: {label}")
    mutations = (
        ("extra unreviewed action", pr.replace(verify, "      - uses: unreviewed/action@v1\n" + verify, 1)),
        ("extra unreviewed run", pr.replace(verify, "      - name: Unreviewed shell\n        run: echo bypass\n" + verify, 1)),
        ("wrong setup action", pr.replace(setup, setup.replace("setup-python@v5", "setup-python@v4"), 1)),
        ("wrong Python version", pr.replace(setup, setup.replace('"3.12"', '"3.11"'), 1)),
        ("disabled setup", pr.replace(setup, setup.replace("        with:", "        if: false\n        with:"), 1)),
        ("masked setup failure", pr.replace(setup, setup.replace("        with:", "        continue-on-error: true\n        with:"), 1)),
        ("shallow checkout", pr.replace(checkout, checkout.replace("fetch-depth: 0", "fetch-depth: 1"), 1)),
        ("unreviewed checkout input", pr.replace(checkout, checkout + "        persist-credentials: true\n", 1)),
        ("duplicate setup", pr.replace(setup, setup + setup, 1)),
        ("reordered checkout and setup", pr.replace(checkout + setup, setup + checkout, 1)),
        ("renamed source verification", pr.replace(verify, "      - name: Unreviewed source verification\n", 1)),
    )
    for label, mutated in mutations:
        require(mutated != pr, f"{label} PR step fixture mutation was a no-op")
        try:
            require_pr_step_allowlist(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR step allowlist authority drift",
                f"{label} PR step fixture rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted {label}")


def pr_job_expected_header() -> list[str]:
    return [
        "jobs:",
        "  validate:",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 8",
        "    steps:",
    ]


def require_pr_job_execution_policy(pr: str) -> None:
    """A disabled or non-fatal job cannot establish a mandatory PR admission."""
    lines = pr.splitlines()
    expected = pr_job_expected_header()
    starts = [index for index, line in enumerate(lines) if line == "  validate:"]
    require(len(starts) == 1, "strict snapshot PR job execution policy drift")
    start = starts[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("      - ")),
        len(lines),
    )
    require(
        start > 0 and lines[start - 1] == "jobs:"
        and lines[start - 1:end] == expected,
        "strict snapshot PR job execution policy drift",
    )


def prove_pr_job_execution_policy_negative(pr: str) -> None:
    require_pr_job_execution_policy(pr)
    block = "\n".join(pr_job_expected_header()) + "\n"
    require(pr.count(block) == 1, "strict snapshot PR job policy fixture block drift")
    substitutions = (
        ("    runs-on: ubuntu-latest", "    if: false\n    runs-on: ubuntu-latest"),
        ("    runs-on: ubuntu-latest", "    continue-on-error: true\n    runs-on: ubuntu-latest"),
        ("    runs-on: ubuntu-latest", "    needs: unreviewed-prerequisite\n    runs-on: ubuntu-latest"),
        ("    runs-on: ubuntu-latest", "    runs-on: windows-latest"),
        ("    timeout-minutes: 8", "    timeout-minutes: 0"),
        ("    steps:", "    # steps:"),
    )
    for original, replacement in substitutions:
        require(block.count(original) == 1, "strict snapshot PR job policy mutation anchor drift")
        mutated = pr.replace(block, block.replace(original, replacement, 1), 1)
        require(mutated != pr, "strict snapshot PR job policy mutation was a no-op")
        try:
            require_pr_job_execution_policy(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR job execution policy drift",
                f"PR job execution policy rejected outside exact guard: {exc}",
            )
        else:
            raise Fail("strict snapshot PR accepted weakened job-level admission policy")
    duplicate = pr + "\n  validate:\n    runs-on: ubuntu-latest\n    steps:\n"
    try:
        require_pr_job_execution_policy(duplicate)
    except Fail as exc:
        require(
            str(exc) == "strict snapshot PR job execution policy drift",
            f"duplicate PR job rejected outside exact guard: {exc}",
        )
    else:
        raise Fail("strict snapshot PR accepted duplicate validate job")



def publisher_trigger_paths() -> tuple[str, ...]:
    return (
        ".github/workflows/ops-p0-007-admission-snapshot.yml",
        ".github/workflows/ops-p0-007-admission-snapshot-pr.yml",
        "contracts/operations/ops-p0-007-admission-snapshot.v1.json",
        *(f"contracts/operations/{name}" for name in REQUIRED_PR_ADMISSION_CONTRACTS),
        "contracts/operations/production-operability-status.json",
        "docs/evidence/backup-restore/**",
        *PR_COMPILE_FILES[:-1],
    )


def require_publisher_trigger_authority(publish: str) -> None:
    """Only the reviewed so push and manual dispatch may publish snapshots."""
    expected = [
        "name: OPS P0 007 Admission Snapshot",
        "",
        "on:",
        "  push:",
        "    branches:",
        "      - so",
        "    paths:",
        *(f'      - "{path}"' for path in publisher_trigger_paths()),
        "  workflow_dispatch:",
        "",
        "permissions:",
        "  contents: write",
    ]
    require(
        publish.splitlines()[:len(expected)] == expected,
        "strict snapshot publisher trigger/path authority drift",
    )


def prove_publisher_trigger_negative(publish: str) -> None:
    require_publisher_trigger_authority(publish)
    marker = "permissions:\n"
    require(publish.count(marker) == 1,
            "strict snapshot publisher trigger fixture boundary drift")
    header, remainder = publish.split(marker, 1)
    suffix = marker + remainder
    def check(label: str, changed: str) -> None:
        require(changed != header, f"{label} publisher trigger mutation was a no-op")
        try:
            require_publisher_trigger_authority(changed + suffix)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher trigger/path authority drift",
                f"{label} publisher trigger rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted {label}")

    for path in publisher_trigger_paths():
        line = f'      - "{path}"\n'
        require(header.count(line) == 1, f"publisher trigger path fixture drift: {path}")
        check(f"missing {path}", header.replace(line, "      # required trigger path removed\n", 1))
    mutations = (
        ("missing push", header.replace("  push:\n", "  workflow_dispatch:\n", 1)),
        ("wrong branch", header.replace("      - so\n", "      - main\n", 1)),
        ("missing branch selector", header.replace("    branches:\n", "    # branches removed\n", 1)),
        ("missing path selector", header.replace("    paths:\n", "    # paths removed\n", 1)),
        ("wrong event", header.replace("  push:\n", "  pull_request_target:\n", 1)),
        ("extra schedule", header.replace("  workflow_dispatch:\n", "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)),
        ("missing manual dispatch", header.replace("  workflow_dispatch:\n", "  # manual dispatch removed\n", 1)),
        ("duplicate protected path", header.replace(
            '      - "contracts/operations/ops-p0-007-admission-snapshot.v1.json"\n',
            '      - "contracts/operations/ops-p0-007-admission-snapshot.v1.json"\n'
            '      - "contracts/operations/ops-p0-007-admission-snapshot.v1.json"\n', 1)),
    )
    for label, mutated in mutations:
        check(label, mutated)


def require_pr_trigger_authority(pr: str) -> None:
    """Require a real pull_request trigger covering all reviewed admission inputs."""
    lines = pr.splitlines()
    starts = [index for index, line in enumerate(lines) if line == "on:"]
    require(len(starts) == 1, "strict snapshot PR trigger/path authority drift")
    start = starts[0]
    end = next(
        (index for index in range(start + 1, len(lines))
         if lines[index].strip() and not lines[index].startswith("  ")),
        len(lines),
    )
    active = [line for line in lines[start:end] if line.strip()]
    require(
        active[:3] == ["on:", "  pull_request:", "    paths:"]
        and all(re.fullmatch(r'      - "[^"]+"', line) for line in active[3:]),
        "strict snapshot PR trigger/path authority drift",
    )
    paths = [line.split('"')[1] for line in active[3:]]
    required = {
        ".github/workflows/ops-p0-007-admission-snapshot.yml",
        ".github/workflows/ops-p0-007-admission-snapshot-pr.yml",
        "contracts/operations/ops-p0-007-admission-snapshot.v1.json",
        "contracts/operations/production-operability-status.json",
        "docs/evidence/backup-restore/**",
        "scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py",
        *PUBLISH_REVALIDATION_CHAIN,
        *PR_COMPILE_FILES,
    }
    required.update(f"contracts/operations/{name}" for name in REQUIRED_PR_ADMISSION_CONTRACTS)
    require(
        len(paths) == len(set(paths)) and required.issubset(paths),
        "strict snapshot PR trigger/path authority drift",
    )


def prove_pr_trigger_negative(pr: str) -> None:
    require_pr_trigger_authority(pr)
    self_path = '      - "scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py"\n'
    status_path = '      - "contracts/operations/production-operability-status.json"\n'
    generator_path = '      - "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"\n'
    mutations = (
        ("  pull_request:\n", "  workflow_dispatch:\n"),
        ("  pull_request:\n", "  pull_request_target:\n"),
        ("  pull_request:\n", "  pull_request:\n  push:\n"),
        ("    paths:\n", "    # paths disabled\n"),
        (self_path, "      # negative guard path filter removed\n"),
        (status_path, "      # production status path filter removed\n"),
        (generator_path, "      # generator path filter removed\n"),
        (self_path, self_path + self_path),
    )
    # Every typed generation/objective/drill/evidence contract and registry
    # must trigger PR admission when changed, not only the snapshot projection.
    for name in REQUIRED_PR_ADMISSION_CONTRACTS:
        original = f'      - "contracts/operations/{name}"\n'
        require(pr.count(original) == 1, f"PR contract path fixture drift: {name}")
        mutated = pr.replace(original, "      # required contract path removed\n", 1)
        try:
            require_pr_trigger_authority(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR trigger/path authority drift",
                f"missing PR contract path rejected outside exact guard ({name}): {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted missing contract path: {name}")
    # A change to any compiled admission input must trigger the PR gate,
    # even when that script is not one of the runtime validator entrypoints.
    for path in PR_COMPILE_FILES:
        original = f'      - "{path}"\n'
        require(pr.count(original) == 1, f"PR compiled-script path fixture drift: {path}")
        mutated = pr.replace(original, "      # compiled admission input removed\n", 1)
        try:
            require_pr_trigger_authority(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR trigger/path authority drift",
                f"missing compiled-script path rejected outside exact guard ({path}): {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted missing compiled-script path: {path}")
    for original, replacement in mutations:
        require(pr.count(original) == 1, "strict snapshot PR trigger mutation anchor drift")
        mutated = pr.replace(original, replacement, 1)
        require(mutated != pr, "strict snapshot PR trigger mutation was a no-op")
        try:
            require_pr_trigger_authority(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR trigger/path authority drift",
                f"PR trigger/path mutation rejected outside exact guard: {exc}",
            )
        else:
            raise Fail("strict snapshot PR accepted weakened trigger or path coverage")



def require_publisher_step_allowlist(publish: str) -> None:
    """Publisher may execute only the seven reviewed Actions steps."""
    lines = publish.splitlines()
    starts = [index for index, line in enumerate(lines) if line == "    steps:"]
    require(len(starts) == 1, "strict snapshot publisher step allowlist authority drift")
    steps: list[list[str]] = []
    for line in lines[starts[0] + 1:]:
        if line.startswith("      - "):
            steps.append([line])
        elif steps:
            steps[-1].append(line)
        elif line.strip():
            raise Fail("strict snapshot publisher step allowlist authority drift")
    require(len(steps) == 7, "strict snapshot publisher step allowlist authority drift")
    require(
        steps[0] == [
            "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "        with:",
            "          ref: ${{ github.sha }}",
            "          fetch-depth: 0",
            "          persist-credentials: true",
        ] and steps[1] == [
            "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
            "        with:",
            '          python-version: "3.12"',
        ] and steps[2][:2] == [
            "      - name: Capture exact OPS-P0-007 snapshot source",
            "        run: |",
        ] and steps[3][:3] == [
            "      - name: Generate and validate strict snapshot",
            "        id: snapshot",
            "        run: |",
        ] and steps[4][:3] == [
            "      - name: Commit deterministic strict snapshot",
            "        if: steps.snapshot.outputs.exit_code == '0' && github.ref == 'refs/heads/so'",
            "        run: |",
        ] and steps[5][:5] == [
            "      - name: Record privacy-safe snapshot diagnostic",
            "        if: steps.snapshot.outputs.exit_code != '0' && github.ref == 'refs/heads/so'",
            "        env:",
            "          SNAPSHOT_EXIT_CODE: ${{ steps.snapshot.outputs.exit_code }}",
            "        run: |",
        ] and steps[6] == [
            "      - name: Enforce strict snapshot",
            '        run: test "${{ steps.snapshot.outputs.exit_code }}" = "0"',
        ],
        "strict snapshot publisher step allowlist authority drift",
    )

    require(
        all(not line.strip() or line.startswith("          ")
            for step in steps[2:6]
            for line in step[step.index("        run: |") + 1:]),
        "strict snapshot publisher step allowlist authority drift",
    )


def prove_publisher_step_allowlist_negative(publish: str) -> None:
    require_publisher_step_allowlist(publish)
    checkout = (
        "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        "        with:\n"
        "          ref: ${{ github.sha }}\n"
        "          fetch-depth: 0\n"
        "          persist-credentials: true\n"
    )
    setup = (
        "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
        "        with:\n"
        '          python-version: "3.12"\n'
    )
    capture = "      - name: Capture exact OPS-P0-007 snapshot source\n"
    commit = "      - name: Commit deterministic strict snapshot\n"
    diagnostic = "      - name: Record privacy-safe snapshot diagnostic\n"
    enforce = (
        "      - name: Enforce strict snapshot\n"
        '        run: test "${{ steps.snapshot.outputs.exit_code }}" = "0"\n'
    )
    require(
        all(publish.count(part) == 1 for part in
            (checkout + setup, capture, commit, diagnostic, enforce)),
        "strict snapshot publisher step allowlist fixture anchor drift",
    )
    for label, mutated in (
        ("disabled source capture after run", publish.replace(
            "      - name: Generate and validate strict snapshot\n",
            "        if: false\n      - name: Generate and validate strict snapshot\n", 1)),
        ("nonfatal generator after run", publish.replace(
            "      - name: Commit deterministic strict snapshot\n",
            "        continue-on-error: true\n      - name: Commit deterministic strict snapshot\n", 1)),
        ("shell override after diagnostic run", publish.replace(
            "      - name: Enforce strict snapshot\n",
            "        shell: bash {0}\n      - name: Enforce strict snapshot\n", 1)),
    ):
        require(mutated != publish, f"{label} publisher trailing metadata fixture was a no-op")
        try:
            require_publisher_step_allowlist(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot publisher step allowlist authority drift",
                    f"{label} publisher trailing metadata rejected outside exact guard: {exc}")
        else:
            raise Fail(f"strict snapshot publisher accepted trailing step metadata: {label}")
    mutations = (
        ("floating checkout", publish.replace(checkout, checkout.replace("checkout@11d5960a326750d5838078e36cf38b85af677262", "checkout@v4"), 1)),
        ("floating setup", publish.replace(setup, setup.replace("setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "setup-python@v5"), 1)),
        ("checkout credential removed", publish.replace(checkout, checkout.replace("          persist-credentials: true\n", ""), 1)),
        ("checkout credential disabled", publish.replace(checkout, checkout.replace("persist-credentials: true", "persist-credentials: false"), 1)),
        ("extra action", publish.replace(capture, "      - uses: unreviewed/action@v1\n" + capture, 1)),
        ("extra run", publish.replace(capture, "      - name: Unreviewed shell\n        run: echo bypass\n" + capture, 1)),
        ("wrong setup action", publish.replace(setup, setup.replace("setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "setup-python@v5"), 1)),
        ("wrong Python version", publish.replace(setup, setup.replace('"3.12"', '"3.11"'), 1)),
        ("shallow checkout", publish.replace(checkout, checkout.replace("fetch-depth: 0", "fetch-depth: 1"), 1)),
        ("duplicate setup", publish.replace(setup, setup + setup, 1)),
        ("reordered checkout and setup", publish.replace(checkout + setup, setup + checkout, 1)),
        ("disabled capture", publish.replace(capture, capture + "        if: false\n", 1)),
        ("disabled generation", publish.replace("        id: snapshot\n", "        if: false\n        id: snapshot\n", 1)),
        ("masked commit failure", publish.replace(commit, commit + "        continue-on-error: true\n", 1)),
        ("masked diagnostic failure", publish.replace(diagnostic, diagnostic + "        continue-on-error: true\n", 1)),
        ("changed diagnostic condition", publish.replace(
            "        if: steps.snapshot.outputs.exit_code != '0' && github.ref == 'refs/heads/so'\n",
            "        if: steps.snapshot.outputs.exit_code == '0' && github.ref == 'refs/heads/so'\n", 1)),
        ("removed final enforcement", publish.replace(enforce, "", 1)),
        ("forged final enforcement", publish.replace(enforce, "      - name: Enforce strict snapshot\n        run: echo bypass\n", 1)),
    )
    for label, mutated in mutations:
        require(mutated != publish, f"{label} publisher step fixture mutation was a no-op")
        try:
            require_publisher_step_allowlist(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher step allowlist authority drift",
                f"{label} publisher step fixture rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted {label}")


def require_publisher_job_execution_policy(publish: str) -> None:
    """A skipped or non-fatal publisher job cannot prove snapshot validation."""
    lines = publish.splitlines()
    expected = [
        "jobs:",
        "  validate:",
        "    runs-on: ubuntu-latest",
        "    timeout-minutes: 8",
        "    steps:",
    ]
    starts = [index for index, line in enumerate(lines) if line == "  validate:"]
    require(len(starts) == 1, "strict snapshot publisher job execution policy drift")
    start = starts[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("      - ")),
        len(lines),
    )
    require(
        start > 0 and lines[start - 1] == "jobs:"
        and lines[start - 1:end] == expected,
        "strict snapshot publisher job execution policy drift",
    )


def prove_publisher_job_execution_policy_negative(publish: str) -> None:
    require_publisher_job_execution_policy(publish)
    block = "jobs:\n  validate:\n    runs-on: ubuntu-latest\n    timeout-minutes: 8\n    steps:\n"
    require(publish.count(block) == 1, "publisher job policy fixture block drift")
    substitutions = (
        ("    runs-on: ubuntu-latest", "    if: false\n    runs-on: ubuntu-latest"),
        ("    runs-on: ubuntu-latest", "    continue-on-error: true\n    runs-on: ubuntu-latest"),
        ("    runs-on: ubuntu-latest", "    needs: unreviewed-job\n    runs-on: ubuntu-latest"),
        ("    runs-on: ubuntu-latest", "    runs-on: windows-latest"),
        ("    timeout-minutes: 8", "    timeout-minutes: 0"),
        ("    steps:", "    # steps disabled"),
    )
    for original, replacement in substitutions:
        require(block.count(original) == 1, "publisher job policy mutation anchor drift")
        mutated = publish.replace(block, block.replace(original, replacement, 1), 1)
        require(mutated != publish, "publisher job policy mutation was a no-op")
        try:
            require_publisher_job_execution_policy(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher job execution policy drift",
                f"publisher job execution policy rejected outside exact guard: {exc}",
            )
        else:
            raise Fail("strict snapshot publisher accepted weakened job-level validation")
    duplicate = publish + "\n  validate:\n    runs-on: ubuntu-latest\n    steps:\n"
    try:
        require_publisher_job_execution_policy(duplicate)
    except Fail as exc:
        require(
            str(exc) == "strict snapshot publisher job execution policy drift",
            f"duplicate publisher job rejected outside exact guard: {exc}",
        )
    else:
        raise Fail("strict snapshot publisher accepted duplicate validate job")


def publisher_protected_shell_starts(workflow: str) -> list[int]:
    lines = workflow.splitlines()
    names = (
        "Capture exact OPS-P0-007 snapshot source",
        "Commit deterministic strict snapshot",
        "Record privacy-safe snapshot diagnostic",
    )
    starts: list[int] = []
    for name in names:
        marker = f"      - name: {name}"
        locations = [index for index, line in enumerate(lines) if line == marker]
        require(len(locations) == 1, f"strict snapshot publisher shell step authority drift: {name}")
        start = locations[0]
        end = next((index for index in range(start + 1, len(lines))
                    if lines[index].startswith("      - ")), len(lines))
        runs = [index for index in range(start + 1, end) if lines[index] == "        run: |"]
        require(len(runs) == 1, f"strict snapshot publisher shell run-step authority drift: {name}")
        starts.append(runs[0] + 1)
    return starts


def require_fail_closed_publisher_shell(workflow: str) -> None:
    lines = workflow.splitlines()
    for start in publisher_protected_shell_starts(workflow):
        body: list[str] = []
        for item in lines[start:]:
            if item.strip() and not item.startswith("          "):
                break
            if item.startswith("          "):
                body.append(item[10:].strip())
        active = [command for command in body if command and not command.startswith("#")]
        require(
            bool(active) and active[0] == "set -euo pipefail",
            "strict snapshot publisher protected shell must start fail-closed",
        )
        require(
            not any(re.match(r"^(?:set|trap|alias|unalias|shopt|enable|source|hash)(?:\s|$)|^\.\s+|^(?:python|git|sha256sum|stat)\s*\(\)\s*\{", command) for command in active[1:]),
            "strict snapshot publisher protected shell options must remain fail-closed",
        )


def prove_publisher_shell_fail_closed_negative(publish: str) -> None:
    require_fail_closed_publisher_shell(publish)
    lines = publish.splitlines(keepends=True)
    starts = publisher_protected_shell_starts(publish)
    require(
        all(lines[start] == "          set -euo pipefail\n" for start in starts),
        "strict snapshot publisher shell fixture boundary drift",
    )
    for start in starts:
        for replacement in (
            "          set -e\n",
            "          # set -euo pipefail\n",
            "          echo 'set -euo pipefail'\n",
        ):
            mutated = lines.copy()
            mutated[start] = replacement
            try:
                require_fail_closed_publisher_shell("".join(mutated))
            except Fail as exc:
                require(
                    str(exc) == "strict snapshot publisher protected shell must start fail-closed",
                    f"publisher shell startup rejected outside exact guard: {exc}",
                )
            else:
                raise Fail("strict snapshot publisher accepted weakened protected shell startup")
        for override in (
            "set +e", "set +u", "set +o pipefail", "set -e +o pipefail",
            "trap 'exit 0' ERR", "trap 'exit 0' EXIT",
            "source ./unreviewed-shell.sh", ". ./unreviewed-shell.sh",
            "shopt -s expand_aliases", "alias python='true'",
            "python() { :; }", "git () { :; }",
            "sha256sum() { echo forged; }", "hash -p /bin/true python",
        ):
            mutated = lines.copy()
            mutated[start] += f"          {override}\n"
            try:
                require_fail_closed_publisher_shell("".join(mutated))
            except Fail as exc:
                require(
                    str(exc) == "strict snapshot publisher protected shell options must remain fail-closed",
                    f"publisher shell override rejected outside exact guard: {exc}",
                )
            else:
                raise Fail(f"strict snapshot publisher accepted {override} in protected shell")



def require_pr_compile_step(pr: str) -> None:
    """Bind the complete reviewed PR run body, including the live compile stage."""
    lines = pr.splitlines()
    name = "      - name: Generate and validate strict snapshot read-only"
    starts = [index for index, line in enumerate(lines) if line == name]
    require(len(starts) == 1, "strict snapshot PR compile step command authority drift")
    start = starts[0]
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("      - ")), len(lines))
    runs = [index for index in range(start + 1, end) if lines[index] == "        run: |"]
    require(len(runs) == 1, "strict snapshot PR compile step command authority drift")
    body = [line[10:].strip() for line in lines[runs[0] + 1:end]
            if line.startswith("          ") and line[10:].strip()]
    expected = [
        "set -euo pipefail",
        "python -m py_compile \\",
        *(f"{path} \\" for path in PR_COMPILE_FILES[:-1]),
        PR_COMPILE_FILES[-1],
        *(f"python {path}" for path in PUBLISH_REVALIDATION_CHAIN),
        "python scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py",
    ]
    require(body == expected, "strict snapshot PR compile step command authority drift")


def prove_pr_compile_step_negative(pr: str) -> None:
    require_pr_compile_step(pr)
    name = "      - name: Generate and validate strict snapshot read-only"
    end_name = "      - name: Reject deterministic snapshot drift"
    require(pr.count(name) == 1 and pr.count(end_name) == 1,
            "strict snapshot PR compile fixture step boundary drift")
    before, remainder = pr.split(name, 1)
    step, after = remainder.split(end_name, 1)
    prefix = before + name
    suffix = end_name + after
    def check(label: str, changed: str) -> None:
        require(changed != step, f"{label} compile fixture mutation was a no-op")
        try:
            require_pr_compile_step(prefix + changed + suffix)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR compile step command authority drift",
                f"{label} compile fixture rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted weakened compile stage: {label}")

    first = f"            {PR_COMPILE_FILES[0]} \\\n"
    second = f"            {PR_COMPILE_FILES[1]} \\\n"
    last = f"            {PR_COMPILE_FILES[-1]}\n"
    command = "          python -m py_compile \\\n"
    require(step.count(first) == step.count(second) == step.count(last) == step.count(command) == 1,
            "strict snapshot PR compile fixture argument anchor drift")
    check("missing first argument", step.replace(first, "", 1))
    check("comment-only first argument", step.replace(first, "          # " + first.strip() + "\n", 1))
    check("wrong first argument", step.replace(first, "          scripts/unreviewed-compile.py \\\n", 1))
    check("reordered arguments", step.replace(first + second, second + first, 1))
    check("missing compile execution", step.replace(command, "          echo python -m py_compile \\\n", 1))
    check("masked compile failure", step.replace(last, last.rstrip("\n") + " || true\n", 1))
    check("extra compile argument", step.replace(last, "          scripts/unreviewed-compile.py \\\n" + last, 1))
    check("comment inside continuation", step.replace(first, first + "          # hidden break in continuation\n", 1))
    check("early exit before compile", step.replace(command, "          exit 0\n" + command, 1))
    check("compile after validator", step.replace(
        command, "", 1).replace(
        "          python scripts/validate-memory-os-recovery-objectives.py\n",
        command + "          python scripts/validate-memory-os-recovery-objectives.py\n", 1))
    check("duplicate compile", step.replace(command, command + command, 1))


def require_unconditional_pr_admission(workflow: str) -> None:
    """A conditional or uncalled shell function cannot establish PR admission."""
    lines = workflow.splitlines()
    name = "      - name: Generate and validate strict snapshot read-only"
    starts = [index for index, line in enumerate(lines) if line == name]
    require(len(starts) == 1, "strict snapshot PR admission run-step authority drift")
    start = starts[0]
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("      - ")), len(lines))
    runs = [index for index in range(start + 1, end) if lines[index] == "        run: |"]
    require(len(runs) == 1, "strict snapshot PR admission executable run block missing")
    require(
        lines[start:runs[0]] == [name],
        "strict snapshot PR admission step execution policy drift",
    )
    body = [line[10:].strip() for line in lines[runs[0] + 1:end]
            if line.startswith("          ")]
    active = [line for line in body if line and not line.startswith("#")]
    # This canonical PR admission step is deliberately linear. Unlike the
    # publisher's explicitly status-capturing generation step, no validator
    # may be moved behind an unknown conditional or into an uncalled function.
    control = re.compile(
        r"^(?:if|elif|else|fi|for|while|until|case|esac|function|eval|exit|return|break|continue|exec|trap|alias|unalias|shopt|enable|source)\b"
        r"|^\.\s+"
        r"|^[A-Za-z_]\w*\(\)\s*\{"
        r"|^bash\s+-c\b"
    )
    require(
        not any(control.search(line) for line in active),
        "strict snapshot PR admission validators must execute unconditionally",
    )
    for validator in FULL_ADMISSION_VALIDATORS:
        require(
            active.count(f"python {validator}") == 1,
            f"strict snapshot PR admission missing unconditional validator: {validator}",
        )
    expected_chain = [f"python {validator}" for validator in PUBLISH_REVALIDATION_CHAIN]
    expected_chain.append(
        "python scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py"
    )
    actual_chain = [line for line in active if re.match(r"^python[ \t]+scripts/", line)]
    require(
        actual_chain == expected_chain,
        "strict snapshot PR admission validator execution order drift",
    )


def prove_pr_conditional_admission_rejected(pr: str) -> None:
    require_unconditional_pr_admission(pr)
    # A correct validator body in a skipped or continue-on-error step is not
    # a mandatory PR admission gate. Bind the reviewed step header as well.
    step = "      - name: Generate and validate strict snapshot read-only\n        run: |\n"
    require(pr.count(step) == 1, "strict snapshot PR admission header fixture drift")
    for injected in (
        "if: false",
        "if: ${{ false }}",
        "continue-on-error: true",
        "shell: pwsh",
    ):
        mutated = pr.replace(step, step.replace("        run: |", f"        {injected}\n        run: |"), 1)
        try:
            require_unconditional_pr_admission(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR admission step execution policy drift",
                f"disabled or weakened PR admission step rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted weakened admission step header: {injected}")
    for validator in FULL_ADMISSION_VALIDATORS:
        command = f"          python {validator}\n"
        require(pr.count(command) == 1, f"strict snapshot PR conditional fixture drift: {validator}")
        for wrapper in (
            f"          if test \"$ALLOW\" = yes; then\n{command}          fi\n",
            f"          unused_admission_gate() {{\n{command}          }}\n",
        ):
            mutated = pr.replace(command, wrapper, 1)
            try:
                require_unconditional_pr_admission(mutated)
            except Fail as exc:
                require(
                    str(exc) == "strict snapshot PR admission validators must execute unconditionally",
                    f"conditional {validator} rejected outside exact guard: {exc}",
                )
            else:
                raise Fail(f"strict snapshot PR accepted conditional or uncalled validator: {validator}")
    # A shell trap can convert validator failure into exit 0; sourcing a file
    # or enabling aliases can replace the command or alter errexit at runtime.
    # The reviewed PR admission is deliberately linear and self-contained.
    validator = FULL_ADMISSION_VALIDATORS[0]
    command = f"          python {validator}\n"
    require(pr.count(command) == 1, "strict snapshot PR shell-indirection fixture drift")
    for indirection in (
        "trap 'exit 0' ERR",
        "trap 'exit 0' EXIT",
        "shopt -s expand_aliases",
        "alias python='true'",
        "unalias python",
        "source ./unreviewed-shell.sh",
        ". ./unreviewed-shell.sh",
        "enable -n command",
    ):
        mutated = pr.replace(command, f"          {indirection}\n" + command, 1)
        require(mutated != pr, f"PR shell-indirection mutation was a no-op: {indirection}")
        try:
            require_unconditional_pr_admission(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR admission validators must execute unconditionally",
                f"PR shell indirection rejected outside exact guard ({indirection}): {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted shell indirection: {indirection}")
    # Comments and quoted shell text are not themselves control flow.
    comment = pr.replace(
        "          set -euo pipefail\n",
        "          set -euo pipefail\n          # if false; then\n          echo 'if false; then'\n",
        1,
    )
    require_unconditional_pr_admission(comment)
    # All canonical validators, not only the first four recovery gates, must
    # execute in order without an intervening successful early exit.
    first, second = PUBLISH_REVALIDATION_CHAIN[:2]
    left, right = f"          python {first}\n", f"          python {second}\n"
    require(left + right in pr, "strict snapshot PR ordering fixture drift")
    swapped = pr.replace(left + right, right + left, 1)
    missing = pr.replace(
        "          python scripts/validate-memory-os-ops-p0-007-admission-snapshot-negative.py\n",
        "          # snapshot negative skipped\n",
        1,
    )
    extra = pr.replace(
        right,
        right + "          python scripts/unreviewed-admission-validator.py\n",
        1,
    )
    for label, mutated in (("reordered", swapped), ("missing negative", missing), ("extra validator", extra)):
        require(mutated != pr, f"{label} PR admission mutation was a no-op")
        try:
            require_unconditional_pr_admission(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR admission validator execution order drift",
                f"{label} PR admission rejected outside exact ordering guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted {label} admission chain")
    for validator in (first, PUBLISH_REVALIDATION_CHAIN[-1]):
        target = f"          python {validator}\n"
        require(target in pr, f"strict snapshot PR early-exit fixture drift: {validator}")
        mutated = pr.replace(target, "          exit 0\n" + target, 1)
        try:
            require_unconditional_pr_admission(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot PR admission validators must execute unconditionally",
                f"early exit before {validator} rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot PR accepted early exit before {validator}")


def prove_comment_only_commands_rejected() -> None:
    commands = "\n".join(f"          python {validator}" for validator in FULL_ADMISSION_VALIDATORS)
    positive = "jobs:\n  validate:\n    steps:\n      - name: live\n        run: |\n" + commands + "\n"
    require_full_admission_chain(positive, "positive run-step fixture")
    redirected = "jobs:\n  validate:\n    steps:\n      - name: logged\n        run: |\n" + "\n".join(
        f'          python {validator} >> "$log" 2>&1' for validator in FULL_ADMISSION_VALIDATORS
    ) + "\n"
    require_full_admission_chain(redirected, "positive logged validator fixture")
    for validator in FULL_ADMISSION_VALIDATORS:
        for suffix in (" || true", " || :", "; true"):
            masked = positive.replace(f"          python {validator}\n", f"          python {validator}{suffix}\n", 1)
            require(masked != positive, f"{validator} masked fixture was a no-op")
            try:
                require_full_admission_chain(masked, "masked PR validator fixture")
            except Fail as exc:
                require(
                    f"does not execute full admission validator fail-closed: {validator}" in str(exc),
                    f"masked {validator} rejected outside exact fail-closed guard: {exc}",
                )
            else:
                raise Fail(f"strict snapshot PR workflow accepted masked validator: {validator}{suffix}")
    live_else = "jobs:\n  validate:\n    steps:\n      - name: live else\n        run: |\n          if false; then\n          :\n          else\n" + commands + "\n          fi\n"
    require_full_admission_chain(live_else, "positive literal-false else fixture")
    # A conditional exit must not erase validators reachable when the
    # condition is false; an indented unconditional exit must erase them.
    unknown_exit = (
        "jobs:\n  validate:\n    steps:\n      - name: conditional exit\n        run: |\n"
        "          if test \"$SOME_RUNTIME_CONDITION\" = yes; then\n"
        "            exit 0\n          fi\n" + commands + "\n"
    )
    require_full_admission_chain(unknown_exit, "positive conditional exit fixture")
    function_exit = (
        "jobs:\n  validate:\n    steps:\n      - name: inert function exit\n        run: |\n"
        "          revalidate_latest_snapshot() {\n"
        "            exit 0\n          }\n" + commands + "\n"
    )
    require_full_admission_chain(function_exit, "positive uncalled function exit fixture")
    fixtures = (
        ("comment-only", "\n".join(f"# python {validator}" for validator in FULL_ADMISSION_VALIDATORS)),
        ("YAML env literal", "jobs:\n  validate:\n    steps:\n      - name: inert\n        env:\n          TEXT: |\n" + commands + "\n"),
        ("disabled step", "jobs:\n  validate:\n    steps:\n      - name: disabled\n        if: false\n        run: |\n" + commands + "\n"),
        ("heredoc body", "jobs:\n  validate:\n    steps:\n      - name: quoted\n        run: |\n          cat <<'EOF'\n" + commands + "\n          EOF\n"),
        ("unreachable after exit", "jobs:\n  validate:\n    steps:\n      - name: exited\n        run: |\n          exit 0\n" + commands + "\n"),
        ("unreachable after indented exit", "jobs:\n  validate:\n    steps:\n      - name: indented exit\n        run: |\n            exit 0\n" + commands + "\n"),
        ("unreachable after indented exit comment", "jobs:\n  validate:\n    steps:\n      - name: indented exit\n        run: |\n            exit 0 # stop\n" + commands + "\n"),
        ("literal false shell branch", "jobs:\n  validate:\n    steps:\n      - name: dead shell\n        run: |\n          if false; then\n" + commands + "\n          fi\n"),
        ("literal true else branch", "jobs:\n  validate:\n    steps:\n      - name: dead else\n        run: |\n          if true; then\n          :\n          else\n" + commands + "\n          fi\n"),
    )
    for label, fixture in fixtures:
        try:
            require_full_admission_chain(fixture, f"{label} fixture")
        except Fail as exc:
            require(
                "does not execute full admission validator" in str(exc),
                f"{label} fixture rejected outside command-reachability guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot full admission validator accepted {label} references")


def publisher_capture_step_lines(publish: str) -> list[str]:
    lines = publish.splitlines()
    marker = "      - name: Generate and validate strict snapshot"
    starts = [index for index, line in enumerate(lines) if line == marker]
    require(len(starts) == 1, "strict snapshot publisher capture step authority drift")
    start = starts[0]
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("      - ")), len(lines))
    runs = [index for index in range(start + 1, end) if lines[index] == "        run: |"]
    require(len(runs) == 1, "strict snapshot publisher capture executable run block missing")
    return [
        line[10:].strip() for line in lines[runs[0] + 1:end]
        if line.startswith("          ") and line[10:].strip()
        and not line[10:].lstrip().startswith("#")
    ]



def require_publisher_compile_stage(publish: str) -> None:
    """Prove publisher compilation is a live, exact, status-propagating command."""
    lines = publish.splitlines()
    name = "      - name: Generate and validate strict snapshot"
    starts = [index for index, line in enumerate(lines) if line == name]
    require(len(starts) == 1, "strict snapshot publisher compile stage authority drift")
    start = starts[0]
    end = next((index for index in range(start + 1, len(lines))
                if lines[index].startswith("      - ")), len(lines))
    runs = [index for index in range(start + 1, end) if lines[index] == "        run: |"]
    require(len(runs) == 1, "strict snapshot publisher compile stage authority drift")
    body = [line[10:] for line in lines[runs[0] + 1:end]
            if line.startswith("          ") and line[10:].strip()]
    expected = [
        "set +e",
        "log=/tmp/ops-p0-007-admission-snapshot.log",
        ': > "$log"',
        "code=0",
        "python -m py_compile \\",
        *(f"  {path} \\" for path in PR_COMPILE_FILES[:-1]),
        '  >> "$log" 2>&1 || code=$?',
        *(f'if [[ "$code" == "0" ]]; then python {path} >> "$log" 2>&1 || code=$?; fi'
          for path in PUBLISH_REVALIDATION_CHAIN),
        'echo "exit_code=$code" >> "$GITHUB_OUTPUT"',
        'printf "OPS-P0-007 snapshot validation exit code: %s (raw validator log suppressed)\\n" "$code"',
        "exit 0",
    ]
    require(body == expected, "strict snapshot publisher compile stage authority drift")


def prove_publisher_compile_stage_negative(publish: str) -> None:
    require_publisher_compile_stage(publish)
    name = "      - name: Generate and validate strict snapshot\n"
    end_name = "      - name: Commit deterministic strict snapshot\n"
    require(publish.count(name) == publish.count(end_name) == 1,
            "strict snapshot publisher compile fixture step boundary drift")
    before, remainder = publish.split(name, 1)
    step, after = remainder.split(end_name, 1)
    prefix = before + name
    suffix = end_name + after
    def check(label: str, changed: str) -> None:
        require(changed != step, f"{label} publisher compile fixture mutation was a no-op")
        try:
            require_publisher_compile_stage(prefix + changed + suffix)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher compile stage authority drift",
                f"{label} publisher compile fixture rejected outside exact guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted weakened compile stage: {label}")

    first = f"            {PR_COMPILE_FILES[0]} \\\n"
    second = f"            {PR_COMPILE_FILES[1]} \\\n"
    last = f"            {PR_COMPILE_FILES[-2]} \\\n"
    command = "          python -m py_compile \\\n"
    redirect = '            >> "$log" 2>&1 || code=$?\n'
    require(all(step.count(line) == 1 for line in (first, second, last, command, redirect)),
            "strict snapshot publisher compile fixture anchor drift")
    check("missing first argument", step.replace(first, "", 1))
    check("comment-only argument", step.replace(first, "            # " + first.strip() + "\n", 1))
    check("wrong argument", step.replace(first, "            scripts/unreviewed-compile.py \\\n", 1))
    check("reordered arguments", step.replace(first + second, second + first, 1))
    check("missing compile invocation", step.replace(command, "          echo python -m py_compile \\\n", 1))
    check("masked compile failure", step.replace(redirect, '            >> "$log" 2>&1 || true\n', 1))
    check("missing status capture", step.replace(redirect, "", 1))
    check("extra compile argument", step.replace(last, last + "            scripts/unreviewed-compile.py \\\n", 1))
    check("comment inside continuation", step.replace(first, first + "            # breaks shell continuation\n", 1))
    check("early exit before compile", step.replace(command, "          exit 0\n" + command, 1))
    check("duplicate compile", step.replace(command, command + command, 1))
    check("raw CI log", step.replace('          printf "OPS-P0-007 snapshot validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', '          cat "$log"\n', 1))
    check("forged status reset", step.replace(redirect, redirect + "          code=0\n", 1))


def require_publisher_capture_status_chain(publish: str) -> None:
    commands = publisher_capture_step_lines(publish)
    require(
        commands[:4] == ["set +e", "log=/tmp/ops-p0-007-admission-snapshot.log",
                         ': > "$log"', "code=0"],
        "strict snapshot publisher capture startup authority drift",
    )
    require(
        not any(
            re.match(r"^(?:exit|return|exec|set|trap|alias|unalias|shopt|enable|source)(?:\s|$)|^\.\s+", line)
            for line in commands[1:-1]
        ),
        "strict snapshot publisher capture unconditional early termination or shell override",
    )
    expected = [
        f'if [[ "$code" == "0" ]]; then python {validator} >> "$log" 2>&1 || code=$?; fi'
        for validator in PUBLISH_REVALIDATION_CHAIN
    ]
    observed = [line for line in commands if "python scripts/" in line]
    require(
        observed == expected,
        "strict snapshot publisher capture validator status propagation drift",
    )
    require(
        "python -m py_compile \\" in commands
        and '>> "$log" 2>&1 || code=$?' in commands
        and commands.index('>> "$log" 2>&1 || code=$?') < commands.index(expected[0])
        and commands[-3:] == ['echo "exit_code=$code" >> "$GITHUB_OUTPUT"', 'printf "OPS-P0-007 snapshot validation exit code: %s (raw validator log suppressed)\\n" "$code"', "exit 0"],
        "strict snapshot publisher capture output/compile status binding drift",
    )


def prove_publisher_capture_status_negative(publish: str) -> None:
    require_publisher_capture_status_chain(publish)
    for validator in PUBLISH_REVALIDATION_CHAIN:
        original = (
            f'          if [[ "$code" == "0" ]]; then python {validator} '
            '>> "$log" 2>&1 || code=$?; fi\n'
        )
        require(publish.count(original) == 1, f"publisher capture fixture drift: {validator}")
        mutated = publish.replace(original, original.replace(" || code=$?", ""), 1)
        try:
            require_publisher_capture_status_chain(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher capture validator status propagation drift",
                f"{validator} status loss rejected outside exact capture guard: {exc}",
            )
        else:
            raise Fail(f"publisher capture accepted unpropagated failure: {validator}")
    # The intentional final exit 0 is allowed only after publishing the
    # captured status. An earlier exit or option override is not a gate.
    for label, anchor_line, injected in (
        ("early exit before first validator",
         f'          if [[ "$code" == "0" ]]; then python {PUBLISH_REVALIDATION_CHAIN[0]}',
         "          exit 0\n"),
        ("early exit before last validator",
         f'          if [[ "$code" == "0" ]]; then python {PUBLISH_REVALIDATION_CHAIN[-1]}',
         "          exit 0\n"),
        ("shell override",
         "          code=0\n",
         "          set -euo pipefail\n"),
    ):
        if label == "shell override":
            require(publish.count(anchor_line) == 1, f"{label} capture fixture drift")
            mutated = publish.replace(anchor_line, anchor_line + injected, 1)
        else:
            matches = [line for line in publish.splitlines(keepends=True) if line.startswith(anchor_line)]
            require(len(matches) == 1, f"{label} capture fixture drift")
            mutated = publish.replace(matches[0], injected + matches[0], 1)
        try:
            require_publisher_capture_status_chain(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher capture unconditional early termination or shell override",
                f"{label} rejected outside exact capture reachability guard: {exc}",
            )
        else:
            raise Fail(f"publisher capture accepted {label}")
    # The intentional non-errexit capture step must not install an EXIT trap
    # that appends a forged success after its real captured exit_code.
    for indirection in (
        'trap \'echo "exit_code=0" >> "$GITHUB_OUTPUT"\' EXIT',
        'trap \'exit 0\' ERR',
        'source ./unreviewed-shell.sh',
        '. ./unreviewed-shell.sh',
        'shopt -s expand_aliases',
        "alias python='true'",
    ):
        marker = "          code=0\n"
        require(publish.count(marker) == 1, "publisher capture indirection fixture drift")
        mutated = publish.replace(marker, marker + f"          {indirection}\n", 1)
        try:
            require_publisher_capture_status_chain(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher capture unconditional early termination or shell override",
                f"publisher capture indirection rejected outside exact guard ({indirection}): {exc}",
            )
        else:
            raise Fail(f"publisher capture accepted status indirection: {indirection}")
    first, second = PUBLISH_REVALIDATION_CHAIN[:2]
    left = f'          if [[ "$code" == "0" ]]; then python {first} >> "$log" 2>&1 || code=$?; fi\n'
    right = f'          if [[ "$code" == "0" ]]; then python {second} >> "$log" 2>&1 || code=$?; fi\n'
    require(left + right in publish, "publisher capture ordering fixture drift")
    reordered = publish.replace(left + right, right + left, 1)
    for label, mutated, expected in (
        ("reordered validators", reordered, "strict snapshot publisher capture validator status propagation drift"),
        ("forged zero exit", publish.replace('          echo "exit_code=$code" >> "$GITHUB_OUTPUT"',
                                            '          echo "exit_code=0" >> "$GITHUB_OUTPUT"', 1),
         "strict snapshot publisher capture output/compile status binding drift"),
        ("wrong initial status", publish.replace('          code=0\n', '          code=1\n', 1),
         "strict snapshot publisher capture startup authority drift"),
        ("compile failure masked", publish.replace('          >> "$log" 2>&1 || code=$?\n',
                                                    '          >> "$log" 2>&1 || true\n', 1),
         "strict snapshot publisher capture output/compile status binding drift"),
    ):
        require(mutated != publish, f"{label} publisher capture mutation was a no-op")
        try:
            require_publisher_capture_status_chain(mutated)
        except Fail as exc:
            require(str(exc) == expected, f"{label} rejected outside exact capture guard: {exc}")
        else:
            raise Fail(f"publisher capture accepted {label}")


def require_publisher_staging_allowlist(publish: str) -> None:
    # A source-bound publisher is still unsafe if it stages unrelated
    # production authorities or force-pushes the resulting commit.
    commands = [
        line.strip() for line in publish.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        and re.search(r"\bgit[ \t]+(?:add|rm|commit|push)\b", line)
    ]
    expected = [
        "git rm -f docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json 2>/dev/null || true",
        "git add contracts/operations/ops-p0-007-admission-snapshot.v1.json",
        "git add -u docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json 2>/dev/null || true",
        'git commit -m "docs(restore): refresh OPS-P0-007 strict admission snapshot"',
        "if git push origin HEAD:so; then",
        "git add docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json",
        'git commit -m "test(restore): record OPS-P0-007 strict snapshot diagnostic"',
        "if git push origin HEAD:so; then exit 0; fi",
    ]
    require(
        commands == expected,
        "strict snapshot publisher staging/push authority allowlist drift",
    )


def prove_publisher_staging_negative(publish: str) -> None:
    require_publisher_staging_allowlist(publish)
    mutations = (
        ("broad staging",
         "git add contracts/operations/ops-p0-007-admission-snapshot.v1.json",
         "git add -A"),
        ("production status staging",
         "git add contracts/operations/ops-p0-007-admission-snapshot.v1.json",
         "git add contracts/operations/production-operability-status.json"),
        ("force push",
         "          if git push origin HEAD:so; then\n",
         "          if git push --force origin HEAD:so; then\n"),
        ("commit all",
         'git commit -m "docs(restore): refresh OPS-P0-007 strict admission snapshot"',
         'git commit -am "docs(restore): refresh OPS-P0-007 strict admission snapshot"'),
        ("diagnostic authority redirect",
         "git add docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json",
         "git add docs/evidence/backup-restore/production-evidence.json"),
    )
    for label, before, after in mutations:
        require(publish.count(before) == 1, f"{label} publisher staging fixture drift")
        mutated = publish.replace(before, after, 1)
        try:
            require_publisher_staging_allowlist(mutated)
        except Fail as exc:
            require(
                str(exc) == "strict snapshot publisher staging/push authority allowlist drift",
                f"{label} rejected outside exact staging guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted {label}")
    anchor = "          git diff --cached --check\n"
    require(publish.count(anchor) == 1, "publisher extra staging fixture drift")
    mutated = publish.replace(
        anchor,
        "          git add contracts/operations/production-operability-status.json\n" + anchor,
        1,
    )
    try:
        require_publisher_staging_allowlist(mutated)
    except Fail as exc:
        require(
            str(exc) == "strict snapshot publisher staging/push authority allowlist drift",
            f"extra staging rejected outside exact guard: {exc}",
        )
    else:
        raise Fail("strict snapshot publisher accepted extra production status staging")


def require_publisher_revalidation_calls(publish: str) -> None:
    # A function definition or comment is not a call. Preserve the three
    # current retry/finalization call sites in enabled run-step shell bodies.
    commands = "\n".join(executable_run_lines(publish))
    require(
        re.search(r"(?m)^[ \t]*revalidate_latest_snapshot\(\)[ \t]*\{", commands) is not None,
        "strict snapshot publisher missing bounded revalidation function definition",
    )
    calls = re.findall(r"(?m)^[ \t]*revalidate_latest_snapshot[ \t]*(?:#.*)?$", commands)
    require(
        len(calls) >= 3,
        "strict snapshot publisher missing executable bounded revalidation call sites",
    )
    # The required validators must execute inside the called revalidation
    # function. Merely mentioning them in another, never-called function or
    # a separate run step is not proof of bounded latest-source revalidation.
    lines = commands.splitlines()
    starts = [
        index for index, line in enumerate(lines)
        if re.fullmatch(r"revalidate_latest_snapshot\(\)[ \t]*\{", line)
    ]
    require(len(starts) == 1, "strict snapshot publisher revalidation function boundary ambiguous")
    start = starts[0]
    ends = [index for index in range(start + 1, len(lines)) if lines[index] == "}"]
    require(bool(ends), "strict snapshot publisher revalidation function closing boundary missing")
    body = "\n".join(lines[start + 1:ends[0]])
    # A syntactically present validator after an unconditional function return
    # or exit is not executable proof of bounded latest-source revalidation.
    for line in body.splitlines():
        require(
            re.match(r"^[ \t]*(?:return|exit)(?:[ \t;]|$)", line) is None,
            "strict snapshot publisher revalidation contains unconditional early return/exit",
        )
    # The bounded retry must refresh source before executing the full
    # review/snapshot chain. The initial workflow validation is not enough.
    source_refresh = (
        "git fetch origin so",
        "git reset --hard origin/so",
        'SOURCE_SHA="$(git rev-parse HEAD)"',
        "export SOURCE_SHA",
        ': > "$log"',
    )
    live_commands = [line.strip() for line in body.splitlines() if line.strip()]
    require(
        tuple(live_commands[:len(source_refresh)]) == source_refresh,
        "strict snapshot publisher bounded revalidation source refresh order drift",
    )
    expected_chain = [f'python {validator} >> "$log" 2>&1' for validator in PUBLISH_REVALIDATION_CHAIN]
    for validator, expected in zip(PUBLISH_REVALIDATION_CHAIN, expected_chain):
        command = rf"(?m)^  python[ \t]+{re.escape(validator)}(?=[ \t]|$)"
        require(
            re.search(command, body) is not None,
            f"strict snapshot publisher missing executable {validator} inside bounded revalidation",
        )
        require(
            live_commands.count(expected) == 1,
            f"strict snapshot publisher masks or redirects {validator} admission failure",
        )
    require(
        live_commands[len(source_refresh):] == expected_chain,
        "strict snapshot publisher bounded revalidation command order drift",
    )


def prove_publisher_revalidation_call_binding(publish: str) -> None:
    require_publisher_revalidation_calls(publish)
    call_pattern = r"(?m)^([ \t]*)revalidate_latest_snapshot[ \t]*$"
    require(len(re.findall(call_pattern, publish)) == 3, "strict snapshot revalidation fixture call count drift")
    for label, replacement in (
        ("comment-only call", r"\1# revalidate_latest_snapshot"),
        ("echo-only call", r"\1echo revalidate_latest_snapshot"),
    ):
        mutated = re.sub(call_pattern, replacement, publish, count=1)
        try:
            require_publisher_revalidation_calls(mutated)
        except Fail as exc:
            require(
                "missing executable bounded revalidation call sites" in str(exc),
                f"{label} rejected outside intended publisher call-site guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted {label}")

    # A decoy validator in another run step cannot replace the one inside
    # the bounded function, even if global command search still finds it.
    validator = FULL_ADMISSION_VALIDATORS[0]
    original = f'            python {validator} >> "$log" 2>&1'
    require(publish.count(original) == 1, "strict snapshot bounded validator fixture drift")
    decoy = publish.replace(original, f"            # python {validator} moved outside", 1)
    decoy += f"\n      - name: unbound validator decoy\n        run: |\n          python {validator}\n"
    require_full_admission_chain(decoy, "decoy still globally reachable")
    try:
        require_publisher_revalidation_calls(decoy)
    except Fail as exc:
        require(
            f"missing executable {validator} inside bounded revalidation" in str(exc),
            f"unbound validator decoy rejected outside function-binding guard: {exc}",
        )
    else:
        raise Fail("strict snapshot publisher accepted validator outside bounded revalidation")

    function_start = "          revalidate_latest_snapshot() {\n"
    require(publish.count(function_start) == 1, "strict snapshot revalidation entry fixture drift")
    for command in ("return 0", "exit 0"):
        mutated = publish.replace(function_start, function_start + f"            {command}\n", 1)
        try:
            require_publisher_revalidation_calls(mutated)
        except Fail as exc:
            require(
                "revalidation contains unconditional early return/exit" in str(exc),
                f"early {command} rejected outside intended reachability guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted validators after early {command}")

    # Source refresh must precede every validator, including after retries.
    for label, before_line, after_line in (
        ("missing fetch", "git fetch origin so", ": # git fetch origin so"),
        ("missing reset", "git reset --hard origin/so", ": # git reset --hard origin/so"),
        ("stale source SHA", 'SOURCE_SHA="$(git rev-parse HEAD)"', 'SOURCE_SHA="$(git rev-parse github.sha)"'),
        ("missing export", "export SOURCE_SHA", ": # export SOURCE_SHA"),
        ("missing log reset", ': > "$log"', ': # > "$log"'),
    ):
        before_function, function_suffix = publish.split(function_start, 1)
        original = "            " + before_line + "\n"
        replacement = "            " + after_line + "\n"
        require(original in function_suffix, f"{label}: bounded source fixture drift")
        mutated = before_function + function_start + function_suffix.replace(original, replacement, 1)
        try:
            require_publisher_revalidation_calls(mutated)
        except Fail as exc:
            require(
                "bounded revalidation source refresh order drift" in str(exc),
                f"{label} rejected outside source-refresh guard: {exc}",
            )
        else:
            raise Fail(f"strict snapshot publisher accepted {label}")

    # All review and snapshot gates must be ordered, not merely present.
    first, second = PUBLISH_REVALIDATION_CHAIN[2:4]
    left = f'            python {first} >> "$log" 2>&1'
    right = f'            python {second} >> "$log" 2>&1'
    require(publish.count(left) == 1 and publish.count(right) == 1,
            "strict snapshot revalidation ordering fixture drift")
    swapped = publish.replace(left + "\n" + right, right + "\n" + left, 1)
    require(swapped != publish, "strict snapshot revalidation order mutation was a no-op")
    try:
        require_publisher_revalidation_calls(swapped)
    except Fail as exc:
        require(
            "bounded revalidation command order drift" in str(exc),
            f"reordered admission chain rejected outside intended order guard: {exc}",
        )
    else:
        raise Fail("strict snapshot publisher accepted reordered review admission chain")

    # A command that ignores a failed admission cannot count as a gate.
    for validator in PUBLISH_REVALIDATION_CHAIN:
        original = f'            python {validator} >> "$log" 2>&1'
        require(publish.count(original) == 1, f"strict snapshot {validator} command fixture drift")
        for suffix in (" || true", " || :", "; true"):
            mutated = publish.replace(original, original + suffix, 1)
            try:
                require_publisher_revalidation_calls(mutated)
            except Fail as exc:
                require(
                    f"masks or redirects {validator} admission failure" in str(exc),
                    f"masked {validator} rejected outside fail-closed guard: {exc}",
                )
            else:
                raise Fail(f"strict snapshot publisher accepted masked {validator} admission failure")



def readonly_trigger_paths() -> tuple[str, ...]:
    return (
        ".github/workflows/ops-p0-007-admission-snapshot-readonly.yml",
        ".github/workflows/ops-p0-007-admission-snapshot-pr.yml",
        ".github/workflows/ops-p0-007-snapshot-permission-boundary.yml",
        *PR_COMPILE_FILES[-6:],
        "contracts/operations/ops-p0-007-admission-snapshot.v1.json",
        "contracts/operations/operability-admission-inventory.v1.json",
        "contracts/operations/production-operability-status.json",
        "contracts/operations/production-equivalent-environment-*.json",
        "contracts/operations/recovery-objectives-*.json",
        "contracts/operations/backup-restore-*.json",
    )


def require_readonly_trigger_authority(readonly: str) -> None:
    """Both PR and so push must reach the independent readonly gate."""
    paths = [f'      - "{path}"' for path in readonly_trigger_paths()]
    expected = [
        "name: OPS P0 007 Admission Snapshot Readonly",
        "",
        "on:",
        "  pull_request:",
        "    paths:",
        *paths,
        "  push:",
        "    branches: [so]",
        "    paths:",
        *paths,
        "  workflow_dispatch:",
        "",
        "permissions:",
        "  contents: read",
    ]
    require(
        readonly.splitlines()[:len(expected)] == expected,
        "strict snapshot readonly trigger/path authority drift",
    )


def prove_readonly_trigger_negative(readonly: str) -> None:
    require_readonly_trigger_authority(readonly)
    marker = "permissions:\n"
    require(readonly.count(marker) == 1,
            "strict snapshot readonly trigger fixture boundary drift")
    header, tail = readonly.split(marker, 1)
    suffix = marker + tail
    def check(label: str, changed: str) -> None:
        require(changed != header, f"{label} readonly trigger mutation was a no-op")
        try:
            require_readonly_trigger_authority(changed + suffix)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly trigger/path authority drift",
                    f"{label} readonly trigger rejected outside exact guard: {exc}")
        else:
            raise Fail(f"strict snapshot readonly accepted {label}")
    require(header.count("  push:\n") == 1, "readonly push trigger fixture drift")
    before_push, after_push = header.split("  push:\n", 1)
    for path in readonly_trigger_paths():
        line = f'      - "{path}"\n'
        require(before_push.count(line) == after_push.count(line) == 1,
                f"readonly trigger path fixture drift: {path}")
        check(f"missing PR path {path}", before_push.replace(line, "", 1) + "  push:\n" + after_push)
        check(f"missing push path {path}", before_push + "  push:\n" + after_push.replace(line, "", 1))
    mutations = (
        ("missing PR event", header.replace("  pull_request:\n", "  # PR event removed\n", 1)),
        ("wrong PR event", header.replace("  pull_request:\n", "  pull_request_target:\n", 1)),
        ("missing push event", header.replace("  push:\n", "  # push event removed\n", 1)),
        ("wrong push branch", header.replace("    branches: [so]\n", "    branches: [main]\n", 1)),
        ("missing manual dispatch", header.replace("  workflow_dispatch:\n", "  # manual dispatch removed\n", 1)),
        ("extra schedule", header.replace("  workflow_dispatch:\n",
            "  schedule:\n    - cron: '0 0 * * *'\n  workflow_dispatch:\n", 1)),
        ("missing PR paths", header.replace("  pull_request:\n    paths:\n",
            "  pull_request:\n    # paths disabled\n", 1)),
        ("missing push paths", header.replace("    branches: [so]\n    paths:\n",
            "    branches: [so]\n    # paths disabled\n", 1)),
    )
    for label, mutated in mutations:
        check(label, mutated)


def require_readonly_workflow_authority(readonly: str) -> None:
    """Require the independent read-only workflow to execute immutable gates."""
    diagnostic = "strict snapshot readonly workflow authority drift"
    try:
        require_readonly_pr_permissions(readonly)
    except Fail as exc:
        raise Fail(diagnostic) from exc
    lines = readonly.splitlines()
    header = ["jobs:", "  readonly:", "    runs-on: ubuntu-latest",
              "    timeout-minutes: 10", "    steps:"]
    starts = [i for i, line in enumerate(lines) if line == "  readonly:"]
    require(len(starts) == 1 and starts[0] > 0 and
            lines[starts[0] - 1:starts[0] + 4] == header, diagnostic)
    steps: list[list[str]] = []
    for line in lines[starts[0] + 4:]:
        if line.startswith("      - "):
            steps.append([line])
        elif steps:
            steps[-1].append(line)
    require(len(steps) == 3, diagnostic)
    require(
        steps[0] == [
            "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "        with:",
            "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}",
            "          fetch-depth: 0",
            "          persist-credentials: false",
        ] and steps[1] == [
            "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
            "        with:",
            '          python-version: "3.12"',
        ] and steps[2][:2] == [
            "      - name: Prove deterministic snapshot authority immutability",
            "        run: |",
        ], diagnostic,
    )
    # YAML keys at step/job scope after the run block are not shell commands.
    # They can silently skip or de-fang the entire integrity gate.
    require(
        all(not line.strip() or line.startswith("          ")
            for line in steps[2][2:]),
        diagnostic,
    )
    body = [line[10:].strip() for line in steps[2][2:]
            if line.startswith("          ") and line[10:].strip()]
    require(body.count("authorities=(") == 1,
            "strict snapshot readonly workflow authority drift")
    authority_start = body.index("authorities=(")
    require(
        body[authority_start:authority_start + len(READONLY_PROTECTED_AUTHORITIES) + 2]
        == ["authorities=(", *READONLY_PROTECTED_AUTHORITIES, ")"],
        "strict snapshot readonly workflow authority drift",
    )
    loop = 'for authority in "${authorities[@]}"; do'
    starts = [i for i, line in enumerate(body) if line == loop]
    require(len(starts) == 2,
            "strict snapshot readonly workflow authority drift")
    require(
        body[starts[0]:starts[0] + 4] == [
            loop, 'test -f "$authority"', READONLY_HASH_LINE, 'done > "$snapshot"',
        ] and body[starts[1]:starts[1] + 3] == [
            loop, READONLY_HASH_LINE, 'done > "$current"',
        ],
        "strict snapshot readonly workflow authority drift",
    )
    # No shell hook may replace errexit, validator commands, or the final
    # before/after authority comparison. The single reviewed EXIT trap only
    # cleans the two temporary digest files.
    control = re.compile(
        r"^(?:if|elif|else|fi|while|until|case|esac|function|eval|exec|exit|return|break|continue|alias|unalias|shopt|enable|source)\b"
        r"|^\.\s+|^bash\s+-c\b|^hash\b|^[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{"
    )
    require(
        not any(control.match(line) for line in body)
        and [line for line in body if re.match(r"^set(?:\s|$)", line)]
        == ["set -euo pipefail"]
        and [line for line in body if line.startswith("trap ")]
        == ['trap \'rm -f "$snapshot" "$current"\' EXIT'],
        "strict snapshot readonly workflow authority drift",
    )
    compiled = PR_COMPILE_FILES[-6:]
    require(
        body[:10] == [
            "set -euo pipefail",
            'expected="' + READONLY_SOURCE_REF + '"',
            '[[ "${{ github.event_name }}" != "pull_request" || "${{ github.event.pull_request.head.sha }}" =~ ^[0-9a-f]{40}$ ]]',
            '[[ "${{ github.event_name }}" != "workflow_dispatch" || "$GITHUB_REF" == "refs/heads/so" ]]',
            '[[ "${{ github.event_name }}" == "pull_request" || "${{ github.event_name }}" == "push" || "${{ github.event_name }}" == "workflow_dispatch" ]]',
            '[[ "${{ github.event_name }}" != "push" || "$GITHUB_REF" == "refs/heads/so" ]]',
            '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]',
            'test -n "$expected"',
            'test "$(git rev-parse HEAD)" = "$expected"',
            'test -z "$(git status --porcelain --untracked-files=all)"',
        ] and body.count("python -m py_compile \\") == 1
        and body.count('for authority in "${authorities[@]}"; do') == 2
        and body.count('done > "$snapshot"') == 1
        and body.count('done > "$current"') == 1,
        diagnostic,
    )
    compile_index = body.index("python -m py_compile \\")
    expected_compile = [
        "python -m py_compile \\",
        *(f"{path} \\" for path in compiled[:-1]),
        compiled[-1],
        *(f"python {path}" for path in compiled),
    ]
    require(body[compile_index:compile_index + len(expected_compile)] == expected_compile, diagnostic)
    require(
        [line for line in body if line.startswith("python scripts/")]
        == [f"python {path}" for path in compiled],
        diagnostic,
    )
    require(
        body[-4:] == [
            'diff -u "$snapshot" "$current"',
            "git diff --check",
            "git diff --exit-code",
            'test -z "$(git status --porcelain --untracked-files=all)"',
        ] and not any(line.startswith(("exit ", "return ", "set +", "source ", "alias "))
                      for line in body),
        diagnostic,
    )


def prove_readonly_workflow_negative(readonly: str) -> None:
    require_readonly_workflow_authority(readonly)
    # Bind the reviewed immutable bootstrap and credential isolation with
    # dedicated negative fixtures, separate from shell-body integrity proofs.
    bootstrap_cases = (
        ("floating checkout", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4"),
        ("substituted checkout", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@11d5960a326750d5838078e36cf38b85af677263"),
        ("floating setup", "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "actions/setup-python@v5"),
        ("persisted credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("missing credential isolation", "          persist-credentials: false\n", ""),
    )
    for label, before, after in bootstrap_cases:
        require(readonly.count(before) == 1, f"strict snapshot readonly bootstrap fixture drift: {label}")
        mutated = readonly.replace(before, after, 1)
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"readonly bootstrap rejected outside exact guard ({label}): {exc}")
        else:
            raise Fail(f"strict snapshot readonly accepted bootstrap mutation: {label}")
    # An absent PR head must not silently validate the merge/event SHA.
    # Manual dispatch from a non-so ref must also fail before any validator.
    source_identity_lines = (
        ("missing PR-head format guard",
         '          [[ "${{ github.event_name }}" != "pull_request" || "${{ github.event.pull_request.head.sha }}" =~ ^[0-9a-f]{40}$ ]]\n'),
        ("missing dispatch ref guard",
         '          [[ "${{ github.event_name }}" != "workflow_dispatch" || "$GITHUB_REF" == "refs/heads/so" ]]\n'),
        ("missing event-family whitelist",
         '          [[ "${{ github.event_name }}" == "pull_request" || "${{ github.event_name }}" == "push" || "${{ github.event_name }}" == "workflow_dispatch" ]]\n'),
        ("missing push ref guard",
         '          [[ "${{ github.event_name }}" != "push" || "$GITHUB_REF" == "refs/heads/so" ]]\n'),
        ("missing event SHA format guard",
         '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n'),
    )
    for label, line in source_identity_lines:
        require(readonly.count(line) == 1, f"strict snapshot readonly source fixture drift: {label}")
        mutated = readonly.replace(line, "", 1)
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"readonly source guard rejected outside exact validator ({label}): {exc}")
        else:
            raise Fail(f"strict snapshot readonly accepted source-identity mutation: {label}")
    marker = "      - name: Prove deterministic snapshot authority immutability\n"
    negative = "          python scripts/validate-memory-os-ops-p0-007-admission-snapshot-negative.py\n"
    diff = '          diff -u "$snapshot" "$current"\n'
    compile_line = "          python -m py_compile \\\n"
    require(all(readonly.count(x) == 1 for x in (marker, negative, diff, compile_line)),
            "strict snapshot readonly fixture anchor drift")
    # The before/after digest+mode snapshot must cover every reviewed
    # authority, including the separate human promotion-review registry.
    for path in READONLY_PROTECTED_AUTHORITIES:
        original = f"            {path}\n"
        require(readonly.count(original) == 1,
                f"readonly protected authority fixture drift: {path}")
        mutated = readonly.replace(original, "            # protected authority omitted\n", 1)
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"missing protected authority rejected outside exact guard ({path}): {exc}")
        else:
            raise Fail(f"readonly accepted missing protected authority: {path}")
    # Both hash loops must actually hash bytes and modes, not merely iterate
    # over the reviewed authority list or write two identical fake snapshots.
    hash_command = "          " + READONLY_HASH_LINE + "\n"
    require(readonly.count(hash_command) == 2,
            "strict snapshot readonly hash fixture anchor drift")
    hash_mutations = (
        ("fake content digest", hash_command.replace("sha256sum", "echo")),
        ("fake mode", hash_command.replace("stat -c", "echo")),
        ("comment-only hash", "          # digest omitted\n"),
        ("masked hash", hash_command.rstrip("\n") + " || true\n"),
    )
    for label, substitute in hash_mutations:
        mutated = readonly.replace(hash_command, substitute, 1)
        require(mutated != readonly, f"{label} readonly hash mutation was a no-op")
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"{label} readonly hash rejected outside exact guard: {exc}")
        else:
            raise Fail(f"readonly accepted {label}")
    missing_existence = readonly.replace(
        '            test -f "$authority"\n', "            # existence not checked\n", 1
    )
    require(missing_existence != readonly, "readonly existence mutation was a no-op")
    try:
        require_readonly_workflow_authority(missing_existence)
    except Fail as exc:
        require(str(exc) == "strict snapshot readonly workflow authority drift",
                f"readonly existence rejected outside exact guard: {exc}")
    else:
        raise Fail("readonly accepted missing protected-file existence check")
    # A later shell trap or alias can make an otherwise correct validator
    # list appear successful without executing its reviewed failure boundary.
    shell_anchor = "          python -m py_compile \\\n"
    require(readonly.count(shell_anchor) == 1,
            "strict snapshot readonly shell fixture anchor drift")
    for command in (
        "trap 'exit 0' ERR",
        "trap 'exit 0' EXIT",
        "source ./unreviewed-shell.sh",
        ". ./unreviewed-shell.sh",
        "alias python='true'",
        "shopt -s expand_aliases",
        "set +e",
        "exit 0",
        "eval 'true'",
        "if false; then",
        "python() { :; }",
        "git () { :; }",
        "sha256sum() { echo forged; }",
        "hash -p /bin/true python",
    ):
        mutated = readonly.replace(shell_anchor, f"          {command}\n" + shell_anchor, 1)
        require(mutated != readonly, f"{command} readonly shell mutation was a no-op")
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"{command} readonly shell rejected outside exact guard: {exc}")
        else:
            raise Fail(f"readonly accepted shell override: {command}")
    # A trailing YAML step/job property is outside the run scalar even when
    # all required commands remain textually intact.
    final_clean = '          test -z "$(git status --porcelain --untracked-files=all)"\n'
    require(readonly.endswith(final_clean),
            "strict snapshot readonly trailing metadata fixture anchor drift")
    for label, metadata in (
        ("nonfatal step", "        continue-on-error: true\n"),
        ("disabled step", "        if: false\n"),
        ("shell override", "        shell: bash {0}\n"),
        ("nonfatal job", "    continue-on-error: true\n"),
        ("disabled job", "    if: false\n"),
    ):
        mutated = readonly + metadata
        require(mutated != readonly, f"{label} readonly mutation was a no-op")
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"{label} readonly metadata rejected outside exact guard: {exc}")
        else:
            raise Fail(f"strict snapshot readonly accepted trailing YAML metadata: {label}")
    mutations = (
        ("write grant", readonly.replace("permissions:\n  contents: read\n",
                                         "permissions:\n  contents: write\n", 1)),
        ("disabled job", readonly.replace("    runs-on: ubuntu-latest\n",
                                          "    if: false\n    runs-on: ubuntu-latest\n", 1)),
        ("nonfatal job", readonly.replace("    runs-on: ubuntu-latest\n",
                                          "    continue-on-error: true\n    runs-on: ubuntu-latest\n", 1)),
        ("unreviewed action", readonly.replace(marker, "      - uses: unreviewed/action@v1\n" + marker, 1)),
        ("disabled run", readonly.replace(marker, marker + "        if: false\n", 1)),
        ("wrong setup", readonly.replace('          python-version: "3.12"\n',
                                          '          python-version: "3.11"\n', 1)),
        ("compile echo", readonly.replace(compile_line, "          echo python -m py_compile \\\n", 1)),
        ("missing negative", readonly.replace(negative, "          # negative skipped\n", 1)),
        ("missing diff", readonly.replace(diff, "          # diff skipped\n", 1)),
        ("masked diff", readonly.replace(diff, diff.rstrip("\n") + " || true\n", 1)),
        ("early exit", readonly.replace(compile_line, "          exit 0\n" + compile_line, 1)),
    )
    for label, mutated in mutations:
        require(mutated != readonly, f"{label} readonly mutation was a no-op")
        try:
            require_readonly_workflow_authority(mutated)
        except Fail as exc:
            require(str(exc) == "strict snapshot readonly workflow authority drift",
                    f"{label} readonly rejected outside exact guard: {exc}")
        else:
            raise Fail(f"strict snapshot readonly accepted {label}")


def require_readonly_pr_permissions(workflow: str) -> None:
    # GitHub accepts 'permissions: write-all'; banning 'contents: write' alone
    # does not prevent a PR workflow from receiving a write-capable token.
    # Normalize only trailing YAML comments; compact/quoted permission values
    # are still real GitHub Actions grants and must not bypass the guard.
    active = "\n".join(line.split("#", 1)[0] for line in workflow.splitlines())
    require(
        re.search(r"(?m)^[ \t]*permissions[ \t]*:[ \t]*['\"]?write-all['\"]?[ \t]*$", active) is None,
        "strict snapshot PR workflow must never use permissions: write-all",
    )
    require(
        re.search(r"(?m)^permissions: *\n +contents: *read(?: *(?:#.*)?)?$", workflow) is not None,
        "strict snapshot PR workflow must declare top-level contents: read",
    )
    require(
        re.search(r"(?m)\bcontents[ \t]*:[ \t]*['\"]?write['\"]?(?=[ \t]*$|[ \t]*[,}])", active) is None,
        "strict snapshot PR workflow must never receive contents: write",
    )
    scopes = "|".join(re.escape(scope) for scope in GITHUB_PERMISSION_SCOPES)
    scope_write = rf"""(?m)(?<![\w-])['"]?(?:{scopes})['"]?[ \t]*:[ \t]*['"]?write['"]?(?=[ \t]*(?:[,}}]|$))"""
    require(
        re.search(scope_write, active) is None,
        "strict snapshot PR workflow must never receive a write-capable permission scope",
    )


def prove_write_all_permissions_rejected() -> None:
    require_readonly_pr_permissions("permissions:\n  contents: read\n")
    for fixture in (
        "permissions: write-all\n# contents: read\n",
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions: write-all\n",
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions: 'write-all'\n",
    ):
        try:
            require_readonly_pr_permissions(fixture)
        except Fail as exc:
            require("permissions: write-all" in str(exc), f"write-all rejected outside permission guard: {exc}")
        else:
            raise Fail("strict snapshot PR workflow accepted write-all permissions")


    for fixture in (
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions:\n      contents:write\n",
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions: {contents:write}\n",
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions:\n      contents: \"write\"\n",
    ):
        try:
            require_readonly_pr_permissions(fixture)
        except Fail as exc:
            require("contents: write" in str(exc), f"compact write grant rejected outside permission guard: {exc}")
        else:
            raise Fail("strict snapshot PR workflow accepted compact or quoted contents-write permission")

    # Preserve a positive read-only control even when comments mention writes.
    require_readonly_pr_permissions("permissions:\n  contents: read\n# actions: write\n")
    for fixture in (
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions:\n      actions: write\n",
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions: {id-token:write}\n",
        'permissions:\n  contents: read\njobs:\n  check:\n    permissions: {"pull-requests": "write"}\n',
        "permissions:\n  contents: read\njobs:\n  check:\n    permissions:\n      security-events: 'write'\n",
    ):
        try:
            require_readonly_pr_permissions(fixture)
        except Fail as exc:
            require(
                "write-capable permission scope" in str(exc),
                f"non-contents write grant rejected outside scope guard: {exc}",
            )
        else:
            raise Fail("strict snapshot PR workflow accepted a non-contents write permission")



def prove_snapshot_permission_gate_source_negatives() -> None:
    """Independently bind the complete permission-gate workflow executable bytes."""
    require_canonical_workflow(
        SNAPSHOT_PERMISSION_WORKFLOW,
        Path(".github/workflows/ops-p0-007-snapshot-permission-boundary.yml"),
    )
    source = SNAPSHOT_PERMISSION_WORKFLOW.read_text(encoding="utf-8")

    def require_reviewed_blob(candidate: str) -> None:
        payload = candidate.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        require(hashlib.sha1(git_blob).hexdigest() == REVIEWED_SNAPSHOT_PERMISSION_WORKFLOW_BLOB_SHA,
                "strict snapshot permission CI complete source drift")

    require_reviewed_blob(source)
    cases = (
        ("floating-checkout", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4"),
        ("persisted-credentials", "persist-credentials: false", "persist-credentials: true"),
        ("missing-so-ref", 'test "$GITHUB_REF" = "refs/heads/so"', "true"),
        ("missing-source-sha-format", '[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]', "true"),
        ("skipped-permission-validator", "python scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py", "echo UNREVIEWED"),
        ("injected-shell", "          python -m py_compile scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py",
         "          echo UNREVIEWED\n          python -m py_compile scripts/validate-memory-os-ops-p0-007-admission-snapshot-workflow-permissions-negative.py"),
    )
    for label, before, after in cases:
        require(source.count(before) == 1, f"strict snapshot permission gate fixture drift: {label}")
        mutated = source.replace(before, after, 1)
        require(mutated != source, f"strict snapshot permission gate fixture unchanged: {label}")
        try:
            require_reviewed_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"strict snapshot permission gate source mutation accepted: {label}")



def prove_snapshot_diagnostic_redaction_runtime(publish: str) -> None:
    """Execute the real diagnostic writer in a sandbox without touching repository authority."""
    start, end = "          python - <<'PY'\n", "          PY\n"
    require(publish.count(start) == 1 and publish.count(end) == 1,
            "strict snapshot diagnostic writer not uniquely reachable")
    inline = publish.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="strict-snapshot-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_SHA": "e" * 40, "SNAPSHOT_EXIT_CODE": "23",
                    "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_SNAPSHOT"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                capture_output=True, text=True, check=False)
        require(result.returncode == 0,
                "strict snapshot isolated diagnostic failed: " + result.stderr[:500])
        path = Path(directory) / "docs/fixtures/memory-os-operability/ops-p0-007-admission-snapshot-diagnostic.last.json"
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw)
        require(value.get("output") == "REDACTED: strict OPS-P0-007 snapshot validation failed; raw output withheld",
                "strict snapshot diagnostic persisted raw validator output")
        require(value.get("sourceCommitSha") == "e" * 40 and value.get("exitCode") == 23,
                "strict snapshot diagnostic source/exit binding drift")
        for field in ("containsSecrets", "generationCreated", "objectiveCreated", "requestCreated",
                      "restoreExecuted", "productionEvidence", "productionReady"):
            require(value.get(field) is False, "strict snapshot diagnostic non-production drift: " + field)
        require("CANARY_DO_NOT_PERSIST_SNAPSHOT" not in raw,
                "strict snapshot diagnostic persisted synthetic canary")

        # The source guard must reject removal of the actual final-path symlink precondition.
        symlink_guard = "          if path.is_symlink():\n"
        require(publish.count(symlink_guard) == 1,
                "strict snapshot diagnostic symlink guard not unique")
        try:
            validate_atomic_diagnostic_publication(publish.replace(symlink_guard, "", 1))
        except Fail as exc:
            require("if path.is_symlink():" in str(exc),
                    "strict snapshot symlink mutation rejected outside intended guard")
        else:
            raise Fail("strict snapshot diagnostic accepted removed symlink guard")
        path.chmod(0o640)
        positive = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                  capture_output=True, text=True, check=False, timeout=15)
        require(positive.returncode == 0 and stat.S_IMODE(path.stat().st_mode) == 0o640,
                "strict snapshot diagnostic failed existing mode preservation")
        previous = path.read_bytes()
        for label, anchor in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            require(script.count(anchor) == 1, "strict snapshot diagnostic fault anchor drift: " + label)
            mutated = script.replace(anchor, "raise OSError('synthetic snapshot " + label + " failure')", 1)
            outcome = subprocess.run([sys.executable, "-c", mutated], cwd=directory, env=env,
                                     capture_output=True, text=True, check=False, timeout=15)
            require(outcome.returncode != 0 and "synthetic snapshot " + label + " failure" in outcome.stderr,
                    "strict snapshot diagnostic intended fault not reached: " + label)
            require(path.read_bytes() == previous and stat.S_IMODE(path.stat().st_mode) == 0o640,
                    "strict snapshot diagnostic failure changed previous bytes/mode: " + label)
            require(not list(path.parent.glob(".ops-p0-007-admission-snapshot-diagnostic.last.json.*.tmp")),
                    "strict snapshot diagnostic failure leaked temporary file: " + label)
        outside = Path(directory) / "external-snapshot-canary"
        outside.write_bytes(b"EXTERNAL_SNAPSHOT_CANARY")
        path.unlink()
        path.symlink_to(outside)
        outcome = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                 capture_output=True, text=True, check=False, timeout=15)
        require(outcome.returncode != 0 and "target must not be a symlink" in outcome.stderr,
                "strict snapshot diagnostic accepted symlink target")
        require(path.is_symlink() and outside.read_bytes() == b"EXTERNAL_SNAPSHOT_CANARY",
                "strict snapshot diagnostic followed external symlink")
        require(not list(path.parent.glob(".ops-p0-007-admission-snapshot-diagnostic.last.json.*.tmp")),
                "strict snapshot diagnostic symlink failure leaked temporary file")

    print("PASS: strict OPS-P0-007 diagnostic redaction/atomic runtime (5 cases)")


def main() -> int:
    prove_snapshot_permission_gate_source_negatives()
    require_canonical_workflow(PR_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot-pr.yml"))
    require_canonical_workflow(PUBLISH_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot.yml"))
    require_canonical_workflow(READONLY_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot-readonly.yml"))
    prove_readonly_workflow_negative(READONLY_WORKFLOW.read_text(encoding="utf-8"))
    prove_readonly_trigger_negative(READONLY_WORKFLOW.read_text(encoding="utf-8"))
    prove_symlink_rejected()
    prove_comment_only_commands_rejected()
    prove_pr_shell_fail_closed_negative(PR_WORKFLOW.read_text(encoding="utf-8"))
    prove_pr_conditional_admission_rejected(PR_WORKFLOW.read_text(encoding="utf-8"))
    prove_write_all_permissions_rejected()
    pr = PR_WORKFLOW.read_text(encoding="utf-8")
    publish = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    prove_checkout_comment_bypass_rejected(pr, publish)
    prove_pr_source_verification_negative(pr)
    prove_pr_compile_step_negative(pr)
    prove_pr_drift_rejection_negative(pr)
    prove_pr_job_execution_policy_negative(pr)
    prove_pr_step_allowlist_negative(pr)
    prove_pr_trigger_negative(pr)
    prove_publisher_trigger_negative(publish)
    prove_publisher_source_capture_negative(publish)
    prove_publisher_job_execution_policy_negative(publish)
    prove_publisher_step_allowlist_negative(publish)

    require("pull_request:" in pr, "read-only strict snapshot PR workflow must be pull-request scoped")
    require_readonly_pr_permissions(pr)
    require("pull_request_target" not in pr, "strict snapshot PR workflow must not use pull_request_target")
    require_exact_checkout_ref(pr, "${{ github.event.pull_request.head.sha }}", "strict snapshot PR workflow")
    require("git diff --exit-code -- contracts/operations/ops-p0-007-admission-snapshot.v1.json" in pr, "strict snapshot PR workflow must reject deterministic authority drift")
    require("git push" not in pr, "strict snapshot PR workflow must not publish authority")
    require_full_admission_chain(pr, "strict snapshot PR workflow")

    require("contents: write" in publish, "strict snapshot publication workflow requires explicit contents: write")
    require("pull_request:" not in publish, "strict snapshot publication workflow must not run on pull requests")
    require("pull_request_target" not in publish, "strict snapshot publication workflow must not use pull_request_target")
    require_exact_checkout_ref(publish, "${{ github.sha }}", "strict snapshot publication workflow")
    require("SOURCE_SHA" in publish, "strict snapshot publication workflow must capture source authority")
    require("git rev-parse origin/so" in publish, "strict snapshot publication workflow must compare publication authority with origin/so")
    require("refusing stale strict snapshot" in publish, "strict snapshot publication workflow must fail closed on stale authority")
    require("refusing stale diagnostic" in publish, "strict snapshot publication workflow must fail closed on stale diagnostics")
    prove_publisher_capture_status_negative(publish)
    prove_publisher_compile_stage_negative(publish)
    prove_publisher_staging_negative(publish)
    prove_publisher_revalidation_call_binding(publish)
    prove_publisher_shell_fail_closed_negative(publish)
    require_full_admission_chain(publish, "strict snapshot publication workflow")
    prove_diagnostic_comment_and_dead_code_rejected(publish)
    prove_diagnostic_unconditional_exit_rejected(publish)
    prove_diagnostic_privacy_boundary_rejected(publish)
    prove_snapshot_diagnostic_redaction_runtime(publish)

    print("Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS")
    print("snapshot permission gate complete-source mutations rejected: 6")
    print("pull request write token exposed: false")
    print("top-level read-only permissions and write-all rejection proven: true")
    print("pull request authority publication allowed: false")
    print("full recovery objective admission validation required: true")
    print("full reviewed drill request admission validation required: true")
    print("full request-bound generation evidence validation required: true")
    print("full typed eight-domain admission validation required: true")
    print("exact-source publication CAS required: true")
    print("crash-safe mode-preserving diagnostic publication required: true")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError) as exc:
        print(f"OPS-P0-007 SNAPSHOT WORKFLOW PERMISSION NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
