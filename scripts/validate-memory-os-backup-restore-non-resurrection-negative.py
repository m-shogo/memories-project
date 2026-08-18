#!/usr/bin/env python3
"""Exercise fail-closed negative cases for typed restore non-resurrection evidence."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
SHA = "a" * 40

class Fail(RuntimeError):
    pass

EXPECTED_FAILURE: type[Exception] = Fail

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value

def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load non-resurrection writer")
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

def base_record(contract: dict[str, Any]) -> dict[str, Any]:
    prefixes = contract["domainEvidencePathPrefixes"]
    review_prefixes = contract["reviewEvidencePathPrefixes"]
    return {
        "schemaVersion": contract["recordSchemaVersion"],
        "recordId": "brnr_negative_base",
        "generationEvidenceId": "brge_negative_generation",
        "sourceCommitSha": SHA,
        "domains": {name: {"result": "PASS", "evidenceRef": prefixes[name] + "synthetic.json"} for name in contract["requiredDomains"]},
        "securityReviewRef": review_prefixes["SECURITY"] + "synthetic.json",
        "operabilityReviewRef": review_prefixes["OPERABILITY"] + "synthetic.json",
        "unresolvedFindings": [],
        "evidenceComplete": True,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }

def domain_payload(generation: str, source_sha: str, domain: str, result: str) -> dict[str, Any]:
    return {"schemaVersion": "memory-os-backup-restore-non-resurrection-domain-evidence.v1", "generationEvidenceId": generation, "sourceCommitSha": source_sha, "domain": domain, "result": result, "productionTraffic": False, "productionCredentials": False, "productionEvidence": False, "productionReady": False}

def review_payload(*, generation: str, source_sha: str, record_id: str, review_type: str, reviewer: str, refs: list[str], digests: dict[str, str], result: str = "APPROVED") -> dict[str, Any]:
    return {"schemaVersion": "memory-os-backup-restore-non-resurrection-review-evidence.v1", "generationEvidenceId": generation, "sourceCommitSha": source_sha, "typedRecordId": record_id, "reviewType": review_type, "reviewerPseudonym": reviewer, "reviewedDomainEvidenceRefs": refs, "reviewedDomainEvidenceSha256": digests, "result": result, "productionTraffic": False, "productionCredentials": False, "productionEvidence": False, "productionReady": False}

def main() -> int:
    global EXPECTED_FAILURE
    contract = load(CONTRACT)
    writer = load_writer()
    EXPECTED_FAILURE = writer.Fail
    require(
        contract.get("recordRules", {}).get("typedRegistryMustRevalidateAfterAppendAndRollbackOnFailure") is True,
        "typed registry transactional append contract guard missing",
    )
    print("PASS accept: typed registry transactional append contract guard")
    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-negative-") as tmp:
        generation_registry = Path(tmp) / "generation-evidence.json"
        generation_registry.write_text(json.dumps({
            "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
            "appendOnly": True,
            "registeredEvidenceCount": 1,
            "records": [{"evidenceId": "brge_negative_generation", "sourceCommitSha": SHA}],
            "productionEvidence": False,
            "productionReady": False,
        }) + "\n", encoding="utf-8")
        writer.GEN_EVIDENCE_REGISTRY = generation_registry
        real_repo_ref, real_load = writer.repo_ref, writer.load
        writer.repo_ref = lambda value, field: value if isinstance(value, str) and value else (_ for _ in ()).throw(writer.Fail(f"{field} invalid"))
        prefixes = contract["domainEvidencePathPrefixes"]
        review_prefixes = contract["reviewEvidencePathPrefixes"]
        state: dict[str, Any] = {"generation": "brge_negative_generation", "sha": SHA, "domain": None, "domainResult": "PASS", "securityReviewer": "reviewer_security", "operabilityReviewer": "reviewer_operability", "reviewGeneration": "brge_negative_generation", "reviewSha": SHA, "reviewRecordId": "brnr_negative_base", "reviewRefsDropOne": False, "reviewDigestMismatch": False, "reviewResult": "APPROVED"}

        valid = base_record(contract)
        refs = [valid["domains"][name]["evidenceRef"] for name in contract["requiredDomains"]]
        expected_digests = {
            valid["domains"][name]["evidenceRef"]: writer.payload_sha256(domain_payload("brge_negative_generation", SHA, name, "PASS"))
            for name in contract["requiredDomains"]
        }
        if "securityReviewSha256" in contract["requiredRecordFields"] or "operabilityReviewSha256" in contract["requiredRecordFields"]:
            require({"securityReviewSha256", "operabilityReviewSha256"}.issubset(set(contract["requiredRecordFields"])), "review digest field contract incomplete")
            valid["securityReviewSha256"] = writer.payload_sha256(review_payload(generation="brge_negative_generation", source_sha=SHA, record_id="brnr_negative_base", review_type="SECURITY", reviewer="reviewer_security", refs=refs, digests=expected_digests))
            valid["operabilityReviewSha256"] = writer.payload_sha256(review_payload(generation="brge_negative_generation", source_sha=SHA, record_id="brnr_negative_base", review_type="OPERABILITY", reviewer="reviewer_operability", refs=refs, digests=expected_digests))

        def fake_load(path: Path) -> dict[str, Any]:
            if path == generation_registry:
                return real_load(path)
            try:
                ref = str(path.relative_to(ROOT))
            except ValueError:
                return real_load(path)
            matched = next((name for name, prefix in prefixes.items() if ref.startswith(prefix)), None)
            if matched:
                return domain_payload(state["generation"], state["sha"], state["domain"] or matched, state["domainResult"])
            for review_type, prefix in review_prefixes.items():
                if ref.startswith(prefix):
                    reviewed = refs[:-1] if state["reviewRefsDropOne"] else refs
                    reviewer = state["securityReviewer"] if review_type == "SECURITY" else state["operabilityReviewer"]
                    digests = dict(expected_digests)
                    if state["reviewDigestMismatch"]:
                        digests[refs[0]] = "0" * 64
                    return review_payload(generation=state["reviewGeneration"], source_sha=state["reviewSha"], record_id=state["reviewRecordId"], review_type=review_type, reviewer=reviewer, refs=reviewed, digests=digests, result=state["reviewResult"])
            return real_load(path)

        writer.load = fake_load
        writer.validate_record(valid)
        print("PASS accept: complete typed record with independently bundle-and-digest-bound reviews")

        def reject_variant(name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
            item = copy.deepcopy(valid); mutate(item); expect_rejected(name, lambda: writer.validate_record(item))

        reject_variant("unregistered generation evidence", lambda r: r.update(generationEvidenceId="brge_missing_generation"))
        reject_variant("source commit mismatch", lambda r: r.update(sourceCommitSha="b" * 40))
        reject_variant("missing required domain", lambda r: r["domains"].pop(contract["requiredDomains"][0]))
        domain_name = contract["requiredDomains"][0]
        reject_variant("domain evidence path is not typed", lambda r: r["domains"][domain_name].update(evidenceRef="SECURITY.md"))
        reject_variant("failed domain cannot claim evidenceComplete", lambda r: r["domains"][domain_name].update(result="FAIL"))
        reject_variant("security and operability review reuse", lambda r: r.update(operabilityReviewRef=r["securityReviewRef"]))
        reject_variant("HIGH unresolved finding", lambda r: r.update(unresolvedFindings=[{"findingId": "finding_high", "severity": "HIGH", "status": "OPEN"}]))
        reject_variant("production evidence relabel", lambda r: r.update(productionEvidence=True))
        reject_variant("mutable latest alias", lambda r: r["domains"][domain_name].update(evidenceRef=prefixes[domain_name] + "latest.json"))
        first, second = contract["requiredDomains"][:2]
        reject_variant("domain evidence references must be distinct", lambda r: r["domains"][second].update(evidenceRef=r["domains"][first]["evidenceRef"]))
        if "securityReviewSha256" in valid:
            reject_variant("security review payload digest binding mismatch", lambda r: r.update(securityReviewSha256="0" * 64))
            reject_variant("operability review payload digest binding mismatch", lambda r: r.update(operabilityReviewSha256="0" * 64))

        state["generation"] = "brge_other_generation"; expect_rejected("domain evidence generation binding mismatch", lambda: writer.validate_record(valid)); state["generation"] = "brge_negative_generation"
        state["sha"] = "b" * 40; expect_rejected("domain evidence source commit binding mismatch", lambda: writer.validate_record(valid)); state["sha"] = SHA
        state["domain"] = "wrongDomain"; expect_rejected("domain evidence domain binding mismatch", lambda: writer.validate_record(valid)); state["domain"] = None
        state["domainResult"] = "FAIL"; expect_rejected("domain evidence result binding mismatch", lambda: writer.validate_record(valid)); state["domainResult"] = "PASS"

        state["reviewGeneration"] = "brge_other_generation"; expect_rejected("review generation binding mismatch", lambda: writer.validate_record(valid)); state["reviewGeneration"] = "brge_negative_generation"
        state["reviewSha"] = "b" * 40; expect_rejected("review source commit binding mismatch", lambda: writer.validate_record(valid)); state["reviewSha"] = SHA
        state["reviewRecordId"] = "brnr_other_record"; expect_rejected("review typed record binding mismatch", lambda: writer.validate_record(valid)); state["reviewRecordId"] = "brnr_negative_base"
        state["reviewRefsDropOne"] = True; expect_rejected("review exact domain bundle mismatch", lambda: writer.validate_record(valid)); state["reviewRefsDropOne"] = False
        state["reviewDigestMismatch"] = True; expect_rejected("review domain evidence digest binding mismatch", lambda: writer.validate_record(valid)); state["reviewDigestMismatch"] = False
        state["operabilityReviewer"] = "reviewer_security"; expect_rejected("security and operability reviewer identity reuse", lambda: writer.validate_record(valid)); state["operabilityReviewer"] = "reviewer_operability"
        state["reviewResult"] = "REJECTED"; expect_rejected("review result not APPROVED", lambda: writer.validate_record(valid)); state["reviewResult"] = "APPROVED"

        empty_registry = {
            "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
            "appendOnly": True,
            "registeredRecordCount": 0,
            "completeRecordCount": 0,
            "candidateCoveredCount": 0,
            "records": [],
            "productionEvidence": False,
            "productionReady": False,
        }
        require(writer.validate_registry_for_append(copy.deepcopy(empty_registry)) == [], "healthy empty typed registry must remain appendable")
        print("PASS accept: healthy empty typed registry append authority")
        drift = copy.deepcopy(empty_registry); drift["registeredRecordCount"] = 1
        expect_rejected("typed writer registeredRecordCount drift before append", lambda: writer.validate_registry_for_append(drift))
        drift = copy.deepcopy(empty_registry); drift["completeRecordCount"] = True
        expect_rejected("typed writer boolean completeRecordCount before append", lambda: writer.validate_registry_for_append(drift))
        drift = copy.deepcopy(empty_registry); drift["candidateCoveredCount"] = 1
        expect_rejected("typed writer candidateCoveredCount drift before append", lambda: writer.validate_registry_for_append(drift))
        drift = copy.deepcopy(empty_registry); drift["productionReady"] = True
        expect_rejected("typed writer production boundary drift before append", lambda: writer.validate_registry_for_append(drift))

        original_registry = writer.REGISTRY
        original_validate_registry = writer.validate_registry_for_append
        transaction_registry = Path(tmp) / "typed-registry-transaction.json"
        transaction_registry.write_text(json.dumps(empty_registry, indent=2) + "\n", encoding="utf-8")
        before = transaction_registry.read_bytes()
        writer.REGISTRY = transaction_registry
        writer.validate_registry_for_append = lambda value: (_ for _ in ()).throw(writer.Fail("synthetic typed post-append validation failure"))
        try:
            candidate = copy.deepcopy(empty_registry)
            candidate["productionReady"] = True
            expect_rejected("typed writer post-append validation failure rollback", lambda: writer.write_registry_transactionally(candidate))
            require(transaction_registry.read_bytes() == before, "typed registry bytes changed after rejected transactional append")
            print("PASS preserve: typed registry append failure rolled back byte-for-byte")
        finally:
            writer.REGISTRY = original_registry
            writer.validate_registry_for_append = original_validate_registry

        writer.repo_ref, writer.load = real_repo_ref, real_load
        expect_rejected("writer evidence ref absolute path", lambda: writer.repo_ref(str((ROOT / "SECURITY.md").resolve()), "securityReviewRef"))
        expect_rejected("writer evidence ref parent traversal alias", lambda: writer.repo_ref("docs/../SECURITY.md", "securityReviewRef"))

        external_evidence = Path(tmp) / "external-evidence.json"
        external_evidence.write_text("{}\n", encoding="utf-8")
        symlink_ref = prefixes[domain_name] + "negative-external-symlink.json"
        symlink_path = ROOT / symlink_ref
        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            symlink_path.unlink(missing_ok=True)
            symlink_path.symlink_to(external_evidence)
            expect_rejected("writer repo-local evidence symlink escaping repository", lambda: writer.repo_ref(symlink_ref, f"domains.{domain_name}.evidenceRef"))
        finally:
            symlink_path.unlink(missing_ok=True)

        missing_file = copy.deepcopy(valid); missing_file["recordId"] = "brnr_missing_evidence_file"
        expect_rejected("typed evidence file must exist", lambda: writer.validate_record(missing_file))

    print("Memory OS backup/restore non-resurrection negative admission suite PASS")
    print("typed domain and independent review evidence are generation/commit/bundle/digest bound: true")
    print("typed record immutably binds review payload digests: true")
    print("typed writer rejects aggregate/current authority drift before append: true")
    print("typed writer rolls back post-append validation failure: true")
    print("writer evidence refs canonical and repository-contained: true")
    print("unexpected exception accepted as a valid rejection: false")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
