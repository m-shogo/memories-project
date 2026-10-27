#!/usr/bin/env python3
"""Fail-closed source-admission negatives for generation independent review CI."""

from __future__ import annotations

import ast
import hashlib
import os
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-independent-review-negative.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "a4ae3121a5542d4dddc9f631f0b6e78302febd3a"
HELPER = ROOT / "scripts/ops_independent_review_fixture_loader.py"
TRANSPORT = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review-transport-negative.py"
REVIEWED_TRANSPORT_GIT_BLOB_SHA = "3a872dcc8554a63feb894f342c3c2960c85c7975"
REVIEWED_HELPER_GIT_BLOB_SHA = "1091ad96042f16bbb538fad2b81050a6f4fa6450"
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed generation independent review negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-generation-independent-review-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-generation-independent-review-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("fixture helper compile", "            scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py \\\n            scripts/ops_independent_review_fixture_loader.py\n", 1),
)


def validate(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"generation independent review workflow source boundary drift: {label}")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("generation independent review workflow complete source blob drift")



def require_transport_path_proof(source: bytes) -> None:
    """Independently reject removal of real canonical path and private-fault probes."""
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError):
        raise SystemExit("independent-review transport path proof unreadable") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not {"load_validator", "prove_validator_path_failures", "main"} <= functions.keys():
        raise SystemExit("independent-review transport path proof missing")
    loader = functions["load_validator"]
    proof = functions["prove_validator_path_failures"]
    main = functions["main"]

    def calls(node, name):
        return [item for item in ast.walk(node) if isinstance(item, ast.Call)
                and isinstance(item.func, ast.Name) and item.func.id == name]

    lexical = [call for call in calls(loader, "require") if call.args
               and isinstance(call.args[0], ast.Compare)
               and isinstance(call.args[0].left, ast.Name)
               and call.args[0].left.id == "VALIDATOR"
               and len(call.args[0].ops) == 1
               and isinstance(call.args[0].ops[0], ast.Eq)
               and len(call.args[0].comparators) == 1
               and ast.unparse(call.args[0].comparators[0]) == "ROOT / VALIDATOR_REL"]
    if len(lexical) != 1 or len(calls(loader, "load_pinned_module")) != 1:
        raise SystemExit("independent-review transport canonical loader binding weakened")
    if not any(isinstance(node, ast.Raise) and isinstance(node.cause, ast.Constant)
               and node.cause.value is None
               for node in ast.walk(loader)):
        raise SystemExit("independent-review transport private loader failure weakened")

    labels = {call.args[0].value for call in calls(proof, "rejected")
              if call.args and isinstance(call.args[0], ast.Constant)
              and isinstance(call.args[0].value, str)}
    if not {"canonical missing", "canonical symlink", "noncanonical substitute"} <= labels:
        raise SystemExit("independent-review transport canonical path probes weakened")
    if not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr == "symlink_to"
               for node in ast.walk(proof)):
        raise SystemExit("independent-review transport actual symlink fixture missing")
    if not any(isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "VALIDATOR"
                       for target in node.targets)
               and isinstance(node.value, ast.Name) and node.value.id == "substitute"
               for node in ast.walk(proof)):
        raise SystemExit("independent-review transport substitute binding missing")
    positive = [call for call in calls(proof, "require") if call.args
                and isinstance(call.args[0], ast.Compare)
                and ast.unparse(call.args[0]) == "load_validator().VALUE == 7"]
    if len(positive) != 1:
        raise SystemExit("independent-review transport canonical positive probe weakened")
    fault_loops = [node for node in ast.walk(proof)
                   if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple)
                   and {elt.func.id for elt in node.iter.elts
                        if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name)}
                   == {"OSError", "RuntimeError", "SystemExit"}
                   and any(isinstance(call.args[0], ast.Attribute)
                           and call.args[0].attr == "__name__"
                           for call in calls(node, "rejected") if call.args)]
    if len(fault_loops) != 1:
        raise SystemExit("independent-review transport private fault probes weakened")
    nested = [node for node in ast.walk(proof)
              if isinstance(node, ast.FunctionDef) and node.name == "rejected"]
    if len(nested) != 1 or not any(isinstance(node, ast.ExceptHandler)
                                   and isinstance(node.type, ast.Name)
                                   and node.type.id == "Fail"
                                   for node in ast.walk(nested[0])):
        raise SystemExit("independent-review transport rejection diagnostic proof missing")
    attrs = {node.attr for node in ast.walk(nested[0]) if isinstance(node, ast.Attribute)}
    if not {"__suppress_context__", "__cause__"} <= attrs:
        raise SystemExit("independent-review transport private exception proof missing")
    restored = {"ROOT", "VALIDATOR", "load_pinned_module"}
    if not any(isinstance(node, ast.Try) and restored <= {
               target.id for statement in node.finalbody if isinstance(statement, ast.Assign)
               for target in statement.targets if isinstance(target, ast.Name)}
               for node in ast.walk(proof)):
        raise SystemExit("independent-review transport fixture cleanup proof missing")
    if len(calls(main, "prove_validator_path_failures")) != 1:
        raise SystemExit("independent-review transport path proof not reachable")


