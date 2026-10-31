#!/usr/bin/env python3
"""Prove upload-route reconcile rollback and canonical validator delegation."""

from __future__ import annotations

import errno
import importlib.util
import os
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-upload-route-authority.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_upload_route_reconciler", RECONCILER)
    require(spec is not None and spec.loader is not None, "unable to load upload-route reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-atomic-") as temp_dir:
        target = Path(temp_dir) / "authority.txt"
        original = b"exact-original-bytes\n"
        target.write_bytes(original)
        original_replace = module.os.replace
        pattern = f".{target.name}.*.tmp"
        before = {item.name for item in target.parent.glob(pattern)}

        def reject_replace(source, destination) -> None:
            if Path(destination) == target:
                raise OSError("synthetic atomic replace rejection")
            original_replace(source, destination)

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(target, b"partial-mutation\n")
            except OSError as exc:
                require("synthetic atomic replace rejection" in str(exc),
                        "atomic replacement failed for unrelated reason")
            else:
                raise Fail("upload-route atomic writer accepted replacement failure")
            require(target.read_bytes() == original,
                    "upload-route canonical bytes changed after failed atomic replacement")
            after = {item.name for item in target.parent.glob(pattern)}
            require(after == before,
                    f"upload-route atomic writer left temporary residue: {sorted(after - before)}")
        finally:
            module.os.replace = original_replace


def expect_guard_rejection(module, attribute: str, substitute, expected: str) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, substitute)
    try:
        try:
            module.enforce_execution_authorities()
        except module.ReconcileFailure as exc:
            require(expected in str(exc), f"{attribute} rejected for unrelated reason: {exc}")
        else:
            raise Fail(f"upload-route reconciler accepted execution substitution: {attribute}")
    finally:
        setattr(module, attribute, original)


def prove_execution_authority(module) -> None:
    module.enforce_execution_authorities()
    cases = (
        ("OBSERVABILITY", module.SERVER, "observability source authority drift"),
        ("SERVER", module.OBSERVABILITY, "server source authority drift"),
        ("LIVE_TEST", module.ROUTE_TEST, "live test source authority drift"),
        ("ROUTE_TEST", module.LIVE_TEST, "route test source authority drift"),
        ("METRICS_VALIDATOR", module.RATE_LIMIT_VALIDATOR, "metrics validator authority drift"),
        ("RATE_LIMIT_VALIDATOR", module.METRICS_VALIDATOR, "rate-limit validator authority drift"),
        ("OBSERVABILITY_VALIDATOR", module.OPERABILITY_VALIDATOR, "observability validator authority drift"),
        ("OPERABILITY_VALIDATOR", module.OBSERVABILITY_VALIDATOR, "operability validator authority drift"),
        ("OLD_LABEL", module.NEW_LABEL, "old label semantic authority drift"),
        ("require", lambda *_args, **_kwargs: None, "require execution authority drift"),
        ("read", lambda _path: "", "reader execution authority drift"),
        ("read_regular_bytes", lambda _path: None, "pinned regular reader execution authority drift"),
        ("atomic_write_bytes", lambda *_args: None, "atomic byte writer execution authority drift"),
        ("atomic_write_text", lambda *_args: None, "atomic text writer execution authority drift"),
        ("write_if_changed", lambda *_args: False, "conditional writer execution authority drift"),
        ("replace_once", lambda value, *_args: (value, False), "replacement helper execution authority drift"),
        ("current_authority_files", lambda: [], "authority scanner execution authority drift"),
        ("snapshot_authority_files", lambda: None, "snapshot helper execution authority drift"),
        ("rollback_authority_files", lambda: None, "rollback helper execution authority drift"),
        ("validate_canonical_authorities", lambda: None, "validator chain execution authority drift"),
    )
    for attribute, substitute, expected in cases:
        expect_guard_rejection(module, attribute, substitute, expected)

    original_run = module.subprocess.run
    module.subprocess.run = lambda *_args, **_kwargs: None
    try:
        try:
            module.enforce_execution_authorities()
        except module.ReconcileFailure as exc:
            require("subprocess transport execution authority drift" in str(exc),
                    f"subprocess transport rejected for unrelated reason: {exc}")
        else:
            raise Fail("upload-route reconciler accepted subprocess transport substitution")
    finally:
        module.subprocess.run = original_run

    original_guard = module.enforce_execution_authorities
    module.enforce_execution_authorities = lambda: None
    try:
        try:
            module.main()
        except module.ReconcileFailure as exc:
            require("execution guard authority drift" in str(exc),
                    f"runtime guard rejected for unrelated reason: {exc}")
        else:
            raise Fail("upload-route reconciler accepted runtime guard substitution")
    finally:
        module.enforce_execution_authorities = original_guard


