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

        def reject_replace(source, destination, *args, **kwargs) -> None:
            if Path(destination) == target or (
                destination == target.name and kwargs.get("dst_dir_fd") is not None
            ):
                raise OSError("synthetic atomic replace rejection")
            original_replace(source, destination, *args, **kwargs)

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
        ("published_identity", lambda _path: (), "published identity guard execution authority drift"),
        ("atomic_write_bytes", lambda *_args: None, "atomic byte writer execution authority drift"),
        ("open_pinned_parent", lambda *_args: -1, "pinned parent transport execution authority drift"),
        ("create_pinned_stage", lambda *_args: (-1, ""), "pinned stage transport execution authority drift"),
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
            "contracts/operations/autonomous-learning-system.json",
            "contracts/operations/production-operability-status.json",
            "contracts/operations/ops-p0-007-admission-snapshot.v1.json",
            "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
            "contracts/operations/recovery-objectives-registry.v1.json",
            "contracts/operations/backup-restore-drill-request-registry.v1.json",
            "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
            "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
            "contracts/operations/backup-restore-promotion-review-registry.v1.json",
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
                        f"protected operations/learning authority entered route-label scan: {relative}")
            alias = root / "docs/operations/learning-alias.md"
            alias.symlink_to(root / protected[0])
            try:
                module.current_authority_files()
            except module.ReconcileFailure as exc:
                require("symlink authority candidate" in str(exc),
                        f"route-label scan rejected alias for unrelated reason: {exc}")
            else:
                raise Fail("route-label scan followed a symlink to append-only learning")
            alias.unlink()
            hidden_alias = root / "docs/operations/learning-alias.txt"
            hidden_alias.symlink_to(root / protected[0])
            try:
                module.current_authority_files()
            except module.ReconcileFailure as exc:
                require("symlink authority candidate" in str(exc),
                        f"nonmatching-suffix alias rejected for unrelated reason: {exc}")
            else:
                raise Fail("route-label scan ignored a disallowed-suffix symlink")
            hidden_alias.unlink()
        finally:
            module.ROOT = previous_root

def prove_scan_root_alias_rejection(module) -> None:
    """Reject linked roots, linked ancestors and non-directory scan roots."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-scan-root-") as temp_dir:
        base = Path(temp_dir)
        root = base / "workspace"
        outside = base / "outside"
        root.mkdir()
        outside.mkdir()
        ordinary = root / "docs/operations/route-guide.md"
        ordinary.parent.mkdir(parents=True)
        ordinary.write_bytes(b"ordinary-route-guide")
        canary = outside / "external.md"
        canary.write_bytes(b"external-canary")
        previous_root = module.ROOT
        try:
            module.ROOT = root
            require(ordinary in set(module.current_authority_files()),
                    "safe route-label scan root was not enumerated")
            for scenario in ("root-symlink", "ancestor-symlink", "non-directory-root"):
                if scenario == "root-symlink":
                    unsafe = root / "contracts"
                    unsafe.symlink_to(outside, target_is_directory=True)
                    expected = "symlink authority scan root"
                elif scenario == "ancestor-symlink":
                    (outside / "import-api").mkdir(exist_ok=True)
                    unsafe = root / "services"
                    unsafe.symlink_to(outside, target_is_directory=True)
                    expected = "symlink authority scan root"
                else:
                    unsafe = root / "contracts"
                    unsafe.write_bytes(b"not-a-directory")
                    expected = "non-directory authority scan root"
                try:
                    module.current_authority_files()
                except module.ReconcileFailure as exc:
                    require(expected in str(exc),
                            f"{scenario} rejected for unrelated reason: {exc}")
                else:
                    raise Fail(f"route-label scanner accepted unsafe root: {scenario}")
                require(canary.read_bytes() == b"external-canary",
                        f"route-label scan changed an external canary: {scenario}")
                unsafe.unlink()
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
        original_stage = module.create_pinned_stage
        original_fdopen = module.os.fdopen

        def capture_stage(parent_fd, leaf):
            descriptor, name = original_stage(parent_fd, leaf)
            opened.append(descriptor)
            return descriptor, name

        def reject_fdopen(*_args, **_kwargs):
            raise OSError("synthetic fdopen failure")

        module.create_pinned_stage = capture_stage
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
            module.create_pinned_stage = original_stage
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



def prove_atomic_dup_failure_cleanup(module) -> None:
    """A failed stage-descriptor duplication must not leak or leave residue."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-dup-fault-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        target.write_bytes(b"original")
        target.chmod(0o755)
        before = {item.name for item in root.glob(".authority.txt.*.tmp")}
        opened: list[int] = []
        duplicated: list[int] = []
        original_stage = module.create_pinned_stage
        original_dup = module.os.dup

        def capture_stage(parent_fd, leaf):
            descriptor, name = original_stage(parent_fd, leaf)
            opened.append(descriptor)
            return descriptor, name

        def reject_dup(fd):
            require(len(opened) == 1 and fd == opened[0],
                    "dup failure was not injected on the staged descriptor")
            duplicated.append(fd)
            raise OSError("synthetic staging dup failure")

        module.create_pinned_stage = capture_stage
        module.os.dup = reject_dup
        try:
            try:
                module.atomic_write_bytes(target, b"unpublished")
            except OSError as exc:
                require(str(exc) == "synthetic staging dup failure",
                        f"dup failure rejected for unrelated reason: {exc}")
            else:
                raise Fail("atomic writer accepted a failed staging descriptor duplication")
        finally:
            module.create_pinned_stage = original_stage
            module.os.dup = original_dup
        require(len(opened) == 1 and duplicated == opened,
                "staging dup failure did not reach the reviewed descriptor")
        try:
            os.fstat(opened[0])
        except OSError as exc:
            require(exc.errno == errno.EBADF,
                    f"failed-dup descriptor closed for unrelated reason: {exc}")
        else:
            os.close(opened[0])
            raise Fail("atomic writer leaked a staged descriptor after dup failure")
        require(target.read_bytes() == b"original",
                "failed staging dup changed original authority bytes")
        require(stat.S_IMODE(target.stat().st_mode) == 0o755,
                "failed staging dup changed original authority mode")
        after = {item.name for item in root.glob(".authority.txt.*.tmp")}
        require(after == before,
                "failed staging dup left temporary residue")


