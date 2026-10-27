#!/usr/bin/env python3
"""Authenticate generation binding CI bootstrap, writer event/ref and source."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/backup-restore-generation-binding.yml"
INDEPENDENT = ".github/workflows/backup-restore-generation-binding-source-negative.yml"
SELF = "scripts/validate-memory-os-backup-restore-generation-binding-source-workflow-negative.py"
BINDING_NEGATIVE = "scripts/validate-memory-os-backup-restore-generation-binding-negative.py"
REVIEWED_PUBLISHER = "d01915e43432927f97c9f15d3243200f1a6a5622"
REVIEWED_INDEPENDENT = "bd93725cf6b91fed44a47bd8c6a0bae8507893ab"
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
MAIN_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("checkout SHA", CHECKOUT, 2),
    ("setup SHA", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("writer branch", PUSH_REF, 1),
    ("writer event", EVENT, 1),
    ("SHA format", SHA_FORMAT, 2),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("PR/writer self execution", "\n          python " + SELF + "\n", 2),
    ("retry self execution", "\n            python " + SELF + "\n", 1),
    ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', 2),
    ("PR checkout source", 'ref: ' + D + '{{ github.event.pull_request.head.sha }}', 1),
    ("writer checkout source", 'ref: ' + D + '{{ github.sha }}', 1),
    ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 1),
    ("capture step", "      - name: Capture exact generation binding authority source\n", 1),
    ("latest reset", "            git reset --hard origin/so\n", 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("writer write token", "      contents: write\n", 1),
    ("diagnostic fixed redaction", "              'output': 'REDACTED: generation binding validation failed; consult CI job logs',\n", 1),
    ("raw CI log suppression", '          printf "Generation binding validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', 1),
    ("no raw diagnostic tail", "text[-12000:]", 0),
    ("no raw CI log echo", '          cat "$log"\n', 0),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("self trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", PUSH_REF, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read token", "  contents: read\n", 2),
    ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("generation binding CI source missing or substituted: " + relative) from exc


def validate(publisher: str, independent: str) -> None:
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("generation binding " + name + " source drift: " + label)
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != digest:
            raise SystemExit("generation binding " + name + " complete source drift")


def runtime(publisher: str, independent: str) -> None:
    for name, content in (("publisher", publisher), ("independent", independent)):
        for label, command, key, value, allow in (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR absent", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if content.count(command) != 1:
                raise SystemExit("generation binding " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("generation binding " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("generation binding writer event runtime drift: " + event)
    print("PASS: generation binding publisher/independent PR-push branch runtime (12 cases), writer event runtime (4 cases)")


def runtime_sha_proof(publisher: str, independent: str) -> None:
    """Execute reviewed generation-binding SHA admission with malformed inputs."""
    cases = (
        ("lowercase hex", "a" * 40, True),
        ("numeric hex", "0" * 40, True),
        ("short SHA", "a" * 39, False),
        ("long SHA", "a" * 41, False),
        ("uppercase SHA", "A" * 40, False),
        ("nonhex SHA", "g" * 40, False),
        ("empty SHA", "", False),
        ("literal shell substitution", "$(echo unexpected)", False),
    )
    for source_label, source_text, count in (
        ("publisher", publisher, 2),
        ("independent", independent, 1),
    ):
        if source_text.count(SHA_FORMAT) != count:
            raise SystemExit("generation binding SHA predicate unreachable: " + source_label)
        for label, value, allowed in cases:
            command = 'expected="${PROBE_SHA:-}"\n' + SHA_FORMAT
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}
            result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
            if (result.returncode == 0) != allowed:
                raise SystemExit("generation binding SHA predicate drift: " + source_label + " " + label)
    print(f"PASS: generation binding publisher/independent SHA runtime ({len(cases) * 2} cases)")

def runtime_diagnostic_redaction(publisher: str) -> None:
    """Execute the generation-binding inline diagnostic writer in isolation."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("generation binding diagnostic writer not uniquely reachable")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="generation-binding-diagnostic-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "a" * 40,
            "RESTORE_EXIT_CODE": "31",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_JKL",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise SystemExit("generation binding isolated diagnostic failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/backup-restore-generation-reconcile-diagnostic.last.json"
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload.get("output") != "REDACTED: generation binding validation failed; consult CI job logs":
            raise SystemExit("generation binding diagnostic persisted raw validator output")
        if payload.get("sourceCommitSha") != "a" * 40 or payload.get("exitCode") != 31:
            raise SystemExit("generation binding diagnostic source/exit drift")
        if payload.get("containsSecrets") is not False or payload.get("productionEquivalentRestoreEvidence") is not False:
            raise SystemExit("generation binding diagnostic secret/evidence flags drift")
        if payload.get("productionEvidence") is not False or payload.get("productionReady") is not False:
            raise SystemExit("generation binding diagnostic production evidence/readiness drift")
        if "CANARY_DO_NOT_PERSIST_JKL" in output.read_text(encoding="utf-8"):
            raise SystemExit("generation binding diagnostic persisted synthetic canary")
        output.chmod(0o640)
        positive = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                  capture_output=True, text=True, timeout=15, check=False)
        if positive.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("generation binding diagnostic failed to preserve existing mode")
        previous = output.read_bytes()
        for label, before in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(before) != 1:
                raise SystemExit("generation binding diagnostic fault anchor drift: " + label)
            failure = subprocess.run([sys.executable, "-c", script.replace(
                before, "raise OSError('synthetic binding diagnostic " + label + " failure')", 1)],
                cwd=tmpdir, env=env, capture_output=True, text=True, timeout=15, check=False)
            if failure.returncode == 0 or "synthetic binding diagnostic " + label + " failure" not in failure.stderr:
                raise SystemExit("generation binding diagnostic intended fault not reached: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("generation binding diagnostic fault altered prior bytes/mode: " + label)
            if list(output.parent.glob(".backup-restore-generation-reconcile-diagnostic.last.json.*.tmp")):
                raise SystemExit("generation binding diagnostic fault left temporary file: " + label)
        outside = Path(tmpdir) / "external-generation-binding-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        if symlink.returncode == 0 or "target must not be a symlink" not in symlink.stderr:
            raise SystemExit("generation binding diagnostic accepted symlink destination")
        if not output.is_symlink() or outside.read_bytes() != previous:
            raise SystemExit("generation binding diagnostic altered external symlink canary")
        if list(output.parent.glob(".backup-restore-generation-reconcile-diagnostic.last.json.*.tmp")):
            raise SystemExit("generation binding diagnostic symlink rejection left temporary file")
    print("PASS: generation binding diagnostic redaction/atomic runtime (5 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, ""),
        ("writer branch", PUSH_REF, ""),
        ("writer event", EVENT, ""),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("broad publisher scope", PUBLISHER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("PR self guard", "\n          python " + SELF + "\n", ""),
        ("retry self guard", "\n            python " + SELF + "\n", ""),
        ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("PR checkout source", 'ref: ' + D + '{{ github.event.pull_request.head.sha }}', 'ref: ' + D + '{{ github.sha }}'),
        ("writer checkout source", 'ref: ' + D + '{{ github.sha }}', 'ref: ' + D + '{{ github.ref }}'),
        ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 'expected="$PR_HEAD_SHA"'),
        ("latest reset", "            git reset --hard origin/so\n", ""),
        ("root write token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("unreviewed Action", "      - name: Capture exact generation binding authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact generation binding authority source\n"),
        ("unreviewed shell", "      - name: Capture exact generation binding authority source\n", "      - run: echo unreviewed\n      - name: Capture exact generation binding authority source\n"),
        ("raw diagnostic", "              'output': 'REDACTED: generation binding validation failed; consult CI job logs',\n", "              'output': Path('/tmp/backup-restore-generation-binding.log').read_text(),\n"),
        ("raw CI log", '          printf "Generation binding validation exit code: %s (raw validator log suppressed)\\n" "$code"\n', '          cat "$log"\n'),
        ("missing redaction", "              'output': 'REDACTED: generation binding validation failed; consult CI job logs',\n", ""),
        ("symlink guard", "          if path.is_symlink():\n              raise SystemExit('generation binding diagnostic target must not be a symlink')\n", ""),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("self trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, ""),
        ("push branch", PUSH_REF, ""),
        ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("self execution", "          python " + SELF + "\n", ""),
        ("injected Action", "      - name: Prove generation binding source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove generation binding source admission\n"),
        ("injected shell", "      - name: Prove generation binding source admission\n", "      - run: echo unreviewed\n      - name: Prove generation binding source admission\n"),
    )
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("generation binding negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("generation binding negative fixture unchanged: " + target + " " + label)
            try:
                validate(mutated, independent) if target == "publisher" else validate(publisher, mutated)
            except SystemExit:
                continue
            raise SystemExit("generation binding accepted source mutation: " + target + " " + label)
    print(f"PASS: generation binding publisher source admission ({len(publisher_cases)} negatives), independent source admission ({len(independent_cases)} negatives)")



def require_binding_writer_import_negative_reachable(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise SystemExit("generation binding negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if "prove_private_writer_import_failures" not in functions or "main" not in functions:
        raise SystemExit("generation binding private writer import negative missing")
    calls = [
        node for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_private_writer_import_failures"
    ]
    if len(calls) != 1:
        raise SystemExit("generation binding private writer import negative invocation drift")
    if "prove_private_escaped_path_diagnostic" not in functions:
        raise SystemExit("generation binding private escaped-path negative missing")
    path_calls = [
        node for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_private_escaped_path_diagnostic"
    ]
    if len(path_calls) != 1:
        raise SystemExit("generation binding private escaped-path negative invocation drift")
    if "prove_private_authority_file_diagnostic" not in functions:
        raise SystemExit("generation binding private missing-authority negative missing")
    missing_calls = [node for node in ast.walk(functions["main"])
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                     and node.func.id == "prove_private_authority_file_diagnostic"]
    if len(missing_calls) != 1:
        raise SystemExit("generation binding private missing-authority negative invocation drift")


def prove_binding_writer_import_negative_deletion_rejected() -> None:
    code = source(BINDING_NEGATIVE)
    require_binding_writer_import_negative_reachable(code)
    anchor = "    prove_private_writer_import_failures(module)\n"
    if code.count(anchor) != 1:
        raise SystemExit("generation binding private writer import negative removal anchor drift")
    mutated = code.replace(anchor, "    pass\n", 1)
    try:
        require_binding_writer_import_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation binding private writer import negative deletion accepted")
    print("PASS: generation binding private writer import negative deletion rejected")
    path_anchor = "    prove_private_escaped_path_diagnostic(module)\n"
    if code.count(path_anchor) != 1:
        raise SystemExit("generation binding private escaped-path negative removal anchor drift")
    mutated_path = code.replace(path_anchor, "    pass\n", 1)
    try:
        require_binding_writer_import_negative_reachable(mutated_path)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation binding private escaped-path negative deletion accepted")
    print("PASS: generation binding private escaped-path negative deletion rejected")
    missing_anchor = "    prove_private_authority_file_diagnostic(module)\n"
    if code.count(missing_anchor) != 1:
        raise SystemExit("generation binding private missing-authority removal anchor drift")
    mutated_missing = code.replace(missing_anchor, "    pass\n", 1)
    try:
        require_binding_writer_import_negative_reachable(mutated_missing)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation binding private missing-authority negative deletion accepted")
    print("PASS: generation binding private missing-authority negative deletion rejected")



def require_binding_json_parent_swap_negative_reachable(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise SystemExit("generation binding JSON parent swap negative syntax invalid") from None
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(mains) != 1:
        raise SystemExit("generation binding JSON parent swap negative main missing")
    nested = {node.name for node in ast.walk(mains[0]) if isinstance(node, ast.FunctionDef)}
    if not {"swap_before_descent", "swap_after_pin"}.issubset(nested):
        raise SystemExit("generation binding JSON parent swap negative missing")
    assignments = [node.value.id for node in ast.walk(mains[0]) if isinstance(node, ast.Assign)
                   and isinstance(node.value, ast.Name)
                   and any(isinstance(target, ast.Attribute) and target.attr == "open"
                           for target in node.targets)]
    if not {"swap_before_descent", "swap_after_pin"}.issubset(assignments):
        raise SystemExit("generation binding JSON parent swap injection unreachable")


def prove_binding_json_parent_swap_negative_deletion_rejected() -> None:
    code = source(BINDING_NEGATIVE)
    require_binding_json_parent_swap_negative_reachable(code)
    start = '        with tempfile.TemporaryDirectory(prefix="memory-os-binding-json-parent-canary-") as outside:\n'
    end = '        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):\n'
    if code.count(start) != 1 or code.count(end) != 1:
        raise SystemExit("generation binding JSON parent swap negative deletion anchor drift")
    left = code.index(start)
    right = code.index(end, left)
    mutated = code[:left] + code[right:]
    try:
        require_binding_json_parent_swap_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation binding JSON parent swap negative deletion accepted")
    print("PASS: generation binding JSON ancestor swap negative deletion rejected")


def require_binding_json_descriptor_fault_negative_reachable(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        raise SystemExit("generation binding JSON descriptor fault negative syntax invalid") from None
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(mains) != 1:
        raise SystemExit("generation binding JSON descriptor fault negative main missing")
    main = mains[0]
    nested = {node.name for node in ast.walk(main) if isinstance(node, ast.FunctionDef)}
    if not {"close_then_fail", "fdopen_then_fail"}.issubset(nested):
        raise SystemExit("generation binding JSON descriptor fault injection missing")
    injections = {node.value.id for node in ast.walk(main)
                  if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)
                  and any(isinstance(target, ast.Attribute) and target.attr in {"close", "fdopen"}
                          for target in node.targets)}
    if not {"close_then_fail", "fdopen_then_fail"}.issubset(injections):
        raise SystemExit("generation binding JSON descriptor fault injection unreachable")
    messages = {node.value for node in ast.walk(main)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    if not {"generation binding JSON cleanup failed", "generation binding JSON unreadable"}.issubset(messages):
        raise SystemExit("generation binding JSON descriptor fault classifications missing")


def prove_binding_json_descriptor_fault_negative_deletion_rejected() -> None:
    code = source(BINDING_NEGATIVE)
    require_binding_json_descriptor_fault_negative_reachable(code)
    start = '        # Close errors must fail privately even after the OS descriptor was closed.\\n'
    end = '        with tempfile.TemporaryDirectory(prefix="memory-os-binding-json-parent-canary-") as outside:\\n'
    if code.count(start) != 1 or code.count(end) != 1:
        raise SystemExit("generation binding JSON descriptor fault deletion anchor drift")
    mutated = code[:code.index(start)] + code[code.index(end, code.index(start)):]
    try:
        require_binding_json_descriptor_fault_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation binding JSON descriptor fault negative deletion accepted")
    print("PASS: generation binding JSON descriptor fault negative deletion rejected")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    runtime(publisher, independent)
    runtime_sha_proof(publisher, independent)
    runtime_diagnostic_redaction(publisher)
    prove_binding_writer_import_negative_deletion_rejected()
    prove_binding_json_parent_swap_negative_deletion_rejected()
    prove_binding_json_descriptor_fault_negative_deletion_rejected()
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