def prove_validator_delegation(module) -> None:
    expected = [
        module.METRICS_VALIDATOR,
        module.RATE_LIMIT_VALIDATOR,
        module.OBSERVABILITY_VALIDATOR,
        module.OPERABILITY_VALIDATOR,
    ]
    calls: list[Path] = []

    class Result:
        def __init__(self, returncode):
            self.returncode = returncode

    original_run = module.subprocess.run

    def passing_run(command, *, cwd, check):
        require(cwd == module.ROOT, "validator did not run from repository root")
        require(check is False, "validator subprocess must return its explicit status")
        calls.append(Path(command[1]))
        return Result(0)

    try:
        module.subprocess.run = passing_run
        module.validate_canonical_authorities()
    finally:
        module.subprocess.run = original_run
    require(calls == expected, "canonical aggregate validators ran in the wrong order")

    calls.clear()

    def failing_run(command, *, cwd, check):
        calls.append(Path(command[1]))
        return Result(1 if len(calls) == 2 else 0)

    try:
        module.subprocess.run = failing_run
        try:
            module.validate_canonical_authorities()
        except module.ReconcileFailure as exc:
            require("validate-memory-os-rate-limit.py" in str(exc), "wrong validator failure was reported")
        else:
            raise Fail("canonical validator rejection was accepted")
    finally:
        module.subprocess.run = original_run
    require(calls == expected[:2], "validator chain continued after fail-closed rejection")

    def boolean_run(command, *, cwd, check):
        return Result(False)

    try:
        module.subprocess.run = boolean_run
        try:
            module.validate_canonical_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise Fail("boolean validator exit status was accepted as integer zero")
    finally:
        module.subprocess.run = original_run



def prove_learning_scan_boundary(module) -> None:
    """A broad route-label reconcile must never rewrite append-only learning."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-learning-") as temp_dir:
        root = Path(temp_dir)
        protected = (
            "docs/operations/AUTONOMOUS-OPS-LEARNING.md",
            "docs/operations/autonomous-learning-records/old.md",
            "docs/operations/autonomous-learning-addenda/old.md",
            "docs/operations/learning/old.md",
        )
        for relative in protected:
            candidate = root / relative
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text(module.OLD_LABEL + chr(10), encoding="utf-8")
        ordinary = root / "docs/operations/route-guide.md"
        ordinary.write_text(module.OLD_LABEL + chr(10), encoding="utf-8")
        previous_root = module.ROOT
        try:
            module.ROOT = root
            scanned = set(module.current_authority_files())
            require(ordinary in scanned, "route-label scan omitted an ordinary authority")
            for relative in protected:
                require(root / relative not in scanned,
                        f"append-only learning entered route-label rewrite scan: {relative}")
            alias = root / "docs/operations/learning-alias.md"
            alias.symlink_to(root / protected[0])
            try:
                module.current_authority_files()
            except module.ReconcileFailure as exc:
                require("symlink authority candidate" in str(exc),
                        f"route-label scan rejected alias for unrelated reason: {exc}")
            else:
                raise Fail("route-label scan followed a symlink to append-only learning")
        finally:
            module.ROOT = previous_root

def prove_rollback_symlink_boundaries(module) -> None:
    """Reject redirected rollback targets before touching any snapshot entry."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-symlink-") as temp_dir:
        root = Path(temp_dir)
        victim = root / "protected.txt"
        victim.write_bytes(b"protected-original\\n")
        ordinary = root / "ordinary.txt"
        ordinary.write_bytes(b"ordinary-mutated\\n")
        alias = root / "alias.txt"
        alias.symlink_to(victim)
        parent_alias = root / "linked-dir"
        parent_alias.symlink_to(root, target_is_directory=True)

        for unsafe in (alias, parent_alias / "protected.txt"):
            module.ROLLBACK_SNAPSHOT = {
                ordinary: b"ordinary-original\\n",
                unsafe: b"snapshot-bytes\\n",
            }
            try:
                module.rollback_authority_files()
            except module.ReconcileFailure as exc:
                require("symlink rollback/write path" in str(exc),
                        f"rollback rejected unsafe target for unrelated reason: {exc}")
            else:
                raise Fail("rollback accepted a symlinked snapshot target")
            require(ordinary.read_bytes() == b"ordinary-mutated\\n",
                    "rollback wrote a safe file before rejecting an unsafe target")
            require(victim.read_bytes() == b"protected-original\\n",
                    "rollback changed a symlink destination")
            try:
                module.atomic_write_bytes(unsafe, b"redirected-write\\n")
            except module.ReconcileFailure as exc:
                require("symlink rollback/write path" in str(exc),
                        f"atomic writer rejected unsafe target for unrelated reason: {exc}")
            else:
                raise Fail("atomic writer accepted a symlinked destination")
            require(victim.read_bytes() == b"protected-original\\n",
                    "atomic writer changed a symlink destination")
        module.ROLLBACK_SNAPSHOT = None


