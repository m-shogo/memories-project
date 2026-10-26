#!/usr/bin/env python3
"""Exercise fail-closed negative cases for backup/restore promotion review admission."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-promotion-review.py"


class Fail(RuntimeError):
    pass


EXPECTED_FAILURE: type[Exception] = Fail


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except EXPECTED_FAILURE:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


@contextmanager
def isolated_review_evidence_namespace(writer):
    fixture_root = ROOT / "docs/fixtures/memory-os-operability"
    require(fixture_root.is_dir(), "isolated operability fixture namespace missing")
    original_evidence_root = writer.EVIDENCE_ROOT
    original_load = writer.load
    with tempfile.TemporaryDirectory(prefix=".promotion-review-negative-", dir=fixture_root) as tmp:
        isolated_root = Path(tmp)

        def isolated_load(path: Path) -> dict[str, Any]:
            value = original_load(path)
            if Path(path) == writer.CONTRACT:
                value = copy.deepcopy(value)
                value["reviewEvidenceRoot"] = repo_rel(isolated_root)
            return value

        writer.EVIDENCE_ROOT = isolated_root
        writer.load = isolated_load
        try:
            yield isolated_root
        finally:
            writer.load = original_load
            writer.EVIDENCE_ROOT = original_evidence_root


def review_payload(
    *,
    role: str,
    reviewer: str,
    decision_id: str = "brpr_negative_base",
    evidence_id: str = "brge_negative_candidate",
) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-evidence.v1",
        "decisionId": decision_id,
        "recoveryEvidenceId": evidence_id,
        "reviewRole": role,
        "reviewResult": "APPROVED",
        "reviewedAt": "2026-08-08T00:00:00Z",
        "reviewerPseudonym": reviewer,
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "automaticPromotion": False,
    }


def build_fixture(root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    rationale = root / "rationale.txt"
    rationale.write_text("Synthetic negative-suite rationale only; not human production authority.\n", encoding="utf-8")
    specs = {
        "recoveryOwner": ("RECOVERY_OWNER", "reviewer_recovery_owner"),
        "security": ("SECURITY", "reviewer_security"),
        "operability": ("OPERABILITY", "reviewer_operability"),
    }
    paths: dict[str, Path] = {"rationale": rationale}
    for name, (role, reviewer) in specs.items():
        path = root / f"{name}.json"
        write_json(path, review_payload(role=role, reviewer=reviewer))
        paths[name] = path
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-record.v2",
        "decisionId": "brpr_negative_base",
        "recoveryEvidenceId": "brge_negative_candidate",
        "decidedAt": "2026-08-08T00:00:00Z",
        "decision": "GO_RECOMMENDATION",
        "rationaleRef": repo_rel(rationale),
        "rationaleSha256": sha256(rationale),
        "recoveryOwnerReviewRef": repo_rel(paths["recoveryOwner"]),
        "recoveryOwnerReviewSha256": sha256(paths["recoveryOwner"]),
        "securityReviewRef": repo_rel(paths["security"]),
        "securityReviewSha256": sha256(paths["security"]),
        "operabilityReviewRef": repo_rel(paths["operability"]),
        "operabilityReviewSha256": sha256(paths["operability"]),
        "unresolvedFindings": [],
        "productionTrafficChanged": False,
        "productionCredentialsUsed": False,
        "productionEvidence": False,
        "productionReady": False,
    }, paths


def empty_registry() -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-backup-restore-promotion-review-registry.v1",
        "appendOnly": True,
        "registeredReviewCount": 0,
        "goRecommendationCount": 0,
        "noGoCount": 0,
        "deferCount": 0,
        "latestDecisionId": None,
        "currentDecisionId": None,
        "records": [],
        "productionTrafficChanged": False,
        "productionEvidence": False,
        "productionReady": False,
        "limitations": [],
    }


def prove_promotion_reader() -> None:
    """Exercise the actual promotion validator JSON reader, never production evidence."""
    validator = load_module(VALIDATOR, "memory_os_promotion_review_json_reader_negative")
    positive = b'{"schemaVersion":"synthetic","nested":{"ok":true}}\n'
    with tempfile.TemporaryDirectory(prefix="promotion-reader-negative-") as tmp:
        root = Path(tmp)
        path = root / "authority.json"
        path.write_bytes(positive)
        require(validator.load(path) == {"schemaVersion": "synthetic", "nested": {"ok": True}},
                "promotion reader positive control failed")
        marker = "PRIVATE_PROMOTION_READER_CANARY_DO_NOT_LOG"
        cases = (
            ("duplicate", b'{"x":1,"x":2}', "promotion review JSON duplicate key refused"),
            ("nested-duplicate", b'{"x":{"y":1,"y":2}}',
             "promotion review JSON duplicate key refused"),
            ("nan", b'{"x":NaN}', "promotion review JSON nonfinite number refused"),
            ("infinity", b'{"x":Infinity}', "promotion review JSON nonfinite number refused"),
            ("overflow", b'{"x":1e309}', "promotion review JSON nonfinite number refused"),
            ("huge-int", b'{"x":' + b"9" * 129 + b'}',
             "promotion review JSON integer too large"),
            ("invalid-utf8", b'{"x":"\xff"}', "promotion review JSON unreadable or invalid"),
            ("malformed", b'{"x":', "promotion review JSON unreadable or invalid"),
            ("nonobject", b'[1,2]', "promotion review JSON root must be object"),
            ("oversized", b" " * (validator.MAX_JSON_BYTES + 1),
             "promotion review JSON size limit exceeded"),
        )
        for label, payload, expected in cases:
            path.write_bytes(payload)
            try:
                validator.load(path)
            except validator.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"promotion reader {label} wrong/private rejection: {exc}")
            else:
                raise Fail(f"promotion reader {label} unexpectedly accepted")
        canary = root / "external-canary.json"
        canary.write_text(marker, encoding="utf-8")
        alias = root / "alias.json"
        alias.symlink_to(canary)
        try:
            validator.load(alias)
        except validator.Fail as exc:
            require(str(exc) == "promotion review JSON path missing or unsafe",
                    f"promotion reader symlink wrong rejection: {exc}")
        else:
            raise Fail("promotion reader symlink unexpectedly accepted")
        require(canary.read_text(encoding="utf-8") == marker,
                "promotion reader external canary mutated")
        path.unlink()
        path.mkdir()
        try:
            validator.load(path)
        except validator.Fail as exc:
            require(str(exc) == "promotion review JSON path missing or unsafe",
                    f"promotion reader directory wrong rejection: {exc}")
        else:
            raise Fail("promotion reader directory unexpectedly accepted")
        path.rmdir()
        path.write_bytes(positive)
        require(validator.load(path) == {"schemaVersion": "synthetic", "nested": {"ok": True}},
                "promotion reader restored positive control failed")
    print(f"PASS: actual promotion review JSON reader positive and {len(cases) + 2} fail-closed negatives")


def prove_promotion_writer_reader() -> None:
    """Exercise the actual promotion writer JSON reader, never production evidence."""
    writer = load_module(WRITER, "memory_os_promotion_review_json_reader_negative")
    require(Path(writer.__file__).resolve() == WRITER.resolve(),
            "promotion writer reader module identity drift")
    positive = b'{"schemaVersion":"synthetic","nested":{"ok":true}}\n'
    with tempfile.TemporaryDirectory(prefix="promotion-writer-reader-negative-") as tmp:
        root = Path(tmp)
        path = root / "authority.json"
        path.write_bytes(positive)
        require(writer.load(path) == {"schemaVersion": "synthetic", "nested": {"ok": True}},
                "promotion writer reader positive control failed")
        marker = "PRIVATE_PROMOTION_READER_CANARY_DO_NOT_LOG"
        cases = (
            ("duplicate", b'{"x":1,"x":2}', "promotion review JSON duplicate key refused"),
            ("nested-duplicate", b'{"x":{"y":1,"y":2}}',
             "promotion review JSON duplicate key refused"),
            ("nan", b'{"x":NaN}', "promotion review JSON nonfinite number refused"),
            ("infinity", b'{"x":Infinity}', "promotion review JSON nonfinite number refused"),
            ("overflow", b'{"x":1e309}', "promotion review JSON nonfinite number refused"),
            ("huge-int", b'{"x":' + b"9" * 129 + b'}',
             "promotion review JSON integer too large"),
            ("invalid-utf8", b'{"x":"\xff"}', "promotion review JSON unreadable or invalid"),
            ("malformed", b'{"x":', "promotion review JSON unreadable or invalid"),
            ("nonobject", b'[1,2]', "promotion review JSON root must be object"),
            ("oversized", b" " * (writer.MAX_JSON_BYTES + 1),
             "promotion review JSON size limit exceeded"),
        )
        for label, payload, expected in cases:
            path.write_bytes(payload)
            try:
                writer.load(path)
            except writer.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"promotion writer reader {label} wrong/private rejection: {exc}")
            else:
                raise Fail(f"promotion writer reader {label} unexpectedly accepted")
        canary = root / "external-canary.json"
        canary.write_text(marker, encoding="utf-8")
        alias = root / "alias.json"
        alias.symlink_to(canary)
        try:
            writer.load(alias)
        except writer.Fail as exc:
            require(str(exc) == "promotion review JSON path missing or unsafe",
                    f"promotion writer reader symlink wrong rejection: {exc}")
        else:
            raise Fail("promotion writer reader symlink unexpectedly accepted")
        require(canary.read_text(encoding="utf-8") == marker,
                "promotion writer reader external canary mutated")
        path.unlink()
        path.mkdir()
        try:
            writer.load(path)
        except writer.Fail as exc:
            require(str(exc) == "promotion review JSON path missing or unsafe",
                    f"promotion writer reader directory wrong rejection: {exc}")
        else:
            raise Fail("promotion writer reader directory unexpectedly accepted")
        path.rmdir()
        path.write_bytes(positive)
        require(writer.load(path) == {"schemaVersion": "synthetic", "nested": {"ok": True}},
                "promotion writer reader restored positive control failed")
    print(f"PASS: actual promotion writer JSON reader positive and {len(cases) + 2} fail-closed negatives")


def prove_private_negative_suite_transport() -> None:
    """Test the real promotion subprocess consumer with private error canaries."""
    validator = load_module(VALIDATOR, "memory_os_promotion_private_suite_negative")
    original_run = validator.subprocess.run
    marker = "PRIVATE_PROMOTION_SUBPROCESS_CANARY_DO_NOT_LOG"
    state = {"returncode": 0, "error": None}
    calls = []

    def fake_run(args, **kwargs):
        require(args == [sys.executable, str(validator.NEGATIVE)],
                "promotion negative suite command authority drift")
        require(
            kwargs.get("cwd") == validator.ROOT
            and kwargs.get("stdout") is subprocess.DEVNULL
            and kwargs.get("stderr") is subprocess.DEVNULL
            and kwargs.get("check") is False and kwargs.get("timeout") == 60
            and "text" not in kwargs,
            "promotion negative suite subprocess privacy/timeout drift",
        )
        calls.append(args)
        if state["error"] is not None:
            raise state["error"]
        return subprocess.CompletedProcess(args, state["returncode"], stdout=marker, stderr=marker)

    validator.subprocess.run = fake_run
    try:
        validator.run_negative_suite()
        cases = (
            ("nonzero", {"returncode": 1}, "promotion review negative suite failed"),
            ("boolean-exit", {"returncode": True}, "promotion review negative suite failed"),
            ("timeout", {"error": subprocess.TimeoutExpired(
                ["python"], 60, stderr=marker)},
             "promotion review negative suite unavailable or timed out"),
            ("unavailable", {"error": OSError(marker)},
             "promotion review negative suite unavailable or timed out"),
        )
        for label, changes, expected in cases:
            state.update({"returncode": 0, "error": None})
            state.update(changes)
            try:
                validator.run_negative_suite()
            except validator.Fail as exc:
                require(str(exc) == expected and marker not in str(exc),
                        f"promotion negative suite {label} wrong/private failure class: {exc}")
            else:
                raise Fail(f"promotion negative suite {label} unexpectedly accepted")
        require(len(calls) == len(cases) + 1,
                "promotion negative suite subprocess case multiplicity drift")
    finally:
        validator.subprocess.run = original_run
    print("PASS: actual promotion negative-suite subprocess bounded/private with four negatives")


def prove_bounded_promotion_payload_digest() -> None:
    """Exercise actual write-side review digest admission without protected writes."""
    writer = load_module(WRITER, "memory_os_promotion_digest_negative")
    require(Path(writer.__file__).resolve() == WRITER.resolve(),
            "promotion digest writer module identity drift")
    original_root = writer.ROOT
    with tempfile.TemporaryDirectory(prefix="promotion-digest-negative-") as tmp:
        root = Path(tmp)
        path = root / "review.json"
        payload = b'{"reviewResult":"APPROVED"}\n'
        path.write_bytes(payload)
        writer.ROOT = root
        try:
            require(writer.payload_sha256("review.json") == hashlib.sha256(payload).hexdigest(),
                    "promotion digest positive control failed")
            for ref in ("../outside.json", "/tmp/outside.json", "review.json/../review.json"):
                try:
                    writer.payload_sha256(ref)
                except writer.Fail as exc:
                    require(str(exc) == "promotion review digest ref invalid",
                            f"promotion digest traversal rejected at wrong boundary: {exc}")
                else:
                    raise Fail(f"promotion digest unsafe ref accepted: {ref}")
            path.write_bytes(b"x" * (writer.MAX_JSON_BYTES + 1))
            try:
                writer.payload_sha256("review.json")
            except writer.Fail as exc:
                require(str(exc) == "promotion review digest size limit exceeded",
                        f"promotion digest oversize wrong rejection: {exc}")
            else:
                raise Fail("promotion digest oversized payload accepted")
            marker = "PRIVATE_PROMOTION_DIGEST_CANARY_DO_NOT_LOG"
            canary = root / "external-canary.json"
            canary.write_text(marker, encoding="utf-8")
            alias = root / "alias.json"
            alias.symlink_to(canary)
            try:
                writer.payload_sha256("alias.json")
            except writer.Fail as exc:
                require(str(exc) == "promotion review digest path unsafe",
                        f"promotion digest symlink wrong rejection: {exc}")
            else:
                raise Fail("promotion digest symlink accepted")
            require(canary.read_text(encoding="utf-8") == marker,
                    "promotion digest external canary mutated")
            path.unlink()
            path.mkdir()
            try:
                writer.payload_sha256("review.json")
            except writer.Fail as exc:
                require(str(exc) == "promotion review digest path unsafe",
                        f"promotion digest directory wrong rejection: {exc}")
            else:
                raise Fail("promotion digest directory accepted")
            path.rmdir()
            path.write_bytes(payload)
            require(writer.payload_sha256("review.json") == hashlib.sha256(payload).hexdigest(),
                    "promotion digest restored positive control failed")
        finally:
            writer.ROOT = original_root
    print("PASS: actual promotion writer digest positive and six fail-closed path/size negatives")


def main() -> int:
    global EXPECTED_FAILURE
    require(WRITER.is_file() and VALIDATOR.is_file(), "promotion review authority scripts missing")
    prove_promotion_reader()
    prove_promotion_writer_reader()
    prove_bounded_promotion_payload_digest()
    prove_private_negative_suite_transport()
    writer = load_module(WRITER, "memory_os_promotion_review_writer_negative")
    validator = load_module(VALIDATOR, "memory_os_promotion_review_validator_negative")
    EXPECTED_FAILURE = writer.Fail

    original_lock = writer.LOCK
    original_load_writer = validator.load_writer
    try:
        writer.LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
        validator.load_writer = lambda: writer
        try:
            validator.main()
        except validator.Fail as exc:
            require("promotion review writer append lock authority drift" in str(exc), f"unexpected promotion lock rejection: {exc}")
            print("PASS reject: promotion review append lock authority substitution")
        else:
            raise Fail("promotion review append lock substitution unexpectedly accepted")
    finally:
        writer.LOCK = original_lock
        validator.load_writer = original_load_writer

    contract = json.loads(writer.CONTRACT.read_text(encoding="utf-8"))
    require(
        contract.get("rules", {}).get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
        "promotion review transactional append contract guard missing",
    )
    print("PASS accept: promotion review transactional append contract guard")

    registry = empty_registry()
    writer.validate_registry_for_append(registry)
    print("PASS accept: empty append-only promotion registry authority")
    for name, mutate in (
        ("promotion registry schema drift", lambda value: value.__setitem__("schemaVersion", "memory-os-backup-restore-promotion-review-registry.v0")),
        ("promotion registry append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        ("promotion registry production-ready relabel", lambda value: value.__setitem__("productionReady", True)),
        ("promotion registry boolean registered count", lambda value: value.__setitem__("registeredReviewCount", False)),
        ("promotion registry boolean decision count", lambda value: value.__setitem__("goRecommendationCount", False)),
        ("empty promotion registry current pointer drift", lambda value: value.__setitem__("currentDecisionId", "brpr_impossible_current")),
        ("empty promotion registry latest pointer drift", lambda value: value.__setitem__("latestDecisionId", "brpr_impossible_latest")),
    ):
        value = copy.deepcopy(registry)
        mutate(value)
        expect_rejected(name, lambda value=value: writer.validate_registry_for_append(value))

    original_registry_path = writer.REGISTRY
    original_validate_registry = writer.validate_registry_for_append
    original_replace = writer.os.replace
    original_atomic_restore = writer.atomic_restore
    with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-append-rollback-") as registry_tmp:
        temp_registry = Path(registry_tmp) / "promotion-registry.json"
        write_json(temp_registry, registry)
        temp_registry.chmod(0o640)
        before = temp_registry.read_bytes()
        before_mode = writer.stat.S_IMODE(temp_registry.stat().st_mode)
        writer.REGISTRY = temp_registry
        try:
            candidate = copy.deepcopy(registry)
            candidate["limitations"] = ["synthetic mode-preservation write"]
            writer.write_registry_transactionally(candidate)
            require(writer.stat.S_IMODE(temp_registry.stat().st_mode) == before_mode, "promotion registry mode changed after successful transactional append")
            require(not list(temp_registry.parent.glob(".backup-restore-promotion-review*.tmp")), "promotion registry successful append left temporary residue")
            print("PASS preserve: promotion registry successful append retains mode and leaves no temporary residue")

            temp_registry.write_bytes(before)
            temp_registry.chmod(before_mode)
            writer.validate_registry_for_append = lambda value: (_ for _ in ()).throw(writer.Fail("synthetic post-append validation failure"))
            expect_rejected(
                "promotion registry post-append validation rollback",
                lambda: writer.write_registry_transactionally(candidate),
            )
            require(temp_registry.read_bytes() == before, "promotion registry bytes changed after rejected transactional append")
            require(writer.stat.S_IMODE(temp_registry.stat().st_mode) == before_mode, "promotion registry mode changed after rejected transactional append")
            require(not list(temp_registry.parent.glob(".backup-restore-promotion-review*.tmp")), "promotion registry rollback left temporary residue")
            print("PASS preserve: promotion registry append failure rolled back bytes and mode")

            temp_registry.write_bytes(before)
            temp_registry.chmod(before_mode)
            writer.validate_registry_for_append = lambda value: (_ for _ in ()).throw(writer.Fail("synthetic post-append promotion validation failure"))
            writer.atomic_restore = lambda _payload, _mode: (_ for _ in ()).throw(OSError("synthetic promotion rollback restore rejection"))
            try:
                writer.write_registry_transactionally(candidate)
            except writer.Fail as exc:
                message = str(exc)
                require("synthetic post-append promotion validation failure" in message, "promotion append rollback failure erased primary validation diagnostic")
                require("rollback incomplete" in message, "promotion append rollback failure marker missing")
                require("synthetic promotion rollback restore rejection" in message, "promotion append rollback failure diagnostic missing")
                print("PASS diagnostics: promotion append preserves primary validation and rollback failure diagnostics")
            else:
                raise Fail("promotion append validation plus rollback failure unexpectedly succeeded")
            finally:
                writer.atomic_restore = original_atomic_restore
            require(not list(temp_registry.parent.glob(".backup-restore-promotion-review*.tmp")), "promotion registry rollback diagnostic negative left temporary residue")

            temp_registry.write_bytes(before)
            temp_registry.chmod(before_mode)
            writer.validate_registry_for_append = original_validate_registry

            def reject_replace(source: str | Path, destination: str | Path) -> None:
                if Path(destination) == temp_registry:
                    raise OSError("synthetic promotion registry replace rejection")
                original_replace(source, destination)

            writer.os.replace = reject_replace
            try:
                writer.write_registry_transactionally(candidate)
            except OSError as exc:
                require("synthetic promotion registry replace rejection" in str(exc), f"unexpected promotion replace rejection: {exc}")
                print("PASS reject: promotion registry candidate replace rejection")
            else:
                raise Fail("promotion registry candidate replace rejection unexpectedly succeeded")
            finally:
                writer.os.replace = original_replace
            require(temp_registry.read_bytes() == before, "promotion registry bytes changed after candidate replace rejection")
            require(writer.stat.S_IMODE(temp_registry.stat().st_mode) == before_mode, "promotion registry mode changed after candidate replace rejection")
            require(not list(temp_registry.parent.glob(".backup-restore-promotion-review*.tmp")), "promotion registry replace rejection left temporary residue")
            print("PASS preserve: promotion registry replace rejection retains bytes and mode without temporary residue")
        finally:
            writer.REGISTRY = original_registry_path
            writer.validate_registry_for_append = original_validate_registry
            writer.os.replace = original_replace
            writer.atomic_restore = original_atomic_restore

    require(writer.EVIDENCE_ROOT.is_dir(), "monitored backup/restore evidence namespace missing")
    with isolated_review_evidence_namespace(writer) as evidence_root:
        record, paths = build_fixture(evidence_root)

        expect_rejected("no current final recovery candidate", lambda: writer.validate_record(copy.deepcopy(record)))
        try:
            expect_rejected("unexpected implementation TypeError", lambda: (_ for _ in ()).throw(TypeError("synthetic implementation fault")))
        except TypeError:
            print("PASS preserve: unexpected implementation TypeError is not normalized as domain rejection")
        else:
            raise Fail("unexpected implementation TypeError was accepted as valid rejection")

        expect_rejected("absolute review authority ref", lambda: writer.repo_ref(str((ROOT / "README.md").resolve()), "negative.absolute"))
        expect_rejected("parent-traversal review authority ref", lambda: writer.repo_ref("docs/../README.md", "negative.parent"))
        expect_rejected("review evidence outside monitored namespace", lambda: writer.promotion_evidence_ref("README.md", "negative.namespace"))

        real_root = writer.ROOT
        with tempfile.TemporaryDirectory(prefix="memory-os-promotion-review-path-negative-") as escaped_root:
            escaped = Path(escaped_root) / "escaped-review.md"
            escaped.symlink_to(ROOT / "README.md")
            writer.ROOT = Path(escaped_root)
            try:
                expect_rejected("review authority symlink escapes repository root", lambda: writer.repo_ref("escaped-review.md", "negative.symlink"))
            finally:
                writer.ROOT = real_root

        real_candidate = writer.recovery_candidate
        real_registered = writer.registered_recovery_evidence
        writer.recovery_candidate = lambda evidence_id: {"evidenceId": evidence_id}
        writer.registered_recovery_evidence = lambda evidence_id: {"evidenceId": evidence_id}
        try:
            valid = copy.deepcopy(record)
            writer.validate_record(valid)
            writer.validate_record(valid, require_current_candidate=False)
            print("PASS accept: isolated typed synthetic current and historical review")

            arbitrary = copy.deepcopy(valid)
            arbitrary["recoveryOwnerReviewRef"] = "README.md"
            arbitrary["recoveryOwnerReviewSha256"] = sha256(ROOT / "README.md")
            expect_rejected("arbitrary repository file cannot impersonate human review evidence", lambda: writer.validate_record(arbitrary))

            duplicate_ref = copy.deepcopy(valid)
            duplicate_ref["operabilityReviewRef"] = duplicate_ref["securityReviewRef"]
            duplicate_ref["operabilityReviewSha256"] = duplicate_ref["securityReviewSha256"]
            expect_rejected("review evidence reuse", lambda: writer.validate_record(duplicate_ref))

            rationale_reuse = copy.deepcopy(valid)
            rationale_reuse["rationaleRef"] = rationale_reuse["securityReviewRef"]
            rationale_reuse["rationaleSha256"] = rationale_reuse["securityReviewSha256"]
            expect_rejected("rationale reused as reviewer evidence", lambda: writer.validate_record(rationale_reuse))

            def mutate_review(path: Path, mutate: Callable[[dict[str, Any]], None]) -> str:
                payload = json.loads(path.read_text(encoding="utf-8"))
                mutate(payload)
                write_json(path, payload)
                return sha256(path)

            wrong_role = copy.deepcopy(valid)
            wrong_role["recoveryOwnerReviewSha256"] = mutate_review(paths["recoveryOwner"], lambda p: p.__setitem__("reviewRole", "OPERABILITY"))
            expect_rejected("review role substitution", lambda: writer.validate_record(wrong_role))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            wrong_decision = copy.deepcopy(valid)
            wrong_decision["recoveryOwnerReviewSha256"] = mutate_review(paths["recoveryOwner"], lambda p: p.__setitem__("decisionId", "brpr_other_review"))
            expect_rejected("review decisionId binding mismatch", lambda: writer.validate_record(wrong_decision))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            wrong_candidate = copy.deepcopy(valid)
            wrong_candidate["recoveryOwnerReviewSha256"] = mutate_review(paths["recoveryOwner"], lambda p: p.__setitem__("recoveryEvidenceId", "brge_other_candidate"))
            expect_rejected("review recoveryEvidenceId binding mismatch", lambda: writer.validate_record(wrong_candidate))
            write_json(paths["recoveryOwner"], review_payload(role="RECOVERY_OWNER", reviewer="reviewer_recovery_owner"))

            duplicate_reviewer = copy.deepcopy(valid)
            duplicate_reviewer["operabilityReviewSha256"] = mutate_review(paths["operability"], lambda p: p.__setitem__("reviewerPseudonym", "reviewer_security"))
            expect_rejected("human reviewer identity reuse", lambda: writer.validate_record(duplicate_reviewer))
            write_json(paths["operability"], review_payload(role="OPERABILITY", reviewer="reviewer_operability"))

            unapproved = copy.deepcopy(valid)
            unapproved["securityReviewSha256"] = mutate_review(paths["security"], lambda p: p.__setitem__("reviewResult", "DEFER"))
            expect_rejected("human review result not approved", lambda: writer.validate_record(unapproved))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            late = copy.deepcopy(valid)
            late["securityReviewSha256"] = mutate_review(paths["security"], lambda p: p.__setitem__("reviewedAt", "2026-08-09T00:00:00Z"))
            expect_rejected("human review post-dates promotion decision", lambda: writer.validate_record(late))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            automatic = copy.deepcopy(valid)
            automatic["securityReviewSha256"] = mutate_review(paths["security"], lambda p: p.__setitem__("automaticPromotion", True))
            expect_rejected("human review cannot authorize automatic promotion", lambda: writer.validate_record(automatic))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            digest_drift = copy.deepcopy(valid)
            paths["security"].write_text(paths["security"].read_text(encoding="utf-8") + "\n", encoding="utf-8")
            expect_rejected("human review payload changed after digest binding", lambda: writer.validate_record(digest_drift))
            write_json(paths["security"], review_payload(role="SECURITY", reviewer="reviewer_security"))

            rationale_drift = copy.deepcopy(valid)
            paths["rationale"].write_text("Mutated rationale after digest binding.\n", encoding="utf-8")
            expect_rejected("rationale changed after digest binding", lambda: writer.validate_record(rationale_drift))
            paths["rationale"].write_text("Synthetic negative-suite rationale only; not human production authority.\n", encoding="utf-8")

            go_findings = copy.deepcopy(valid)
            go_findings["unresolvedFindings"] = [{"findingId": "finding_open", "severity": "LOW", "status": "OPEN", "ownerRef": "README.md"}]
            expect_rejected("GO recommendation with unresolved finding", lambda: writer.validate_record(go_findings))
            defer_findings = copy.deepcopy(go_findings)
            defer_findings["decision"] = "DEFER"
            writer.validate_record(defer_findings)
            print("PASS accept: DEFER may preserve owned unresolved finding")

            for field, value, label in (
                ("productionTrafficChanged", True, "traffic change claimed by review"),
                ("productionCredentialsUsed", True, "production credentials claimed by review"),
                ("productionEvidence", True, "production evidence relabel"),
                ("productionReady", True, "production ready relabel"),
            ):
                changed = copy.deepcopy(valid)
                changed[field] = value
                expect_rejected(label, lambda changed=changed: writer.validate_record(changed))

            one = empty_registry()
            one.update({
                "registeredReviewCount": 1,
                "goRecommendationCount": 1,
                "latestDecisionId": valid["decisionId"],
                "currentDecisionId": valid["decisionId"],
                "records": [copy.deepcopy(valid)],
            })
            writer.validate_registry_for_append(one)
            print("PASS accept: latest historical review is current while candidate remains current")
            writer.recovery_candidate = lambda evidence_id: (_ for _ in ()).throw(writer.Fail("synthetic supersession"))
            expect_rejected("stale current pointer after candidate supersession", lambda: writer.validate_registry_for_append(copy.deepcopy(one)))
            revoked = copy.deepcopy(one)
            rows, current_id = writer.reconcile_current_decision(revoked)
            require(len(rows) == 1 and revoked["records"] == one["records"], "reconcile mutated historical review rows")
            require(current_id is None and revoked["currentDecisionId"] is None, "reconcile did not revoke current promotion authority")
            writer.validate_registry_for_append(revoked)
            print("PASS preserve: superseded review remains historical while current authority is revoked")
            corrupt = copy.deepcopy(revoked)
            corrupt["currentDecisionId"] = "brpr_unregistered_corrupt"
            expect_rejected("reconcile refuses corrupt current pointer", lambda: writer.reconcile_current_decision(corrupt))

            writer.recovery_candidate = lambda evidence_id: (_ for _ in ()).throw(TypeError("synthetic current predicate fault"))
            try:
                writer.review_current(valid)
            except TypeError:
                print("PASS preserve: unexpected current-predicate TypeError surfaces")
            else:
                raise Fail("unexpected current-predicate TypeError was normalized into revocation")
        finally:
            writer.recovery_candidate = real_candidate
            writer.registered_recovery_evidence = real_registered

    print("Memory OS backup/restore promotion review negative suite PASS")
    print("canonical registry mutated: false")
    print("synthetic typed review evidence persisted: false")
    print("promotion evidence outside monitored namespace accepted: false")
    print("arbitrary repository file accepted as human review: false")
    print("review payload mutation accepted after digest binding: false")
    print("candidate bypass: false")
    print("historical review deleted on supersession: false")
    print("current promotion authority retained after supersession: false")
    print("review authority path escape accepted: false")
    print("promotion review lock substitution accepted: false")
    print("corrupt promotion registry accepted on append: false")
    print("post-append promotion registry validation failure persisted: false")
    print("promotion append primary validation diagnostic preservation: enforced")
    print("promotion append rollback diagnostic preservation: enforced")
    print("promotion registry mode drift accepted: false")
    print("promotion registry replace rejection mutated canonical state: false")
    print("promotion registry temporary residue retained: false")
    print("review can change traffic: false")
    print("GO recommendation implies production ready: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
