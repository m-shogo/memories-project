#!/usr/bin/env python3
"""Prove strict OPS-P0-007 snapshot PR validation is read-only and publication remains source-bound."""

from __future__ import annotations

import ast
import re
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot-pr.yml"
PUBLISH_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot.yml"
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
        "output": "text[-12000:]",
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
        ("log bound", "'output': text[-12000:]", "'output': text"),
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
    require(
        checkout_steps == ["actions/checkout@v4"],
        f"{label} checkout must bind to exact event source SHA",
    )
    matches = re.findall(
        r"(?m)^      - uses: actions/checkout@v4[ \t]*\n        with:[ \t]*\n          ref:[ \t]*(.+?)[ \t]*$",
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
        for extra_ref in ("actions/checkout@v4", "actions/checkout@v3", "actions/checkout@v4.2.0", "actions/checkout@main"):
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
            '          test -z "$(git status --porcelain)"\n',
            '          true\n          test -z "$(git status --porcelain)"\n',
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
            not any(re.match(r"^set(?:\s|$)", command) for command in active[1:]),
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
        for override in ("set +e", "set +u", "set +o pipefail", "set -e +o pipefail"):
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


def require_publisher_capture_status_chain(publish: str) -> None:
    commands = publisher_capture_step_lines(publish)
    require(
        commands[:4] == ["set +e", "log=/tmp/ops-p0-007-admission-snapshot.log",
                         ': > "$log"', "code=0"],
        "strict snapshot publisher capture startup authority drift",
    )
    require(
        not any(
            re.match(r"^(?:exit|return|exec|set)(?:\s|$)", line)
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
        and commands[-3:] == ['echo "exit_code=$code" >> "$GITHUB_OUTPUT"', 'cat "$log"', "exit 0"],
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



def main() -> int:
    require_canonical_workflow(PR_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot-pr.yml"))
    require_canonical_workflow(PUBLISH_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot.yml"))
    prove_symlink_rejected()
    prove_comment_only_commands_rejected()
    prove_pr_shell_fail_closed_negative(PR_WORKFLOW.read_text(encoding="utf-8"))
    prove_pr_conditional_admission_rejected(PR_WORKFLOW.read_text(encoding="utf-8"))
    prove_write_all_permissions_rejected()
    pr = PR_WORKFLOW.read_text(encoding="utf-8")
    publish = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
    prove_checkout_comment_bypass_rejected(pr, publish)
    prove_pr_source_verification_negative(pr)

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
    prove_publisher_staging_negative(publish)
    prove_publisher_revalidation_call_binding(publish)
    prove_publisher_shell_fail_closed_negative(publish)
    require_full_admission_chain(publish, "strict snapshot publication workflow")
    prove_diagnostic_comment_and_dead_code_rejected(publish)
    prove_diagnostic_unconditional_exit_rejected(publish)
    prove_diagnostic_privacy_boundary_rejected(publish)

    print("Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS")
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