def prove_atomic_mode_preservation(module) -> None:
    """Atomic replacement must not silently change an existing file mode."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-mode-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        for mode in (0o644, 0o755):
            target.write_bytes(b"original")
            target.chmod(mode)
            module.atomic_write_bytes(target, b"reconciled")
            require(target.read_bytes() == b"reconciled",
                    "atomic mode fixture lost expected payload")
            require(stat.S_IMODE(target.stat().st_mode) == mode,
                    f"atomic writer changed existing authority mode {mode:o}")
        new_file = root / "new-authority.txt"
        module.atomic_write_bytes(new_file, b"new")
        require(stat.S_IMODE(new_file.stat().st_mode) == 0o600,
                "new atomic file did not retain private default mode")



def prove_atomic_mode_failure_cleanup(module) -> None:
    """A failed chmod or fsync must preserve original bytes, mode and directory."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-mode-fault-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        for operation in ("fchmod", "fsync"):
            target.write_bytes(b"original")
            target.chmod(0o755)
            before = {item.name for item in root.glob(".authority.txt.*.tmp")}
            original = getattr(module.os, operation)

            def reject(*_args, **_kwargs):
                raise OSError(f"synthetic {operation} failure")

            setattr(module.os, operation, reject)
            try:
                try:
                    module.atomic_write_bytes(target, b"partial")
                except OSError as exc:
                    require(str(exc) == f"synthetic {operation} failure",
                            f"atomic writer failed for unrelated reason: {exc}")
                else:
                    raise Fail(f"atomic writer accepted {operation} failure")
            finally:
                setattr(module.os, operation, original)
            require(target.read_bytes() == b"original",
                    f"atomic writer changed original bytes after {operation} failure")
            require(stat.S_IMODE(target.stat().st_mode) == 0o755,
                    f"atomic writer changed original mode after {operation} failure")
            after = {item.name for item in root.glob(".authority.txt.*.tmp")}
            require(after == before,
                    f"atomic writer left temporary residue after {operation} failure")



