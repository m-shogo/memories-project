#!/usr/bin/env python3
"""Prove admission-chain authority identity, fail-closed validation, and rollback."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-admission-chain.py"
LOAD_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-load-negative.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
PREFLIGHT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
BINDING_CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "admission-chain fixture guard no-follow directory open unsupported")
    anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError as exc:
        raise Fail("admission-chain fixture guard parent outside trusted roots") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    require(anchor.is_dir() and not anchor.is_symlink(),
            "admission-chain fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except OSError as exc:
        raise Fail("admission-chain fixture guard anchor open failed") from exc
    try:
        opened = os.fstat(fd)
        entry = anchor.lstat()
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "admission-chain fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "admission-chain fixture guard ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            opened = os.fstat(fd)
            entry = cursor.lstat()
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "admission-chain fixture guard ancestor identity drift",
            )
        return fd
    except OSError as exc:
        os.close(fd)
        raise Fail("admission-chain fixture guard parent open failed") from exc
    except BaseException:
        os.close(fd)
        raise


MAX_HELPER_SOURCE_BYTES = 1024 * 1024


def load_pinned_fixture_guard(path: Path, name: str):
    """Bind checked ancestors and leaf source to pinned FDs."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            raise Fail("admission-chain fixture guard source open failed") from exc
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "admission-chain fixture guard source identity drift",
            )
            with os.fdopen(os.dup(fd), "rb") as stream:
                source = stream.read(MAX_HELPER_SOURCE_BYTES + 1)
            require(len(source) <= MAX_HELPER_SOURCE_BYTES,
                    "fixture guard pinned source oversized")
            class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
                def get_code(self, fullname):
                    require(fullname == name, "fixture guard module identity drift")
                    try:
                        return compile(source, str(path), "exec")
                    except Exception:
                        raise Fail("fixture guard pinned source compilation failed") from None
            spec = importlib.util.spec_from_file_location(name, path, loader=PinnedSourceLoader(name, str(path)))
            require(spec is not None and spec.loader is not None,
                    "admission-chain fixture guard cannot load")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except OSError:
            raise Fail("admission-chain fixture guard pinned source read failed") from None
        finally:
            try:
                os.close(fd)
            except (Exception, SystemExit):
                raise Fail("fixture guard pinned descriptor cleanup failed") from None
    finally:
        try:
            os.close(parent_fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None


def guarded_temporary_directory(prefix: str, parent: Path = TMP_PARENT):
    # Reuse the existing admission-chain load fixture's checked parent policy.
    require(LOAD_NEGATIVE.is_file() and not LOAD_NEGATIVE.is_symlink(),
            "admission-chain fixture guard source missing or symlinked")
    helper = load_pinned_fixture_guard(LOAD_NEGATIVE, "memory_os_admission_chain_checked_fixture_parent")
    guard = getattr(helper, "guarded_temporary_directory", None)
    require(callable(guard), "admission-chain checked fixture parent helper missing")
    try:
        return guard(prefix, parent)
    except helper.Fail as exc:
        raise Fail(str(exc)) from exc


def prove_symlink_parent_rejected() -> None:
    with guarded_temporary_directory(".tmp-admission-chain-reconcile-parent-") as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(path.name for path in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("admission-chain reconcile symlink parent accepted")
        except Fail as exc:
            require(str(exc) == "admission-chain load temp ancestor missing or symlinked",
                    f"admission-chain reconcile parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("admission-chain reconcile symlink parent accepted")
        require(sorted(path.name for path in sandbox.iterdir()) == before,
                "admission-chain reconcile symlink parent published a child")
    print("PASS: admission-chain reconcile fixture symlink parent rejected before creation")


def prove_helper_source_symlink_rejected() -> None:
    # A symlinked executable helper must fail before import or fixture creation.
    global LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="admission-chain-helper-source-") as raw:
        sandbox = Path(raw)
        real = sandbox / "real-helper.py"
        real.touch()
        link = sandbox / "helper.py"
        link.symlink_to(real)
        original = LOAD_NEGATIVE
        try:
            LOAD_NEGATIVE = link
            try:
                with guarded_temporary_directory(".tmp-must-not-create-"):
                    raise Fail("admission-chain symlinked fixture helper accepted")
            except Fail as exc:
                require(str(exc) == "admission-chain fixture guard source missing or symlinked",
                        f"admission-chain fixture helper rejected at wrong boundary: {exc}")
            else:
                raise Fail("admission-chain symlinked fixture helper accepted")
        finally:
            LOAD_NEGATIVE = original
    print("PASS: admission-chain fixture helper symlink rejected before import")


def prove_helper_source_swap_during_import_is_pinned() -> None:
    # The valid source is checked and opened before a deterministic name swap.
    global LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="admission-chain-helper-import-race-") as raw:
        sandbox = Path(raw)
        trusted = sandbox / "helper.py"
        parked = sandbox / "original-helper.py"
        untrusted = sandbox / "untrusted.py"
        trusted.write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-source', prefix)\n",
            encoding="utf-8",
        )
        untrusted.write_text("raise RuntimeError('untrusted helper executed')\n", encoding="utf-8")
        original_path = LOAD_NEGATIVE
        original_spec = importlib.util.spec_from_file_location
        swapped = False
        try:
            LOAD_NEGATIVE = trusted
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-source", ".tmp-positive-"),
                "admission-chain helper pinned import positive control failed",
            )

            def swap_before_spec(name, location, *args, **kwargs):
                nonlocal swapped
                if not swapped and Path(location) == trusted:
                    swapped = True
                    trusted.rename(parked)
                    trusted.symlink_to(untrusted)
                return original_spec(name, location, *args, **kwargs)

            importlib.util.spec_from_file_location = swap_before_spec
            require(
                guarded_temporary_directory(".tmp-race-", TMP_PARENT)
                == ("pinned-source", ".tmp-race-"),
                "admission-chain helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "admission-chain helper race probe did not substitute checked source")
        finally:
            importlib.util.spec_from_file_location = original_spec
            LOAD_NEGATIVE = original_path
    print("PASS: admission-chain reconcile helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    # A checked parent may be renamed after its FD is pinned but before the
    # leaf opens. Source bytes must still come from the original directory.
    global LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="admission-chain-helper-parent-race-") as raw:
        sandbox = Path(raw)
        trusted_parent = sandbox / "trusted"
        parked_parent = sandbox / "parked"
        untrusted_parent = sandbox / "untrusted"
        trusted_parent.mkdir()
        untrusted_parent.mkdir()
        (trusted_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-parent', prefix)\n",
            encoding="utf-8",
        )
        (untrusted_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted parent helper executed')\n", encoding="utf-8")
        original_path = LOAD_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            LOAD_NEGATIVE = trusted_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-parent", ".tmp-positive-"),
                "admission-chain parent-pinned helper positive control failed",
            )

            def swap_before_leaf_open(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "helper.py" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    trusted_parent.rename(parked_parent)
                    trusted_parent.symlink_to(untrusted_parent, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_leaf_open
            require(
                guarded_temporary_directory(".tmp-parent-race-", TMP_PARENT)
                == ("pinned-parent", ".tmp-parent-race-"),
                "admission-chain helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "admission-chain helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            LOAD_NEGATIVE = original_path
    print("PASS: admission-chain reconcile helper parent swap preserves pinned source")


def prove_helper_parent_swap_before_pin_rejected() -> None:
    # If the checked parent changes before the directory FD opens, refuse it.
    global LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="admission-chain-helper-parent-preopen-") as raw:
        sandbox = Path(raw)
        trusted_parent = sandbox / "trusted"
        parked_parent = sandbox / "parked"
        untrusted_parent = sandbox / "untrusted"
        trusted_parent.mkdir()
        untrusted_parent.mkdir()
        (trusted_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-parent', prefix)\n",
            encoding="utf-8",
        )
        (untrusted_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted parent helper executed')\n", encoding="utf-8")
        original_path = LOAD_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            LOAD_NEGATIVE = trusted_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-parent", ".tmp-positive-"),
                "admission-chain parent pre-open positive control failed",
            )

            def swap_before_parent_open(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "trusted" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    trusted_parent.rename(parked_parent)
                    trusted_parent.symlink_to(untrusted_parent, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_parent_open
            try:
                guarded_temporary_directory(".tmp-parent-preopen-", TMP_PARENT)
            except Fail as exc:
                require(str(exc) == "admission-chain fixture guard parent open failed",
                        f"admission-chain helper parent pre-open rejected at wrong boundary: {exc}")
            else:
                raise Fail("admission-chain substituted helper parent accepted before FD pinning")
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "admission-chain helper parent pre-open race did not substitute checked parent")
        finally:
            os.open = original_open
            LOAD_NEGATIVE = original_path
    print("PASS: admission-chain reconcile helper parent swap before pin rejected")


def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:
    # A leaf/parent O_NOFOLLOW alone cannot protect a mutable higher ancestor.
    # Swap an owned nonterminal directory after it was pinned, before descent.
    global LOAD_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="admission-chain-helper-ancestor-race-") as raw:
        sandbox = Path(raw)
        checked_ancestor = sandbox / "checked"
        parked_ancestor = sandbox / "parked"
        redirect_ancestor = sandbox / "redirect"
        checked_parent = checked_ancestor / "nested"
        redirect_parent = redirect_ancestor / "nested"
        checked_parent.mkdir(parents=True)
        redirect_parent.mkdir(parents=True)
        (checked_parent / "helper.py").write_text(
            "class Fail(RuntimeError):\n    pass\n\n"
            "def guarded_temporary_directory(prefix, parent):\n"
            "    return ('pinned-ancestor', prefix)\n",
            encoding="utf-8",
        )
        (redirect_parent / "helper.py").write_text(
            "raise RuntimeError('untrusted ancestor helper executed')\n", encoding="utf-8"
        )
        original_path = LOAD_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            LOAD_NEGATIVE = checked_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-ancestor", ".tmp-positive-"),
                "admission-chain reconcile ancestor helper positive control failed",
            )

            def swap_before_descend(target, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and target == "nested" and kwargs.get("dir_fd") is not None:
                    swapped = True
                    checked_ancestor.rename(parked_ancestor)
                    checked_ancestor.symlink_to(redirect_ancestor, target_is_directory=True)
                return original_open(target, flags, *args, **kwargs)

            os.open = swap_before_descend
            try:
                guarded_temporary_directory(".tmp-ancestor-race-", TMP_PARENT)
            except Fail as exc:
                require(
                    str(exc) == "admission-chain fixture guard ancestor identity drift",
                    f"admission-chain reconcile helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("admission-chain reconcile helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "admission-chain reconcile helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "admission-chain reconcile helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            LOAD_NEGATIVE = original_path
    print("PASS: admission-chain reconcile helper ancestor swap fails closed during FD walk")


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_direct_authority_rejected(
    reconciler: object,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    contract_before: bytes,
    status_before: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == contract_before, f"canonical admission-chain contract mutated while rejecting {name}")
        require(STATUS.read_bytes() == status_before, f"canonical production status mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    cases = (
        ("admission-chain contract substitution", "admission-chain contract", "CONTRACT", PREFLIGHT),
        ("preflight contract substitution", "preflight contract", "PREFLIGHT", CONTRACT),
        ("drill registry substitution", "drill request registry", "DRILL_REGISTRY", GEN_REGISTRY),
        ("generation registry substitution", "generation evidence registry", "GEN_REGISTRY", DRILL_REGISTRY),
        ("generation binding substitution", "generation binding contract", "BINDING_CONTRACT", CONTRACT),
        ("typed registry substitution", "typed non-resurrection registry", "TYPED_REGISTRY", GEN_REGISTRY),
        ("drill writer substitution", "drill request writer", "DRILL_WRITER", reconciler.GEN_WRITER),
        ("generation writer substitution", "generation evidence writer", "GEN_WRITER", reconciler.DRILL_WRITER),
        ("typed writer substitution", "typed non-resurrection writer", "TYPED_WRITER", reconciler.GEN_WRITER),
        ("admission-chain validator substitution", "admission-chain validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.VALIDATOR),
        ("production status substitution", "production operability status", "STATUS", CONTRACT),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            contract_before=contract_before,
            status_before=status_before,
        )
    print(f"PASS boundary: direct admission-chain data/executable substitutions rejected: {len(cases)}")


def mutate_copy(value: dict[str, object], field: str, replacement: object) -> dict[str, object]:
    copied = json.loads(json.dumps(value))
    require(isinstance(copied, dict), "copied registry root invalid")
    copied[field] = replacement
    return copied


def prove_shared_registry_fail_closed(reconciler: object) -> None:
    drill_writer = reconciler.load_writer(
        reconciler.DRILL_WRITER,
        "memory_os_drill_writer_admission_chain_negative",
        "drill request",
    )
    gen_writer = reconciler.load_writer(
        reconciler.GEN_WRITER,
        "memory_os_generation_writer_admission_chain_negative",
        "generation evidence",
    )
    typed_writer = reconciler.load_writer(
        reconciler.TYPED_WRITER,
        "memory_os_typed_writer_admission_chain_negative",
        "typed non-resurrection",
    )

    drill = json.loads(DRILL_REGISTRY.read_text(encoding="utf-8"))
    generation = json.loads(GEN_REGISTRY.read_text(encoding="utf-8"))
    typed = json.loads(TYPED_REGISTRY.read_text(encoding="utf-8"))
    require(all(isinstance(value, dict) for value in (drill, generation, typed)), "canonical registry root invalid")

    cases = (
        ("drill registry boolean registeredRequestCount", drill_writer, mutate_copy(drill, "registeredRequestCount", False), "drill request"),
        ("drill registry productionEvidence promotion", drill_writer, mutate_copy(drill, "productionEvidence", True), "drill request"),
        ("generation registry boolean registeredEvidenceCount", gen_writer, mutate_copy(generation, "registeredEvidenceCount", False), "generation evidence"),
        ("generation registry productionReady promotion", gen_writer, mutate_copy(generation, "productionReady", True), "generation evidence"),
        ("typed registry boolean registeredRecordCount", typed_writer, mutate_copy(typed, "registeredRecordCount", False), "typed non-resurrection"),
        ("typed registry appendOnly corruption", typed_writer, mutate_copy(typed, "appendOnly", False), "typed non-resurrection"),
        ("typed registry productionEvidence promotion", typed_writer, mutate_copy(typed, "productionEvidence", True), "typed non-resurrection"),
    )
    for name, module, value, label in cases:
        expect_domain_fail(
            name,
            lambda module=module, value=value, label=label: reconciler.validate_shared_registry(module, value, label),
            reconciler.Fail,
        )
    print(f"PASS boundary: shared append-only registry corruption rejected without canonical mutation: {len(cases)}")


def prove_atomic_write_failure(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    contract_mode_before = mode(CONTRACT)
    original_replace = reconciler.os.replace

    def reject_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("synthetic atomic replace rejection")

    reconciler.os.replace = reject_replace
    try:
        try:
            reconciler.write_text(CONTRACT, contract_before.decode("utf-8") + " ")
        except reconciler.Fail as exc:
            require("cannot atomically write" in str(exc), f"atomic write rejected at wrong boundary: {exc}")
        else:
            raise Fail("synthetic atomic replace failure unexpectedly accepted")
    finally:
        reconciler.os.replace = original_replace

    require(CONTRACT.read_bytes() == contract_before, "atomic replace failure mutated canonical admission-chain contract")
    require(mode(CONTRACT) == contract_mode_before, "atomic replace failure changed canonical admission-chain contract mode")
    leftovers = list(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    require(not leftovers, f"atomic replace failure left temporary authority files: {leftovers}")
    print("PASS boundary: atomic replace failure preserves canonical admission-chain contract bytes and mode")
    print("PASS boundary: failed atomic write leaves no temporary authority file")


def prove_mode_preserving_write(reconciler: object) -> None:
    with guarded_temporary_directory(".tmp-admission-chain-mode-") as tmpdir:
        target = Path(tmpdir) / "mode-preservation.json"
        target.write_text("{}\n", encoding="utf-8")
        target.chmod(0o640)
        reconciler.write_text(target, '{"preserved": true}\n')
        require(mode(target) == 0o640, f"atomic admission-chain write changed file mode: {oct(mode(target))}")
        leftovers = list(target.parent.glob(f".{target.name}.*.tmp"))
        require(not leftovers, f"mode-preserving admission-chain write left temporary files: {leftovers}")
    print("PASS boundary: atomic admission-chain write preserves existing file mode")


def prove_post_validation_rollback(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    contract_mode_before = mode(CONTRACT)
    status_before = STATUS.read_bytes()
    original_run_validator = reconciler.run_validator
    calls: list[tuple[Path, str]] = []

    def fail_at_aggregate(path: Path, label: str) -> None:
        calls.append((path, label))
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail(f"post-reconcile {label} failed: synthetic aggregate rejection")

    reconciler.run_validator = fail_at_aggregate
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("synthetic aggregate rejection" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced admission-chain aggregate post-validation failure unexpectedly accepted")
    finally:
        reconciler.run_validator = original_run_validator

    require(
        calls
        == [
            (reconciler.VALIDATOR, "admission-chain validator"),
            (reconciler.OPERABILITY_VALIDATOR, "operability validator"),
        ],
        f"admission-chain post-write validator order drift: {calls}",
    )
    require(CONTRACT.read_bytes() == contract_before, "admission-chain contract rollback drift")
    require(mode(CONTRACT) == contract_mode_before, "admission-chain contract mode rollback drift")
    require(STATUS.read_bytes() == status_before, "production status mutated during admission-chain rollback test")
    leftovers = list(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    require(not leftovers, f"admission-chain rollback left temporary authority files: {leftovers}")
    print("PASS rollback: aggregate Operability rejection restores admission-chain contract bytes and mode")
    print("PASS boundary: post-write validator order is admission-chain then aggregate Operability")


def prove_rollback_failure_preserves_primary_diagnostic(reconciler: object) -> None:
    contract_before = CONTRACT.read_bytes()
    contract_mode_before = mode(CONTRACT)
    status_before = STATUS.read_bytes()
    original_write_text = reconciler.write_text
    original_run_validator = reconciler.run_validator
    writes = 0

    def fail_rollback(path: Path, text: str) -> None:
        nonlocal writes
        require(path == reconciler.CONTRACT, f"unexpected admission-chain rollback diagnostic write target: {path}")
        writes += 1
        if writes == 1:
            return
        raise reconciler.Fail("synthetic admission chain rollback rejection")

    def fail_chain_validator(path: Path, label: str) -> None:
        require(path == reconciler.VALIDATOR and label == "admission-chain validator", f"unexpected admission-chain rollback diagnostic validator invocation: {(path, label)}")
        raise reconciler.Fail("synthetic admission chain post-validator rejection")

    reconciler.write_text = fail_rollback
    reconciler.run_validator = fail_chain_validator
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            message = str(exc)
            require("admission chain reconcile failed" in message, f"rollback failure missing reconcile context: {message}")
            require("synthetic admission chain post-validator rejection" in message, f"rollback failure lost primary error: {message}")
            require("rollback incomplete" in message, f"rollback failure missing incomplete marker: {message}")
            require("synthetic admission chain rollback rejection" in message, f"rollback failure lost rollback error: {message}")
        else:
            raise Fail("synthetic admission-chain rollback failure unexpectedly accepted")
    finally:
        reconciler.write_text = original_write_text
        reconciler.run_validator = original_run_validator

    require(writes == 2, f"admission-chain rollback diagnostic did not attempt publication and rollback exactly once: {writes}")
    require(CONTRACT.read_bytes() == contract_before, "rollback diagnostic fixture mutated canonical admission-chain contract")
    require(mode(CONTRACT) == contract_mode_before, "rollback diagnostic fixture changed canonical admission-chain contract mode")
    require(STATUS.read_bytes() == status_before, "rollback diagnostic fixture mutated canonical production status")
    print("PASS rollback: admission-chain rollback failure reports both primary rejection and incomplete rollback without canonical mutation")


def main() -> int:
    require(VALIDATOR.is_file(), "admission-chain validator missing")
    require(RECONCILER.is_file(), "admission-chain reconciler missing")
    require(STATUS.is_file(), "production operability status missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_symlink_parent_rejected()
    prove_helper_source_symlink_rejected()
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_parent_swap_before_pin_rejected()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
    validator = load_module(VALIDATOR, "memory_os_admission_chain_validator_negative")
    reconciler = load_module(RECONCILER, "memory_os_admission_chain_reconcile_negative")

    prove_direct_authority_identity(reconciler)
    prove_shared_registry_fail_closed(reconciler)

    with guarded_temporary_directory(".tmp-admission-chain-reconcile-") as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("admission-chain invalid UTF-8 authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("admission-chain unreadable authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        loop_authority = tmp / "loop-authority.json"
        loop_authority.symlink_to(loop_authority.name)
        expect_domain_fail("admission-chain validator authority symlink loop", lambda: validator.load(loop_authority), validator.Fail)
        expect_domain_fail("admission-chain reconciler authority symlink loop", lambda: reconciler.load(loop_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-chain-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("admission-chain validator authority escapes repository", lambda: validator.load(outside), validator.Fail)
            expect_domain_fail("admission-chain reconciler authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

    prove_atomic_write_failure(reconciler)
    prove_mode_preserving_write(reconciler)
    prove_post_validation_rollback(reconciler)
    prove_rollback_failure_preserves_primary_diagnostic(reconciler)

    print("direct admission-chain data/executable substitutions accepted: false")
    print("shared append-only registry corruption auto-healed by reconciler: false")
    print("non-atomic derived admission-chain contract write accepted: false")
    print("admission-chain authority mode loss accepted: false")
    print("Admission-chain validator/reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
