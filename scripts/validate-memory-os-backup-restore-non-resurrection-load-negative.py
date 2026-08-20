#!/usr/bin/env python3
"""Prove typed non-resurrection authority loading and reconcile rollback fail closed."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-non-resurrection-authority.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def prove_reconcile_operability_rollback() -> None:
    require(RECONCILER.is_file(), "typed non-resurrection reconciler missing")
    reconciler = load_module(RECONCILER, "memory_os_typed_non_resurrection_reconcile_rollback_negative")
    with tempfile.TemporaryDirectory(prefix=".tmp-typed-reconcile-rollback-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        paths: dict[str, Path] = {}
        for attr in ("REGISTRY", "GEN_REGISTRY", "CONTRACT", "STATUS"):
            source = getattr(reconciler, attr)
            target = tmp / source.name
            shutil.copyfile(source, target)
            paths[attr] = target

        pass_validator = tmp / "pass-validator.py"
        pass_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8")
        fail_validator = tmp / "fail-validator.py"
        fail_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(47)\n", encoding="utf-8")

        originals: dict[str, Any] = {attr: getattr(reconciler, attr) for attr in paths}
        originals["VALIDATOR"] = reconciler.VALIDATOR
        originals["OPERABILITY_VALIDATOR"] = reconciler.OPERABILITY_VALIDATOR
        before = {attr: path.read_bytes() for attr, path in paths.items()}
        try:
            for attr, path in paths.items():
                setattr(reconciler, attr, path)
            reconciler.VALIDATOR = pass_validator
            reconciler.OPERABILITY_VALIDATOR = fail_validator
            expect_domain_fail(
                "typed recovery operability aggregate failure",
                reconciler.main,
                reconciler.Fail,
            )
            for attr, path in paths.items():
                require(path.read_bytes() == before[attr], f"{attr} drift after operability rollback")
        finally:
            for attr, value in originals.items():
                setattr(reconciler, attr, value)

    print("PASS rollback: typed recovery authority restored byte-for-byte after operability failure")


def main() -> int:
    require(WRITER.is_file(), "typed evidence writer missing")
    require(VALIDATOR.is_file(), "typed admission validator missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    writer = load_module(WRITER, "memory_os_typed_non_resurrection_writer_load_negative")
    validator = load_module(VALIDATOR, "memory_os_typed_non_resurrection_load_negative")
    require(writer.canonical_repo_file(WRITER, "typed evidence writer") == WRITER, "canonical typed writer path rejected")

    original_lock = writer.LOCK
    original_validator_loader = validator.load_module
    try:
        writer.LOCK = ROOT / "contracts/operations/.backup-restore-generation-evidence.lock"
        def substituted_loader(path: Path, name: str):
            if path == WRITER:
                return writer
            return original_validator_loader(path, name)
        validator.load_module = substituted_loader
        expect_domain_fail("typed writer append lock authority substitution", validator.main, validator.Fail)
    finally:
        writer.LOCK = original_lock
        validator.load_module = original_validator_loader

    with tempfile.TemporaryDirectory(prefix=".tmp-typed-load-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 typed authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)
        expect_domain_fail("invalid UTF-8 typed writer input", lambda: writer.load(invalid_utf8), writer.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("typed authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)
        expect_domain_fail("typed writer input path is unreadable directory", lambda: writer.load(directory_authority), writer.Fail)

        ref_loop = tmp / "loop-evidence-ref.json"
        ref_loop.symlink_to(ref_loop.name)
        ref_loop_relative = ref_loop.relative_to(ROOT).as_posix()
        expect_domain_fail(
            "typed evidence repository ref symlink loop",
            lambda: writer.repo_ref(ref_loop_relative, "negativeEvidenceRef"),
            writer.Fail,
        )

        with tempfile.TemporaryDirectory(prefix="memory-os-typed-writer-outside-") as outside_dirname:
            outside_dir = Path(outside_dirname)
            outside_writer = outside_dir / "outside-generation-writer.py"
            outside_writer.write_text("VALUE = 1\n", encoding="utf-8")
            escaped_link = tmp / "escaped-generation-writer.py"
            escaped_link.symlink_to(outside_writer)
            loop_link = tmp / "loop-generation-writer.py"
            loop_link.symlink_to(loop_link.name)

            original_generation_writer = writer.GEN_WRITER
            try:
                writer.GEN_WRITER = outside_writer
                expect_domain_fail("generation writer absolute path escapes repository", writer.load_generation_writer, writer.Fail)
                writer.GEN_WRITER = escaped_link
                expect_domain_fail("generation writer repository symlink escapes repository", writer.load_generation_writer, writer.Fail)
                writer.GEN_WRITER = loop_link
                expect_domain_fail("generation writer repository symlink loop", writer.load_generation_writer, writer.Fail)
            finally:
                writer.GEN_WRITER = original_generation_writer

            outside_json = outside_dir / "outside-authority.json"
            outside_json.write_text("{}\n", encoding="utf-8")
            escaped_authority = tmp / "escaped-canonical-authority.json"
            escaped_authority.symlink_to(outside_json)
            loop_authority = tmp / "loop-canonical-authority.json"
            loop_authority.symlink_to(loop_authority.name)

            for field in (
                "typed non-resurrection contract",
                "typed non-resurrection registry",
                "generation evidence registry",
            ):
                expect_domain_fail(
                    f"{field} repository symlink escapes repository",
                    lambda field=field: writer.require_canonical_runtime_authority(escaped_authority, escaped_authority, field),
                    writer.Fail,
                )
                expect_domain_fail(
                    f"{field} repository symlink loop",
                    lambda field=field: writer.require_canonical_runtime_authority(loop_authority, loop_authority, field),
                    writer.Fail,
                )

    prove_reconcile_operability_rollback()

    print("Typed unreadable/escaped-authority negative suite PASS")
    print("canonical typed contract/registry/generation registry containment: enforced")
    print("typed append lock authority substitution accepted: false")
    print("typed operability failure leaves partial authority: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