def prove_atomic_fdopen_failure_cleanup(module) -> None:
    """Failed stream acquisition must not leak the staged file descriptor."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-fdopen-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        target.write_bytes(b"original")
        target.chmod(0o755)
        before = {item.name for item in root.glob(".authority.txt.*.tmp")}
        opened: list[int] = []
        original_mkstemp = module.tempfile.mkstemp
        original_fdopen = module.os.fdopen

        def capture_mkstemp(*args, **kwargs):
            descriptor, name = original_mkstemp(*args, **kwargs)
            opened.append(descriptor)
            return descriptor, name

        def reject_fdopen(*_args, **_kwargs):
            raise OSError("synthetic fdopen failure")

        module.tempfile.mkstemp = capture_mkstemp
        module.os.fdopen = reject_fdopen
        try:
            try:
                module.atomic_write_bytes(target, b"partial")
            except OSError as exc:
                require(str(exc) == "synthetic fdopen failure",
                        f"fdopen failure rejected for unrelated reason: {exc}")
            else:
                raise Fail("atomic writer accepted fdopen acquisition failure")
        finally:
            module.tempfile.mkstemp = original_mkstemp
            module.os.fdopen = original_fdopen
        require(len(opened) == 1, "atomic writer did not stage exactly one descriptor")
        try:
            module.os.fstat(opened[0])
        except OSError as exc:
            require(exc.errno == errno.EBADF,
                    f"descriptor verification failed for unrelated reason: {exc}")
        else:
            module.os.close(opened[0])
            raise Fail("atomic writer leaked a descriptor after fdopen failure")
        require(target.read_bytes() == b"original",
                "atomic writer changed original bytes after fdopen failure")
        require(stat.S_IMODE(target.stat().st_mode) == 0o755,
                "atomic writer changed original mode after fdopen failure")
        after = {item.name for item in root.glob(".authority.txt.*.tmp")}
        require(after == before,
                "atomic writer left temporary residue after fdopen failure")



def prove_atomic_poststage_drift_rejection(module) -> None:
    """Staged writes must not replace independent edits made during fsync."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-poststage-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        created = root / "created.txt"
        replacement = root / "replacement.txt"
        canary = root / "external-canary.txt"
        canary.write_bytes(b"canary")
        original_fsync = module.os.fsync
        for scenario in ("modified", "inode-replaced", "mode-changed",
                         "symlink-swapped", "deleted", "created"):
            if target.is_symlink():
                target.unlink()
            target.write_bytes(b"original")
            target.chmod(0o644)
            created.unlink(missing_ok=True)
            replacement.unlink(missing_ok=True)
            destination = created if scenario == "created" else target
            pattern = f".{destination.name}.*.tmp"
            before = {item.name for item in root.glob(pattern)}

            def inject_drift(fd):
                original_fsync(fd)
                if scenario == "modified":
                    target.write_bytes(b"external-edit")
                elif scenario == "inode-replaced":
                    replacement.write_bytes(b"original")
                    replacement.replace(target)
                elif scenario == "mode-changed":
                    target.chmod(0o600)
                elif scenario == "symlink-swapped":
                    target.unlink()
                    target.symlink_to(canary)
                elif scenario == "deleted":
                    target.unlink()
                elif scenario == "created":
                    created.write_bytes(b"external-new")

            module.os.fsync = inject_drift
            try:
                try:
                    module.atomic_write_bytes(destination, b"our-staged-change")
                except module.ReconcileFailure as exc:
                    expected = ("symlink rollback/write path" if scenario == "symlink-swapped"
                                else "concurrent authority drift before publication")
                    require(expected in str(exc),
                            f"{scenario} rejected for unrelated reason: {exc}")
                else:
                    raise Fail(f"atomic writer overwrote poststage drift: {scenario}")
            finally:
                module.os.fsync = original_fsync

            require(canary.read_bytes() == b"canary",
                    f"poststage {scenario} changed external canary")
            if scenario == "modified":
                require(target.read_bytes() == b"external-edit",
                        "poststage byte drift was overwritten")
            elif scenario == "inode-replaced":
                require(target.read_bytes() == b"original",
                        "poststage inode replacement was overwritten")
            elif scenario == "mode-changed":
                require(stat.S_IMODE(target.stat().st_mode) == 0o600,
                        "poststage mode drift was overwritten")
            elif scenario == "symlink-swapped":
                require(target.is_symlink() and target.resolve() == canary,
                        "poststage symlink was overwritten")
            elif scenario == "deleted":
                require(not target.exists(), "poststage deletion was overwritten")
            elif scenario == "created":
                require(created.read_bytes() == b"external-new",
                        "poststage creation was overwritten")
            after = {item.name for item in root.glob(pattern)}
            require(after == before,
                    f"poststage {scenario} left temporary residue")


