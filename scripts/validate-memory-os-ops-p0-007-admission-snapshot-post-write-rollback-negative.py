#!/usr/bin/env python3
"""Prove strict OPS-P0-007 snapshot publication rolls back bytes/mode and preserves rollback diagnostics."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

PROTECTED_RECOVERY_REGISTRIES = (
    ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json",
)


class Fail(RuntimeError):
    pass


def require_canonical_rollback_authority(
    path: Path, expected_relative: Path, root: Path = ROOT
) -> None:
    try:
        lexical = path.relative_to(root)
        resolved = path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"strict snapshot rollback canonical authority path drift: {expected_relative}") from exc
    if (
        lexical != expected_relative or resolved != expected_relative
        or not path.is_file() or path.is_symlink() or path.parent.is_symlink()
    ):
        raise Fail(f"strict snapshot rollback canonical authority path drift: {expected_relative}")


def prove_rollback_symlink_guard() -> None:
    # All alias mutations stay outside the checked-out canonical authority.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-rollback-path-negative-") as tmp:
        root = Path(tmp)
        parent = root / "authority"
        parent.mkdir()
        path = parent / "snapshot.json"
        path.write_text('{"productionDecision":"NO_GO"}\n', encoding="utf-8")
        relative = Path("authority/snapshot.json")
        require_canonical_rollback_authority(path, relative, root)
        original = parent / "original.json"
        path.rename(original)
        path.symlink_to(original.name)
        for label in ("file symlink",):
            try:
                require_canonical_rollback_authority(path, relative, root)
            except Fail as exc:
                if str(exc) != f"strict snapshot rollback canonical authority path drift: {relative}":
                    raise Fail(f"{label} rejected outside exact path guard: {exc}") from exc
            else:
                raise Fail(f"strict snapshot rollback accepted {label}")
        path.unlink()
        original.rename(path)
        require_canonical_rollback_authority(path, relative, root)
        moved = root / "actual"
        parent.rename(moved)
        parent.symlink_to(moved.name, target_is_directory=True)
        try:
            require_canonical_rollback_authority(path, relative, root)
        except Fail as exc:
            if str(exc) != f"strict snapshot rollback canonical authority path drift: {relative}":
                raise Fail(f"parent symlink rejected outside exact path guard: {exc}") from exc
        else:
            raise Fail("strict snapshot rollback accepted parent symlink")


def require_canonical_rollback_sources() -> None:
    for path in (SNAPSHOT, STATUS, GENERATOR, *PROTECTED_RECOVERY_REGISTRIES):
        require_canonical_rollback_authority(path, path.relative_to(ROOT))


def protected_state(path: Path) -> tuple[object, ...]:
    """Protect registry bytes and source/parent inode identity across rollback."""
    entry = path.lstat()
    parent = path.parent.lstat()
    return (
        path.read_bytes(),
        (entry.st_mode, entry.st_dev, entry.st_ino),
        (parent.st_mode, parent.st_dev, parent.st_ino),
        path.resolve(strict=True),
    )


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_ops_p0_007_snapshot_post_write_rollback_negative_generator",
        GENERATOR,
    )
    if spec is None or spec.loader is None:
        raise Fail("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corrupt_published_snapshot() -> None:
    value = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fail("published strict snapshot candidate was not an object")
    value["productionAuthorization"] = True
    SNAPSHOT.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")



PRIMARY_ROLLBACK_DIAGNOSTIC = "generated strict snapshot invalid: snapshot field set drift"
FAILED_ROLLBACK_DIAGNOSTIC = (
    PRIMARY_ROLLBACK_DIAGNOSTIC
    + "; rollback incomplete: cannot atomically write contracts/operations/ops-p0-007-admission-snapshot.v1.json: synthetic strict snapshot rollback replace rejection"
)


def require_rollback_diagnostic(message: str, failed_rollback: bool) -> None:
    expected = FAILED_ROLLBACK_DIAGNOSTIC if failed_rollback else PRIMARY_ROLLBACK_DIAGNOSTIC
    if message != expected:
        raise Fail(f"post-write rollback rejected outside exact canonical diagnostic: {message!r}")


def prove_rollback_diagnostic_classifier() -> None:
    for failed, expected in (
        (False, PRIMARY_ROLLBACK_DIAGNOSTIC),
        (True, FAILED_ROLLBACK_DIAGNOSTIC),
    ):
        require_rollback_diagnostic(expected, failed)
        for wrong in (
            expected + " unrelated",
            "unrelated " + expected,
            expected + "\nunrelated diagnostic",
            expected.replace("snapshot field set drift", "unrelated failure"),
        ):
            try:
                require_rollback_diagnostic(wrong, failed)
            except Fail as exc:
                if "outside exact canonical diagnostic" not in str(exc):
                    raise Fail(f"rollback classifier rejected outside intended guard: {exc}") from exc
            else:
                raise Fail("rollback classifier accepted unrelated or multiline diagnostic")


def run_successful_rollback() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    original_mode = mode(SNAPSHOT)
    status_before = STATUS.read_bytes()
    status_mode = mode(STATUS)
    protected_before = {
        path: protected_state(path)
        for path in (STATUS, GENERATOR, *PROTECTED_RECOVERY_REGISTRIES)
    }
    module = load_generator_module()
    original_replace = module.os.replace
    snapshot_replace_count = 0

    def replace_then_corrupt_once(source: str | Path, destination: str | Path) -> None:
        nonlocal snapshot_replace_count
        original_replace(source, destination)
        try:
            destination_path = Path(destination).resolve()
        except (OSError, RuntimeError):
            return
        if destination_path != SNAPSHOT.resolve():
            return
        snapshot_replace_count += 1
        if snapshot_replace_count == 1:
            # Corrupt only the just-published candidate. The generator must let the
            # canonical validator reject it, then perform a second atomic replace
            # that restores the exact previous authority.
            corrupt_published_snapshot()

    try:
        SNAPSHOT.chmod(0o640)
        module.os.replace = replace_then_corrupt_once
        try:
            module.main()
        except SystemExit as exc:
            message = str(exc)
            try:
                require_rollback_diagnostic(message, False)
            except Fail as mismatch:
                raise Fail(f"post-write rejection surfaced at unexpected boundary: {message}") from mismatch
        else:
            raise Fail("corrupted post-write strict snapshot candidate unexpectedly validated")
        finally:
            module.os.replace = original_replace

        if snapshot_replace_count != 2:
            raise Fail(f"expected candidate publication plus rollback replace, observed {snapshot_replace_count}")
        if SNAPSHOT.read_bytes() != snapshot_before:
            raise Fail("post-write validation failure did not restore exact canonical snapshot bytes")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"post-write validation rollback changed canonical mode: {oct(mode(SNAPSHOT))}")
        leftovers = list(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
        if leftovers:
            raise Fail(f"post-write validation rollback left temporary strict snapshot files: {leftovers}")
    finally:
        module.os.replace = original_replace
        if SNAPSHOT.read_bytes() != snapshot_before:
            SNAPSHOT.write_bytes(snapshot_before)
        SNAPSHOT.chmod(original_mode)

    if SNAPSHOT.read_bytes() != snapshot_before:
        raise Fail("successful rollback case mutated canonical strict snapshot bytes")
    if mode(SNAPSHOT) != original_mode:
        raise Fail("successful rollback case did not restore original canonical strict snapshot mode")
    if STATUS.read_bytes() != status_before or mode(STATUS) != status_mode:
        raise Fail("successful rollback case mutated canonical production status bytes/mode")
    for path, state in protected_before.items():
        if protected_state(path) != state:
            raise Fail(f"post-write rollback changed protected recovery authority bytes/identity: {path.relative_to(ROOT)}")


def run_failed_rollback_preserves_primary_diagnostic() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    original_mode = mode(SNAPSHOT)
    status_before = STATUS.read_bytes()
    status_mode = mode(STATUS)
    protected_before = {
        path: protected_state(path)
        for path in (STATUS, GENERATOR, *PROTECTED_RECOVERY_REGISTRIES)
    }
    module = load_generator_module()
    original_replace = module.os.replace
    snapshot_replace_count = 0

    def replace_corrupt_then_reject_rollback(source: str | Path, destination: str | Path) -> None:
        nonlocal snapshot_replace_count
        try:
            destination_path = Path(destination).resolve()
        except (OSError, RuntimeError):
            original_replace(source, destination)
            return
        if destination_path != SNAPSHOT.resolve():
            original_replace(source, destination)
            return
        snapshot_replace_count += 1
        if snapshot_replace_count == 1:
            original_replace(source, destination)
            corrupt_published_snapshot()
            return
        if snapshot_replace_count == 2:
            raise OSError("synthetic strict snapshot rollback replace rejection")
        raise Fail(f"unexpected strict snapshot replace attempt: {snapshot_replace_count}")

    try:
        SNAPSHOT.chmod(0o640)
        module.os.replace = replace_corrupt_then_reject_rollback
        try:
            module.main()
        except SystemExit as exc:
            message = str(exc)
            require_rollback_diagnostic(message, True)
        else:
            raise Fail("synthetic rollback replace failure unexpectedly accepted")
        finally:
            module.os.replace = original_replace

        if snapshot_replace_count != 2:
            raise Fail(f"expected candidate publication plus rejected rollback replace, observed {snapshot_replace_count}")
        published = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        if SNAPSHOT.read_bytes() == snapshot_before or published.get("productionAuthorization") is not True:
            raise Fail("failed rollback did not retain the injected invalid published candidate")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"failed rollback changed canonical snapshot mode before cleanup: {oct(mode(SNAPSHOT))}")
        leftovers = list(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
        if leftovers:
            raise Fail(f"failed rollback left temporary strict snapshot files: {leftovers}")
    finally:
        module.os.replace = original_replace
        SNAPSHOT.write_bytes(snapshot_before)
        SNAPSHOT.chmod(original_mode)

    if SNAPSHOT.read_bytes() != snapshot_before:
        raise Fail("failed rollback negative cleanup did not restore canonical strict snapshot bytes")
    if mode(SNAPSHOT) != original_mode:
        raise Fail("failed rollback negative cleanup did not restore canonical strict snapshot mode")
    if STATUS.read_bytes() != status_before or mode(STATUS) != status_mode:
        raise Fail("failed rollback case mutated canonical production status bytes/mode")
    for path, state in protected_before.items():
        if protected_state(path) != state:
            raise Fail(f"post-write rollback changed protected recovery authority bytes/identity: {path.relative_to(ROOT)}")


def main() -> int:
    prove_rollback_diagnostic_classifier()
    prove_rollback_symlink_guard()
    require_canonical_rollback_sources()
    run_successful_rollback()
    require_canonical_rollback_sources()
    run_failed_rollback_preserves_primary_diagnostic()
    require_canonical_rollback_sources()

    print("Memory OS OPS-P0-007 strict snapshot post-write rollback negative PASS")
    print("canonical post-write validator rejection exercised after candidate publication: true")
    print("exact snapshot bytes restored after successful validation rollback: true")
    print("canonical 0640 mode preserved across candidate publication and rollback: true")
    print("rollback writer failure preserves primary validation diagnostic: true")
    print("rollback writer failure is surfaced as rollback incomplete: true")
    print("failed rollback leaves the injected invalid candidate until explicit negative cleanup: true")
    print("canonical production status and six recovery registries bytes/identity remain unchanged: true")
    print("temporary snapshot authority residue after rollback attempts: false")
    print("negative cleanup restores canonical strict snapshot bytes/mode: true")
    print("production evidence/readiness/promotion created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, json.JSONDecodeError, OSError) as exc:
        print(f"OPS-P0-007 SNAPSHOT POST-WRITE ROLLBACK NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
