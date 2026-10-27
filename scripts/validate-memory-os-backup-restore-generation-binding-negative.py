#!/usr/bin/env python3
"""Negative suite for recovery-candidate versus human-promotion separation."""

from __future__ import annotations

import copy
import importlib.util
import os
import stat
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
STATUS_RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py"
RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-negative.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pin_checked_helper_parent(path: Path) -> int:
    """Walk from a trusted repository/temp anchor, never through a symlinked ancestor."""
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
            "generation-binding fixture guard no-follow directory open unsupported")
    anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    try:
        relative = path.parent.relative_to(anchor)
    except ValueError as exc:
        raise Fail("generation-binding fixture guard parent outside trusted roots") from exc
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    require(anchor.is_dir() and not anchor.is_symlink(),
            "generation-binding fixture guard trusted anchor missing or symlinked")
    try:
        fd = os.open(anchor, flags)
    except OSError as exc:
        raise Fail("generation-binding fixture guard anchor open failed") from exc
    try:
        opened = os.fstat(fd)
        entry = anchor.lstat()
        require(
            stat.S_ISDIR(entry.st_mode)
            and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
            "generation-binding fixture guard trusted anchor identity drift",
        )
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            require(cursor.is_dir() and not cursor.is_symlink(),
                    "generation-binding fixture guard ancestor missing or symlinked")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            opened = os.fstat(fd)
            entry = cursor.lstat()
            require(
                stat.S_ISDIR(entry.st_mode)
                and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                "generation-binding fixture guard ancestor identity drift",
            )
        return fd
    except OSError as exc:
        os.close(fd)
        raise Fail("generation-binding fixture guard parent open failed") from exc
    except BaseException:
        os.close(fd)
        raise


def load_pinned_fixture_guard(path: Path, name: str):
    """Bind every checked helper ancestor and source leaf to FDs."""
    parent_fd = pin_checked_helper_parent(path)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        except OSError as exc:
            raise Fail("generation-binding fixture guard source open failed") from exc
        try:
            opened = os.fstat(fd)
            entry = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            require(
                stat.S_ISREG(opened.st_mode) and stat.S_ISREG(entry.st_mode)
                and (opened.st_dev, opened.st_ino) == (entry.st_dev, entry.st_ino),
                "generation-binding fixture guard source identity drift",
            )
            with os.fdopen(os.dup(fd), "rb") as stream:
                source = stream.read()
            spec = importlib.util.spec_from_file_location(name, path)
            require(spec is not None and spec.loader is not None,
                    "generation-binding fixture guard cannot load")
            module = importlib.util.module_from_spec(spec)
            exec(compile(source, str(path), "exec"), module.__dict__)
            return module
        except OSError as exc:
            raise Fail("generation-binding fixture guard pinned source read failed") from exc
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def guarded_temporary_directory(prefix: str, parent: Path = TMP_PARENT):
    # Reuse the generation-evidence negative harness's canonical parent check.
    require(RECONCILE_NEGATIVE.is_file() and not RECONCILE_NEGATIVE.is_symlink(),
            "generation-binding fixture guard source missing or symlinked")
    helper = load_pinned_fixture_guard(RECONCILE_NEGATIVE, "memory_os_generation_binding_checked_fixture_parent")
    guard = getattr(helper, "guarded_temporary_directory", None)
    require(callable(guard), "generation-binding checked fixture parent helper missing")
    try:
        return guard(prefix=prefix, parent=parent)
    except helper.Fail as exc:
        raise Fail(str(exc)) from exc


def prove_symlink_parent_rejected() -> None:
    with guarded_temporary_directory(".tmp-generation-binding-parent-") as raw:
        sandbox = Path(raw)
        link = sandbox / "redirect"
        link.symlink_to(sandbox, target_is_directory=True)
        before = sorted(path.name for path in sandbox.iterdir())
        try:
            with guarded_temporary_directory(".tmp-must-not-create-", link):
                raise Fail("generation-binding symlink parent accepted")
        except Fail as exc:
            require(str(exc) == "reconcile negative temp ancestor missing or symlinked",
                    f"generation-binding parent rejected at wrong boundary: {exc}")
        else:
            raise Fail("generation-binding symlink parent accepted")
        require(sorted(path.name for path in sandbox.iterdir()) == before,
                "generation-binding symlink parent published a child")
    print("PASS: generation-binding fixture symlink parent rejected before creation")