def validate_transport_source(source: bytes, *, check_blob: bool = True) -> None:
    require_transport_path_proof(source)
    if len(source) > 1024 * 1024:
        raise SystemExit("independent-review transport negative source oversized")
    git_blob = b"blob " + str(len(source)).encode("ascii") + b"\0" + source
    if check_blob and hashlib.sha1(git_blob).hexdigest() != REVIEWED_TRANSPORT_GIT_BLOB_SHA:
        raise SystemExit("independent-review transport negative complete source blob drift")


def validate_helper_source(source: bytes) -> None:
    if len(source) > 1024 * 1024:
        raise SystemExit("independent-review fixture helper source oversized")
    git_blob = b"blob " + str(len(source)).encode("ascii") + b"\0" + source
    if hashlib.sha1(git_blob).hexdigest() != REVIEWED_HELPER_GIT_BLOB_SHA:
        raise SystemExit("independent-review fixture helper source binding drift")


MAX_SOURCE_BYTES = 128 * 1024
PRIVATE_SOURCE_ERROR = "independent-review workflow source unreadable or unsafe"


def read_bounded_regular(path: Path, limit: int = MAX_SOURCE_BYTES) -> bytes:
    """Pin every ancestor and the regular leaf before bounded source reading."""
    directory_fds: list[int] = []
    fd = -1
    try:
        if not path.is_absolute() or not path.name:
            raise ValueError("unsafe source path")
        checked = path.lstat()
        if not stat.S_ISREG(checked.st_mode):
            raise ValueError("unsafe source type")
        if not all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                   for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")):
            raise ValueError("unsafe platform flags")
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
        parent_fd = os.open(path.anchor, directory_flags)
        directory_fds.append(parent_fd)
        for component in path.parts[1:-1]:
            parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            directory_fds.append(parent_fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent_fd)
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode) or
                (opened.st_dev, opened.st_ino) != (checked.st_dev, checked.st_ino)):
            raise ValueError("source inode drift")
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("source size limit")
        return data
    except (Exception, SystemExit):
        raise SystemExit(PRIVATE_SOURCE_ERROR) from None
    finally:
        cleanup_failed = False
        if fd >= 0:
            try:
                os.close(fd)
            except (Exception, SystemExit):
                cleanup_failed = True
        for directory_fd in reversed(directory_fds):
            try:
                os.close(directory_fd)
            except (Exception, SystemExit):
                cleanup_failed = True
        if cleanup_failed:
            raise SystemExit(PRIVATE_SOURCE_ERROR) from None