def prove_postpublication_temp_reuse_preserved(module) -> None:
    """A completed rename must not delete an independent reused temp name."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-temp-reuse-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        target.write_bytes(b"original")
        original_replace = module.os.replace
        reused = []

        def replace_then_reuse(source, destination, *args, **kwargs):
            result = original_replace(source, destination, *args, **kwargs)
            if Path(destination) == target or destination == target.name:
                independent = root / Path(source).name
                independent.write_bytes(b"independent-temp-canary")
                reused.append(independent)
            return result

        module.os.replace = replace_then_reuse
        try:
            module.atomic_write_bytes(target, b"published")
        finally:
            module.os.replace = original_replace
        require(target.read_bytes() == b"published",
                "published authority bytes were not committed")
        require(len(reused) == 1, "postpublication temp reuse was not injected")
        require(reused[0].read_bytes() == b"independent-temp-canary",
                "successful publication cleanup removed an independent file")



def prove_failed_publication_temp_reuse_preserved(module) -> None:
    """A failed replace must not unlink a different inode reusing the stage name."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-failed-reuse-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        target.write_bytes(b"original")
        original_replace = module.os.replace
        original_unlink = module.os.unlink
        original_dup = module.os.dup
        reused = []
        pinned_fds = []

        def capture_stage_pin(fd):
            guard_fd = original_dup(fd)
            pinned_fds.append(guard_fd)
            return guard_fd

        def reuse_before_failed_replace(source, destination, *args, **kwargs):
            if destination == target.name and kwargs.get("src_dir_fd") is not None:
                require(len(pinned_fds) == 1,
                        "publication did not hold a staging inode descriptor")
                original_stat = os.fstat(pinned_fds[0])
                original_unlink(source, dir_fd=kwargs["src_dir_fd"])
                require(os.fstat(pinned_fds[0]).st_nlink == 0,
                        "publication did not pin the unlinked staging inode")
                independent = root / Path(source).name
                independent.write_bytes(b"independent-failed-replace-canary")
                require(independent.stat().st_ino != original_stat.st_ino,
                        "independent name reused an inode that should remain pinned")
                reused.append(independent)
                raise OSError("synthetic failed publication with reused stage name")
            return original_replace(source, destination, *args, **kwargs)

        module.os.dup = capture_stage_pin
        module.os.replace = reuse_before_failed_replace
        try:
            try:
                module.atomic_write_bytes(target, b"unpublished")
            except OSError as exc:
                require(str(exc) == "synthetic failed publication with reused stage name",
                        f"failed publication rejected for unrelated reason: {exc}")
            else:
                raise Fail("failed publication unexpectedly succeeded")
        finally:
            module.os.replace = original_replace
            module.os.dup = original_dup
        require(len(pinned_fds) == 1,
                "publication staging descriptor was not acquired")
        try:
            os.fstat(pinned_fds[0])
        except OSError as exc:
            require(exc.errno == errno.EBADF,
                    f"publication staging descriptor closed for unrelated reason: {exc}")
        else:
            os.close(pinned_fds[0])
            raise Fail("publication staging descriptor leaked after failed rename")
        require(target.read_bytes() == b"original",
                "failed publication changed original authority bytes")
        require(len(reused) == 1, "failed publication stage reuse not injected")
        require(reused[0].read_bytes() == b"independent-failed-replace-canary",
                "failed publication cleanup deleted an independent stage-name owner")


