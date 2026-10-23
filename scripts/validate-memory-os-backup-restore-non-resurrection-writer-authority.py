#!/usr/bin/env python3
"""Prove the typed non-resurrection writer CLI cannot substitute production authorities."""
from __future__ import annotations

import ast
import importlib.util
import inspect
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_typed_non_resurrection_writer_authority", WRITER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(writer: Any, field: str, substitute: Path) -> None:
    original = getattr(writer, field)
    try:
        setattr(writer, field, substitute)
        try:
            writer.require_cli_authorities()
        except writer.Fail:
            return
        raise NegativeFailure(f"typed non-resurrection writer accepted {field} CLI authority substitution")
    finally:
        setattr(writer, field, original)


def require_canonical_lock_parent(parent: Path, root: Path = ROOT) -> tuple[int, int]:
    try:
        relative = parent.relative_to(root)
    except ValueError as exc:
        raise NegativeFailure("typed negative lock parent escapes fixture root") from exc
    require(root.is_dir() and not root.is_symlink(),
            "typed negative lock fixture root missing or symlinked")
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        require(cursor.is_dir() and not cursor.is_symlink(),
                "typed negative lock parent missing or symlinked")
    require(parent.resolve(strict=True) == root.resolve(strict=True) / relative,
            "typed negative lock parent canonical resolution drift")
    parent_stat = parent.stat()
    return parent_stat.st_dev, parent_stat.st_ino


def require_owned_lock_symlink(lock: Path, target: Path, leaf_identity: tuple[int, int],
                               parent_identity: tuple[int, int], root: Path = ROOT) -> None:
    require(require_canonical_lock_parent(lock.parent, root) == parent_identity,
            "typed negative lock parent identity drift")
    require(lock.is_symlink() and lock.resolve() == target.resolve(),
            "typed negative lock symlink target drift")
    leaf_stat = lock.lstat()
    require((leaf_stat.st_dev, leaf_stat.st_ino) == leaf_identity,
            "typed negative lock symlink identity drift")


def prove_materialized_lock_symlink_fails_closed(writer: Any) -> None:
    lock = writer.LOCK
    require(lock == ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock",
            "typed non-resurrection canonical lock path drift")
    require(not lock.exists() and not lock.is_symlink(),
            "typed non-resurrection canonical lock must be absent before symlink negative")
    with tempfile.TemporaryDirectory(prefix="memory-os-typed-lock-negative-") as temp_dir:
        target = Path(temp_dir) / "outside.lock"
        target.write_bytes(b"outside-lock-target\n")
        before = target.read_bytes()
        parent_identity = require_canonical_lock_parent(lock.parent)
        lock.symlink_to(target)
        leaf_stat = lock.lstat()
        leaf_identity = (leaf_stat.st_dev, leaf_stat.st_ino)
        try:
            try:
                writer.os.open(lock, writer.os.O_WRONLY | writer.os.O_CREAT | writer.os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                raise NegativeFailure("typed non-resurrection writer lock flags followed a materialized symlink")
            require_owned_lock_symlink(lock, target, leaf_identity, parent_identity)
            require(target.read_bytes() == before,
                    "typed non-resurrection lock symlink rejection mutated external target")
        finally:
            # Never delete a lock path whose parent or symlink inode was replaced.
            require_owned_lock_symlink(lock, target, leaf_identity, parent_identity)
            lock.unlink()

        # A symlinked ancestor must not redirect even a still-vacant lock leaf.
        isolated_root = Path(temp_dir) / "isolated-root"
        isolated_root.mkdir()
        external_parent = Path(temp_dir) / "external-lock-parent"
        external_parent.mkdir()
        alias_parent = isolated_root / "alias"
        alias_parent.symlink_to(external_parent, target_is_directory=True)
        try:
            try:
                require_canonical_lock_parent(alias_parent, isolated_root)
            except NegativeFailure as exc:
                require(str(exc) == "typed negative lock parent missing or symlinked",
                        "typed lock parent-alias diagnostic drift")
                require(alias_parent.is_symlink() and alias_parent.resolve() == external_parent.resolve(),
                        "isolated lock parent alias changed")
                print("PASS reject: typed lock fixture symlinked parent")
            else:
                raise NegativeFailure("typed lock fixture symlinked parent unexpectedly accepted")
        finally:
            alias_parent.unlink()

        # A same-target replacement must not count as ownership of the original inode.
        isolated_link = Path(temp_dir) / "isolated-owned-link"
        isolated_replacement = Path(temp_dir) / "isolated-replacement-link"
        isolated_parent_stat = isolated_link.parent.stat()
        isolated_parent_identity = (isolated_parent_stat.st_dev, isolated_parent_stat.st_ino)
        isolated_link.symlink_to(target)
        original = isolated_link.lstat()
        isolated_replacement.symlink_to(target)
        isolated_replacement.replace(isolated_link)
        try:
            require_owned_lock_symlink(isolated_link, target,
                                      (original.st_dev, original.st_ino), isolated_parent_identity,
                                      root=Path(temp_dir))
        except NegativeFailure as exc:
            require(str(exc) == "typed negative lock symlink identity drift",
                    "typed lock replacement diagnostic drift")
            print("PASS reject: same-target symlink replacement is not fixture ownership")
        else:
            raise NegativeFailure("same-target symlink replacement unexpectedly accepted")
        finally:
            isolated_link.unlink()
    require(not lock.exists() and not lock.is_symlink(),
            "typed non-resurrection lock symlink negative left canonical lock materialized")


def require_direct_first_guard(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise NegativeFailure("writer main source syntax invalid") from exc
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
            and tree.body[0].name == "main",
            "writer main must be one synchronous definition")
    statements = tree.body[0].body
    require(bool(statements) and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Call)
            and isinstance(statements[0].value.func, ast.Name)
            and statements[0].value.func.id == "require_cli_authorities"
            and not statements[0].value.args and not statements[0].value.keywords,
            "writer main must begin with direct CLI authority guard")


