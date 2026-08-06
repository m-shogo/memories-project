#!/usr/bin/env python3
"""Connect the canonical version validator to bounded foundation validation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/validate-memory-os-version-compatibility.py"
OLD_IMPORT = "import json\nimport sys\n"
NEW_IMPORT = "import json\nimport subprocess\nimport sys\n"
MARKER = '    print("Memory OS version compatibility validation PASS")\n'
SENTINEL = "integrated compatibility foundation validation failed"
INJECTED = "\n".join([
    "    foundation = subprocess.run(",
    "        [sys.executable,",
    "         str(ROOT / \"scripts/validate-memory-os-version-compatibility-foundations.py\")],",
    "        cwd=ROOT,",
    "        check=False,",
    "    )",
    "    require(foundation.returncode == 0,",
    "            \"integrated compatibility foundation validation failed\")",
    "",
    "    print(\"Memory OS version compatibility validation PASS\")",
    "",
])


class PatchFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PatchFailure(message)


def main() -> int:
    try:
        text = TARGET.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PatchFailure("canonical version compatibility validator is missing") from exc

    changed = False
    if NEW_IMPORT not in text:
        require(text.count(OLD_IMPORT) == 1,
                "canonical validator import authority drift")
        text = text.replace(OLD_IMPORT, NEW_IMPORT)
        changed = True
    else:
        require(text.count(NEW_IMPORT) == 1,
                "canonical validator subprocess import duplicated")

    if SENTINEL not in text:
        require(text.count(MARKER) == 1,
                f"canonical validator success marker drift: count={text.count(MARKER)}")
        text = text.replace(MARKER, INJECTED)
        changed = True
    else:
        require(text.count(SENTINEL) == 1,
                "canonical foundation validator connection duplicated")
        require("validate-memory-os-version-compatibility-foundations.py" in text,
                "canonical foundation validator target drift")

    if changed:
        TARGET.write_text(text, encoding="utf-8")
        print("Connected canonical version validator to compatibility foundations")
    else:
        print("Canonical version validator foundation connection already current")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchFailure as exc:
        print(f"VERSION COMPATIBILITY VALIDATOR PATCH FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