def prove_atomic_short_write_rejection(module) -> None:
    """A non-raising partial or non-integer stream write cannot be published."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-short-write-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        original_fdopen = module.os.fdopen
        for label, reported in (("partial", 1), ("boolean", True), ("none", None)):
            target.write_bytes(b"original")
            target.chmod(0o755)
            before = {item.name for item in root.glob(".authority.txt.*.tmp")}

            class ShortStream:
                def __init__(self, handle):
                    self.handle = handle

                def __enter__(self):
                    self.handle.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.handle.__exit__(*args)

                def write(self, payload):
                    self.handle.write(payload[:1])
                    return reported

                def flush(self):
                    return self.handle.flush()

                def fileno(self):
                    return self.handle.fileno()

            module.os.fdopen = lambda fd, mode: ShortStream(original_fdopen(fd, mode))
            try:
                try:
                    module.atomic_write_bytes(target, b"staged-long-payload")
                except module.ReconcileFailure as exc:
                    require("short atomic authority write" in str(exc),
                            f"{label} stream rejected for unrelated reason: {exc}")
                else:
                    raise Fail(f"atomic writer accepted {label} stream result")
            finally:
                module.os.fdopen = original_fdopen
            require(target.read_bytes() == b"original",
                    f"{label} stream changed original authority bytes")
            require(stat.S_IMODE(target.stat().st_mode) == 0o755,
                    f"{label} stream changed original authority mode")
            after = {item.name for item in root.glob(".authority.txt.*.tmp")}
            require(after == before,
                    f"{label} stream left temporary residue")


def prove_nonblocking_special_file_reads(module) -> None:
    """FIFO and leaf-alias inputs cannot stall snapshot, write or rollback."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-fifo-") as temp_dir:
        root = Path(temp_dir)
        fifo = root / "authority.fifo"
        os.mkfifo(fifo)
        regular = root / "regular.txt"
        regular.write_bytes(b"regular")
        canary = root / "canary.txt"
        canary.write_bytes(b"canary")
        alias = root / "alias.txt"
        alias.symlink_to(canary)
        require(module.read_regular_bytes(regular) == b"regular",
                "pinned regular reader rejected an ordinary file")
        require(module.read_regular_bytes(root / "missing.txt") is None,
                "pinned regular reader rejected an absent file")
        for unsafe in (fifo, root, alias):
            try:
                module.read_regular_bytes(unsafe)
            except module.ReconcileFailure as exc:
                require(("nonregular rollback/write path" in str(exc)
                         or "symlink rollback/write path" in str(exc)),
                        f"pinned regular reader rejected {unsafe.name} for unrelated reason: {exc}")
            else:
                raise Fail(f"pinned regular reader accepted special path: {unsafe.name}")

        module.ROLLBACK_SNAPSHOT = {fifo: b"snapshot"}
        module.ROLLBACK_WRITTEN.clear()
        try:
            module.atomic_write_bytes(fifo, b"partial")
        except module.ReconcileFailure as exc:
            require("nonregular rollback/write path" in str(exc),
                    f"atomic FIFO write rejected for unrelated reason: {exc}")
        else:
            raise Fail("atomic writer blocked or accepted a FIFO snapshot target")
        module.ROLLBACK_WRITTEN[fifo] = b"owned"
        try:
            module.rollback_authority_files()
        except module.ReconcileFailure as exc:
            require("nonregular rollback/write path" in str(exc),
                    f"rollback FIFO read rejected for unrelated reason: {exc}")
        else:
            raise Fail("rollback blocked or accepted a FIFO owned target")

        previous_scan = module.current_authority_files
        previous_fixed = {
            name: getattr(module, name)
            for name in ("OBSERVABILITY", "SERVER", "LIVE_TEST", "ROUTE_TEST")
        }
        module.current_authority_files = lambda: [fifo]
        for name in previous_fixed:
            setattr(module, name, regular)
        try:
            try:
                module.snapshot_authority_files()
            except module.ReconcileFailure as exc:
                require("nonregular rollback/write path" in str(exc),
                        f"snapshot FIFO read rejected for unrelated reason: {exc}")
            else:
                raise Fail("snapshot blocked or accepted a FIFO target")
        finally:
            module.current_authority_files = previous_scan
            for name, value in previous_fixed.items():
                setattr(module, name, value)
            module.ROLLBACK_SNAPSHOT = None
            module.ROLLBACK_WRITTEN.clear()
        require(canary.read_bytes() == b"canary",
                "special-file read modified an external canary")
        require(fifo.is_fifo(), "special-file negative changed FIFO identity")