def prove_helper_source_symlink_rejected() -> None:
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-binding-helper-source-") as raw:
        sandbox = Path(raw)
        real = sandbox / "real-helper.py"
        real.touch()
        link = sandbox / "helper.py"
        link.symlink_to(real)
        original = RECONCILE_NEGATIVE
        try:
            RECONCILE_NEGATIVE = link
            try:
                with guarded_temporary_directory(".tmp-must-not-create-"):
                    raise Fail("generation-binding symlinked fixture helper accepted")
            except Fail as exc:
                require(str(exc) == "generation-binding fixture guard source missing or symlinked",
                        f"generation-binding fixture helper rejected at wrong boundary: {exc}")
            else:
                raise Fail("generation-binding symlinked fixture helper accepted")
        finally:
            RECONCILE_NEGATIVE = original
    print("PASS: generation-binding fixture helper symlink rejected before import")


def prove_helper_source_swap_during_import_is_pinned() -> None:
    # Establish a valid helper, then swap its name after the source FD opens.
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-binding-helper-import-race-") as raw:
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
        original_path = RECONCILE_NEGATIVE
        original_spec = importlib.util.spec_from_file_location
        swapped = False
        try:
            RECONCILE_NEGATIVE = trusted
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-source", ".tmp-positive-"),
                "generation-binding helper pinned import positive control failed",
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
                "generation-binding helper import executed substituted source",
            )
            require(swapped and trusted.is_symlink() and parked.is_file(),
                    "generation-binding helper race probe did not substitute checked source")
        finally:
            importlib.util.spec_from_file_location = original_spec
            RECONCILE_NEGATIVE = original_path
    print("PASS: generation-binding helper import uses pinned source after pathname substitution")


def prove_helper_parent_swap_after_pin_uses_original_source() -> None:
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-binding-helper-parent-race-") as raw:
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
        original_path = RECONCILE_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            RECONCILE_NEGATIVE = trusted_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-parent", ".tmp-positive-"),
                "generation-binding parent-pinned helper positive control failed",
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
                "generation-binding helper import followed substituted parent",
            )
            require(swapped and trusted_parent.is_symlink() and (parked_parent / "helper.py").is_file(),
                    "generation-binding helper parent race did not substitute checked parent")
        finally:
            os.open = original_open
            RECONCILE_NEGATIVE = original_path
    print("PASS: generation-binding helper parent swap preserves pinned source")


def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:
    # A leaf/parent O_NOFOLLOW alone cannot protect a mutable higher ancestor.
    # Swap an owned nonterminal directory after it was pinned, before descent.
    global RECONCILE_NEGATIVE
    with tempfile.TemporaryDirectory(prefix="generation-binding-helper-ancestor-race-") as raw:
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
        original_path = RECONCILE_NEGATIVE
        original_open = os.open
        swapped = False
        try:
            RECONCILE_NEGATIVE = checked_parent / "helper.py"
            require(
                guarded_temporary_directory(".tmp-positive-", TMP_PARENT)
                == ("pinned-ancestor", ".tmp-positive-"),
                "generation-binding ancestor helper positive control failed",
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
                    str(exc) == "generation-binding fixture guard ancestor identity drift",
                    f"generation-binding helper ancestor swap rejected at wrong boundary: {exc}",
                )
            else:
                raise Fail("generation-binding helper ancestor swap accepted")
            require(swapped and checked_ancestor.is_symlink()
                    and (parked_ancestor / "nested/helper.py").is_file(),
                    "generation-binding helper ancestor swap did not preserve pinned original")
            require((redirect_parent / "helper.py").read_text(encoding="utf-8")
                    == "raise RuntimeError('untrusted ancestor helper executed')\n",
                    "generation-binding helper ancestor swap modified untrusted source")
        finally:
            os.open = original_open
            RECONCILE_NEGATIVE = original_path
    print("PASS: generation-binding helper ancestor swap fails closed during FD walk")


