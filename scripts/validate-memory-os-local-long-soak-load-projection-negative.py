#!/usr/bin/env python3
"""Negative checks for local long-soak projection and delegated operability boundaries."""

from __future__ import annotations

import copy
import importlib.util
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/reconcile-memory-os-local-long-soak-load-projection.py"
CANONICAL_SOAK = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
SOAK_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak.py"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_LOCAL_SOAK_NEGATIVE = ROOT / "scripts/validate-memory-os-operability-local-soak-negative.py"
SPEC = importlib.util.spec_from_file_location("local_long_soak_projection", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("LOCAL LONG SOAK LOAD PROJECTION NEGATIVE FAILED: cannot load projection module")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def file_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def expect_reject(label: str, mutate) -> None:
    row = module.derived_row(local_evidence=True)
    mutate(row)
    try:
        module.assert_local_only_boundary(row)
    except module.Fail:
        print(f"PASS reject: {label}")
        return
    raise AssertionError(f"corruption accepted: {label}")


def expect_legacy_reject(label: str, mutate) -> None:
    row = {
        "scenarioId": module.LEGACY_ALIAS_ID,
        "productionEvidence": False,
        "productionSustainedSoakEvidence": False,
        "leakProof": False,
        "capacityApproved": False,
        "thresholdsApproved": False,
        "runMetadata": {
            "productionEquivalent": False,
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "approvalAuthority": "NONE",
        },
    }
    mutate(row)
    try:
        module.assert_legacy_alias_safe_to_remove(row)
    except module.Fail:
        print(f"PASS reject legacy alias removal: {label}")
        return
    raise AssertionError(f"corrupt legacy alias accepted for removal: {label}")


def expect_projection_input_reject(label: str, rows) -> None:
    try:
        module.assert_projection_input_safe(rows)
    except module.Fail:
        print(f"PASS reject projection input: {label}")
        return
    raise AssertionError(f"corrupt projection input accepted: {label}")


def authority_substitution_rejected() -> None:
    load_bytes = CANONICAL_LOAD.read_bytes()
    load_mode = file_mode(CANONICAL_LOAD)
    substitutions = (
        ("SOAK_PATH", CANONICAL_LOAD, "sustained-soak contract authority drift"),
        ("LOAD_PATH", CANONICAL_SOAK, "load contract authority drift"),
        ("SOAK_VALIDATOR", LOAD_VALIDATOR, "sustained-soak validator authority drift"),
        ("LOAD_VALIDATOR", SOAK_VALIDATOR, "load validator authority drift"),
    )
    for attr, substitute, expected in substitutions:
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            try:
                module.validate_authorities()
            except module.Fail as exc:
                if expected not in str(exc):
                    raise AssertionError(f"unexpected {attr} authority rejection: {exc}") from exc
            else:
                raise AssertionError(f"substituted projection authority accepted: {attr}")
            if CANONICAL_LOAD.read_bytes() != load_bytes:
                raise AssertionError(f"canonical load authority changed after rejected substitution: {attr}")
            if file_mode(CANONICAL_LOAD) != load_mode:
                raise AssertionError(f"canonical load authority mode changed after rejected substitution: {attr}")
        finally:
            setattr(module, attr, original)


def atomic_replacement_failure_rejected() -> None:
    original_bytes = CANONICAL_LOAD.read_bytes()
    original_mode = file_mode(CANONICAL_LOAD)
    temp_glob = f".{CANONICAL_LOAD.name}.*.tmp"
    before = {path.name for path in CANONICAL_LOAD.parent.glob(temp_glob)}
    real_replace = module.os.replace

    def reject_replace(_source, _destination) -> None:
        raise OSError("synthetic load projection atomic replace failure")

    module.os.replace = reject_replace
    try:
        try:
            module.atomic_replace_bytes(CANONICAL_LOAD, original_bytes + b"\n")
        except OSError as exc:
            if "synthetic load projection atomic replace failure" not in str(exc):
                raise AssertionError(f"unexpected atomic replacement rejection: {exc}") from exc
        else:
            raise AssertionError("load projection atomic replacement unexpectedly succeeded")
    finally:
        module.os.replace = real_replace

    if CANONICAL_LOAD.read_bytes() != original_bytes:
        raise AssertionError("atomic replacement failure changed canonical load authority")
    if file_mode(CANONICAL_LOAD) != original_mode:
        raise AssertionError("atomic replacement failure changed canonical load authority mode")
    after = {path.name for path in CANONICAL_LOAD.parent.glob(temp_glob)}
    if after != before:
        raise AssertionError("atomic replacement failure leaked temporary load authority")


def successful_replacement_preserves_mode() -> None:
    original_bytes = CANONICAL_LOAD.read_bytes()
    original_mode = file_mode(CANONICAL_LOAD)
    test_mode = 0o640
    CANONICAL_LOAD.chmod(test_mode)
    try:
        module.atomic_replace_bytes(CANONICAL_LOAD, original_bytes)
        if CANONICAL_LOAD.read_bytes() != original_bytes:
            raise AssertionError("successful load projection replacement changed canonical bytes")
        if file_mode(CANONICAL_LOAD) != test_mode:
            raise AssertionError("successful load projection replacement changed canonical mode")
    finally:
        module.atomic_replace_bytes(CANONICAL_LOAD, original_bytes, original_mode)


def transaction_rollback_rejected() -> None:
    original_bytes = CANONICAL_LOAD.read_bytes()
    original_mode = file_mode(CANONICAL_LOAD)
    original_source_validator = module.validate_source_authority
    original_load_validator = module.validate_projected_load_authority
    module.validate_source_authority = lambda: None

    def reject_after_write() -> None:
        raise module.Fail("synthetic post-write load projection rejection")

    module.validate_projected_load_authority = reject_after_write
    try:
        try:
            module.main()
        except module.Fail as exc:
            if ("transaction failed: Fail" not in str(exc)
                    or "synthetic post-write" in str(exc) or not exc.__suppress_context__):
                raise AssertionError("local long-soak primary failure leaked raw exception") from None
        else:
            raise AssertionError("post-write load projection validator failure was accepted")
        if CANONICAL_LOAD.read_bytes() != original_bytes:
            raise AssertionError("canonical load authority was not restored after rejected projection")
        if file_mode(CANONICAL_LOAD) != original_mode:
            raise AssertionError("canonical load authority mode was not restored after rejected projection")
    finally:
        module.validate_source_authority = original_source_validator
        module.validate_projected_load_authority = original_load_validator
        if CANONICAL_LOAD.read_bytes() != original_bytes or file_mode(CANONICAL_LOAD) != original_mode:
            module.atomic_replace_bytes(CANONICAL_LOAD, original_bytes, original_mode)




def atomic_path_containment_negative() -> None:
    secret = b"SYNTHETIC_LOCAL_LONG_SOAK_OUTSIDE_CANARY"
    with tempfile.TemporaryDirectory(prefix="local-long-soak-outside-") as outside_temp, \
         tempfile.TemporaryDirectory(prefix=".local-long-soak-path-", dir=ROOT) as inside_temp:
        inside = Path(inside_temp)
        outside = Path(outside_temp)
        canary = outside / "canary"
        canary.write_bytes(secret)
        target = inside / "authority.json"
        target.write_bytes(b"original")
        target.chmod(0o640)
        module.atomic_replace_bytes(target, b"updated")
        if target.read_bytes() != b"updated" or file_mode(target) != 0o640:
            raise AssertionError("local long-soak atomic existing-file positive drift")
        new = inside / "new.json"
        module.atomic_replace_bytes(new, b"new")
        if new.read_bytes() != b"new" or file_mode(new) != 0o600:
            raise AssertionError("local long-soak atomic new-file mode drift")
        link = inside / "link.json"
        link.symlink_to(canary)
        parent_link = inside / "linked-parent"
        parent_link.symlink_to(outside, target_is_directory=True)
        directory = inside / "directory"
        directory.mkdir()
        for unsafe in (link, parent_link / "canary", directory, inside / "missing" / "file", canary):
            try:
                module.atomic_replace_bytes(unsafe, b"forbidden")
            except module.Fail:
                pass
            else:
                raise AssertionError("local long-soak atomic writer accepted unsafe path")
        for unsafe in (link, parent_link / "canary", canary):
            try:
                module.require_exact_authority(unsafe, unsafe, "synthetic")
            except module.Fail:
                pass
            else:
                raise AssertionError("local long-soak authority reader accepted unsafe path")
        if canary.read_bytes() != secret or list(outside.iterdir()) != [canary]:
            raise AssertionError("local long-soak outside canary changed")
        for operation in ("replace", "fsync"):
            original = getattr(module.os, operation)
            setattr(module.os, operation, lambda *args: (_ for _ in ()).throw(OSError("synthetic atomic failure")))
            try:
                try:
                    module.atomic_replace_bytes(target, b"forbidden")
                except OSError:
                    pass
                else:
                    raise AssertionError("local long-soak accepted synthetic atomic failure")
            finally:
                setattr(module.os, operation, original)
            if target.read_bytes() != b"updated" or list(inside.glob(".authority.json.*.tmp")):
                raise AssertionError("local long-soak atomic failure changed bytes or left residue")
    print("PASS: local long-soak atomic writer/reader containment and rollback negatives")


def validator_output_and_rollback_redaction_negative() -> None:
    marker = "SYNTHETIC_LOCAL_LONG_SOAK_SECRET"
    original_run = module.subprocess.run

    def failed_validator(command, **kwargs):
        if (kwargs.get("stdout") != subprocess.DEVNULL
                or kwargs.get("stderr") != subprocess.DEVNULL or kwargs.get("check") is not True):
            raise AssertionError("local long-soak validator output not suppressed")
        raise subprocess.CalledProcessError(17, command, output=marker, stderr=marker)

    try:
        module.subprocess.run = failed_validator
        for validator, label in ((module.SOAK_VALIDATOR, "sustained-soak"),
                                 (module.LOAD_VALIDATOR, "load")):
            try:
                module.run_validator(validator, label)
            except module.Fail as exc:
                if marker in str(exc) or "exit 17" not in str(exc) or not exc.__suppress_context__:
                    raise AssertionError("local long-soak validator leaked output or lost exit code") from None
            else:
                raise AssertionError("local long-soak accepted failing validator")
        module.subprocess.run = lambda *args, **kwargs: (_ for _ in ()).throw(OSError(marker))
        try:
            module.run_validator(module.SOAK_VALIDATOR, "sustained-soak")
        except module.Fail as exc:
            if marker in str(exc) or "execution failed: OSError" not in str(exc) or not exc.__suppress_context__:
                raise AssertionError("local long-soak validator startup leaked raw exception") from None
        else:
            raise AssertionError("local long-soak accepted validator startup failure")
    finally:
        module.subprocess.run = original_run

    original_bytes = CANONICAL_LOAD.read_bytes()
    original_mode = file_mode(CANONICAL_LOAD)
    original_source_validator = module.validate_source_authority
    original_load_validator = module.validate_projected_load_authority
    original_atomic = module.atomic_replace_bytes
    attempts = []
    module.validate_source_authority = lambda: None
    module.validate_projected_load_authority = lambda: (_ for _ in ()).throw(RuntimeError(marker))
    try:
        for fail_rollback in (False, True):
            attempts.clear()
            def synthetic_atomic(path, payload, mode=None):
                attempts.append((path, mode))
                if fail_rollback and len(attempts) == 2:
                    raise OSError(marker)
            module.atomic_replace_bytes = synthetic_atomic
            try:
                module.main()
            except module.Fail as exc:
                expected = ("rollback incomplete: OSError; primary RuntimeError" if fail_rollback
                            else "transaction failed: RuntimeError")
                if marker in str(exc) or expected not in str(exc) or not exc.__suppress_context__:
                    raise AssertionError("local long-soak transaction leaked primary/rollback exception") from None
            else:
                raise AssertionError("local long-soak accepted synthetic transaction failure")
            if len(attempts) != 2 or attempts[0][0] != CANONICAL_LOAD or attempts[1][0] != CANONICAL_LOAD:
                raise AssertionError("local long-soak transaction did not attempt rollback")
    finally:
        module.validate_source_authority = original_source_validator
        module.validate_projected_load_authority = original_load_validator
        module.atomic_replace_bytes = original_atomic
    if CANONICAL_LOAD.read_bytes() != original_bytes or file_mode(CANONICAL_LOAD) != original_mode:
        raise AssertionError("local long-soak synthetic transaction changed canonical load authority")
    print("PASS: local long-soak validator and transaction secret redaction (5 cases)")


def delegated_local_soak_negatives_pass() -> None:
    subprocess.run([sys.executable, str(OPERABILITY_LOCAL_SOAK_NEGATIVE)], cwd=ROOT, check=True)


def main() -> int:
    valid = copy.deepcopy(module.derived_row(local_evidence=True))
    module.assert_local_only_boundary(valid)
    module.assert_projection_input_safe([valid])

    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
    ):
        expect_reject(f"{key} manufactured", lambda row, key=key: row.__setitem__(key, True))

    expect_reject("duplicate alias scenario identity", lambda row: row.__setitem__("scenarioId", module.LEGACY_ALIAS_ID))
    expect_reject("contract authority drift", lambda row: row.__setitem__("contractRef", "README.md"))
    expect_reject("validator authority drift", lambda row: row.__setitem__("validatorRef", "README.md"))
    expect_reject("dependency mode drift", lambda row: row.__setitem__("dependencyMode", "PRODUCTION_EQUIVALENT"))
    expect_reject("classification drift", lambda row: row.__setitem__("classification", "PRODUCTION_LONG_SOAK"))
    expect_reject("local evidence flag non-boolean", lambda row: row.__setitem__("localSustainedSoakEvidence", 1))

    duplicate_rows = [copy.deepcopy(valid), copy.deepcopy(valid)]
    expect_projection_input_reject("duplicate external scenario ID", duplicate_rows)
    expect_projection_input_reject("non-object external row", [copy.deepcopy(valid), "bad-row"])
    production_row = copy.deepcopy(valid)
    production_row["scenarioId"] = "unrelated-local-scenario"
    production_row["productionEvidence"] = True
    expect_projection_input_reject("unrelated production evidence promotion", [production_row])
    production_dependency_row = copy.deepcopy(valid)
    production_dependency_row["scenarioId"] = "unrelated-local-dependency-scenario"
    production_dependency_row["productionEquivalentDependencies"] = True
    expect_projection_input_reject("unrelated production-equivalent dependency promotion", [production_dependency_row])

    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityApproved",
        "thresholdsApproved",
    ):
        expect_legacy_reject(f"{key} manufactured", lambda row, key=key: row.__setitem__(key, True))
    for key in ("productionEquivalent", "productionTraffic", "productionCredentials", "productionEvidence"):
        expect_legacy_reject(
            f"runMetadata.{key} manufactured",
            lambda row, key=key: row["runMetadata"].__setitem__(key, True),
        )
    expect_legacy_reject(
        "approval authority manufactured",
        lambda row: row["runMetadata"].__setitem__("approvalAuthority", "HUMAN_APPROVED"),
    )
    expect_legacy_reject("run metadata removed", lambda row: row.pop("runMetadata"))

    authority_substitution_rejected()
    atomic_replacement_failure_rejected()
    successful_replacement_preserves_mode()
    transaction_rollback_rejected()
    validator_output_and_rollback_redaction_negative()
    atomic_path_containment_negative()
    delegated_local_soak_negatives_pass()

    print("Memory OS local long-soak load projection negative suite PASS")
    print("canonical scenario ID binding enforced: true")
    print("canonical source/load authority identity enforced: true")
    print("crash-safe atomic load replacement preserves bytes and mode: true")
    print("successful atomic load replacement preserves existing mode: true")
    print("post-write load validation rollback preserves bytes and mode: true")
    print("semantic pending operability and review-registry transaction state are negative-covered: true")
    print("aggregate external scenario corruption accepted: false")
    print("legacy LOCAL_LONG_SOAK alias may be removed only when non-production: true")
    print("production evidence promotion accepted: false")
    print("production traffic promotion accepted: false")
    print("production credentials promotion accepted: false")
    print("automatic approval authority accepted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