def prove_rollback_write_ownership(module) -> None:
    """Rollback only owned writes; reject both prewrite and rollback-time drift."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-ownership-") as temp_dir:
        root = Path(temp_dir)
        owned = root / "owned.txt"
        independent = root / "independent.txt"
        created = root / "created.txt"
        owned.write_bytes(b"baseline")
        independent.write_bytes(b"baseline")

        module.ROLLBACK_SNAPSHOT = {
            owned: b"baseline", independent: b"baseline", created: None,
        }
        module.ROLLBACK_WRITTEN.clear()
        module.atomic_write_bytes(owned, b"our-change")
        module.atomic_write_bytes(created, b"new-file")
        independent.write_bytes(b"external-change")
        module.rollback_authority_files()
        require(owned.read_bytes() == b"baseline",
                "rollback failed to restore its own change")
        require(independent.read_bytes() == b"external-change",
                "rollback overwrote an independent change to an untouched file")
        require(not created.exists(), "rollback retained an owned new file")

        module.ROLLBACK_SNAPSHOT = {
            owned: b"baseline", independent: b"external-change",
        }
        module.ROLLBACK_WRITTEN.clear()
        module.atomic_write_bytes(owned, b"our-change")
        module.atomic_write_bytes(independent, b"our-second-change")
        owned.write_bytes(b"concurrent-change")
        try:
            module.rollback_authority_files()
        except module.ReconcileFailure as exc:
            require("concurrent authority drift before rollback" in str(exc),
                    f"rollback rejected concurrent drift for unrelated reason: {exc}")
        else:
            raise Fail("rollback overwrote a concurrent edit to its own target")
        require(owned.read_bytes() == b"concurrent-change",
                "rollback clobbered concurrent owned-target change")
        require(independent.read_bytes() == b"our-second-change",
                "rollback partially restored before detecting concurrent drift")

        module.ROLLBACK_SNAPSHOT = {owned: b"concurrent-change"}
        module.ROLLBACK_WRITTEN.clear()
        owned.write_bytes(b"newer-external-change")
        try:
            module.atomic_write_bytes(owned, b"stale-write")
        except module.ReconcileFailure as exc:
            require("concurrent authority drift before write" in str(exc),
                    f"atomic writer rejected stale snapshot for unrelated reason: {exc}")
        else:
            raise Fail("atomic writer overwrote an independent prewrite edit")
        require(owned.read_bytes() == b"newer-external-change",
                "atomic writer clobbered a prewrite concurrent edit")
        try:
            module.atomic_write_bytes(created, b"untracked")
        except module.ReconcileFailure as exc:
            require("untracked rollback/write path" in str(exc),
                    f"atomic writer rejected untracked path for unrelated reason: {exc}")
        else:
            raise Fail("atomic writer accepted a path missing from the snapshot")
        require(not created.exists(), "untracked atomic write created a file")
        module.ROLLBACK_SNAPSHOT = None
        module.ROLLBACK_WRITTEN.clear()


def main() -> int:
    module = load_module()
    prove_atomic_replace_failure(module)
    prove_atomic_mode_preservation(module)
    prove_atomic_mode_failure_cleanup(module)
    prove_atomic_fdopen_failure_cleanup(module)
    prove_atomic_poststage_drift_rejection(module)
    prove_atomic_short_write_rejection(module)
    prove_nonblocking_special_file_reads(module)
    prove_learning_scan_boundary(module)
    prove_rollback_symlink_boundaries(module)
    prove_rollback_write_ownership(module)

    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-rollback-") as temp_dir:
        root = Path(temp_dir)
        existing = root / "existing.txt"
        created = root / "created.txt"
        original = b"exact-original-bytes\x00\n"
        existing.write_bytes(original)

        module.ROLLBACK_SNAPSHOT = {
            existing: original,
            created: None,
        }
        module.ROLLBACK_WRITTEN.clear()

        module.atomic_write_bytes(existing, b"partial-mutation\n")
        module.atomic_write_bytes(created, b"partial-created-file\n")
        module.rollback_authority_files()

        require(existing.read_bytes() == original, "existing authority was not restored byte-for-byte")
        require(not created.exists(), "new partial authority was not removed during rollback")

    prove_validator_delegation(module)
    prove_execution_authority(module)

    print("PASS: upload-route reconcile atomic publication, rollback, execution authority and canonical validator delegation are fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"UPLOAD ROUTE RECONCILE ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