def load_module():
    return load_target(VALIDATOR, "memory_os_restore_generation_binding_negative_target")


def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def candidate_state(module) -> dict[Path, dict[str, Any]]:
    real_load = module.load
    contract = copy.deepcopy(real_load(module.CONTRACT))
    backup = copy.deepcopy(real_load(module.BACKUP_POLICY))
    local = copy.deepcopy(real_load(module.LOCAL_FOUNDATIONS))
    generation = copy.deepcopy(real_load(module.GENERATION))
    evidence_contract = copy.deepcopy(real_load(module.EVIDENCE_CONTRACT))

    contract["currentBoundary"].update({
        "registeredProductionEquivalentGenerationCount": 1,
        "generationBoundBackupCount": 1,
        "generationBoundRestoreCount": 1,
        "productionEquivalentRecoveryCandidateCount": 1,
        "productionEquivalentRestoreEvidence": True,
        "independentReviewCompleted": True,
        "humanProductionPromotionReviewCompleted": False,
        "humanProductionPromotionAuthorized": False,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
    })
    contract["readiness"].update({
        "environmentGenerationAvailable": True,
        "generationBoundBackupAvailable": True,
        "generationBoundRestoreAvailable": True,
        "productionEquivalentRecoveryCandidateAvailable": True,
        "independentReviewCompleted": True,
        "humanProductionPromotionReviewCompleted": False,
        "humanProductionPromotionAuthorized": False,
        "productionEquivalentRestoreEvidence": True,
        "productionReady": False,
    })
    generation["currentBoundary"].update({
        "registeredGenerationCount": 1,
        "productionEvidence": False,
        "productionReady": False,
    })
    generation_registry = {
        "appendOnly": True,
        "productionEvidence": False,
        "registeredGenerationCount": 1,
        "generations": [{}],
    }
    evidence_registry = {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "productionEvidence": False,
        "productionReady": False,
        "registeredEvidenceCount": 1,
        "completeGenerationBoundBackupCount": 1,
        "completeGenerationBoundRestoreCount": 1,
        "productionEquivalentRecoveryCandidateCount": 1,
        "records": [{
            "syntheticCandidate": True,
            "evidenceComplete": True,
            "isolatedRestoreVerified": True,
            "backupArtifactSha256": "a" * 64,
            "restoredBackupArtifactSha256": "a" * 64,
        }],
    }
    return {
        module.CONTRACT: contract,
        module.BACKUP_POLICY: backup,
        module.LOCAL_FOUNDATIONS: local,
        module.GENERATION: generation,
        module.GEN_REGISTRY: generation_registry,
        module.EVIDENCE_CONTRACT: evidence_contract,
        module.EVIDENCE_REGISTRY: evidence_registry,
    }


def run_with_state(module, state: dict[Path, dict[str, Any]]) -> int:
    original_load = module.load
    original_load_evidence_writer = module.load_evidence_writer

    def fake_load(path: Path) -> dict[str, Any]:
        if path in state:
            return copy.deepcopy(state[path])
        return original_load(path)

    class SyntheticEvidenceWriter:
        @staticmethod
        def validate_record(record: dict[str, Any], *, require_current_drill_request: bool = True) -> None:
            require(isinstance(record, dict), "synthetic evidence row invalid")

        @staticmethod
        def candidate(record: dict[str, Any]) -> bool:
            return record.get("syntheticCandidate") is True

    module.load = fake_load
    module.load_evidence_writer = lambda: SyntheticEvidenceWriter
    try:
        return module.main()
    finally:
        module.load = original_load
        module.load_evidence_writer = original_load_evidence_writer


