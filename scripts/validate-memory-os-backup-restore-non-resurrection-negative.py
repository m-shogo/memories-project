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
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")

def base_record(contract: dict[str, Any]) -> dict[str, Any]:
    prefixes = contract["domainEvidencePathPrefixes"]
    domains = {
        name: {"result": "PASS", "evidenceRef": prefixes[name] + "synthetic.json"}
        for name in contract["requiredDomains"]
    }
    return {
        "schemaVersion": contract["recordSchemaVersion"],
        "recordId": "brnr_negative_base",
        "generationEvidenceId": "brge_negative_generation",
        "sourceCommitSha": SHA,
        "domains": domains,
        "securityReviewRef": "SECURITY.md",
        "operabilityReviewRef": "README.md",
        "unresolvedFindings": [],
        "evidenceComplete": True,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False
    }

def main() -> int:
    require(WRITER.is_file() and CONTRACT.is_file(), "typed non-resurrection foundation missing")
    contract = load(CONTRACT)
    writer = load_writer()

    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-negative-") as tmp:
        tmp_path = Path(tmp)
        generation_registry = tmp_path / "generation-evidence.json"
        generation_registry.write_text(json.dumps({
            "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
            "records": [{"evidenceId": "brge_negative_generation", "sourceCommitSha": SHA}]
        }) + "\n", encoding="utf-8")
        writer.GEN_EVIDENCE_REGISTRY = generation_registry

        real_repo_ref = writer.repo_ref
        writer.repo_ref = lambda value, field: value if isinstance(value, str) and value else (_ for _ in ()).throw(writer.Fail(f"{field} invalid"))

        valid = base_record(contract)
        writer.validate_record(valid)
        print("PASS accept: structurally complete typed record")

        unregistered = copy.deepcopy(valid)
        unregistered["recordId"] = "brnr_unregistered_generation"
        unregistered["generationEvidenceId"] = "brge_missing_generation"
        expect_rejected("unregistered generation evidence", lambda: writer.validate_record(unregistered))

        sha_mismatch = copy.deepcopy(valid)
        sha_mismatch["recordId"] = "brnr_sha_mismatch"
        sha_mismatch["sourceCommitSha"] = "b" * 40
        expect_rejected("source commit mismatch", lambda: writer.validate_record(sha_mismatch))

        missing_domain = copy.deepcopy(valid)
        missing_domain["recordId"] = "brnr_missing_domain"
        missing_domain["domains"].pop(contract["requiredDomains"][0])
        expect_rejected("missing required domain", lambda: writer.validate_record(missing_domain))

        bad_path = copy.deepcopy(valid)
        bad_path["recordId"] = "brnr_bad_domain_path"
        domain_name = contract["requiredDomains"][0]
        bad_path["domains"][domain_name]["evidenceRef"] = "SECURITY.md"
        expect_rejected("domain evidence path is not typed", lambda: writer.validate_record(bad_path))

        failed_domain = copy.deepcopy(valid)
        failed_domain["recordId"] = "brnr_failed_domain"
        failed_domain["domains"][domain_name]["result"] = "FAIL"
        expect_rejected("failed domain cannot claim evidenceComplete", lambda: writer.validate_record(failed_domain))

        same_review = copy.deepcopy(valid)
        same_review["recordId"] = "brnr_same_review"
        same_review["operabilityReviewRef"] = same_review["securityReviewRef"]
        expect_rejected("security and operability review reuse", lambda: writer.validate_record(same_review))

        high_finding = copy.deepcopy(valid)
        high_finding["recordId"] = "brnr_high_finding"
        high_finding["unresolvedFindings"] = [{"findingId": "finding_high", "severity": "HIGH", "status": "OPEN"}]
        expect_rejected("HIGH unresolved finding", lambda: writer.validate_record(high_finding))

        prod_flag = copy.deepcopy(valid)
        prod_flag["recordId"] = "brnr_prod_flag"
        prod_flag["productionEvidence"] = True
        expect_rejected("production evidence relabel", lambda: writer.validate_record(prod_flag))

        mutable_alias = copy.deepcopy(valid)
        mutable_alias["recordId"] = "brnr_latest_alias"
        mutable_alias["domains"][domain_name]["evidenceRef"] = contract["domainEvidencePathPrefixes"][domain_name] + "latest.json"
        expect_rejected("mutable latest alias", lambda: writer.validate_record(mutable_alias))

        duplicate_ref = copy.deepcopy(valid)
        duplicate_ref["recordId"] = "brnr_duplicate_domain_ref"
        first, second = contract["requiredDomains"][:2]
        duplicate_ref["domains"][second]["evidenceRef"] = duplicate_ref["domains"][first]["evidenceRef"]
        expect_rejected("domain evidence references must be distinct", lambda: writer.validate_record(duplicate_ref))

        writer.repo_ref = real_repo_ref
        missing_file = copy.deepcopy(valid)
        missing_file["recordId"] = "brnr_missing_evidence_file"
        expect_rejected("typed evidence file must exist", lambda: writer.validate_record(missing_file))

    print("Memory OS backup/restore non-resurrection negative admission suite PASS")
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