def prove_bounded_reader() -> None:
    """Actual unsafe-source and FD fault negatives on disposable files."""
    def rejected(path: Path) -> None:
        try:
            read_bounded_regular(path)
        except SystemExit as exc:
            if str(exc) == PRIVATE_SOURCE_ERROR and exc.__suppress_context__:
                return
            raise SystemExit("independent-review bounded source diagnostic drift") from None
        raise SystemExit("independent-review bounded source accepted unsafe input")

    with tempfile.TemporaryDirectory(prefix="independent-review-source-") as raw:
        root = Path(raw)
        source = root / "source.py"
        source.write_bytes(b"VALUE = 7\n")
        if read_bounded_regular(source) != b"VALUE = 7\n":
            raise SystemExit("independent-review bounded source positive drift")
        link = root / "symlink.py"
        link.symlink_to(source)
        rejected(link)
        fifo = root / "fifo.py"
        os.mkfifo(fifo)
        rejected(fifo)
        oversized = root / "oversized.py"
        oversized.write_bytes(b"x" * (MAX_SOURCE_BYTES + 1))
        rejected(oversized)
        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):
            original_flag = getattr(os, flag)
            for unsupported in (None, 0):
                try:
                    setattr(os, flag, unsupported)
                    rejected(source)
                finally:
                    setattr(os, flag, original_flag)

        parent = root / "source-parent"
        parent.mkdir()
        pinned = parent / "source.py"
        pinned.write_bytes(b"PINNED_SOURCE\n")
        external = root / "external"
        external.mkdir()
        canary = external / "source.py"
        canary.write_bytes(b"PRIVATE_EXTERNAL_CANARY\n")
        parked = root / "parked"
        original_open = os.open
        before_swap = len(os.listdir("/proc/self/fd"))
        swapped = False

        def swap_parent_before_open(target, flags, *args, **kwargs):
            nonlocal swapped
            if not swapped and target == parent.name and kwargs.get("dir_fd") is not None:
                swapped = True
                parent.rename(parked)
                parent.symlink_to(external, target_is_directory=True)
            return original_open(target, flags, *args, **kwargs)

        os.open = swap_parent_before_open
        try:
            rejected(pinned)
        finally:
            os.open = original_open
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
        if not swapped or canary.read_bytes() != b"PRIVATE_EXTERNAL_CANARY\n":
            raise SystemExit("independent-review bounded source parent-swap proof drift")
        if len(os.listdir("/proc/self/fd")) != before_swap:
            raise SystemExit("independent-review bounded source parent-swap FD leak")
        if read_bounded_regular(pinned) != b"PINNED_SOURCE\n":
            raise SystemExit("independent-review bounded source parent-swap restoration drift")

        before_post_pin = len(os.listdir("/proc/self/fd"))
        swapped_after_pin = False

        def swap_after_parent_pin(target, flags, *args, **kwargs):
            nonlocal swapped_after_pin
            if not swapped_after_pin and target == pinned.name and kwargs.get("dir_fd") is not None:
                swapped_after_pin = True
                parent.rename(parked)
                parent.symlink_to(external, target_is_directory=True)
            return original_open(target, flags, *args, **kwargs)

        os.open = swap_after_parent_pin
        try:
            if read_bounded_regular(pinned) != b"PINNED_SOURCE\n":
                raise SystemExit("independent-review pinned parent source changed after swap")
        finally:
            os.open = original_open
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
        if not swapped_after_pin or canary.read_bytes() != b"PRIVATE_EXTERNAL_CANARY\n":
            raise SystemExit("independent-review pinned parent post-open canary drift")
        if len(os.listdir("/proc/self/fd")) != before_post_pin:
            raise SystemExit("independent-review pinned parent post-open FD leak")

        before = len(os.listdir("/proc/self/fd"))
        original_fdopen = os.fdopen

        def fail_fdopen(*_args, **_kwargs):
            raise OSError("PRIVATE_SOURCE_FDOPEN_CANARY")

        os.fdopen = fail_fdopen
        try:
            rejected(source)
        finally:
            os.fdopen = original_fdopen
        if len(os.listdir("/proc/self/fd")) != before:
            raise SystemExit("independent-review bounded source fdopen leak")

        original_close = os.close
        fired = False

        def close_then_fail(fd: int) -> None:
            nonlocal fired
            original_close(fd)
            if not fired:
                fired = True
                raise OSError("PRIVATE_SOURCE_CLOSE_CANARY")

        os.fdopen = fail_fdopen
        os.close = close_then_fail
        try:
            rejected(source)
        finally:
            os.fdopen = original_fdopen
            os.close = original_close
        if not fired or len(os.listdir("/proc/self/fd")) != before:
            raise SystemExit("independent-review bounded source close cleanup drift")
        if read_bounded_regular(source) != b"VALUE = 7\n":
            raise SystemExit("independent-review bounded source restoration drift")
    print("PASS independent-review bounded workflow/helper/transport source: symlink FIFO oversize platform-flags ancestor-swap post-pin-swap fdopen close")


