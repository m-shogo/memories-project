#!/usr/bin/env python3
"""Focused negative for cross-generation material-delta review execution authority."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


MAX_MODULE_BYTES = 1024 * 1024
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-material-delta-review.py")


def load_pinned_module(path: Path, name: str) -> Any:
    """Execute only regular, bounded source bytes from checked directory FDs."""
    try:
        relative = path.relative_to(ROOT)
        require(path.resolve(strict=True) == ROOT.resolve() / relative,
                "cannot load material-delta validator")
        checked = path.lstat()
        require(stat.S_ISREG(checked.st_mode), "cannot load material-delta validator")
        require(all(type(getattr(os, flag, None)) is int and getattr(os, flag) > 0
                    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_DIRECTORY")),
                "cannot load material-delta validator")
        directory_fds = []
        source_fd = -1
        try:
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
            parent_fd = os.open(ROOT, directory_flags)
            directory_fds.append(parent_fd)
            for component in relative.parts[:-1]:
                parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
                directory_fds.append(parent_fd)
            source_fd = os.open(relative.name,
                                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                dir_fd=parent_fd)
            opened = os.fstat(source_fd)
            require(stat.S_ISREG(opened.st_mode)
                    and (opened.st_dev, opened.st_ino) == (checked.st_dev, checked.st_ino),
                    "cannot load material-delta validator")
            with os.fdopen(source_fd, "rb") as stream:
                source_fd = -1
                source = stream.read(MAX_MODULE_BYTES + 1)
        finally:
            cleanup_failed = False
            if source_fd >= 0:
                try:
                    os.close(source_fd)
                except (Exception, SystemExit):
                    cleanup_failed = True
            for directory_fd in reversed(directory_fds):
                try:
                    os.close(directory_fd)
                except (Exception, SystemExit):
                    cleanup_failed = True
            require(not cleanup_failed, "cannot load material-delta validator")
        require(len(source) <= MAX_MODULE_BYTES, "cannot load material-delta validator")

        class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(self, fullname):
                require(fullname == name, "cannot load material-delta validator")
                try:
                    return compile(source, str(path), "exec")
                except (Exception, SystemExit):
                    raise Fail("cannot load material-delta validator") from None

        spec = importlib.util.spec_from_file_location(
            name, path, loader=PinnedSourceLoader(name, str(path)))
        require(spec is not None and spec.loader is not None,
                "cannot load material-delta validator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Fail:
        raise
    except (Exception, SystemExit):
        raise Fail("cannot load material-delta validator") from None


def load_validator() -> Any:
    require(VALIDATOR == ROOT / VALIDATOR_REL,
            "canonical material-delta validator path drift")
    return load_pinned_module(VALIDATOR, "memory_os_material_delta_execution_negative")


def prove_pinned_validator_import() -> None:
    """Parent swaps after reading cannot redirect executed validator bytes."""
    original_spec = importlib.util.spec_from_file_location
    with tempfile.TemporaryDirectory(prefix=".material-delta-import-", dir=ROOT) as raw:
        sandbox = Path(raw)
        parent = sandbox / "trusted"
        parent.mkdir()
        source = parent / "validator.py"
        source.write_text("VALUE = 7" + chr(10), encoding="utf-8")
        parked = sandbox / "parked"
        redirected = sandbox / "redirected"
        redirected.mkdir()
        canary = redirected / "validator.py"
        canary.write_text("raise RuntimeError('PRIVATE_MATERIAL_DELTA_CANARY')" + chr(10),
                          encoding="utf-8")
        require(load_pinned_module(source, "material_delta_pinned_positive").VALUE == 7,
                "material-delta pinned import positive failed")
        swapped = False
        def swap_after_read(name, location, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(location) == source:
                swapped = True
                parent.rename(parked)
                parent.symlink_to(redirected, target_is_directory=True)
            return original_spec(name, location, *args, **kwargs)
        importlib.util.spec_from_file_location = swap_after_read
        try:
            loaded = load_pinned_module(source, "material_delta_parent_swap_negative")
            require(swapped and loaded.VALUE == 7,
                    "material-delta pinned import executed redirected source")
            require(canary.read_text(encoding="utf-8") ==
                    "raise RuntimeError('PRIVATE_MATERIAL_DELTA_CANARY')" + chr(10),
                    "material-delta pinned import modified external canary")
        finally:
            importlib.util.spec_from_file_location = original_spec
            if parent.is_symlink():
                parent.unlink()
            if parked.exists():
                parked.rename(parent)
        require(load_pinned_module(source, "material_delta_restored").VALUE == 7,
                "material-delta pinned import restoration failed")
    print("PASS material-delta descriptor-pinned import parent swap")


def same_generation_row() -> dict[str, Any]:
    return {
        "sourceEnvironmentGenerationId": "pegen_same_execution_negative",
        "restoreTargetGenerationId": "pegen_same_execution_negative",
        "materialDeltaReviewRef": None,
    }


def expect_candidate_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    try:
        try:
            module.material_delta_review_approved(same_generation_row())
        except module.Fail:
            return
        raise Fail(f"material-delta candidate execution substitution unexpectedly passed: {field}")
    finally:
        setattr(module, field, original)


def expect_transport_rejected(module: Any) -> None:
    original = module.subprocess.run
    module.subprocess.run = lambda *_args, **_kwargs: None
    try:
        try:
            module.material_delta_review_approved(same_generation_row())
        except module.Fail as exc:
            require("execution transport drift" in str(exc), f"subprocess transport rejected at wrong boundary: {exc}")
            return
        raise Fail("material-delta subprocess transport substitution unexpectedly passed")
    finally:
        module.subprocess.run = original


def expect_candidate_mutation_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str) -> None:
    mutate()
    try:
        try:
            module.material_delta_review_approved(same_generation_row())
        except module.Fail as exc:
            require("semantic authority drift" in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"material-delta candidate semantic authority substitution unexpectedly passed: {label}")
    finally:
        restore()


def expect_main_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str, expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"material-delta main execution substitution unexpectedly passed: {label}")
    finally:
        restore()


def expect_row_rejected(module: Any, row: dict[str, Any], label: str, expected: str) -> None:
    # A rejection at an unrelated boundary is not proof that the row rule ran.
    required_fields = module.validate_contract_authority()["requiredMaterialDeltaReviewEvidenceFields"]
    try:
        module.validate_row(row, 0, required_fields)
    except module.Fail as exc:
        require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
        return
    raise Fail(f"material-delta row semantic negative unexpectedly passed: {label}")


def main() -> int:
    prove_pinned_validator_import()
    module = load_validator()
    canonical_contract = module.CONTRACT.read_bytes()
    canonical_registry = module.REGISTRY.read_bytes()

    # A negative is not proof unless its unmodified execution path succeeds.
    # This is planning/guard validation only, never production recovery evidence.
    require(
        module.material_delta_review_approved(same_generation_row()) is True,
        "unmodified same-generation material-delta candidate failed positive control",
    )
    require(module.main() == 0, "unmodified material-delta validator failed positive control")
    print("PASS positive control: canonical same-generation candidate and validator")

    for field, replacement in (
        ("enforce_execution_authority", lambda: None),
        ("enforce_runtime_authorities", lambda: None),
        ("require", lambda *_args: None),
        ("require_exact_repo_file", lambda path, *_args: path),
        ("load_json", lambda *_args: {}),
        ("validate_contract_authority", lambda: {"requiredMaterialDeltaReviewEvidenceFields": []}),
        ("canonical_material_delta_ref", lambda *_args: ("docs/evidence/backup-restore/material-delta/fake.json", Path("/tmp/fake-material-delta.json"))),
        ("git_history", lambda *_args: ["a" * 40]),
        ("require_append_only_review", lambda *_args: None),
        ("require_utc_rfc3339", lambda value, _field: value),
        ("validate_material_delta_payload", lambda *_args: None),
        ("validate_row", lambda *_args: None),
    ):
        expect_candidate_rejected(module, field, replacement)

    expect_transport_rejected(module)

    original_contract = module.CONTRACT
    original_contract_rel = module.CONTRACT_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "CONTRACT", module.REGISTRY), setattr(module, "CONTRACT_REL", module.REGISTRY_REL)),
        lambda: (setattr(module, "CONTRACT", original_contract), setattr(module, "CONTRACT_REL", original_contract_rel)),
        "paired contract path authority substitution",
    )

    original_registry = module.REGISTRY
    original_registry_rel = module.REGISTRY_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "REGISTRY", module.CONTRACT), setattr(module, "REGISTRY_REL", module.CONTRACT_REL)),
        lambda: (setattr(module, "REGISTRY", original_registry), setattr(module, "REGISTRY_REL", original_registry_rel)),
        "paired registry path authority substitution",
    )

    original_validator = module.VALIDATOR
    original_validator_rel = module.VALIDATOR_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "VALIDATOR", module.NEGATIVE), setattr(module, "VALIDATOR_REL", module.NEGATIVE_REL)),
        lambda: (setattr(module, "VALIDATOR", original_validator), setattr(module, "VALIDATOR_REL", original_validator_rel)),
        "paired validator authority substitution",
    )

    original_negative = module.NEGATIVE
    original_negative_rel = module.NEGATIVE_REL
    expect_candidate_mutation_rejected(
        module,
        lambda: (setattr(module, "NEGATIVE", module.VALIDATOR), setattr(module, "NEGATIVE_REL", module.VALIDATOR_REL)),
        lambda: (setattr(module, "NEGATIVE", original_negative), setattr(module, "NEGATIVE_REL", original_negative_rel)),
        "paired negative validator authority substitution",
    )

    original_root = module.MATERIAL_DELTA_ROOT
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "MATERIAL_DELTA_ROOT", Path("docs/evidence/backup-restore")),
        lambda: setattr(module, "MATERIAL_DELTA_ROOT", original_root),
        "material-delta evidence root widening",
    )

    original_schema = module.EXPECTED_SCHEMA
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "EXPECTED_SCHEMA", "memory-os-backup-restore-material-delta-review.v0"),
        lambda: setattr(module, "EXPECTED_SCHEMA", original_schema),
        "material-delta schema substitution",
    )

    original_result = module.REVIEW_RESULT
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REVIEW_RESULT", "REJECTED"),
        lambda: setattr(module, "REVIEW_RESULT", original_result),
        "material-delta approval result substitution",
    )

    original_reviewer = module.REVIEWER
    expect_candidate_mutation_rejected(
        module,
        lambda: setattr(module, "REVIEWER", re.compile(r"^.*$")),
        lambda: setattr(module, "REVIEWER", original_reviewer),
        "material-delta reviewer rule widening",
    )

    original_guard = module.enforce_execution_authority
    expect_main_rejected(
        module,
        lambda: setattr(module, "enforce_execution_authority", lambda: None),
        lambda: setattr(module, "enforce_execution_authority", original_guard),
        "main execution guard substitution",
        "main execution guard drift",
    )

    original_candidate = module.material_delta_review_approved
    expect_main_rejected(
        module,
        lambda: setattr(module, "material_delta_review_approved", lambda _row: True),
        lambda: setattr(module, "material_delta_review_approved", original_candidate),
        "main material-delta candidate substitution",
        "candidate authority drift",
    )

    original_guard = module.enforce_execution_authority
    original_candidate = module.material_delta_review_approved
    def mutate_both() -> None:
        module.enforce_execution_authority = lambda: None
        module.material_delta_review_approved = lambda _row: True
    def restore_both() -> None:
        module.enforce_execution_authority = original_guard
        module.material_delta_review_approved = original_candidate
    expect_main_rejected(
        module,
        mutate_both,
        restore_both,
        "main guard and candidate double substitution",
        "main execution guard drift",
    )

    expect_row_rejected(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_source_execution_negative",
            "restoreTargetGenerationId": "pegen_target_execution_negative",
            "materialDeltaReviewRef": "SECURITY.md",
        },
        "generic repository review ref",
        "must remain inside docs/evidence/backup-restore/material-delta/",
    )
    expect_row_rejected(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_same_execution_negative",
            "restoreTargetGenerationId": "pegen_same_execution_negative",
            "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/should-be-null.json",
        },
        "same-generation non-null review ref",
        "same-generation restore must not declare materialDeltaReviewRef",
    )
    expect_row_rejected(
        module,
        {
            "sourceEnvironmentGenerationId": "pegen_source_execution_negative",
            "restoreTargetGenerationId": "pegen_target_execution_negative",
            "materialDeltaReviewRef": "docs/evidence/backup-restore/material-delta/../escape.json",
        },
        "material-delta path traversal",
        "must be canonical repository-relative path",
    )

    require(module.CONTRACT.read_bytes() == canonical_contract, "execution substitution mutated canonical generation evidence contract")
    require(module.REGISTRY.read_bytes() == canonical_registry, "execution substitution mutated canonical generation evidence registry")
    print("Memory OS generation material-delta execution authority negative PASS")
    print("candidate execution helper substitution accepted: false")
    print("subprocess execution transport substitution accepted: false")
    print("paired semantic authority substitution accepted: false")
    print("main execution guard substitution accepted: false")
    print("main candidate helper substitution accepted: false")
    print("main double substitution accepted: false")
    print("generic repository material-delta ref accepted: false")
    print("same-generation non-null material-delta ref accepted: false")
    print("material-delta path traversal accepted: false")
    print("canonical authority mutation: false")
    print("automatic production promotion authority created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION MATERIAL DELTA EXECUTION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