def prove_status_reconcile_boundaries() -> None:
    reconciler = load_target(STATUS_RECONCILER, "memory_os_restore_generation_status_negative_target")
    require(TMP_PARENT.is_dir(), "generation-status temporary fixture parent missing")

    with guarded_temporary_directory(".tmp-generation-status-negative-") as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_rejected(reconciler, "generation status invalid UTF-8 authority", lambda: reconciler.load(invalid_utf8))

        loop_authority = tmp / "loop-authority.json"
        loop_authority.symlink_to(loop_authority.name)
        expect_rejected(reconciler, "generation status authority symlink loop", lambda: reconciler.load(loop_authority))

        contract_copy = tmp / reconciler.CONTRACT.name
        status_copy = tmp / reconciler.STATUS.name
        shutil.copyfile(reconciler.CONTRACT, contract_copy)
        shutil.copyfile(reconciler.STATUS, status_copy)
        original_status = status_copy.read_bytes()

        pass_validator = tmp / "pass-validator.py"
        pass_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8")
        fail_validator = tmp / "fail-validator.py"
        fail_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(43)\n", encoding="utf-8")

        original_contract_path = reconciler.CONTRACT
        original_status_path = reconciler.STATUS
        original_validator = reconciler.VALIDATOR
        original_backup_validator = reconciler.BACKUP_VALIDATOR
        original_operability_validator = reconciler.OPERABILITY_VALIDATOR
        try:
            reconciler.CONTRACT = contract_copy
            reconciler.STATUS = status_copy
            reconciler.VALIDATOR = pass_validator
            reconciler.BACKUP_VALIDATOR = fail_validator
            reconciler.OPERABILITY_VALIDATOR = pass_validator
            expect_rejected(reconciler, "generation status forced post-validator failure", reconciler.main)
            require(status_copy.read_bytes() == original_status, "generation status rollback drift after post-validator failure")

            reconciler.BACKUP_VALIDATOR = pass_validator
            reconciler.OPERABILITY_VALIDATOR = fail_validator
            expect_rejected(reconciler, "generation status forced operability failure", reconciler.main)
            require(status_copy.read_bytes() == original_status, "generation status rollback drift after operability failure")

            contract = json.loads(contract_copy.read_text(encoding="utf-8"))
            contract["currentBoundary"]["generationBoundBackupCount"] = True
            contract_copy.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
            reconciler.OPERABILITY_VALIDATOR = pass_validator
            expect_rejected(reconciler, "generation status boolean boundary count", reconciler.main)
            require(status_copy.read_bytes() == original_status, "generation status mutated after boolean count rejection")
        finally:
            reconciler.CONTRACT = original_contract_path
            reconciler.STATUS = original_status_path
            reconciler.VALIDATOR = original_validator
            reconciler.BACKUP_VALIDATOR = original_backup_validator
            reconciler.OPERABILITY_VALIDATOR = original_operability_validator

    print("PASS rollback: generation status restored byte-for-byte after forced backup and operability validator failures")