def prove_branch_guards_runtime() -> None:
    """Execute the reviewed shell predicates against disposable synthetic refs."""
    cases = (
        ("PR so", REQUIRED[14][1].strip(), "GITHUB_BASE_REF", "so", True),
        ("PR main", REQUIRED[14][1].strip(), "GITHUB_BASE_REF", "main", False),
        ("PR missing", REQUIRED[14][1].strip(), "GITHUB_BASE_REF", "", False),
        ("push so", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("generation independent review runtime branch guard drift: " + label)
    print("PASS: generation independent review PR/push branch guard runtime (6 cases)")


def main() -> int:
    prove_bounded_reader()
    try:
        source = read_bounded_regular(WORKFLOW).decode("utf-8")
    except UnicodeDecodeError:
        raise SystemExit(PRIVATE_SOURCE_ERROR) from None
    validate(source)
    helper_source = read_bounded_regular(HELPER)
    validate_helper_source(helper_source)
    transport_source = read_bounded_regular(TRANSPORT)
    validate_transport_source(transport_source)
    for label, old, new in (
        ("delete canonical missing probe", b'rejected("canonical missing")',
         b'pass  # missing probe removed'),
        ("delete canonical symlink probe", b'rejected("canonical symlink")',
         b'pass  # symlink probe removed'),
        ("delete canonical symlink fixture", b'canonical.symlink_to(original_validator)',
         b'pass  # symlink fixture removed'),
        ("delete noncanonical substitute probe", b'rejected("noncanonical substitute")',
         b'pass  # substitute probe removed'),
        ("delete substitute binding", b'VALIDATOR = substitute',
         b'VALIDATOR = canonical'),
        ("bypass canonical positive", b'require(load_validator().VALUE == 7,',
         b'require(True or load_validator().VALUE == 7,'),
        ("replace OSError fault", b'OSError("PRIVATE_TRANSPORT_OS_CANARY")',
         b'ValueError("PRIVATE_TRANSPORT_OS_CANARY")'),
        ("remove private loader suppression",
         b'raise Fail("canonical independent-review validator path rejected") from None',
         b'raise Fail("canonical independent-review validator path rejected")'),
        ("bypass lexical canonical check", b'require(VALIDATOR == ROOT / VALIDATOR_REL,',
         b'require(True or VALIDATOR == ROOT / VALIDATOR_REL,'),
        ("bypass pinned module", b'return load_pinned_module(ROOT, VALIDATOR,',
         b'return object() # load_pinned_module(ROOT, VALIDATOR,'),
        ("remove path probe reachability", b'    prove_validator_path_failures()\n',
         b'    pass  # path proof removed\n'),
        ("remove final root restoration", b'    finally:\n        ROOT = original_root',
         b'    finally:\n        pass  # root restoration removed'),
    ):
        if transport_source.count(old) != 1:
            raise SystemExit("independent-review transport semantic mutation anchor drift: " + label)
        mutant = transport_source.replace(old, new, 1)
        try:
            validate_transport_source(mutant, check_blob=False)
        except SystemExit:
            continue
        raise SystemExit("independent-review transport semantic weakening accepted: " + label)
    print("PASS independent-review transport 12 semantic path-proof mutations")

    for label, old, new in (
        ("restore mutable transport source read", b"raw = read_pinned_source(ROOT, SOURCE_ORDER_EXECUTION_NEGATIVE)", b"raw = SOURCE_ORDER_EXECUTION_NEGATIVE.read_bytes()"),
        ("remove transport private read failure", b"except (FixtureImportFail, UnicodeDecodeError):", b"except UnicodeDecodeError:"),
        ("restore unbounded contract read", b"canonical_contract = read_authority(module.CONTRACT)", b"canonical_contract = module.CONTRACT.read_bytes()"),
        ("skip pinned registry postcondition", b"require(read_authority(module.REGISTRY) == canonical_registry", b"require(True or read_authority(module.REGISTRY) == canonical_registry"),
        ("remove transport validator private failure", b"except (Exception, SystemExit):", b"except FixtureImportFail:"),
        ("remove canonical transport validator path binding", b"require(VALIDATOR == ROOT / VALIDATOR_REL,", b"require(True,"),
        ("remove transport validator path fault probe", b"    prove_validator_path_failures()\n", b"    pass\n"),
        ("remove isolated canonical symlink fault", b'rejected("canonical symlink")', b'pass  # removed canonical symlink proof'),
        ("remove isolated canonical positive", b"require(load_validator().VALUE == 7,", b"require(True or load_validator().VALUE == 7,"),
    ):
        if old not in transport_source:
            raise SystemExit("independent-review transport mutation anchor missing: " + label)
        try:
            validate_transport_source(transport_source.replace(old, new, 1))
        except SystemExit:
            continue
        raise SystemExit("independent-review transport source weakening accepted: " + label)
    for label, old, new in (
        ("remove pinned source safety flag", b"os.O_NOFOLLOW", b"os.O_RDONLY"),
        ("remove real pinned import negative", b"    prove_pinned_import()\n", b"    pass\n"),
        ("remove after-close fault", b"independent_fixture_close_after_close", b"independent_fixture_close_skipped"),
        ("remove unsupported flag loop", b'        for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY"):\n', b'        for flag in ():\n'),
        ("remove compile exit probe", b'            expect_rejected(root, source, "independent_fixture_compile_exit")\n', b'            pass\n'),
        ("remove pinned source reader delegation", b"source = read_pinned_source(root, path)", b"source = path.read_bytes()"),
    ):
        if old not in helper_source:
            raise SystemExit("independent-review helper negative anchor missing: " + label)
        mutated_helper = helper_source.replace(old, new, 1)
        if mutated_helper == helper_source:
            raise SystemExit("independent-review helper negative inert: " + label)
        try:
            validate_helper_source(mutated_helper)
        except SystemExit:
            continue
        raise SystemExit("independent-review helper mutation accepted: " + label)
    prove_branch_guards_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup-python SHA", REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("persist credentials", REQUIRED[2][1], ""),
        ("PR source checkout", REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR event admission", REQUIRED[4][1], ""),
        ("PR head SHA", REQUIRED[5][1], '            expected="${GITHUB_SHA:-}"\n'),
        ("SHA format", REQUIRED[6][1], '            test -n "$expected"\n'),
        ("event whitelist", REQUIRED[7][1], ""),
        ("push/dispatch branch", REQUIRED[8][1], ""),
        ("unreviewed event rejection", REQUIRED[9][1], ""),
        ("source HEAD", REQUIRED[10][1], ""),
        ("clean source", REQUIRED[11][1], ""),
        ("fixture helper compile continuation", REQUIRED[16][1], REQUIRED[16][1].replace(chr(92) + chr(10), chr(10))),
        ("self-trigger", REQUIRED[12][1], ""),
        ("self-execution", REQUIRED[13][1], ""),
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"generation independent review negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit(f"generation independent review accepted forbidden mutation: {label}")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("generation independent review PR branch negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("generation independent review accepted forbidden PR branch mutation: " + label)
    # Whole-source binding rejects otherwise anchor-preserving workflow changes.
    for label, mutated in (
        ("extra executable step", source.replace(
            "      - name: Validate final-candidate independent-review authority read-only\n",
            "      - run: echo unreviewed\n      - name: Validate final-candidate independent-review authority read-only\n", 1)),
        ("missing domain trigger", source.replace(
            '      - "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py"\n',
            "", 1)),
    ):
        if mutated == source:
            raise SystemExit("generation independent review source digest negative anchor missing: " + label)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("generation independent review accepted whole-source mutation: " + label)
    print(f"PASS: generation independent review workflow source admission ({len(cases) + 4} negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