def prove_atomic_parent_publication_capability(module) -> None:
    """A parent swap at replace must not overwrite an external authority."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-publication-") as temp_dir:
        root = Path(temp_dir)
        parent = root / "owned"
        outside = root / "outside"
        parent.mkdir()
        outside.mkdir()
        target = parent / "authority.txt"
        target.write_bytes(b"original-owned")
        canary = outside / "authority.txt"
        canary.write_bytes(b"external-canary")
        original_replace = module.os.replace
        swapped = [False]
        decoy = [None]

        def swap_parent_at_replace(source, destination, *args, **kwargs):
            if Path(destination) == target or destination == target.name:
                require(not swapped[0], "publication race injected twice")
                parent.rename(root / "renamed-owned")
                parent.symlink_to(outside, target_is_directory=True)
                decoy[0] = outside / Path(source).name
                decoy[0].write_bytes(b"external-decoy")
                swapped[0] = True
            return original_replace(source, destination, *args, **kwargs)

        module.os.replace = swap_parent_at_replace
        try:
            try:
                module.atomic_write_bytes(target, b"published-owned")
            except module.ReconcileFailure as exc:
                require("concurrent publication parent drift" in str(exc),
                        f"parent swap rejected for unrelated reason: {exc}")
            else:
                raise Fail("atomic publication accepted a redirected parent")
        finally:
            module.os.replace = original_replace
        require(swapped[0], "parent-swap injection never reached actual replace")
        require(canary.read_bytes() == b"external-canary",
                "atomic publication overwrote an external canary")
        require(decoy[0] is not None and decoy[0].read_bytes() == b"external-decoy",
                "atomic publication consumed a redirected external temporary file")
        require((root / "renamed-owned/authority.txt").read_bytes() == b"published-owned",
                "pinned publication did not stay in the original directory")

        safe = root / "safe"
        safe.mkdir()
        safe_target = safe / "authority.txt"
        safe_target.write_bytes(b"untouched")
        original_directory_flag = module.os.O_DIRECTORY
        module.os.O_DIRECTORY = None
        try:
            try:
                module.atomic_write_bytes(safe_target, b"unreviewed")
            except module.ReconcileFailure as exc:
                require("unsupported safe publication directory flags" in str(exc),
                        f"missing directory capability rejected for unrelated reason: {exc}")
            else:
                raise Fail("atomic publication downgraded without O_DIRECTORY")
        finally:
            module.os.O_DIRECTORY = original_directory_flag
        require(safe_target.read_bytes() == b"untouched",
                "unsupported publication changed an existing authority")


def prove_atomic_prestage_parent_swap(module) -> None:
    """Pre-stage aliases cannot create files in an independent external tree."""
    for scenario in ("symlink-before-open", "directory-before-open", "symlink-before-stage"):
        with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-prestage-") as temp_dir:
            root = Path(temp_dir)
            parent = root / "owned"
            moved = root / "moved-owned"
            outside = root / "outside"
            parent.mkdir()
            outside.mkdir()
            target = parent / "authority.txt"
            target.write_bytes(b"original-owned")
            canary = outside / "authority.txt"
            canary.write_bytes(b"external-canary")
            original_open_parent = module.open_pinned_parent
            original_stage = module.create_pinned_stage
            swapped = [False]

            def perform_swap():
                require(not swapped[0], "prestage parent race injected twice")
                parent.rename(moved)
                if scenario == "directory-before-open":
                    parent.mkdir()
                    (parent / "authority.txt").write_bytes(b"independent-parent")
                else:
                    parent.symlink_to(outside, target_is_directory=True)
                swapped[0] = True

            def swap_before_open(path, expected):
                perform_swap()
                return original_open_parent(path, expected)

            def swap_before_stage(parent_fd, leaf):
                perform_swap()
                return original_stage(parent_fd, leaf)

            if scenario == "symlink-before-stage":
                module.create_pinned_stage = swap_before_stage
            else:
                module.open_pinned_parent = swap_before_open
            try:
                try:
                    module.atomic_write_bytes(target, b"must-not-publish")
                except module.ReconcileFailure as exc:
                    expected_reason = ("symlink rollback/write path"
                                       if scenario == "symlink-before-stage"
                                       else "concurrent publication parent drift")
                    require(expected_reason in str(exc),
                            f"{scenario} rejected for unrelated reason: {exc}")
                else:
                    raise Fail(f"prestage parent replacement accepted: {scenario}")
            finally:
                module.open_pinned_parent = original_open_parent
                module.create_pinned_stage = original_stage
            require(swapped[0], f"prestage swap was not injected: {scenario}")
            require(canary.read_bytes() == b"external-canary",
                    f"prestage swap changed external canary: {scenario}")
            require(sorted(item.name for item in outside.iterdir()) == ["authority.txt"],
                    f"prestage swap staged a temporary file outside: {scenario}")
            require((moved / "authority.txt").read_bytes() == b"original-owned",
                    f"prestage swap modified original authority: {scenario}")
            require(not list(moved.glob(".authority.txt.*.tmp")),
                    f"prestage swap left a temporary file in pinned parent: {scenario}")
            if scenario == "directory-before-open":
                require((parent / "authority.txt").read_bytes() == b"independent-parent",
                        "prestage real-directory replacement was modified")


    # A renamed ancestor must not be followed through an external symlink.
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-ancestor-") as temp_dir:
        root = Path(temp_dir)
        parent = root / "top" / "owned"
        parent.mkdir(parents=True)
        target = parent / "authority.txt"
        target.write_bytes(b"original-owned")
        external_parent = root / "outside" / "owned"
        external_parent.mkdir(parents=True)
        canary = external_parent / "authority.txt"
        canary.write_bytes(b"external-canary")
        original_open_parent = module.open_pinned_parent
        swapped = [False]

        def swap_ancestor_before_open(path, expected):
            (root / "top").rename(root / "moved-top")
            (root / "top").symlink_to(root / "outside", target_is_directory=True)
            swapped[0] = True
            return original_open_parent(path, expected)

        module.open_pinned_parent = swap_ancestor_before_open
        try:
            try:
                module.atomic_write_bytes(target, b"must-not-publish")
            except module.ReconcileFailure as exc:
                require("concurrent publication parent drift" in str(exc),
                        f"ancestor swap rejected for unrelated reason: {exc}")
            else:
                raise Fail("prestage ancestor symlink swap was accepted")
        finally:
            module.open_pinned_parent = original_open_parent
        require(swapped[0], "ancestor swap did not execute")
        require(canary.read_bytes() == b"external-canary"
                and sorted(item.name for item in external_parent.iterdir()) == ["authority.txt"],
                "ancestor swap staged or published into external canary tree")
        require((root / "moved-top/owned/authority.txt").read_bytes() == b"original-owned",
                "ancestor swap modified the original owned authority")

    # Permission and ctime changes before parent acquisition are authority drift.
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-parent-mode-") as temp_dir:
        root = Path(temp_dir)
        target = root / "authority.txt"
        target.write_bytes(b"original-owned")
        root.chmod(0o700)
        original_open_parent = module.open_pinned_parent
        mutated = [False]

        def change_mode_before_open(path, expected):
            root.chmod(0o755)
            mutated[0] = True
            return original_open_parent(path, expected)

        module.open_pinned_parent = change_mode_before_open
        try:
            try:
                module.atomic_write_bytes(target, b"must-not-publish")
            except module.ReconcileFailure as exc:
                require("concurrent publication parent drift" in str(exc),
                        f"parent mode drift rejected for unrelated reason: {exc}")
            else:
                raise Fail("prestage parent mode drift was accepted")
        finally:
            module.open_pinned_parent = original_open_parent
        require(mutated[0] and target.read_bytes() == b"original-owned",
                "prestage parent mode drift altered the authority")
        require(not list(root.glob(".authority.txt.*.tmp")),
                "prestage parent mode drift left temporary residue")


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
                         "ctime-only", "symlink-swapped", "deleted", "created"):
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
                elif scenario == "ctime-only":
                    previous = target.stat()
                    target.write_bytes(b"original")
                    os.utime(target, ns=(previous.st_atime_ns, previous.st_mtime_ns))
                    observed = target.stat()
                    require(observed.st_size == previous.st_size
                            and observed.st_mtime_ns == previous.st_mtime_ns
                            and observed.st_ino == previous.st_ino
                            and observed.st_ctime_ns != previous.st_ctime_ns,
                            "ctime-only publication fixture did not isolate ctime drift")
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
            elif scenario == "ctime-only":
                require(target.read_bytes() == b"original",
                        "poststage ctime-only rewrite was overwritten")
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


def prove_pinned_pathname_swap_rejection(module) -> None:
    """A stable descriptor must not certify a replaced live pathname."""
    for scenario in ("same-content-leaf-swap", "parent-symlink-swap"):
        with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-path-swap-") as temp_dir:
            root = Path(temp_dir)
            parent = root / "authority"
            parent.mkdir()
            target = parent / "record.txt"
            target.write_bytes(b"original")
            replacement = root / "replacement.txt"
            replacement.write_bytes(b"original")
            outside = root / "outside"
            outside.mkdir()
            (outside / "record.txt").write_bytes(b"original")
            original_inode = target.stat().st_ino
            original_read = module.os.read
            original_fstat = module.os.fstat
            frozen = [None]
            swapped = [False]

            def frozen_fstat(fd):
                actual = original_fstat(fd)
                if frozen[0] is None:
                    frozen[0] = actual
                return frozen[0]

            def swap_after_read(fd, count):
                chunk = original_read(fd, count)
                if chunk and not swapped[0]:
                    if scenario == "same-content-leaf-swap":
                        replacement.replace(target)
                    else:
                        parent.rename(root / "original-parent")
                        parent.symlink_to(outside, target_is_directory=True)
                    swapped[0] = True
                return chunk

            # Freeze descriptor metadata to isolate the pathname identity
            # check: ctime-only descriptor checking cannot be the proof here.
            module.os.fstat = frozen_fstat
            module.os.read = swap_after_read
            try:
                try:
                    module.read_regular_bytes(target)
                except module.ReconcileFailure as exc:
                    expected = ("symlink rollback/write path" if scenario == "parent-symlink-swap"
                                else "concurrent authority drift during read")
                    require(expected in str(exc),
                            f"{scenario} rejected for unrelated reason: {exc}")
                else:
                    raise Fail(f"pinned reader accepted replaced live path: {scenario}")
            finally:
                module.os.read = original_read
                module.os.fstat = original_fstat
            require(swapped[0] and frozen[0] is not None,
                    f"{scenario} did not exercise the pinned descriptor")
            require(target.read_bytes() == b"original",
                    f"{scenario} changed the independent live authority bytes")
            if scenario == "same-content-leaf-swap":
                require(target.stat().st_ino != original_inode,
                        "same-content leaf swap did not change pathname identity")
            else:
                require(parent.is_symlink()
                        and (root / "original-parent/record.txt").read_bytes() == b"original"
                        and (outside / "record.txt").read_bytes() == b"original",
                        "parent alias swap did not preserve both independent authorities")


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
        require(module.read(regular) == "regular",
                "pinned text reader rejected an ordinary UTF-8 authority")
        try:
            module.read(root / "missing.txt")
        except module.ReconcileFailure as exc:
            require("missing file:" in str(exc),
                    f"pinned text reader rejected missing file for unrelated reason: {exc}")
        else:
            raise Fail("pinned text reader accepted missing authority")
        # A same-length in-place rewrite can restore mtime and retain inode.
        # The pinned descriptor must still detect the changed ctime.
        original_read = module.os.read
        baseline = regular.stat()
        injected = [False]

        def concurrent_same_mtime_rewrite(fd, count):
            chunk = original_read(fd, count)
            if chunk and not injected[0]:
                regular.write_bytes(b"changed")
                os.utime(regular, ns=(baseline.st_atime_ns, baseline.st_mtime_ns))
                injected[0] = True
            return chunk

        module.os.read = concurrent_same_mtime_rewrite
        try:
            try:
                module.read_regular_bytes(regular)
            except module.ReconcileFailure as exc:
                require("concurrent authority drift during read" in str(exc),
                        f"pinned reader rejected ctime drift for unrelated reason: {exc}")
            else:
                raise Fail("pinned reader accepted same-size same-mtime in-place rewrite")
        finally:
            module.os.read = original_read
        observed = regular.stat()
        require(injected[0] and observed.st_size == baseline.st_size
                and observed.st_ino == baseline.st_ino
                and observed.st_mtime_ns == baseline.st_mtime_ns
                and observed.st_ctime_ns != baseline.st_ctime_ns,
                "pinned reader ctime-only fixture did not isolate ctime drift")
        hardlink = root / "hardlink.txt"
        os.link(regular, hardlink)
        try:
            for candidate in (regular, hardlink):
                for reader in (module.read_regular_bytes, module.read):
                    try:
                        reader(candidate)
                    except module.ReconcileFailure as exc:
                        require("hardlinked rollback/write path" in str(exc),
                                f"hardlinked reader rejected for unrelated reason: {exc}")
                    else:
                        raise Fail("pinned reader accepted a hardlinked authority")
            module.ROLLBACK_SNAPSHOT = {regular: b"changed"}
            module.ROLLBACK_WRITTEN.clear()
            try:
                module.atomic_write_bytes(regular, b"unreviewed")
            except module.ReconcileFailure as exc:
                require("hardlinked rollback/write path" in str(exc),
                        f"hardlinked writer rejected for unrelated reason: {exc}")
            else:
                raise Fail("atomic writer accepted a hardlinked authority")
        finally:
            module.ROLLBACK_SNAPSHOT = None
            module.ROLLBACK_WRITTEN.clear()
            hardlink.unlink()
        # Replace a regular leaf with an external symlink at the actual open
        # boundary. The initial lstat is deliberately valid; the no-follow
        # open must reject the later alias with a fixed domain diagnostic.
        raced = root / "raced.txt"
        raced.write_bytes(b"owned")
        outside = root / "external.txt"
        outside.write_bytes(b"external-canary")
        original_open = module.os.open
        opened_raced = [False]

        def redirect_leaf_before_open(candidate, flags, *args, **kwargs):
            if Path(candidate) == raced and flags & os.O_NOFOLLOW:
                raced.unlink()
                raced.symlink_to(outside)
                opened_raced[0] = True
            return original_open(candidate, flags, *args, **kwargs)

        module.os.open = redirect_leaf_before_open
        try:
            try:
                module.read_regular_bytes(raced)
            except module.ReconcileFailure as exc:
                require("concurrent authority drift during read" in str(exc),
                        f"reader open race rejected for unrelated reason: {exc}")
                require(exc.__suppress_context__,
                        "reader open race exposed raw OS exception context")
            else:
                raise Fail("reader accepted a leaf swapped to an external symlink")
        finally:
            module.os.open = original_open
        require(opened_raced[0] and raced.is_symlink(),
                "reader open race did not replace the reviewed leaf")
        require(outside.read_bytes() == b"external-canary",
                "reader open race changed external canary bytes")

        require(module.read_regular_bytes(regular) == b"changed",
                "hardlink removal did not restore a single-name authority")
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
            try:
                module.read(unsafe)
            except module.ReconcileFailure as exc:
                require(("nonregular rollback/write path" in str(exc)
                         or "symlink rollback/write path" in str(exc)),
                        f"pinned text reader rejected {unsafe.name} for unrelated reason: {exc}")
            else:
                raise Fail(f"pinned text reader accepted special path: {unsafe.name}")

        invalid = root / "invalid-utf8.txt"
        invalid.write_bytes(b"\xff")
        try:
            module.read(invalid)
        except module.ReconcileFailure as exc:
            require("invalid UTF-8 authority" in str(exc),
                    f"pinned text reader rejected invalid UTF-8 for unrelated reason: {exc}")
        else:
            raise Fail("pinned text reader accepted invalid UTF-8 authority")

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

def prove_bounded_authority_reads(module) -> None:
    """Reject oversized sparse inputs and reads growing beyond the initial size."""
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-route-read-bound-") as temp_dir:
        root = Path(temp_dir)
        small = root / "small.txt"
        small.write_bytes(b"ok")
        require(module.read_regular_bytes(small) == b"ok",
                "bounded reader rejected a small regular file")
        oversized = root / "oversized.txt"
        with oversized.open("wb") as handle:
            handle.truncate(module.MAX_AUTHORITY_READ_BYTES + 1)
        try:
            module.read_regular_bytes(oversized)
        except module.ReconcileFailure as exc:
            require("oversized rollback/write path" in str(exc),
                    f"oversized sparse file rejected for unrelated reason: {exc}")
        else:
            raise Fail("pinned reader accepted an oversized sparse authority")
        original_read = module.os.read
        chunk = b"x" * (1024 * 1024)
        calls = [0]

        def growing_read(fd, count):
            calls[0] += 1
            return chunk if calls[0] <= 9 else b""

        module.os.read = growing_read
        try:
            try:
                module.read_regular_bytes(small)
            except module.ReconcileFailure as exc:
                require("oversized rollback/write path" in str(exc),
                        f"growing read rejected for unrelated reason: {exc}")
            else:
                raise Fail("pinned reader accepted more than the bounded read limit")
        finally:
            module.os.read = original_read
        require(calls[0] == 9, "growing-read negative did not reach the limit")
        require(small.read_bytes() == b"ok",
                "growing-read negative changed the original authority")
        require(module.read_regular_bytes(small) == b"ok",
                "bounded reader did not recover after a rejected read")


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

        # An independent writer can replace an owned inode with identical bytes,
        # or change only its mode. Neither may be rolled back as our own write.
        for scenario in ("identical-inode-swap", "identical-mode-change"):
            owned.write_bytes(b"baseline")
            owned.chmod(0o644)
            module.ROLLBACK_SNAPSHOT = {owned: b"baseline"}
            module.ROLLBACK_WRITTEN.clear()
            module.ROLLBACK_PUBLISHED_IDENTITIES.clear()
            module.atomic_write_bytes(owned, b"our-change")
            if scenario == "identical-inode-swap":
                alternate = root / "alternate.txt"
                alternate.write_bytes(b"our-change")
                os.replace(alternate, owned)
            else:
                owned.chmod(0o600)
            before_inode = owned.stat().st_ino
            try:
                module.rollback_authority_files()
            except module.ReconcileFailure as exc:
                require("concurrent authority identity drift before rollback" in str(exc),
                        f"{scenario} rollback rejected for unrelated reason: {exc}")
            else:
                raise Fail(f"rollback accepted {scenario}")
            require(owned.read_bytes() == b"our-change"
                    and owned.stat().st_ino == before_inode,
                    f"rollback overwrote {scenario}")
            try:
                module.atomic_write_bytes(owned, b"another-write")
            except module.ReconcileFailure as exc:
                require("concurrent authority identity drift before write" in str(exc),
                        f"{scenario} prewrite rejected for unrelated reason: {exc}")
            else:
                raise Fail(f"atomic write accepted {scenario}")
            require(owned.read_bytes() == b"our-change",
                    f"atomic writer overwrote {scenario}")

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
        # Force a parent-directory rename/symlink swap at the unlink syscall.
        # The pinned dir_fd must remove only our original inode, not a file
        # reached through the newly redirected live pathname.
        parent = root / "owned-parent"
        parent.mkdir()
        created_under_parent = parent / "created.txt"
        outside = root / "outside-parent"
        outside.mkdir()
        canary = outside / "created.txt"
        canary.write_bytes(b"external-canary")
        module.ROLLBACK_SNAPSHOT = {created_under_parent: None}
        module.ROLLBACK_WRITTEN.clear()
        module.ROLLBACK_PUBLISHED_IDENTITIES.clear()
        module.atomic_write_bytes(created_under_parent, b"owned-new-file")
        original_unlink = module.os.unlink
        swapped = [False]

        def swap_parent_at_unlink(candidate, *args, **kwargs):
            if candidate == "created.txt" and kwargs.get("dir_fd") is not None:
                parent.rename(root / "renamed-owned-parent")
                parent.symlink_to(outside, target_is_directory=True)
                swapped[0] = True
            return original_unlink(candidate, *args, **kwargs)

        module.os.unlink = swap_parent_at_unlink
        try:
            module.rollback_authority_files()
        finally:
            module.os.unlink = original_unlink
        require(swapped[0], "rollback did not use a pinned directory-fd unlink")
        require(canary.read_bytes() == b"external-canary",
                "parent-swap rollback removed or changed an external canary")
        require(not (root / "renamed-owned-parent/created.txt").exists(),
                "parent-swap rollback retained its owned new file")
        require(parent.is_symlink() and parent.resolve() == outside,
                "parent-swap fixture did not redirect the live pathname")

        # A swap before opening the parent must fail closed with a fixed
        # diagnostic instead of leaking a raw OS error or following the alias.
        guarded_parent = root / "guarded-parent"
        guarded_parent.mkdir()
        guarded_file = guarded_parent / "created.txt"
        guarded_outside = root / "guarded-outside"
        guarded_outside.mkdir()
        guarded_canary = guarded_outside / "created.txt"
        guarded_canary.write_bytes(b"guarded-external")
        module.ROLLBACK_SNAPSHOT = {guarded_file: None}
        module.ROLLBACK_WRITTEN.clear()
        module.ROLLBACK_PUBLISHED_IDENTITIES.clear()
        module.atomic_write_bytes(guarded_file, b"guarded-owned")
        original_open = module.os.open
        open_swapped = [False]

        def redirect_before_parent_open(candidate, flags, *args, **kwargs):
            if Path(candidate) == guarded_parent and flags & os.O_DIRECTORY:
                guarded_parent.rename(root / "renamed-guarded-parent")
                guarded_parent.symlink_to(guarded_outside, target_is_directory=True)
                open_swapped[0] = True
            return original_open(candidate, flags, *args, **kwargs)

        module.os.open = redirect_before_parent_open
        try:
            try:
                module.rollback_authority_files()
            except module.ReconcileFailure as exc:
                require("concurrent rollback parent drift" in str(exc),
                        f"parent-open swap rejected for unrelated reason: {exc}")
            else:
                raise Fail("rollback followed a swapped parent before open")
        finally:
            module.os.open = original_open
        require(open_swapped[0], "parent-open swap did not reach directory acquisition")
        require(guarded_canary.read_bytes() == b"guarded-external",
                "parent-open swap changed the external canary")
        require((root / "renamed-guarded-parent/created.txt").read_bytes()
                == b"guarded-owned", "parent-open swap changed the owned file")

        # Missing O_DIRECTORY is an explicit unsupported capability, never
        # permission to downgrade to pathname unlink.
        unsupported_parent = root / "unsupported-parent"
        unsupported_parent.mkdir()
        unsupported_file = unsupported_parent / "created.txt"
        module.ROLLBACK_SNAPSHOT = {unsupported_file: None}
        module.ROLLBACK_WRITTEN.clear()
        module.ROLLBACK_PUBLISHED_IDENTITIES.clear()
        module.atomic_write_bytes(unsupported_file, b"unsupported-owned")
        original_directory_flag = module.os.O_DIRECTORY
        module.os.O_DIRECTORY = None
        try:
            try:
                module.rollback_authority_files()
            except module.ReconcileFailure as exc:
                require("unsupported safe rollback directory flags" in str(exc),
                        f"missing O_DIRECTORY rejected for unrelated reason: {exc}")
            else:
                raise Fail("rollback downgraded when O_DIRECTORY was unavailable")
        finally:
            module.os.O_DIRECTORY = original_directory_flag
        require(unsupported_file.read_bytes() == b"unsupported-owned",
                "missing O_DIRECTORY changed an owned new file")

        module.ROLLBACK_SNAPSHOT = None
        module.ROLLBACK_WRITTEN.clear()
        module.ROLLBACK_PUBLISHED_IDENTITIES.clear()


def main() -> int:
    module = load_module()
    prove_atomic_replace_failure(module)
    prove_atomic_mode_preservation(module)
    prove_atomic_mode_failure_cleanup(module)
    prove_atomic_fdopen_failure_cleanup(module)
    prove_atomic_dup_failure_cleanup(module)
    prove_postpublication_temp_reuse_preserved(module)
    prove_failed_publication_temp_reuse_preserved(module)
    prove_atomic_parent_publication_capability(module)
    prove_atomic_prestage_parent_swap(module)
    prove_atomic_poststage_drift_rejection(module)
    prove_atomic_short_write_rejection(module)
    prove_pinned_pathname_swap_rejection(module)
    prove_nonblocking_special_file_reads(module)
    prove_bounded_authority_reads(module)
    prove_learning_scan_boundary(module)
    prove_scan_root_alias_rejection(module)
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
