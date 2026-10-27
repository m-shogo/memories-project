#!/usr/bin/env python3
"""Exercise fail-closed negative cases for typed restore non-resurrection evidence."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
ADMISSION = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
SHA = "a" * 40

class Fail(RuntimeError):
    pass

EXPECTED_FAILURE: type[Exception] = Fail
EXPECTED_DIAGNOSTICS: dict[str, str] = {}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def require_fixture_path_vacant(path: Path) -> None:
    # Never delete or replace an existing repository artifact to seed a negative fixture.
    require(not path.exists() and not path.is_symlink(), f"negative fixture path already occupied: {path}")

def require_fixture_parent_canonical(parent: Path, root: Path = ROOT) -> tuple[int, int]:
    # Vacant leaf paths are unsafe when an ancestor aliases another evidence directory.
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise Fail("negative fixture parent escapes canonical root") from exc
    require(root.is_dir() and not root.is_symlink(), "negative fixture root missing or symlinked")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        require(cursor.is_dir() and not cursor.is_symlink(), "negative fixture parent missing or symlinked")
    require(parent.resolve(strict=True) == root.resolve(strict=True) / relative,
            "negative fixture parent canonical resolution drift")
    parent_stat = parent.stat()
    return parent_stat.st_dev, parent_stat.st_ino

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
    expected = EXPECTED_DIAGNOSTICS.get(name)
    require(isinstance(expected, str) and bool(expected), f"negative case lacks canonical diagnostic binding: {name}")
    try:
        action()
    except EXPECTED_FAILURE as exc:
        require(str(exc) == expected, f"wrong rejection diagnostic for {name}: expected {expected!r}, observed {str(exc)!r}")
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

def require_writer_authority_reachability(tree: ast.Module) -> None:
    expected_path = ast.parse(
        'ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-writer-authority.py"',
        mode="eval",
    ).body
    bindings = [
        node.value for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "WRITER_AUTHORITY_NEGATIVE"
                for target in node.targets)
    ]
    require(len(bindings) == 1 and ast.dump(bindings[0]) == ast.dump(expected_path),
            "typed writer CLI negative path authority drift")
    mains = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"
    ]
    require(len(mains) == 1 and isinstance(mains[0], ast.FunctionDef),
            "typed writer CLI negative canonical main binding drift")
    direct_calls = [
        node for node in mains[0].body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name) and node.value.func.id == "run_validator"
        and len(node.value.args) == 2
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id == "WRITER_AUTHORITY_NEGATIVE"
        and isinstance(node.value.args[1], ast.Constant)
        and node.value.args[1].value == "non-resurrection writer CLI authority negative suite"
        and not node.value.keywords
    ]
    require(len(direct_calls) == 1,
            "typed writer CLI negative not directly executed by admission main")

    call_index = mains[0].body.index(direct_calls[0])

    def exits_before_guard(node: ast.AST) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return False
        if isinstance(node, ast.Return):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"exit", "quit"}:
                return True
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in
                    {("sys", "exit"), ("os", "_exit")}):
                return True
        if (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and node.exc.func.id == "SystemExit"
                and len(node.exc.args) == 1
                and isinstance(node.exc.args[0], ast.Constant)
                and node.exc.args[0].value == 0):
            return True
        return any(exits_before_guard(child) for child in ast.iter_child_nodes(node))

    require(not any(exits_before_guard(node) for node in mains[0].body[:call_index]),
            "typed writer CLI negative can exit successfully before admission execution")


def prove_writer_authority_reachability() -> None:
    try:
        tree = ast.parse(ADMISSION.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise Fail("typed writer CLI negative admission source unavailable") from exc
    require_writer_authority_reachability(tree)
    main_node = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "main")
    call_index = next(index for index, node in enumerate(main_node.body)
                      if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                      and isinstance(node.value.func, ast.Name)
                      and node.value.func.id == "run_validator"
                      and node.value.args and isinstance(node.value.args[0], ast.Name)
                      and node.value.args[0].id == "WRITER_AUTHORITY_NEGATIVE")
    for label in ("removed", "dead-branch", "string-only", "duplicate"):
        mutated = copy.deepcopy(tree)
        main_copy = next(node for node in mutated.body
                         if isinstance(node, ast.FunctionDef) and node.name == "main")
        original = main_copy.body[call_index]
        if label == "removed":
            del main_copy.body[call_index]
        elif label == "dead-branch":
            main_copy.body[call_index] = ast.If(
                test=ast.Constant(value=False), body=[original], orelse=[])
        elif label == "string-only":
            main_copy.body[call_index] = ast.Expr(
                value=ast.Constant(value="run_validator(WRITER_AUTHORITY_NEGATIVE)"))
        else:
            main_copy.body.insert(call_index, copy.deepcopy(original))
        try:
            require_writer_authority_reachability(mutated)
        except Fail as exc:
            require(str(exc) == "typed writer CLI negative not directly executed by admission main",
                    f"typed writer CLI reachability {label} rejection diagnostic drift")
        else:
            raise Fail(f"typed writer CLI reachability {label} bypass unexpectedly accepted")
    early_exit_cases = (
        ("direct-return", ast.Return(value=ast.Constant(value=0))),
        ("conditional-return", ast.If(test=ast.Constant(value=True),
                                      body=[ast.Return(value=ast.Constant(value=0))],
                                      orelse=[])),
        ("success-exit", ast.Expr(value=ast.Call(
            func=ast.Attribute(value=ast.Name(id="sys", ctx=ast.Load()),
                               attr="exit", ctx=ast.Load()),
            args=[ast.Constant(value=0)], keywords=[]))),
        ("system-exit", ast.Raise(exc=ast.Call(
            func=ast.Name(id="SystemExit", ctx=ast.Load()),
            args=[ast.Constant(value=0)], keywords=[]), cause=None)),
        ("finally-return", ast.Try(body=[ast.Pass()], handlers=[], orelse=[],
                                   finalbody=[ast.Return(value=ast.Constant(value=0))])),
    )
    for label, early_exit in early_exit_cases:
        mutated = copy.deepcopy(tree)
        main_copy = next(node for node in mutated.body
                         if isinstance(node, ast.FunctionDef) and node.name == "main")
        main_copy.body.insert(call_index, early_exit)
        try:
            require_writer_authority_reachability(mutated)
        except Fail as exc:
            require(str(exc) == "typed writer CLI negative can exit successfully before admission execution",
                    f"typed writer CLI early-exit {label} diagnostic drift")
        else:
            raise Fail(f"typed writer CLI early-exit {label} unexpectedly accepted")
    mutated = copy.deepcopy(tree)
    binding = next(node for node in mutated.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "WRITER_AUTHORITY_NEGATIVE"
                           for target in node.targets))
    binding.value = ast.Constant(value="unrelated-validator.py")
    try:
        require_writer_authority_reachability(mutated)
    except Fail as exc:
        require(str(exc) == "typed writer CLI negative path authority drift",
                "typed writer CLI reachability binding diagnostic drift")
    else:
        raise Fail("typed writer CLI path substitution unexpectedly accepted")
    print("PASS reject: typed writer CLI admission missing/dead/string/duplicate/path and five early-exit bypasses")


def main() -> int:
    global EXPECTED_FAILURE, EXPECTED_DIAGNOSTICS
    prove_writer_authority_reachability()
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
        state: dict[str, Any] = {
            "generation": "brge_negative_generation",
            "sha": SHA,
            "domain": None,
            "domainTarget": None,
            "domainResult": "PASS",
            "domainProductionField": None,
            "domainFieldMutation": None,
            "domainSchemaMutation": False,
            "securityReviewer": "reviewer_security",
            "operabilityReviewer": "reviewer_operability",
            "reviewGeneration": "brge_negative_generation",
            "reviewSha": SHA,
            "reviewRecordId": "brnr_negative_base",
            "reviewRefsDropOne": False,
            "reviewRefsDropDomain": None,
            "reviewDigestMismatch": False,
            "reviewDigestTarget": None,
            "reviewDigestCoverageMutation": None,
            "reviewResult": "APPROVED",
            "reviewProductionField": None,
            "reviewFieldMutation": None,
            "reviewSchemaMutation": False,
            "reviewRefsMutation": None,
            "reviewDigestValueMutation": None,
            "reviewTypeOverride": None,
            "reviewTarget": "BOTH",
        }

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
                mutate_domain = state["domainTarget"] is None or state["domainTarget"] == matched
                payload = domain_payload(
                    state["generation"] if mutate_domain else "brge_negative_generation",
                    state["sha"] if mutate_domain else SHA,
                    (state["domain"] or matched) if mutate_domain else matched,
                    state["domainResult"] if mutate_domain else "PASS",
                )
                if mutate_domain and state["domainProductionField"] is not None:
                    payload[state["domainProductionField"]] = True
                if mutate_domain and state["domainFieldMutation"] == "MISSING":
                    payload.pop("schemaVersion")
                if mutate_domain and state["domainFieldMutation"] == "EXTRA":
                    payload["unexpectedField"] = False
                if mutate_domain and state["domainSchemaMutation"]:
                    payload["schemaVersion"] = "memory-os-backup-restore-non-resurrection-domain-evidence.v0"
                return payload
            for review_type, prefix in review_prefixes.items():
                if ref.startswith(prefix):
                    mutate_review = state["reviewTarget"] in ("BOTH", review_type)
                    reviewed = ([ref for ref in refs if ref != (state["reviewRefsDropDomain"] or refs[-1])]
                                if mutate_review and state["reviewRefsDropOne"] else refs)
                    if mutate_review and state["reviewRefsMutation"] == "DUPLICATE":
                        reviewed = refs + [refs[0]]
                    if mutate_review and state["reviewRefsMutation"] == "NON_LIST":
                        reviewed = "not-a-list"
                    reviewer = state["securityReviewer"] if review_type == "SECURITY" else state["operabilityReviewer"]
                    digests = dict(expected_digests)
                    if mutate_review and state["reviewDigestMismatch"]:
                        digests[state["reviewDigestTarget"] or refs[0]] = "0" * 64
                    if mutate_review and state["reviewDigestCoverageMutation"] == "MISSING":
                        digests.pop(state["reviewDigestTarget"] or refs[0])
                    if mutate_review and state["reviewDigestCoverageMutation"] == "EXTRA":
                        digests["synthetic-unreviewed-domain.json"] = "0" * 64
                    if mutate_review and state["reviewDigestValueMutation"] == "BAD_HEX":
                        digests[refs[0]] = "G" * 64
                    if mutate_review and state["reviewDigestValueMutation"] == "BOOLEAN":
                        digests[refs[0]] = True
                    payload = review_payload(
                        generation=state["reviewGeneration"] if mutate_review else "brge_negative_generation",
                        source_sha=state["reviewSha"] if mutate_review else SHA,
                        record_id=state["reviewRecordId"] if mutate_review else "brnr_negative_base",
                        review_type=state["reviewTypeOverride"] if mutate_review and state["reviewTypeOverride"] is not None else review_type,
                        reviewer=reviewer, refs=reviewed, digests=digests,
                        result=state["reviewResult"] if mutate_review else "APPROVED",
                    )
                    if mutate_review and state["reviewProductionField"] is not None:
                        payload[state["reviewProductionField"]] = True
                    if mutate_review and state["reviewFieldMutation"] == "MISSING":
                        payload.pop("schemaVersion")
                    if mutate_review and state["reviewFieldMutation"] == "EXTRA":
                        payload["unexpectedField"] = False
                    if mutate_review and state["reviewSchemaMutation"]:
                        payload["schemaVersion"] = "memory-os-backup-restore-non-resurrection-review-evidence.v0"
                    return payload
            return real_load(path)

        writer.load = fake_load
        writer.validate_record(valid)
        print("PASS accept: complete typed record with independently bundle-and-digest-bound reviews")


        domain_name = contract["requiredDomains"][0]
        second_domain = contract["requiredDomains"][1]
        EXPECTED_DIAGNOSTICS = {
            "unregistered generation evidence": "generationEvidenceId is not uniquely registered",
            "source commit mismatch": "sourceCommitSha must match generation recovery evidence",
            # Each of the eight typed domains has an independent fail-closed deletion proof.
            "domain evidence path is not typed": f"domain {domain_name} evidence path is not typed",
            "domain result contradicts typed evidence": f"domain {domain_name} evidence result binding mismatch",
            "evidenceComplete false despite eight PASS domains": "evidenceComplete derivation drift",
            "security and operability review reuse": "security and operability reviews must be distinct",
            "HIGH unresolved finding": "HIGH/CRITICAL findings block admission",
            "production traffic relabel": "productionTraffic must remain false",
            "production credentials relabel": "productionCredentials must remain false",
            "production evidence relabel": "productionEvidence must remain false",
            "production ready relabel": "productionReady must remain false",
            "mutable alias breaks reviewed domain bundle": "SECURITY review does not bind exact typed domain bundle",
            "cross-domain evidence path prefix mismatch": f"domain {second_domain} evidence path is not typed",
            "security review payload digest binding mismatch": "security review payload digest binding mismatch",
            "operability review payload digest binding mismatch": "operability review payload digest binding mismatch",
            "domain evidence generation binding mismatch": f"domain {domain_name} evidence generation binding mismatch",
            "domain evidence source commit binding mismatch": f"domain {domain_name} evidence source commit binding mismatch",
            "domain evidence domain binding mismatch": f"domain {domain_name} evidence domain binding mismatch",
            "domain evidence result binding mismatch": f"domain {domain_name} evidence result binding mismatch",
            "review generation binding mismatch": "SECURITY review generation binding mismatch",
            "review source commit binding mismatch": "SECURITY review source commit binding mismatch",
            "review typed record binding mismatch": "SECURITY review typed record binding mismatch",
            "review exact domain bundle mismatch": "SECURITY review does not bind exact typed domain bundle",
            "review domain evidence digest binding mismatch": "SECURITY review domain evidence digest binding mismatch",
            "security and operability reviewer identity reuse": "security and operability reviewers must be independent",
            "review result not APPROVED": "SECURITY review must be APPROVED",
            "operability review exact domain bundle mismatch": "OPERABILITY review does not bind exact typed domain bundle",
            "operability review domain evidence digest binding mismatch": "OPERABILITY review domain evidence digest binding mismatch",
            "operability review result not APPROVED": "OPERABILITY review must be APPROVED",
            "operability review generation binding mismatch": "OPERABILITY review generation binding mismatch",
            "operability review source commit binding mismatch": "OPERABILITY review source commit binding mismatch",
            "operability review typed record binding mismatch": "OPERABILITY review typed record binding mismatch",
            "operability review type mismatch": "OPERABILITY review type mismatch",
            "typed writer registeredRecordCount drift before append": "registeredRecordCount drift",
            "typed writer boolean completeRecordCount before append": "completeRecordCount drift",
            "typed writer candidateCoveredCount drift before append": "candidateCoveredCount drift",
            "typed writer production evidence drift before append": "registry production boundary drift",
            "typed writer production ready drift before append": "registry production boundary drift",
            "typed writer post-append validation failure rollback": "typed non-resurrection append failed; rollback completed",
            "writer evidence ref absolute path": "securityReviewRef must be a canonical repository-relative path",
            "writer evidence ref parent traversal alias": "securityReviewRef must be a canonical repository-relative path",
            "writer repo-local evidence symlink escaping repository": f"domains.{domain_name}.evidenceRef evidence path missing or escapes repository",
            "typed evidence file must exist": f"domains.{domain_name}.evidenceRef evidence path missing or escapes repository",
        }
        for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
            EXPECTED_DIAGNOSTICS[f"domain evidence {field} production boundary"] = f"domain {domain_name} evidence {field} must remain false"
            EXPECTED_DIAGNOSTICS[f"review evidence {field} production boundary"] = f"SECURITY review {field} must remain false"
            EXPECTED_DIAGNOSTICS[f"operability review evidence {field} production boundary"] = f"OPERABILITY review {field} must remain false"

        # A generic writer.Fail must never count as proof of the intended rejection.
        try:
            expect_rejected("source commit mismatch", lambda: (_ for _ in ()).throw(writer.Fail("unrelated synthetic failure")))
        except Fail as exc:
            require("wrong rejection diagnostic" in str(exc), "negative diagnostic classifier accepted unrelated writer.Fail")
            print("PASS reject: unrelated writer.Fail cannot satisfy source-commit negative")
        else:
            raise Fail("negative diagnostic classifier accepted unrelated writer.Fail")

        def reject_variant(name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
            item = copy.deepcopy(valid); mutate(item); expect_rejected(name, lambda: writer.validate_record(item))

        reject_variant("unregistered generation evidence", lambda r: r.update(generationEvidenceId="brge_missing_generation"))
        reject_variant("source commit mismatch", lambda r: r.update(sourceCommitSha="b" * 40))
        for missing_domain in contract["requiredDomains"]:
            case = f"missing required domain: {missing_domain}"
            EXPECTED_DIAGNOSTICS[case] = "domain coverage drift"
            reject_variant(case, lambda r, domain=missing_domain: r["domains"].pop(domain))
        reject_variant("domain evidence path is not typed", lambda r: r["domains"][domain_name].update(evidenceRef="SECURITY.md"))
        reject_variant("domain result contradicts typed evidence", lambda r: r["domains"][domain_name].update(result="FAIL"))
        # Probe every other typed domain independently, not only the first-domain representative.
        for domain in contract["requiredDomains"][1:]:
            path_case = f"domain evidence path is not typed: {domain}"
            EXPECTED_DIAGNOSTICS[path_case] = f"domain {domain} evidence path is not typed"
            reject_variant(path_case, lambda r, name=domain: r["domains"][name].update(evidenceRef="SECURITY.md"))
            result_case = f"domain result contradicts typed evidence: {domain}"
            EXPECTED_DIAGNOSTICS[result_case] = f"domain {domain} evidence result binding mismatch"
            reject_variant(result_case, lambda r, name=domain: r["domains"][name].update(result="FAIL"))
        reject_variant("evidenceComplete false despite eight PASS domains", lambda r: r.update(evidenceComplete=False))
        reject_variant("security and operability review reuse", lambda r: r.update(operabilityReviewRef=r["securityReviewRef"]))
        reject_variant("HIGH unresolved finding", lambda r: r.update(unresolvedFindings=[{"findingId": "finding_high", "severity": "HIGH", "status": "OPEN"}]))
        # Non-blocking findings are allowed only when the record explicitly remains incomplete.
        # An approved review cannot silently convert LOW/MEDIUM unresolved findings into completeness.
        for severity, finding_status in (("LOW", "OPEN"), ("MEDIUM", "ACCEPTED_WITH_OWNER")):
            finding = {"findingId": f"finding_{severity.lower()}", "severity": severity, "status": finding_status}
            incomplete = copy.deepcopy(valid)
            incomplete["unresolvedFindings"] = [finding]
            incomplete["evidenceComplete"] = False
            writer.validate_record(incomplete)
            case = f"{severity} unresolved finding cannot claim complete typed evidence"
            EXPECTED_DIAGNOSTICS[case] = "evidenceComplete derivation drift"
            reject_variant(case, lambda r, row=finding: r.update(unresolvedFindings=[row], evidenceComplete=True))
        print("PASS reject: unresolved LOW/MEDIUM findings cannot create complete typed evidence")
        reject_variant("production traffic relabel", lambda r: r.update(productionTraffic=True))
        reject_variant("production credentials relabel", lambda r: r.update(productionCredentials=True))
        reject_variant("production evidence relabel", lambda r: r.update(productionEvidence=True))
        reject_variant("production ready relabel", lambda r: r.update(productionReady=True))
        reject_variant("mutable alias breaks reviewed domain bundle", lambda r: r["domains"][domain_name].update(evidenceRef=prefixes[domain_name] + "latest.json"))
        first, second = contract["requiredDomains"][:2]
        reject_variant("cross-domain evidence path prefix mismatch", lambda r: r["domains"][second].update(evidenceRef=r["domains"][first]["evidenceRef"]))
        if "securityReviewSha256" in valid:
            reject_variant("security review payload digest binding mismatch", lambda r: r.update(securityReviewSha256="0" * 64))
            reject_variant("operability review payload digest binding mismatch", lambda r: r.update(operabilityReviewSha256="0" * 64))

        state["generation"] = "brge_other_generation"; expect_rejected("domain evidence generation binding mismatch", lambda: writer.validate_record(valid)); state["generation"] = "brge_negative_generation"
        state["sha"] = "b" * 40; expect_rejected("domain evidence source commit binding mismatch", lambda: writer.validate_record(valid)); state["sha"] = SHA
        state["domain"] = "wrongDomain"; expect_rejected("domain evidence domain binding mismatch", lambda: writer.validate_record(valid)); state["domain"] = None
        state["domainResult"] = "FAIL"; expect_rejected("domain evidence result binding mismatch", lambda: writer.validate_record(valid)); state["domainResult"] = "PASS"
        # Each remaining typed domain independently rejects all four evidence provenance drifts.
        # The first domain is already exercised by the four cases immediately above.
        for domain in contract["requiredDomains"][1:]:
            state["domainTarget"] = domain
            for label, field, bad, good, diagnostic in (
                ("generation", "generation", "brge_other_generation", "brge_negative_generation", "generation binding mismatch"),
                ("source commit", "sha", "b" * 40, SHA, "source commit binding mismatch"),
                ("domain", "domain", "wrongDomain", None, "domain binding mismatch"),
                ("result", "domainResult", "FAIL", "PASS", "result binding mismatch"),
            ):
                case = f"domain evidence {label} binding mismatch: {domain}"
                EXPECTED_DIAGNOSTICS[case] = f"domain {domain} evidence {diagnostic}"
                state[field] = bad
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state[field] = good
        state["domainTarget"] = None
        writer.validate_record(valid)
        print("PASS accept: all eight typed domains independently enforce four provenance bindings")
        for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
            state["domainProductionField"] = field
            expect_rejected(f"domain evidence {field} production boundary", lambda: writer.validate_record(valid))
        state["domainProductionField"] = None
        # Every remaining typed domain must independently reject each production-boundary flag.
        for domain in contract["requiredDomains"][1:]:
            state["domainTarget"] = domain
            for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
                case = f"domain evidence {field} production boundary: {domain}"
                EXPECTED_DIAGNOSTICS[case] = f"domain {domain} evidence {field} must remain false"
                state["domainProductionField"] = field
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state["domainProductionField"] = None
        state["domainTarget"] = None
        writer.validate_record(valid)
        print("PASS accept: all eight typed domains independently reject production-boundary flags")

        state["reviewGeneration"] = "brge_other_generation"; expect_rejected("review generation binding mismatch", lambda: writer.validate_record(valid)); state["reviewGeneration"] = "brge_negative_generation"
        state["reviewSha"] = "b" * 40; expect_rejected("review source commit binding mismatch", lambda: writer.validate_record(valid)); state["reviewSha"] = SHA
        state["reviewRecordId"] = "brnr_other_record"; expect_rejected("review typed record binding mismatch", lambda: writer.validate_record(valid)); state["reviewRecordId"] = "brnr_negative_base"
        state["reviewRefsDropOne"] = True; expect_rejected("review exact domain bundle mismatch", lambda: writer.validate_record(valid)); state["reviewRefsDropOne"] = False
        state["reviewDigestMismatch"] = True; expect_rejected("review domain evidence digest binding mismatch", lambda: writer.validate_record(valid)); state["reviewDigestMismatch"] = False
        state["operabilityReviewer"] = "reviewer_security"; expect_rejected("security and operability reviewer identity reuse", lambda: writer.validate_record(valid)); state["operabilityReviewer"] = "reviewer_operability"
        state["reviewResult"] = "REJECTED"; expect_rejected("review result not APPROVED", lambda: writer.validate_record(valid)); state["reviewResult"] = "APPROVED"
        for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
            state["reviewProductionField"] = field
            expect_rejected(f"review evidence {field} production boundary", lambda: writer.validate_record(valid))
        state["reviewProductionField"] = None

        # Target OPERABILITY alone: SECURITY remains valid so its approval cannot mask an OPERABILITY failure.
        state["reviewTarget"] = "OPERABILITY"
        # SECURITY remains canonical while OPERABILITY alone violates each provenance binding.
        state["reviewGeneration"] = "brge_other_generation"; expect_rejected("operability review generation binding mismatch", lambda: writer.validate_record(valid)); state["reviewGeneration"] = "brge_negative_generation"
        state["reviewSha"] = "b" * 40; expect_rejected("operability review source commit binding mismatch", lambda: writer.validate_record(valid)); state["reviewSha"] = SHA
        state["reviewRecordId"] = "brnr_other_record"; expect_rejected("operability review typed record binding mismatch", lambda: writer.validate_record(valid)); state["reviewRecordId"] = "brnr_negative_base"
        state["reviewTypeOverride"] = "SECURITY"; expect_rejected("operability review type mismatch", lambda: writer.validate_record(valid)); state["reviewTypeOverride"] = None
        state["reviewRefsDropOne"] = True; expect_rejected("operability review exact domain bundle mismatch", lambda: writer.validate_record(valid)); state["reviewRefsDropOne"] = False
        state["reviewDigestMismatch"] = True; expect_rejected("operability review domain evidence digest binding mismatch", lambda: writer.validate_record(valid)); state["reviewDigestMismatch"] = False
        state["reviewResult"] = "REJECTED"; expect_rejected("operability review result not APPROVED", lambda: writer.validate_record(valid)); state["reviewResult"] = "APPROVED"
        for field in ("productionTraffic", "productionCredentials", "productionEvidence", "productionReady"):
            state["reviewProductionField"] = field
            expect_rejected(f"operability review evidence {field} production boundary", lambda: writer.validate_record(valid))
        state["reviewProductionField"] = None
        state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS accept: independent OPERABILITY review negative probes restore valid review state")

        # Bind each review independently to every typed bundle member and digest.
        for review_type in ("SECURITY", "OPERABILITY"):
            state["reviewTarget"] = review_type
            for domain in contract["requiredDomains"]:
                target_ref = valid["domains"][domain]["evidenceRef"]
                missing_case = f"{review_type} review missing domain bundle member: {domain}"
                EXPECTED_DIAGNOSTICS[missing_case] = f"{review_type} review does not bind exact typed domain bundle"
                state["reviewRefsDropDomain"] = target_ref
                state["reviewRefsDropOne"] = True
                try:
                    expect_rejected(missing_case, lambda: writer.validate_record(valid))
                finally:
                    state["reviewRefsDropOne"] = False
                    state["reviewRefsDropDomain"] = None

                digest_case = f"{review_type} review domain digest mismatch: {domain}"
                EXPECTED_DIAGNOSTICS[digest_case] = f"{review_type} review domain evidence digest binding mismatch"
                state["reviewDigestTarget"] = target_ref
                state["reviewDigestMismatch"] = True
                try:
                    expect_rejected(digest_case, lambda: writer.validate_record(valid))
                finally:
                    state["reviewDigestMismatch"] = False
                    state["reviewDigestTarget"] = None
            writer.validate_record(valid)
        state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS reject: both independent reviews bind all eight domain members and payload digests")

        # Digest-key coverage is a separate gate from digest-value equality.
        # Prove all eight missing keys per reviewer and an unreviewed extra key.
        for review_type in ("SECURITY", "OPERABILITY"):
            state["reviewTarget"] = review_type
            for domain in contract["requiredDomains"]:
                case = f"{review_type} review missing domain digest key: {domain}"
                EXPECTED_DIAGNOSTICS[case] = f"{review_type} reviewedDomainEvidenceSha256 coverage mismatch"
                state["reviewDigestTarget"] = valid["domains"][domain]["evidenceRef"]
                state["reviewDigestCoverageMutation"] = "MISSING"
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state["reviewDigestCoverageMutation"] = None
                    state["reviewDigestTarget"] = None
            case = f"{review_type} review extra unreviewed domain digest key"
            EXPECTED_DIAGNOSTICS[case] = f"{review_type} reviewedDomainEvidenceSha256 coverage mismatch"
            state["reviewDigestCoverageMutation"] = "EXTRA"
            try:
                expect_rejected(case, lambda: writer.validate_record(valid))
            finally:
                state["reviewDigestCoverageMutation"] = None
            writer.validate_record(valid)
        state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS reject: both reviewers enforce exact eight-domain digest-key coverage")

        # Reviewer identity format is checked independently for each review role,
        # before an otherwise-valid payload could be accepted by digest comparison.
        for review_type, state_field in (("SECURITY", "securityReviewer"), ("OPERABILITY", "operabilityReviewer")):
            canonical_reviewer = state[state_field]
            for label, invalid in (
                ("empty", ""),
                ("short", "ab"),
                ("uppercase", "ReviewerUpper"),
                ("whitespace", "reviewer person"),
                ("boolean", True),
                ("overlong", "r" * 65),
            ):
                case = f"{review_type} invalid reviewer pseudonym: {label}"
                EXPECTED_DIAGNOSTICS[case] = f"{review_type} reviewerPseudonym invalid"
                state[state_field] = invalid
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state[state_field] = canonical_reviewer
            writer.validate_record(valid)

        state["reviewTarget"] = "SECURITY"
        state["reviewTypeOverride"] = "OPERABILITY"
        EXPECTED_DIAGNOSTICS["security review type mismatch"] = "SECURITY review type mismatch"
        try:
            expect_rejected("security review type mismatch", lambda: writer.validate_record(valid))
        finally:
            state["reviewTypeOverride"] = None
            state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS reject: both reviewer pseudonym formats and SECURITY review type are fail-closed")

        # A PASS domain/review cannot smuggle unknown schema keys or omit required keys.
        # Exercise the exact payload field-set gate for every domain and both review roles.
        for domain in contract["requiredDomains"]:
            state["domainTarget"] = domain
            for mutation, differing_key in (("MISSING", "schemaVersion"), ("EXTRA", "unexpectedField")):
                case = f"domain {domain} payload field-set {mutation.lower()}"
                EXPECTED_DIAGNOSTICS[case] = f"domain {domain} evidence field set drift: ['{differing_key}']"
                state["domainFieldMutation"] = mutation
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state["domainFieldMutation"] = None
        state["domainTarget"] = None
        writer.validate_record(valid)
        for review_type in ("SECURITY", "OPERABILITY"):
            state["reviewTarget"] = review_type
            for mutation, differing_key in (("MISSING", "schemaVersion"), ("EXTRA", "unexpectedField")):
                case = f"{review_type} review payload field-set {mutation.lower()}"
                EXPECTED_DIAGNOSTICS[case] = f"{review_type} review field set drift: ['{differing_key}']"
                state["reviewFieldMutation"] = mutation
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state["reviewFieldMutation"] = None
            writer.validate_record(valid)
        state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS reject: all eight typed domains and both reviews enforce exact payload field sets")

        # Correct field sets cannot excuse obsolete domain/review schema versions.
        for domain in contract["requiredDomains"]:
            case = f"domain {domain} evidence obsolete schema version"
            EXPECTED_DIAGNOSTICS[case] = f"domain {domain} evidence schemaVersion drift"
            state["domainTarget"] = domain
            state["domainSchemaMutation"] = True
            try:
                expect_rejected(case, lambda: writer.validate_record(valid))
            finally:
                state["domainSchemaMutation"] = False
        state["domainTarget"] = None
        writer.validate_record(valid)
        for review_type in ("SECURITY", "OPERABILITY"):
            case = f"{review_type} review obsolete schema version"
            EXPECTED_DIAGNOSTICS[case] = f"{review_type} review schemaVersion drift"
            state["reviewTarget"] = review_type
            state["reviewSchemaMutation"] = True
            try:
                expect_rejected(case, lambda: writer.validate_record(valid))
            finally:
                state["reviewSchemaMutation"] = False
            writer.validate_record(valid)
        state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS reject: all eight domains and both reviews reject obsolete schema versions")

        # The exact bundle/digest checks must reject malformed types and duplicate
        # refs before a superficially approved review can reach candidate admission.
        for review_type in ("SECURITY", "OPERABILITY"):
            state["reviewTarget"] = review_type
            for mutation in ("DUPLICATE", "NON_LIST"):
                case = f"{review_type} malformed reviewed refs: {mutation.lower()}"
                EXPECTED_DIAGNOSTICS[case] = f"{review_type} reviewedDomainEvidenceRefs invalid"
                state["reviewRefsMutation"] = mutation
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state["reviewRefsMutation"] = None
            for mutation in ("BAD_HEX", "BOOLEAN"):
                case = f"{review_type} malformed reviewed digest: {mutation.lower()}"
                EXPECTED_DIAGNOSTICS[case] = f"{review_type} reviewedDomainEvidenceSha256 invalid"
                state["reviewDigestValueMutation"] = mutation
                try:
                    expect_rejected(case, lambda: writer.validate_record(valid))
                finally:
                    state["reviewDigestValueMutation"] = None
            writer.validate_record(valid)
        state["reviewTarget"] = "BOTH"
        writer.validate_record(valid)
        print("PASS reject: both reviews reject duplicate/nonlist refs and invalid digest value types")

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
        drift = copy.deepcopy(empty_registry); drift["productionEvidence"] = True
        expect_rejected("typed writer production evidence drift before append", lambda: writer.validate_registry_for_append(drift))
        drift = copy.deepcopy(empty_registry); drift["productionReady"] = True
        expect_rejected("typed writer production ready drift before append", lambda: writer.validate_registry_for_append(drift))

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

        # Positive/negative controls for collision protection live entirely in the temp fixture.
        occupied = Path(tmp) / "occupied-negative-fixture.json"
        occupied.write_bytes(b"sentinel")
        try:
            require_fixture_path_vacant(occupied)
        except Fail as exc:
            require(str(exc) == f"negative fixture path already occupied: {occupied}", "occupied-file collision diagnostic drift")
            require(occupied.read_bytes() == b"sentinel", "occupied fixture file was changed")
            print("PASS reject: occupied negative fixture file is preserved")
        else:
            raise Fail("occupied negative fixture file unexpectedly accepted")
        dangling = Path(tmp) / "occupied-dangling-symlink"
        dangling.symlink_to(Path(tmp) / "missing-target")
        try:
            try:
                require_fixture_path_vacant(dangling)
            except Fail as exc:
                require(str(exc) == f"negative fixture path already occupied: {dangling}", "dangling-symlink collision diagnostic drift")
                require(dangling.is_symlink(), "dangling symlink was changed")
                print("PASS reject: dangling negative fixture symlink is preserved")
            else:
                raise Fail("dangling negative fixture symlink unexpectedly accepted")
        finally:
            dangling.unlink()

        # Isolated controls never touch repository evidence authorities.
        isolated_root = Path(tmp) / "isolated-fixture-root"
        isolated_parent = isolated_root / "evidence"
        isolated_parent.mkdir(parents=True)
        parent_identity = require_fixture_parent_canonical(isolated_parent, isolated_root)
        require(parent_identity == (isolated_parent.stat().st_dev, isolated_parent.stat().st_ino),
                "isolated fixture parent identity drift")
        for rejected_parent, expected_diagnostic in (
            (isolated_root / "missing", "negative fixture parent missing or symlinked"),
            (Path(tmp), "negative fixture parent escapes canonical root"),
        ):
            try:
                require_fixture_parent_canonical(rejected_parent, isolated_root)
            except Fail as exc:
                require(str(exc) == expected_diagnostic, "fixture parent rejection diagnostic drift")
            else:
                raise Fail("unsafe negative fixture parent unexpectedly accepted")
        outside_parent = Path(tmp) / "external-parent"
        outside_parent.mkdir()
        alias_parent = isolated_root / "alias"
        alias_parent.symlink_to(outside_parent, target_is_directory=True)
        try:
            try:
                require_fixture_parent_canonical(alias_parent, isolated_root)
            except Fail as exc:
                require(str(exc) == "negative fixture parent missing or symlinked",
                        "symlinked fixture parent rejection diagnostic drift")
                require(alias_parent.is_symlink() and alias_parent.resolve() == outside_parent.resolve(),
                        "isolated symlinked parent was changed")
                print("PASS reject: symlinked negative fixture parent cannot redirect evidence")
            else:
                raise Fail("symlinked negative fixture parent unexpectedly accepted")
        finally:
            alias_parent.unlink()

        external_evidence = Path(tmp) / "external-evidence.json"
        external_evidence.write_text("{}\n", encoding="utf-8")
        symlink_ref = prefixes[domain_name] + "negative-external-symlink.json"
        symlink_path = ROOT / symlink_ref
        canonical_parent_identity = require_fixture_parent_canonical(symlink_path.parent)
        require_fixture_path_vacant(symlink_path)
        created_symlink = False
        try:
            symlink_path.symlink_to(external_evidence)
            created_symlink = True
            created_identity = symlink_path.lstat()
            expect_rejected("writer repo-local evidence symlink escaping repository", lambda: writer.repo_ref(symlink_ref, f"domains.{domain_name}.evidenceRef"))
        finally:
            if created_symlink:
                require(require_fixture_parent_canonical(symlink_path.parent) == canonical_parent_identity,
                        "negative fixture parent identity drift before cleanup")
                current_identity = symlink_path.lstat()
                require((current_identity.st_dev, current_identity.st_ino) ==
                        (created_identity.st_dev, created_identity.st_ino),
                        "negative fixture symlink inode drift before cleanup")
                require(symlink_path.is_symlink() and symlink_path.resolve() == external_evidence.resolve(), "negative fixture symlink identity drift before cleanup")
                symlink_path.unlink()

        missing_file = copy.deepcopy(valid); missing_file["recordId"] = "brnr_missing_evidence_file"
        expect_rejected("typed evidence file must exist", lambda: writer.validate_record(missing_file))

    print("Memory OS backup/restore non-resurrection negative admission suite PASS")
    print("typed domain and independent review evidence are generation/commit/bundle/digest bound: true")
    print("typed record immutably binds review payload digests: true")
    print("typed production boundaries fail closed across record/domain/review/registry: true")
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
