#!/usr/bin/env python3
"""Negative checks for admission authority path containment."""

from __future__ import annotations

import fnmatch
import json
import hashlib
import subprocess
import importlib.util
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-admission-authority-linkage.py"
WORKFLOW_PATH = ROOT / ".github/workflows/admission-authority-linkage.yml"


def load_validator():
    spec = importlib.util.spec_from_file_location("admission_authority_linkage_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load admission authority linkage validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_entry_fail(module, value: str, *, directory: bool, contains: str) -> None:
    try:
        module.repository_entry(value, "negative.fixture", directory=directory)
    except module.Fail as exc:
        if contains not in str(exc):
            raise AssertionError(f"unexpected failure for {value}: {exc}") from exc
    else:
        raise AssertionError(f"unsafe authority path unexpectedly accepted: {value}")


def expect_slot_fail(module, value: str, *, contains: str) -> None:
    try:
        module.repository_file_slot(value, "negative.appendLockPath")
    except module.Fail as exc:
        if contains not in str(exc):
            raise AssertionError(f"unexpected slot failure for {value}: {exc}") from exc
    else:
        raise AssertionError(f"unsafe authority file slot unexpectedly accepted: {value}")


def workflow_path_patterns(section: str) -> set[str]:
    patterns: set[str] = set()
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith('- "') and stripped.endswith('"'):
            patterns.add(stripped[3:-1])
    return patterns


def validate_workflow_trigger_coverage(required_contracts: set[str]) -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    try:
        pull_section = text.split("  pull_request:\n", 1)[1].split("  push:\n", 1)[0]
        push_section = text.split("  push:\n", 1)[1].split("  workflow_dispatch:\n", 1)[0]
    except (IndexError, ValueError) as exc:
        raise AssertionError("unable to parse admission linkage workflow trigger sections") from exc
    required_paths = required_contracts | {
        ".github/workflows/admission-authority-linkage.yml",
        "scripts/validate-memory-os-admission-authority-linkage.py",
        "scripts/validate-memory-os-admission-authority-linkage-negative.py",
    }
    for trigger, section in (("pull_request", pull_section), ("push", push_section)):
        patterns = workflow_path_patterns(section)
        missing = sorted(
            path for path in required_paths
            if not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)
        )
        if missing:
            raise AssertionError(f"{trigger} does not cover admission linkage authorities: {missing}")


def validate_atomic_diagnostic_publication() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    required_fragments = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
        "if path.is_symlink():",
        "raw validator log suppressed",
        "REDACTED: admission linkage validation failed; raw output withheld",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise AssertionError(f"linkage diagnostic publication is not crash-safe: missing {missing}")
    if "path.write_text(json.dumps(value" in text:
        raise AssertionError("linkage diagnostic publication regressed to direct write_text")



REVIEWED_LINKAGE_WORKFLOW_BLOB_SHA = "454db6f547eae4e6c0c779c71566bbb6f65f1bda"