def prove_guard_source_classifier() -> None:
    valid = "def main():\n    require_cli_authorities()\n    parser = argparse.ArgumentParser()\n"
    require_direct_first_guard(valid)
    negatives = (
        ("comment", "def main():\n    # require_cli_authorities()\n    parser = argparse.ArgumentParser()\n"),
        ("string", "def main():\n    'require_cli_authorities()'\n    parser = argparse.ArgumentParser()\n"),
        ("dead", "def main():\n    if False:\n        require_cli_authorities()\n    parser = argparse.ArgumentParser()\n"),
        ("early-return", "def main():\n    return 0\n    require_cli_authorities()\n"),
        ("async", "async def main():\n    require_cli_authorities()\n"),
    )
    for label, source in negatives:
        try:
            require_direct_first_guard(source)
        except NegativeFailure as exc:
            expected = ("writer main must be one synchronous definition" if label == "async"
                        else "writer main must begin with direct CLI authority guard")
            require(str(exc) == expected, f"writer entrypoint {label} diagnostic drift")
        else:
            raise NegativeFailure(f"writer entrypoint {label} bypass unexpectedly accepted")
    print("PASS reject: comment/string/dead/early-return/async CLI guard substitutes")


def main() -> int:
    prove_guard_source_classifier()
    writer = load_writer()
    guard = getattr(writer, "require_cli_authorities", None)
    require(callable(guard), "typed non-resurrection writer CLI authority guard missing")

    main_source = inspect.getsource(writer.main)
    require_direct_first_guard(main_source)
    guard_offset = main_source.find("require_cli_authorities()")
    parser_offset = main_source.find("argparse.ArgumentParser")
    lock_open_offset = main_source.find("os.O_CREAT | os.O_EXCL")
    require(guard_offset >= 0, "typed non-resurrection writer main does not invoke CLI authority guard")
    require(parser_offset >= 0 and guard_offset < parser_offset,
            "typed non-resurrection writer must validate CLI authority before parsing input")
    require(lock_open_offset >= 0 and parser_offset < lock_open_offset,
            "typed non-resurrection writer must retain exclusive-create lock semantics")

    writer.require_cli_authorities()
    contract_before = writer.CANONICAL_CONTRACT.read_bytes()
    registry_before = writer.CANONICAL_REGISTRY.read_bytes()
    generation_before = writer.CANONICAL_GEN_EVIDENCE_REGISTRY.read_bytes()

    substitutions = (
        ("CONTRACT", writer.CANONICAL_REGISTRY),
        ("REGISTRY", writer.CANONICAL_CONTRACT),
        ("GEN_EVIDENCE_REGISTRY", writer.CANONICAL_REGISTRY),
        ("GEN_WRITER", ROOT / "scripts/request-memory-os-backup-restore-drill.py"),
        ("LOCK", ROOT / "contracts/operations/.backup-restore-non-resurrection-admission-alternate.lock"),
    )
    for field, substitute in substitutions:
        expect_rejected(writer, field, substitute)

    prove_materialized_lock_symlink_fails_closed(writer)
    writer.require_cli_authorities()
    require(writer.CANONICAL_CONTRACT.read_bytes() == contract_before,
            "typed writer CLI authority rejection mutated canonical contract")
    require(writer.CANONICAL_REGISTRY.read_bytes() == registry_before,
            "typed writer CLI authority rejection mutated canonical registry")
    require(writer.CANONICAL_GEN_EVIDENCE_REGISTRY.read_bytes() == generation_before,
            "typed writer CLI authority rejection mutated generation evidence registry")

    print("Memory OS typed non-resurrection writer CLI authority negative PASS")
    print("canonical typed evidence authorities substitution-rejected: true")
    print("CLI authority guard executes before input parsing: true")
    print("materialized lock symlink rejected by exclusive-create semantics: true")
    print("external lock target mutated: false")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"TYPED NON-RESURRECTION WRITER AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