def prove_private_writer_import_failures(module: Any) -> None:
    """Exercise the actual binding writer loader with private filesystem canaries."""
    original_spec = module.importlib.util.spec_from_file_location
    original_module = module.importlib.util.module_from_spec
    canary = "private-generation-binding-writer-import-canary"

    def fail_private(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError(canary)

    try:
        for target in ("spec", "module"):
            if target == "spec":
                module.importlib.util.spec_from_file_location = fail_private
            else:
                module.importlib.util.spec_from_file_location = original_spec
                module.importlib.util.module_from_spec = fail_private
            try:
                module.load_evidence_writer()
            except module.Fail as exc:
                require(str(exc) == "generation evidence writer import unavailable",
                        "generation binding writer import disclosed private failure")
                require(canary not in str(exc) and exc.__suppress_context__,
                        "generation binding writer import leaked exception context")
            else:
                raise Fail("generation binding writer import accepted private failure: " + target)
    finally:
        module.importlib.util.spec_from_file_location = original_spec
        module.importlib.util.module_from_spec = original_module
    require(callable(getattr(module.load_evidence_writer(), "validate_record", None)),
            "generation binding writer real import positive control failed")
    print("PASS: generation binding writer import private failures and real positive")




def prove_private_escaped_path_diagnostic(module: Any) -> None:
    canary = "private-generation-binding-path-canary"
    outside = Path(tempfile.gettempdir()) / canary
    try:
        module.repo_relative(outside)
    except module.Fail as exc:
        require(str(exc) == "artifact path escapes repository root",
                "generation binding escaped-path diagnostic disclosed private path")
        require(canary not in str(exc) and exc.__suppress_context__,
                "generation binding escaped-path exception context exposed")
    else:
        raise Fail("generation binding accepted outside private path")
    print("PASS: generation binding escaped-path diagnostic is private")



def main() -> int:
    prove_symlink_parent_rejected()
    prove_helper_source_symlink_rejected()
    prove_helper_source_swap_during_import_is_pinned()
    prove_helper_parent_swap_after_pin_uses_original_source()
    prove_helper_ancestor_swap_during_fd_walk_rejected()
    module = load_module()
    prove_private_writer_import_failures(module)
    prove_private_escaped_path_diagnostic(module)
    state = candidate_state(module)

    require(run_with_state(module, state) == 0, "candidate baseline must validate with evidence review but without human promotion review")
    print("PASS baseline: recovery candidate includes independently re-derived evidence review while human promotion review remains false")

    require(TMP_PARENT.is_dir(), "generation-binding temporary fixture parent missing")
    with guarded_temporary_directory(".tmp-generation-binding-load-negative-") as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_rejected(module, "generation binding invalid UTF-8 authority", lambda: module.load(invalid_utf8))

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_rejected(module, "generation binding unreadable authority directory", lambda: module.load(directory_authority))

        loop_authority = tmp / "loop-authority.json"
        loop_authority.symlink_to(loop_authority.name)
        expect_rejected(module, "generation binding authority symlink loop", lambda: module.load(loop_authority))

        valid_json = tmp / "valid-authority.json"
        valid_json.write_text('{"nested":{"value":1}}', encoding="utf-8")
        require(module.load(valid_json) == {"nested": {"value": 1}},
                "generation binding strict JSON reader positive control failed")
        for flag in ("O_NOFOLLOW", "O_NONBLOCK"):
            original_flag = getattr(module.os, flag)
            try:
                setattr(module.os, flag, None)
                try:
                    module.load(valid_json)
                except module.Fail as exc:
                    require(str(exc) == "generation binding JSON nofollow support required",
                            "generation binding JSON accepted missing nofollow support")
                else:
                    raise Fail("generation binding JSON accepted missing platform flag: " + flag)
            finally:
                setattr(module.os, flag, original_flag)
        require(module.load(valid_json) == {"nested": {"value": 1}},
                "generation binding JSON reader failed after flag restoration")
        print("PASS: generation binding JSON missing nofollow/nonblocking support rejected")
        linked_json = tmp / "linked-authority.json"
        linked_json.symlink_to(valid_json)
        expect_rejected(module, "generation binding JSON symlink", lambda: module.load(linked_json))
        fifo_json = tmp / "fifo-authority.json"
        os.mkfifo(fifo_json)
        expect_rejected(module, "generation binding JSON FIFO", lambda: module.load(fifo_json))
        for label, payload in (
            ("duplicate nested keys", b'{"nested":{"a":1,"a":2}}'),
            ("nonfinite NaN", b'{"value":NaN}'),
            ("nonfinite Infinity", b'{"value":Infinity}'),
            ("nonfinite float overflow", b'{"value":1e999}'),
            ("oversized integer", ('{"value":' + '9' * 129 + '}').encode()),
            ("malformed JSON", b'{"value":'),
            ("nonobject root", b'[1,2]'),
            ("oversized authority", b' ' * (module.MAX_JSON_BYTES + 1)),
        ):
            target = tmp / (label.replace(" ", "-") + ".json")
            target.write_bytes(payload)
            before = target.read_bytes()
            expect_rejected(module, "generation binding JSON " + label,
                            lambda path=target: module.load(path))
            require(target.read_bytes() == before,
                    "generation binding JSON negative mutated fixture: " + label)
        print("PASS: generation binding strict JSON reader positive and 10 additional negatives")

    outside_path = Path(tempfile.gettempdir()) / "memory-os-generation-binding-outside-root.json"
    expect_rejected(
        module,
        "generation binding artifact path escapes repository root",
        lambda: module.load(outside_path),
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        escaped_target = Path(temporary_directory) / "outside-local-foundation.json"
        escaped_target.write_text("{}\n", encoding="utf-8")
        link_path = ROOT / ".memory-os-generation-binding-outside-foundation"
        require(ROOT.is_dir() and not ROOT.is_symlink(),
                "generation-binding symlink fixture root missing or symlinked")
        parent_stat = ROOT.stat()
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        require(not link_path.exists() and not link_path.is_symlink(),
                "temporary generation-binding symlink path already exists")
        link_path.symlink_to(escaped_target)
        created_stat = link_path.lstat()
        created_identity = (created_stat.st_dev, created_stat.st_ino)
        try:
            symlink_state = copy.deepcopy(state)
            symlink_state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"] = str(link_path.relative_to(ROOT))
            expect_rejected(
                module,
                "local foundation evidence symlink escapes repository root",
                lambda: run_with_state(module, symlink_state),
            )
        finally:
            require(ROOT.is_dir() and not ROOT.is_symlink(),
                    "generation-binding symlink fixture parent substituted before cleanup")
            current_parent = ROOT.stat()
            require((current_parent.st_dev, current_parent.st_ino) == parent_identity,
                    "generation-binding symlink fixture parent inode drift before cleanup")
            current_link = link_path.lstat()
            require((current_link.st_dev, current_link.st_ino) == created_identity,
                    "generation-binding symlink fixture inode drift before cleanup")
            require(link_path.is_symlink() and link_path.resolve() == escaped_target.resolve(),
                    "generation-binding symlink fixture target drift before cleanup")
            link_path.unlink()

    canonical_ref = state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"]
    require(isinstance(canonical_ref, str) and canonical_ref, "baseline local foundation contract ref missing")

    absolute_ref_state = copy.deepcopy(state)
    absolute_ref_state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"] = str((ROOT / canonical_ref).resolve())
    expect_rejected(
        module,
        "local foundation absolute in-repository path is not canonical authority",
        lambda: run_with_state(module, absolute_ref_state),
    )

    parent_alias_state = copy.deepcopy(state)
    parent_alias_state[module.LOCAL_FOUNDATIONS]["foundations"][0]["contract"] = f"scripts/../{canonical_ref}"
    expect_rejected(
        module,
        "local foundation parent-traversal alias is not canonical authority",
        lambda: run_with_state(module, parent_alias_state),
    )

    impossible_count_order = copy.deepcopy(state)
    impossible_count_order[module.EVIDENCE_REGISTRY]["completeGenerationBoundRestoreCount"] = 0
    expect_rejected(
        module,
        "recovery candidate count cannot exceed complete generation-bound restore count",
        lambda: run_with_state(module, impossible_count_order),
    )

    restore_without_backup = copy.deepcopy(state)
    restore_without_backup[module.EVIDENCE_REGISTRY]["completeGenerationBoundBackupCount"] = 0
    expect_rejected(
        module,
        "generation-bound restore count cannot exceed generation-bound backup count",
        lambda: run_with_state(module, restore_without_backup),
    )

    manufactured_backup_aggregate = copy.deepcopy(state)
    manufactured_backup_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["evidenceComplete"] = False
    expect_rejected(
        module,
        "generation-bound backup aggregate without complete immutable evidence",
        lambda: run_with_state(module, manufactured_backup_aggregate),
    )

    manufactured_restore_aggregate = copy.deepcopy(state)
    manufactured_restore_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["isolatedRestoreVerified"] = False
    expect_rejected(
        module,
        "generation-bound restore aggregate without isolated exact-artifact restore evidence",
        lambda: run_with_state(module, manufactured_restore_aggregate),
    )

    manufactured_aggregate = copy.deepcopy(state)
    manufactured_aggregate[module.EVIDENCE_REGISTRY]["records"][0]["syntheticCandidate"] = False
    expect_rejected(
        module,
        "recovery candidate aggregate without current executable reviewed candidate evidence",
        lambda: run_with_state(module, manufactured_aggregate),
    )

    backup_rederivation_rule = copy.deepcopy(state)
    backup_rederivation_rule[module.CONTRACT]["promotionRules"]["backupCountMustBeRederivedFromImmutableEvidence"] = False
    expect_rejected(
        module,
        "generation-bound backup aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, backup_rederivation_rule),
    )

    restore_rederivation_rule = copy.deepcopy(state)
    restore_rederivation_rule[module.CONTRACT]["promotionRules"]["restoreCountMustBeRederivedFromImmutableEvidence"] = False
    expect_rejected(
        module,
        "generation-bound restore aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, restore_rederivation_rule),
    )

    missing_boundary_review = copy.deepcopy(state)
    missing_boundary_review[module.CONTRACT]["currentBoundary"]["independentReviewCompleted"] = False
    expect_rejected(
        module,
        "recovery candidate without independent evidence review boundary",
        lambda: run_with_state(module, missing_boundary_review),
    )

    missing_readiness_review = copy.deepcopy(state)
    missing_readiness_review[module.CONTRACT]["readiness"]["independentReviewCompleted"] = False
    expect_rejected(
        module,
        "recovery candidate without independent evidence review readiness",
        lambda: run_with_state(module, missing_readiness_review),
    )

    independent_review_rule = copy.deepcopy(state)
    independent_review_rule[module.CONTRACT]["promotionRules"]["independentReviewRequired"] = False
    expect_rejected(
        module,
        "recovery candidate independent-review requirement disabled",
        lambda: run_with_state(module, independent_review_rule),
    )

    candidate_rederivation_rule = copy.deepcopy(state)
    candidate_rederivation_rule[module.CONTRACT]["promotionRules"]["candidateCountMustBeRederivedFromCurrentExecutableReviewedEvidence"] = False
    expect_rejected(
        module,
        "recovery candidate aggregate re-derivation requirement disabled",
        lambda: run_with_state(module, candidate_rederivation_rule),
    )

    promotion_reviewed = copy.deepcopy(state)
    promotion_reviewed[module.CONTRACT]["currentBoundary"]["humanProductionPromotionReviewCompleted"] = True
    promotion_reviewed[module.CONTRACT]["readiness"]["humanProductionPromotionReviewCompleted"] = True
    expect_rejected(
        module,
        "recovery candidate cannot automatically complete human production-promotion review",
        lambda: run_with_state(module, promotion_reviewed),
    )

    promoted = copy.deepcopy(state)
    promoted[module.CONTRACT]["currentBoundary"]["humanProductionPromotionAuthorized"] = True
    promoted[module.CONTRACT]["readiness"]["humanProductionPromotionAuthorized"] = True
    expect_rejected(
        module,
        "recovery candidate cannot automatically authorize production promotion",
        lambda: run_with_state(module, promoted),
    )

    automatic_review_rule = copy.deepcopy(state)
    automatic_review_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyCompletesHumanProductionPromotionReview"] = True
    expect_rejected(
        module,
        "automatic candidate-to-human-promotion-review rule",
        lambda: run_with_state(module, automatic_review_rule),
    )

    automatic_promotion_rule = copy.deepcopy(state)
    automatic_promotion_rule[module.CONTRACT]["promotionRules"]["recoveryCandidateAutomaticallyAuthorizesProductionPromotion"] = True
    expect_rejected(
        module,
        "automatic candidate-to-production-promotion rule",
        lambda: run_with_state(module, automatic_promotion_rule),
    )

    prove_status_reconcile_boundaries()

    print("Memory OS backup/restore generation binding negative suite PASS")
    print("invalid UTF-8 or unreadable generation-binding authority accepted: false")
    print("generation-binding authority symlink loop accepted: false")
    print("generation status post-validator failure leaves partial status: false")
    print("generation status operability failure leaves partial status: false")
    print("generation status boolean boundary count accepted: false")
    print("artifact path escape accepted: false")
    print("local foundation evidence symlink escape accepted: false")
    print("absolute or parent-traversal local foundation ref accepted: false")
    print("candidate count may exceed complete restore count: false")
    print("generation-bound restore count may exceed backup count: false")
    print("backup aggregate without row-derived complete evidence accepted: false")
    print("restore aggregate without row-derived isolated exact-artifact evidence accepted: false")
    print("backup/restore aggregate re-derivation contract can be disabled: false")
    print("candidate aggregate without current executable reviewed candidate evidence accepted: false")
    print("candidate aggregate re-derivation contract can be disabled: false")
    print("candidate without independent evidence review accepted: false")
    print("candidate requires independent evidence review: true")
    print("candidate implies human production-promotion review: false")
    print("candidate implies production promotion: false")
    print("unexpected exception accepted as a valid rejection: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION BINDING NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