def prove_linkage_workflow_source() -> None:
    """Authenticate reviewed executable workflow and bounded branch predicates."""
    if not WORKFLOW_PATH.is_file() or WORKFLOW_PATH.is_symlink():
        raise AssertionError("admission linkage workflow missing or substituted")
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    required = (
        ("PR target", "  pull_request:\n    branches: [so]\n", 1),
        ("checkout", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 2),
        ("setup", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 2),
        ("PR creds", "          persist-credentials: false\n", 1),
        ("publisher creds", "          persist-credentials: true\n", 1),
        ("PR base env", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
        ("PR base guard", "          test \"${PR_BASE_REF:-}\" = \"so\"\n", 1),
        ("publisher job if", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
        ("publisher ref", "          test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", 1),
        ("SHA", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", 2),
        ("HEAD", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", 2),
        ("self guard", "          python scripts/validate-memory-os-admission-authority-linkage-negative.py", 2),
    )
    for label, token, count in required:
        if source.count(token) != count:
            raise AssertionError("admission linkage workflow source drift: " + label)

    def enforce_digest(value: str) -> None:
        payload = value.encode("utf-8")
        blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(blob).hexdigest() != REVIEWED_LINKAGE_WORKFLOW_BLOB_SHA:
            raise AssertionError("admission linkage complete workflow source drift")

    enforce_digest(source)
    mutations = (
        ("PR target", "  pull_request:\n    branches: [so]\n", "  pull_request:\n    branches: [main]\n"),
        ("PR base", "          test \"${PR_BASE_REF:-}\" = \"so\"\n", "          test -n \"${PR_BASE_REF:-}\"\n"),
        ("PR base env", "          PR_BASE_REF: ${{ github.base_ref }}\n", ""),
        ("checkout pin", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", "      - uses: actions/checkout@v4\n"),
        ("setup pin", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", "      - uses: actions/setup-python@v5\n"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("publisher credentials", "          persist-credentials: true\n", "          persist-credentials: false\n"),
        ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", "    if: github.event_name != 'pull_request'\n"),
        ("publisher ref", "          test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", "          true # bypass ref\n"),
        ("SHA format", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", "          test -n \"$expected\"\n"),
        ("HEAD identity", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", ""),
        ("guard execution", "          python scripts/validate-memory-os-admission-authority-linkage-negative.py", ""),
        ("injected shell", "          python scripts/validate-memory-os-admission-authority-linkage.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-admission-authority-linkage.py\n"),
        ("injected action", "      - name: Validate admission authority links read-only\n", "      - uses: unreviewed/action@v1\n      - name: Validate admission authority links read-only\n"),
        ("removed PR self-trigger", "      - \"scripts/validate-memory-os-admission-authority-linkage-negative.py\"\n", ""),
        ("diagnostic symlink guard", "          if path.is_symlink():\n", ""),
    )
    if len(mutations) != 16:
        raise AssertionError("admission linkage workflow negative inventory drift")
    for label, before, after in mutations:
        if before not in source:
            raise AssertionError("admission linkage negative anchor missing: " + label)
        mutated = source.replace(before, after, 1)
        if mutated == source:
            raise AssertionError("admission linkage negative fixture unchanged: " + label)
        try:
            enforce_digest(mutated)
        except AssertionError:
            pass
        else:
            raise AssertionError("admission linkage accepted forbidden mutation: " + label)

    cases = (
        ("PR so", required[6][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", required[6][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", required[6][1].strip(), "PR_BASE_REF", "", False),
        ("push so", required[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", required[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", required[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise AssertionError("admission linkage workflow runtime branch drift: " + label)
    print("PASS: admission linkage workflow PR/push branch guard runtime (6 cases)")
    print("PASS: admission linkage workflow source admission (16 negatives)")



def prove_linkage_diagnostic_runtime() -> None:
    """Execute the real failure writer against mode, redaction and I/O fault fixtures."""
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    marker = "      - name: Record privacy-safe linkage diagnostic\n"
    start, end = "          python - <<'PY'\n", "          PY\n"
    if source.count(marker) != 1:
        raise AssertionError("admission linkage diagnostic step is not unique")
    section = source.split(marker, 1)[1]
    if section.count(start) != 1 or end not in section:
        raise AssertionError("admission linkage diagnostic inline writer extraction drift")
    inline = section.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="admission-linkage-diagnostic-runtime-") as temp:
        root = Path(temp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "--allow-empty", "-qm", "fixture"],
                       cwd=root, check=True, capture_output=True)
        expected_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        path = root / "docs/fixtures/memory-os-operability/admission-authority-linkage-diagnostic.last.json"
        path.parent.mkdir(parents=True)
        previous = b'{"previous": "preserve"}\n'
        env = os.environ.copy()
        env.update({"LINKAGE_EXIT_CODE": "23", "SENSITIVE_CANARY": "CANARY_LINKAGE_MUST_NOT_PERSIST"})

        def run(program: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "-c", program], cwd=root, env=env,
                                  capture_output=True, text=True, timeout=15, check=False)

        def clean(label: str) -> None:
            if list(path.parent.glob(".admission-authority-linkage-diagnostic.last.json.*.tmp")):
                raise AssertionError("admission linkage diagnostic temporary file leaked: " + label)

        path.write_bytes(previous)
        path.chmod(0o640)
        success = run(script)
        if success.returncode:
            raise AssertionError("admission linkage diagnostic positive failed: " + success.stderr[-400:])
        payload = path.read_text(encoding="utf-8")
        value = json.loads(payload)
        if (set(value) != {"schemaVersion", "workflow", "result", "sourceCommitSha", "exitCode",
                           "output", "containsSecrets", "productionEvidence", "productionReady"}
                or value["schemaVersion"] != "memory-os-validator-diagnostic.v1"
                or value["workflow"] != "admission-authority-linkage" or value["result"] != "FAIL"
                or value["sourceCommitSha"] != expected_sha or value["exitCode"] != 23
                or value["output"] != "REDACTED: admission linkage validation failed; raw output withheld"
                or value["containsSecrets"] is not False or value["productionEvidence"] is not False
                or value["productionReady"] is not False or "CANARY_LINKAGE" in payload):
            raise AssertionError("admission linkage diagnostic privacy/authority drift")
        if stat.S_IMODE(path.stat().st_mode) != 0o640:
            raise AssertionError("admission linkage diagnostic failed to preserve mode")
        clean("positive")
        saved = path.read_bytes()
        for label, anchor in (("replace", "os.replace(tmp_name, path)"),
                              ("fsync", "os.fsync(handle.fileno())")):
            if script.count(anchor) != 1:
                raise AssertionError("admission linkage diagnostic fault anchor drift: " + label)
            injection = "raise OSError('synthetic admission linkage " + label + " failure')"
            outcome = run(script.replace(anchor, injection, 1))
            if outcome.returncode == 0 or "synthetic admission linkage " + label + " failure" not in outcome.stderr:
                raise AssertionError("admission linkage diagnostic fault was not reached: " + label)
            if path.read_bytes() != saved or stat.S_IMODE(path.stat().st_mode) != 0o640:
                raise AssertionError("admission linkage diagnostic fault altered previous bytes/mode: " + label)
            clean(label)
        outside = root / "external-canary"
        outside.write_bytes(b"EXTERNAL_LINKAGE_CANARY")
        path.unlink()
        path.symlink_to(outside)
        outcome = run(script)
        if outcome.returncode == 0 or "target must not be a symlink" not in outcome.stderr:
            raise AssertionError("admission linkage diagnostic accepted symlink target")
        if not path.is_symlink() or outside.read_bytes() != b"EXTERNAL_LINKAGE_CANARY":
            raise AssertionError("admission linkage diagnostic followed external symlink")
        clean("symlink")
    print("PASS: admission linkage diagnostic redaction/atomic runtime (4 cases)")


def main() -> int:
    prove_linkage_workflow_source()
    module = load_validator()
    required_contracts = {
        "contracts/operations/migration-production-shaped-admission-contract.v1.json",
        "contracts/operations/release-baseline-registry-contract.v1.json",
        "contracts/operations/release-compatibility-pair-contract.v1.json",
        "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
        "contracts/operations/incident-contact-routing-admission-contract.v1.json",
        "contracts/operations/observability-stack-deployment-contract.v1.json",
        "contracts/operations/rate-limit-distributed-runtime-admission-contract.v1.json",
        "contracts/operations/deletion-worker-host-failure-contract.v1.json",
        "contracts/operations/backup-restore-generation-binding-contract.v1.json",
        "contracts/operations/client-baseline-registry-contract.v1.json",
        "contracts/operations/production-shaped-failure-drill-contract.v1.json",
        "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    }
    missing_contracts = sorted(required_contracts - set(module.CONTRACTS))
    if missing_contracts:
        raise AssertionError(f"high-impact admission contracts are not covered: {missing_contracts}")
    validate_workflow_trigger_coverage(required_contracts)
    required_file_keys = {
        "sourceReleasePairRegistry",
        "registry",
        "releaseRegistry",
        "independentReviewValidator",
        "independentReviewNegativeValidator",
        "environmentRecordSemanticValidator",
        "generationRegistryRecordSchema",
        "negativeAdmissionValidator",
    }
    missing = sorted(required_file_keys - module.FILE_KEYS)
    if missing:
        raise AssertionError(f"high-impact admission linkage keys are not covered: {missing}")
    validate_atomic_diagnostic_publication()
    prove_linkage_diagnostic_runtime()
    fixture = ROOT / f".tmp-admission-authority-linkage-negative-{os.getpid()}"
    external_root = Path(tempfile.mkdtemp(prefix="memory-os-linkage-negative-"))
    try:
        fixture.mkdir(parents=True, exist_ok=False)
        normal = fixture / "normal.txt"
        normal.write_text("safe\n", encoding="utf-8")
        module.repository_entry(str(normal.relative_to(ROOT)), "negative.normal", directory=False)
        module.repository_file_slot(str((fixture / ".safe.lock").relative_to(ROOT)), "negative.safeLock")

        expect_entry_fail(module, ".", directory=True, contains="unsafe linked path")

        final_link = fixture / "final-link.txt"
        final_link.symlink_to(normal.name)
        expect_entry_fail(
            module,
            str(final_link.relative_to(ROOT)),
            directory=False,
            contains="symlinked admission authority path",
        )

        external_file = external_root / "payload.txt"
        external_file.write_text("outside\n", encoding="utf-8")
        parent_link = fixture / "external"
        parent_link.symlink_to(external_root, target_is_directory=True)
        expect_entry_fail(
            module,
            str((parent_link / external_file.name).relative_to(ROOT)),
            directory=False,
            contains="symlinked admission authority path",
        )
        expect_slot_fail(
            module,
            str((parent_link / ".escaped.lock").relative_to(ROOT)),
            contains="symlinked admission authority path",
        )

        external_dir = external_root / "directory"
        external_dir.mkdir()
        directory_link = fixture / "external-directory"
        directory_link.symlink_to(external_dir, target_is_directory=True)
        expect_entry_fail(
            module,
            str(directory_link.relative_to(ROOT)),
            directory=True,
            contains="symlinked admission authority path",
        )

        expect_slot_fail(module, "../outside.lock", contains="unsafe linked path")
        expect_slot_fail(module, ".", contains="unsafe linked path")

        lock_target = fixture / "real.lock"
        lock_target.write_text("lock\n", encoding="utf-8")
        lock_link = fixture / "alias.lock"
        lock_link.symlink_to(lock_target.name)
        expect_slot_fail(
            module,
            str(lock_link.relative_to(ROOT)),
            contains="symlinked admission authority file slot",
        )

        print("PASS: admission authority paths and atomic diagnostic publication remain fail-closed")
        return 0
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
        shutil.rmtree(external_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
