#!/usr/bin/env python3
"""Read-only external reachability proof for helper ancestor race negatives."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "validate-memory-os-backup-restore-non-resurrection-load-negative.py":
        "typed contract path fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-generation-evidence-load-negative.py":
        "generation-evidence fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-non-resurrection-transport-negative.py":
        "typed contract path fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-generation-binding-negative.py":
        "generation-binding fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-drill-request-reconcile-negative.py":
        "drill request fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-admission-chain-reconcile-negative.py":
        "admission-chain fixture guard ancestor identity drift",
    "validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py":
        "preflight fixture guard ancestor identity drift",
}
PROOF = "prove_helper_ancestor_swap_during_fd_walk_rejected"
PIN = "pin_checked_helper_parent"
MIN_CANONICAL_TARGETS = 7


class GuardFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardFailure(message)


def named_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(matches) == 1, f"missing or duplicate function: {name}")
    return matches[0]


def direct_call_count(fn: ast.FunctionDef, name: str) -> int:
    return sum(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == name
        for node in fn.body
    )


def has_call(fn: ast.FunctionDef, name: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
        for node in ast.walk(fn)
    )


def has_method(fn: ast.FunctionDef, method: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
        for node in ast.walk(fn)
    )


def module_effect_nodes(node: ast.AST):
    """Inspect eager module expressions without treating function bodies as eager."""
    yield node
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        expressions = [
            *node.decorator_list,
            *node.args.defaults,
            *(value for value in node.args.kw_defaults if value is not None),
        ]
    elif isinstance(node, ast.Lambda):
        expressions = [
            *node.args.defaults,
            *(value for value in node.args.kw_defaults if value is not None),
            node.body,
        ]
    else:
        expressions = ast.iter_child_nodes(node)
    for child in expressions:
        yield from module_effect_nodes(child)


def is_module_namespace_mutation(node: ast.AST, names: tuple[str, ...]) -> bool:
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"}:
            return True
        if (isinstance(node.func, ast.Name)
                and node.func.id in {"setattr", "delattr"}
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value in names):
            return True
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in {
                    "update", "pop", "popitem", "clear", "setdefault",
                    "__setitem__", "__delitem__",
                }):
            receiver = node.func.value
            if (isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Name)
                    and receiver.func.id in {"globals", "locals", "vars"}
                    and not receiver.args and not receiver.keywords):
                return True
            if isinstance(receiver, ast.Attribute) and receiver.attr == "__dict__":
                return True
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, (ast.Store, ast.Del)):
        receiver = node.value
        if (isinstance(receiver, ast.Call)
                and isinstance(receiver.func, ast.Name)
                and receiver.func.id in {"globals", "locals", "vars"}
                and not receiver.args and not receiver.keywords):
            return True
        if isinstance(receiver, ast.Attribute) and receiver.attr == "__dict__":
            return True
    return False


def validate_step_key_inventory(
    source: str, expected: tuple[tuple[str, ...], ...], diagnostic: str
) -> None:
    """Bind executable step headers and step-level keys, including duplicates."""
    headers = re.findall(r"(?m)^      - ([a-z][a-z-]*):", source)
    require(headers == ["uses", "uses", *(["name"] * (len(expected) - 2))],
            diagnostic)
    # A quoted YAML mapping key on a new step is executable even though
    # the unquoted-only header extractor would silently ignore that step.
    job_source = source.split("\njobs:\n", 1)[1]
    raw_headers = re.findall(r"(?m)^      - ([^\n]+)$", job_source)
    require(len(raw_headers) == len(expected)
            and all(re.fullmatch(r"(?:uses|name): .+", header)
                    for header in raw_headers),
            diagnostic)
    blocks = re.split(r"(?m)(?=^      - (?:uses|name): )", source)
    step_blocks = [block for block in blocks if block.startswith("      - ")]
    def keys_for_step(block: str) -> tuple[str, ...]:
        # Eight-space lines are step properties, not ten-space run/with bodies.
        # A quoted YAML key must not impersonate a comment or disappear from
        # an unquoted-only inventory.
        lines = re.findall(r"(?m)^        ([^ \t#\n][^\n]*)$", block)
        keys = []
        for line in lines:
            match = re.fullmatch(r"([a-z][a-z-]*):(?:[ \t].*)?", line)
            require(match is not None, diagnostic)
            keys.append(match.group(1))
        return tuple(keys)

    actual = tuple(keys_for_step(block) for block in step_blocks)
    require(actual == expected, diagnostic)


def validate_root_key_inventory(
    source: str, expected: tuple[str, ...], diagnostic: str
) -> None:
    """Reject YAML-equivalent quoted or duplicate root keys."""
    actual = []
    for line in source.splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, diagnostic)
        actual.append(match.group(1))
    require(tuple(actual) == expected, diagnostic)


def validate_job_key_inventory(
    source: str, expected: tuple[str, ...], diagnostic: str
) -> None:
    """Reject quoted or duplicate job properties that change effective CI."""
    sections = source.split("\njobs:\n", 1)
    require(len(sections) == 2, diagnostic)
    lines = re.findall(r"(?m)^    ([^ \t#\n][^\n]*)$", sections[1])
    actual = []
    for line in lines:
        match = re.fullmatch(r"([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, diagnostic)
        actual.append(match.group(1))
    require(tuple(actual) == expected, diagnostic)



def validate_event_key_inventory(
    source: str, expected: tuple[tuple[str, tuple[str, ...]], ...],
    diagnostic: str,
) -> None:
    """Bind event names and options, rejecting quoted YAML key overrides."""
    event_block = source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    actual: list[list] = []
    for line in event_block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("   "):
            match = re.fullmatch(r"  ([a-z_]+):", line)
            require(match is not None, diagnostic)
            actual.append([match.group(1), []])
        elif line.startswith("    ") and not line.startswith("     "):
            match = re.fullmatch(r"    ([a-z][a-z-]*):(?:[ \t].*)?", line)
            require(match is not None and bool(actual), diagnostic)
            actual[-1][1].append(match.group(1))
    require(
        tuple((event, tuple(keys)) for event, keys in actual) == expected,
        diagnostic,
    )



def validate_trigger_path_inventory(
    source: str, expected_paths: tuple[str, ...], diagnostic: str
) -> None:
    """Reject unquoted, negative or duplicate YAML path filters."""
    event_block = source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    for event, next_event in (
        ("push", "pull_request"),
        ("pull_request", "workflow_dispatch"),
    ):
        body = event_block.split(f"  {event}:\n", 1)[1].split(
            f"  {next_event}:\n", 1
        )[0]
        require(body.count("    paths:\n") == 1, diagnostic)
        path_block = body.split("    paths:\n", 1)[1]
        actual = [
            line for line in path_block.splitlines()
            if line.startswith("      - ")
        ]
        require(actual == [f'      - "{path}"' for path in expected_paths],
                diagnostic)



def validate_setup_python_input_inventory(source: str, diagnostic: str) -> None:
    """Bind complete setup-python inputs, not just an approved prefix."""
    anchor = "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
    require(source.count(anchor) == 1, diagnostic)
    block = source.split(anchor, 1)[1].split("      - name:", 1)[0]
    require(block == '        with:\n          python-version: "3.12"\n',
            diagnostic)



FINAL_READONLY_LINE = '          test -z "$(git status --porcelain)"\n'
ANCESTOR_RUN_BOUNDARIES = (
    (FINAL_READONLY_LINE,
     "      - name: Prove seven canonical ancestor negatives remain reachable\n"),
    ("          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n",
     "      - name: Prove every canonical helper ancestor race from the validator target set\n"),
    ("          PY\n",
     "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n"),
    ("          PY\n",
     "      - name: Verify read-only postcondition\n"),
)
LEARNING_RUN_BOUNDARIES = (
    (FINAL_READONLY_LINE,
     "      - name: Enforce append-only learning authority against parent\n"),
    ("          PY\n",
     "      - name: Validate learning contract and executable negatives\n"),
    ("          python -B scripts/validate-memory-os-entry-docs.py\n",
     "      - name: Independently enforce helper ancestor runtime workflow reachability\n"),
    ("          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n",
     "      - name: Confirm read-only execution\n"),
)


def validate_run_step_boundaries(
    source: str, boundaries: tuple[tuple[str, str], ...], diagnostic: str
) -> None:
    """No unreviewed shell commands may follow a canonical run-body prefix."""
    require(all(source.count(last + next_step) == 1
                for last, next_step in boundaries), diagnostic)
    require(source.endswith(FINAL_READONLY_LINE), diagnostic)



def validate_learning_root_mapping_bodies(source: str, diagnostic: str) -> None:
    """Prevent trailing token permission or concurrency key overrides."""
    permissions = source.split("\npermissions:\n", 1)[1].split(
        "\nconcurrency:\n", 1
    )[0]
    concurrency = source.split("\nconcurrency:\n", 1)[1].split(
        "\njobs:\n", 1
    )[0]
    require(permissions == "  contents: read\n", diagnostic)
    require(
        concurrency ==
        "  group: autonomous-learning-guard-${{ github.sha }}\n"
        "  cancel-in-progress: false\n",
        diagnostic,
    )


def validate_target_matrix(targets: dict[str, str], workflow_source: str) -> None:
    """Reject silent loss of a canonical harness or its workflow trigger."""
    require(len(targets) >= MIN_CANONICAL_TARGETS,
            "ancestor target matrix below seven canonical harnesses")
    require(
        re.search(r"(?m)^on:\n  push:\n    branches: \[so\]\n", workflow_source)
        is not None,
        "ancestor workflow so push trigger drift",
    )
    require(
        re.search(r"(?m)^  pull_request:\n    branches: \[so\]\n", workflow_source)
        is not None,
        "ancestor workflow so PR trigger drift",
    )
    for event in ("push", "pull_request"):
        section = re.search(
            r"(?m)^  " + event + r":\n(?P<body>(?:    [^\n]*\n)+)",
            workflow_source,
        )
        require(section is not None,
                "ancestor target matrix workflow trigger drift")
        triggered = set(re.findall(
            r'^      - "scripts/(validate-memory-os-backup-restore-[^"]+-negative\.py)"\s*$',
            section.group("body"),
            flags=re.MULTILINE,
        ))
        require(set(targets) == triggered,
                "ancestor target matrix workflow trigger drift")
        require(section.group("body").count(
            '      - ".github/workflows/autonomous-learning-guard.yml"\n'
        ) == 1, "ancestor independent learning workflow trigger drift")
        all_paths = set(re.findall(r'(?m)^      - "([^"]+)"$', section.group("body")))
        required_authority_paths = {
            ".github/workflows/backup-restore-helper-ancestor-reachability.yml",
            ".github/workflows/autonomous-learning-guard.yml",
            "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py",
        }
        require(all_paths - {f"scripts/{filename}" for filename in targets}
                == required_authority_paths,
                "ancestor workflow authority trigger drift")
        event_options = re.findall(r"(?m)^    ([a-z][a-z-]*):", section.group("body"))
        require(event_options == ["branches", "paths"],
                "ancestor workflow event options drift")


def validate_workflow_runtime_reachability(workflow_source: str) -> None:
    """Bind the independent workflow to its real validator and runtime proofs."""
    require(not re.search(r"(?m)^\s*(?:if|continue-on-error):", workflow_source),
            "ancestor workflow conditional bypass")
    require(not re.search(r"(?m)^(?:env|defaults|strategy):|^    (?:env|defaults|strategy):", workflow_source),
            "ancestor workflow execution context override")
    require(not re.search(r"(?m)^concurrency:", workflow_source),
            "ancestor workflow concurrency drift")
    require(len(re.findall(r"(?m)^on:", workflow_source)) == 1
            and len(re.findall(r"(?m)^permissions:", workflow_source)) == 1,
            "ancestor workflow duplicate root authority")
    validate_root_key_inventory(
        workflow_source, ("name", "on", "permissions", "jobs"),
        "ancestor workflow root key inventory drift",
    )
    event_block = workflow_source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    require(re.findall(r"(?m)^  ([a-z_]+):", event_block)
            == ["push", "pull_request", "workflow_dispatch"],
            "ancestor workflow event inventory drift")
    require(not event_block.split("  workflow_dispatch:\n", 1)[1].strip(),
            "ancestor workflow dispatch options drift")
    validate_event_key_inventory(
        workflow_source,
        (("push", ("branches", "paths")), ("pull_request", ("branches", "paths")),
         ("workflow_dispatch", ())),
        "ancestor workflow event key inventory drift",
    )
    static_step = """      - name: Prove seven canonical ancestor negatives remain reachable
        run: |
          set -euo pipefail
          python -m py_compile scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py
          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py
          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative
"""
    require(workflow_source.count(static_step) == 1,
            "ancestor validator workflow invocation drift")
    step_name = "Prove every canonical helper ancestor race from the validator target set"
    pattern = (
        r"(?m)^      - name: " + re.escape(step_name)
        + r"\n        run: \|\n(?P<body>(?:          [^\n]*\n)+)"
    )
    matches = list(re.finditer(pattern, workflow_source))
    require(len(matches) == 1, "ancestor runtime workflow step missing or duplicate")
    expected_body = """          set -euo pipefail
          python - <<'PY'
          import runpy
          targets = runpy.run_path(
              "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py"
          )["TARGETS"]
          for filename in targets:
              proof = runpy.run_path(f"scripts/{filename}")
              proof["prove_helper_ancestor_swap_during_fd_walk_rejected"]()
          PY
"""
    require(matches[0].group("body") == expected_body,
            "ancestor runtime workflow proof invocation drift")
    require(
        workflow_source.index(static_step) < matches[0].start()
        < workflow_source.index("      - name: Verify read-only postcondition\n"),
        "ancestor runtime workflow step order drift",
    )

    # An otherwise valid proof can be bypassed by an unreviewed Actions step,
    # altered checkout/setup action, extra job, or elevated workflow token.
    job_sections = workflow_source.split("\n"+"jobs:\n")
    require(len(job_sections) == 2
            and re.findall(r"(?m)^  [A-Za-z][\w-]*:$", job_sections[1]) == ["  verify:"]
            and "\npermissions:\n  contents: read\n\njobs:\n" in workflow_source,
            "ancestor workflow job or permissions drift")
    require(not re.search(r"(?m)^    permissions:", workflow_source),
            "ancestor workflow job-level permissions override")
    require(not re.search(r"(?m)^    (?:container|services|uses|needs|environment|outputs|secrets|concurrency):", workflow_source)
            and "jobs:\n  verify:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n" in workflow_source,
            "ancestor workflow job execution drift")
    require(all(len(re.findall(r"(?m)^    " + key + ":", workflow_source)) == 1
                for key in ("runs-on", "timeout-minutes", "steps")),
            "ancestor workflow duplicate job authority")
    validate_job_key_inventory(
        workflow_source, ("runs-on", "timeout-minutes", "steps"),
        "ancestor workflow job key inventory drift",
    )
    expected_actions = "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n          fetch-depth: 0\n          persist-credentials: false\n      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n"
    require(workflow_source.count(expected_actions) == 1,
            "ancestor workflow checkout/setup drift")
    expected_headers = ["      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262","      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065","      - name: Confirm exact clean source","      - name: Prove seven canonical ancestor negatives remain reachable","      - name: Prove every canonical helper ancestor race from the validator target set","      - name: Prove preflight reconcile helper races without downstream source-binding dependency","      - name: Verify read-only postcondition"]
    actual_headers = re.findall(r"(?m)^      - (?:uses|name):[^\n]*", workflow_source)
    require(actual_headers == expected_headers,
            "ancestor workflow step allowlist drift")

    # Bind remaining preflight, exact-source and read-only run bodies, not just headers.
    require(workflow_source.count("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n") == 1,
            "ancestor preflight runtime proof drift")
    require(workflow_source.count("      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"workflow_dispatch\" ]; then\n            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n              echo \"ANCESTOR DISPATCH REF REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"pull_request\" ]; then\n            pr_head=\"${{ github.event.pull_request.head.sha }}\"\n            if [[ ! \"$pr_head\" =~ ^[0-9a-f]{40}$ ]]; then\n              echo \"ANCESTOR PR HEAD SHA REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "ancestor exact-source workflow check drift")
    require(workflow_source.count("      - name: Verify read-only postcondition\n        run: |\n          git diff --check\n          git diff --exit-code\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "ancestor read-only workflow postcondition drift")
    validate_step_key_inventory(
        workflow_source,
        (("with",), ("with",), ("run",), ("run",), ("run",), ("run",), ("run",)),
        "ancestor workflow step authority drift",
    )


    expected_paths = (
        ".github/workflows/backup-restore-helper-ancestor-reachability.yml",
        ".github/workflows/autonomous-learning-guard.yml",
        "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py",
    ) + tuple(f"scripts/{filename}" for filename in TARGETS)
    validate_trigger_path_inventory(
        workflow_source, expected_paths,
        "ancestor workflow trigger path inventory drift",
    )


    validate_setup_python_input_inventory(
        workflow_source, "ancestor workflow setup-python input inventory drift",
    )


    validate_run_step_boundaries(
        workflow_source, ANCESTOR_RUN_BOUNDARIES,
        "ancestor workflow run boundary drift",
    )


    require(workflow_source.startswith(
        "name: Backup Restore Helper Ancestor Reachability\n"
    ), "ancestor workflow identity drift")


def validate_independent_learning_workflow(source: str) -> None:
    """Guard independent learning CI from the ancestor validator."""
    require(not re.search(r"(?m)^\s*(?:if|continue-on-error):", source),
            "independent learning workflow conditional bypass")
    require(not re.search(r"(?m)^(?:env|defaults|strategy):|^    (?:env|defaults|strategy):", source),
            "independent learning workflow execution context override")
    require(len(re.findall(r"(?m)^concurrency:$", source)) == 1
            and source.count("concurrency:\n  group: autonomous-learning-guard-${{ github.sha }}\n  cancel-in-progress: false\n") == 1,
            "independent learning workflow concurrency drift")
    require(len(re.findall(r"(?m)^on:", source)) == 1
            and len(re.findall(r"(?m)^permissions:", source)) == 1,
            "independent learning workflow duplicate root authority")
    validate_root_key_inventory(
        source, ("name", "on", "permissions", "concurrency", "jobs"),
        "independent learning workflow root key inventory drift",
    )
    require(re.search(r"(?m)^on:\n  push:\n    branches: \[so\]\n    paths:\n", source)
            is not None and "\n  workflow_dispatch:\n" in source,
            "independent learning workflow trigger drift")
    event_block = source.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    require(re.findall(r"(?m)^  ([a-z_]+):", event_block)
            == ["push", "pull_request", "workflow_dispatch"],
            "independent learning workflow event inventory drift")
    push_body = event_block.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
    require(re.findall(r"(?m)^    ([a-z][a-z-]*):", push_body) == ["branches", "paths"],
            "independent learning workflow push options drift")
    require(not event_block.split("  workflow_dispatch:\n", 1)[1].strip(),
            "independent learning workflow dispatch options drift")
    match = re.search(r'(?m)^    paths:\n(?P<paths>(?:      - "[^"]+"\n)+)', source)
    require(match is not None, "independent learning workflow trigger drift")
    paths = set(re.findall(r'^      - "([^"]+)"$', match.group("paths"),
                           flags=re.MULTILINE))
    require({".github/workflows/autonomous-learning-guard.yml", ".github/workflows/backup-restore-helper-ancestor-reachability.yml", "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py", "contracts/operations/autonomous-learning-system.json", "docs/operations/AUTONOMOUS-OPS-LEARNING.md"} <= paths,
            "independent learning workflow trigger drift")
    triggered_harnesses = {
        item for item in paths
        if item.startswith("scripts/validate-memory-os-backup-restore-")
        and item.endswith("-negative.py")
    }
    expected_harnesses = {f"scripts/{filename}" for filename in TARGETS}
    require(triggered_harnesses == expected_harnesses,
            "independent learning workflow target trigger drift")
    required_authority_paths = {
        ".github/workflows/autonomous-learning-guard.yml",
        ".github/workflows/backup-restore-helper-ancestor-reachability.yml",
        "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py",
        "contracts/operations/autonomous-learning-system.json",
        "docs/operations/AUTONOMOUS-OPS-LEARNING.md",
        "scripts/validate-autonomous-learning-system.py",
        "scripts/validate-autonomous-learning-system-negative.py",
        "scripts/validate-memory-os-entry-docs.py",
    }
    require(paths - triggered_harnesses == required_authority_paths,
            "independent learning workflow source trigger drift")
    pr_body = event_block.split("  pull_request:\n", 1)[1].split("  workflow_dispatch:\n", 1)[0]
    require(re.search(r"(?m)^    branches: \[so\]\n    paths:\n", pr_body)
            is not None, "independent learning workflow PR trigger drift")
    require(re.findall(r"(?m)^    ([a-z][a-z-]*):", pr_body)
            == ["branches", "paths"], "independent learning workflow PR options drift")
    validate_event_key_inventory(
        source,
        (("push", ("branches", "paths")),
         ("pull_request", ("branches", "paths")),
         ("workflow_dispatch", ())),
        "independent learning workflow event key inventory drift",
    )
    pr_match = re.search(r'(?m)^    paths:\n(?P<paths>(?:      - "[^"]+"\n)+)', pr_body)
    require(pr_match is not None, "independent learning workflow PR trigger drift")
    pr_paths = set(re.findall(r'^      - "([^"]+)"$', pr_match.group("paths"),
                              flags=re.MULTILINE))
    require(pr_paths == paths, "independent learning workflow PR source trigger drift")
    require(source.count("      - name: Validate learning contract and executable negatives\n        shell: bash\n        env:\n          PYTHONDONTWRITEBYTECODE: \"1\"\n        run: |\n          set -euo pipefail\n          python -B scripts/validate-autonomous-learning-system.py\n          python -B scripts/validate-autonomous-learning-system-negative.py\n          python -B scripts/validate-memory-os-entry-docs.py\n") == 1,
            "independent learning workflow learning validation drift")
    require(source.count("      - name: Independently enforce helper ancestor runtime workflow reachability\n        shell: bash\n        env:\n          PYTHONDONTWRITEBYTECODE: \"1\"\n        run: |\n          set -euo pipefail\n          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py\n          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n") == 1,
            "independent learning workflow ancestor invocation drift")
    require(source.count("""      - name: Enforce append-only learning authority against parent
        shell: bash
        run: |
          set -euo pipefail
          python - <<'PY'
          from pathlib import Path
          import subprocess
          import re
          import os

          authority = "docs/operations/AUTONOMOUS-OPS-LEARNING.md"
          event_name = "${{ github.event_name }}"
          before = "${{ github.event.before }}"
          if event_name == "push":
              if not re.fullmatch(r"[0-9a-f]{40}", before) or before == "0" * 40:
                  raise SystemExit(
                      "AUTONOMOUS LEARNING APPEND-ONLY FAILED: invalid push baseline"
                  )
              baseline = before
          elif event_name == "pull_request":
              baseline = "${{ github.event.pull_request.base.sha }}"
              head_sha = "${{ github.event.pull_request.head.sha }}"
              merge_sha = "${{ github.sha }}"
              if not all(re.fullmatch(r"[0-9a-f]{40}", value)
                         for value in (baseline, head_sha, merge_sha)):
                  raise SystemExit(
                      "AUTONOMOUS LEARNING APPEND-ONLY FAILED: invalid PR source SHA"
                  )
              parents = subprocess.check_output(
                  ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
                  text=True,
              ).split()
              if parents != [merge_sha, baseline, head_sha]:
                  raise SystemExit(
                      "AUTONOMOUS LEARNING APPEND-ONLY FAILED: PR merge parent mismatch"
                  )
          elif event_name == "workflow_dispatch":
              if os.environ.get("GITHUB_REF") != "refs/heads/so":
                  raise SystemExit(
                      "AUTONOMOUS LEARNING APPEND-ONLY FAILED: unreviewed dispatch ref"
                  )
              # Immutable, previously validated append-only authority baseline.
              baseline = "77b4b4a7f5d6282524ecb5e6dba4b614622d28e3"
          else:
              raise SystemExit(
                  "AUTONOMOUS LEARNING APPEND-ONLY FAILED: unreviewed event"
              )
          if subprocess.run(
              ["git", "merge-base", "--is-ancestor", baseline, "HEAD"],
              check=False,
          ).returncode:
              raise SystemExit(
                  "AUTONOMOUS LEARNING APPEND-ONLY FAILED: baseline is not an ancestor"
              )
          previous = subprocess.check_output(
              ["git", "show", f"{baseline}:{authority}"]
          )
          current = Path(authority).read_bytes()
          if not current.startswith(previous):
              raise SystemExit(
                  "AUTONOMOUS LEARNING APPEND-ONLY FAILED: previous authority bytes changed"
              )
          print("Autonomous learning append-only PASS")
          PY
""") == 1,
            "independent learning workflow append-only drift")
    require(source.count("      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.sha }}\n          persist-credentials: false\n          fetch-depth: 0\n      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n") == 1,
            "independent learning workflow checkout/setup drift")
    require(source.count("      - name: Confirm exact clean source\n        shell: bash\n        run: |\n          set -euo pipefail\n          test \"$(git rev-parse HEAD)\" = \"${{ github.sha }}\"\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "independent learning workflow exact-source drift")
    require(source.count("      - name: Confirm read-only execution\n        shell: bash\n        run: |\n          set -euo pipefail\n          git diff --check\n          git diff --exit-code\n          test -z \"$(git status --porcelain)\"\n") == 1,
            "independent learning workflow read-only drift")
    jobs = source.split("\njobs:\n")
    require(len(jobs) == 2
            and re.findall(r"(?m)^  [A-Za-z][\w-]*:$", jobs[1]) == ["  validate:"]
            and "\npermissions:\n  contents: read\n" in source,
            "independent learning workflow job or permissions drift")
    require(not re.search(r"(?m)^    permissions:", source),
            "independent learning workflow job-level permissions override")
    require(not re.search(r"(?m)^    (?:container|services|uses|needs|environment|outputs|secrets|concurrency):", source)
            and "jobs:\n  validate:\n    runs-on: ubuntu-latest\n    timeout-minutes: 10\n    steps:\n" in source,
            "independent learning workflow job execution drift")
    require(all(len(re.findall(r"(?m)^    " + key + ":", source)) == 1
                for key in ("runs-on", "timeout-minutes", "steps")),
            "independent learning workflow duplicate job authority")
    validate_job_key_inventory(
        source, ("runs-on", "timeout-minutes", "steps"),
        "independent learning workflow job key inventory drift",
    )
    require(re.findall(r"(?m)^      - (?:uses|name):[^\n]*", source) == [
        "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "      - name: Confirm exact clean source",
        "      - name: Enforce append-only learning authority against parent",
        "      - name: Validate learning contract and executable negatives",
        "      - name: Independently enforce helper ancestor runtime workflow reachability",
        "      - name: Confirm read-only execution",
    ], "independent learning workflow step allowlist drift")
    validate_step_key_inventory(
        source,
        (("with",), ("with",), ("shell", "run"), ("shell", "run"),
         ("shell", "env", "run"), ("shell", "env", "run"), ("shell", "run")),
        "independent learning workflow step authority drift",
    )


    expected_paths = (
        ".github/workflows/autonomous-learning-guard.yml",
        ".github/workflows/backup-restore-helper-ancestor-reachability.yml",
        "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py",
    ) + tuple(f"scripts/{filename}" for filename in TARGETS) + (
        "contracts/operations/autonomous-learning-system.json",
        "docs/operations/AUTONOMOUS-OPS-LEARNING.md",
        "scripts/validate-autonomous-learning-system.py",
        "scripts/validate-autonomous-learning-system-negative.py",
        "scripts/validate-memory-os-entry-docs.py",
    )
    validate_trigger_path_inventory(
        source, expected_paths,
        "independent learning workflow trigger path inventory drift",
    )


    validate_setup_python_input_inventory(
        source, "independent learning workflow setup-python input inventory drift",
    )


    validate_run_step_boundaries(
        source, LEARNING_RUN_BOUNDARIES,
        "independent learning workflow run boundary drift",
    )


    validate_learning_root_mapping_bodies(
        source, "independent learning workflow root mapping drift",
    )


    require(source.startswith(
        "name: Autonomous Learning Guard\n"
    ), "independent learning workflow identity drift")


def validate_source(source: str, expected_diagnostic: str) -> None:
    tree = ast.parse(source)
    require(source.count("MAX_HELPER_SOURCE_BYTES = 1024 * 1024\n") == 1,
            "loader source execution not pinned to FD")
    main = named_function(tree, "main")
    proof = named_function(tree, PROOF)
    pin = named_function(tree, PIN)
    expected_parent_failure_cleanup = ast.parse("""try:
    os.close(fd)
except (Exception, SystemExit):
    raise Fail("fixture guard pinned descriptor cleanup failed") from None
""").body[0]
    base_handlers = [
        handler for node in ast.walk(pin)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name) and handler.type.id == "BaseException"
    ]
    require(
        len(base_handlers) == 1
        and base_handlers[0].name == "exc"
        and len(base_handlers[0].body) == 3
        and ast.dump(base_handlers[0].body[0], include_attributes=False)
            == ast.dump(expected_parent_failure_cleanup, include_attributes=False)
        and ast.dump(base_handlers[0].body[1], include_attributes=False)
            == ast.dump(ast.parse("""if isinstance(exc, RuntimeError) and not isinstance(exc, Fail):
    raise Fail("fixture guard parent runtime open failed") from None
""").body[0], include_attributes=False)
        and isinstance(base_handlers[0].body[2], ast.Raise)
        and base_handlers[0].body[2].exc is None
        and base_handlers[0].body[2].cause is None,
        "loader parent unexpected cleanup not private",
    )
    expected_anchor_condition = ast.parse(
        "anchor.is_dir() and not anchor.is_symlink()", mode="eval"
    ).body
    expected_anchor_handler = ast.parse("""try:
    pass
except (OSError, RuntimeError):
    raise Fail("fixture guard trusted anchor check failed") from None
""").body[0].handlers[0]
    anchor_checks = [
        (index, node) for index, node in enumerate(pin.body)
        if isinstance(node, ast.Try)
        and len(node.body) == 1
        and isinstance(node.body[0], ast.Assign)
        and len(node.body[0].targets) == 1
        and isinstance(node.body[0].targets[0], ast.Name)
        and node.body[0].targets[0].id == "anchor_ok"
        and ast.dump(node.body[0].value, include_attributes=False)
            == ast.dump(expected_anchor_condition, include_attributes=False)
    ]
    require(
        len(anchor_checks) == 1
        and len(anchor_checks[0][1].handlers) == 1
        and ast.dump(anchor_checks[0][1].handlers[0], include_attributes=False)
            == ast.dump(expected_anchor_handler, include_attributes=False)
        and not anchor_checks[0][1].orelse and not anchor_checks[0][1].finalbody
        and anchor_checks[0][0] + 1 < len(pin.body)
        and isinstance(pin.body[anchor_checks[0][0] + 1], ast.Expr)
        and isinstance(pin.body[anchor_checks[0][0] + 1].value, ast.Call)
        and isinstance(pin.body[anchor_checks[0][0] + 1].value.func, ast.Name)
        and pin.body[anchor_checks[0][0] + 1].value.func.id == "require"
        and len(pin.body[anchor_checks[0][0] + 1].value.args) == 2
        and isinstance(pin.body[anchor_checks[0][0] + 1].value.args[0], ast.Name)
        and pin.body[anchor_checks[0][0] + 1].value.args[0].id == "anchor_ok",
        "loader anchor predicate fault not private",
    )
    for suffix, expected_type, expected_count in (
        ("fixture guard parent outside trusted roots", "ValueError", 1),
        ("fixture guard anchor open failed", ("OSError", "RuntimeError"), 1),
        ("fixture guard parent open failed", "OSError", 2),
    ):
        matches = [
            handler for node in ast.walk(pin) if isinstance(node, ast.Try)
            for handler in node.handlers
            if handler.body
            and isinstance(handler.body[-1], ast.Raise)
            and isinstance(handler.body[-1].exc, ast.Call)
            and isinstance(handler.body[-1].exc.func, ast.Name)
            and handler.body[-1].exc.func.id == "Fail"
            and len(handler.body[-1].exc.args) == 1
            and isinstance(handler.body[-1].exc.args[0], ast.Constant)
            and isinstance(handler.body[-1].exc.args[0].value, str)
            and handler.body[-1].exc.args[0].value.endswith(suffix)
        ]
        require(
            len(matches) == 1
            and (
                (isinstance(expected_type, str)
                 and isinstance(matches[0].type, ast.Name)
                 and matches[0].type.id == expected_type)
                or (isinstance(expected_type, tuple)
                    and isinstance(matches[0].type, ast.Tuple)
                    and [elt.id for elt in matches[0].type.elts
                         if isinstance(elt, ast.Name)] == list(expected_type)
                    and len(matches[0].type.elts) == len(expected_type))
            )
            and matches[0].name is None
            and len(matches[0].body) == expected_count
            and isinstance(matches[0].body[-1].cause, ast.Constant)
            and matches[0].body[-1].cause.value is None
            and (expected_count == 1 or ast.dump(
                matches[0].body[0], include_attributes=False)
                == ast.dump(expected_parent_failure_cleanup,
                            include_attributes=False)),
            "loader parent pin failure not private",
        )
    loaders = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"load_pinned_fixture_helper", "load_pinned_fixture_guard"}
    ]
    require(len(loaders) == 1, "missing or duplicate pinned fixture loader")
    for marker, delegate in (
        ("typed transport fixture guard source open failed", "load_pinned_fixture_helper"),
        ("admission-chain fixture guard source open failed", "load_pinned_fixture_guard"),
    ):
        if marker in source:
            module_import = named_function(tree, "load_module")
            module_body = [
                statement for statement in module_import.body
                if not (isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str))
            ]
            expected_delegate = ast.parse(
                f"return {delegate}(path, name)"
            ).body[0]
            require(
                len(module_body) == 1
                and ast.dump(module_body[0], include_attributes=False)
                    == ast.dump(expected_delegate, include_attributes=False),
                "canonical module import not pinned",
            )
    # A source-string marker alone is not an authority: the marker and a
    # mutable-path import could be changed together. Bind every canonical
    # load_module(path, name) directly to a pinned loader or checked spec.
    module_imports = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "load_module"
        and [arg.arg for arg in node.args.args] == ["path", "name"]
    ]
    for module_import in module_imports:
        for call in ast.walk(module_import):
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "spec_from_file_location"):
                require(any(keyword.arg == "loader" for keyword in call.keywords),
                        "canonical module import not pinned")
        module_body = [
            statement for statement in module_import.body
            if not (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str))
        ]
        if len(module_body) == 1 and isinstance(module_body[0], ast.Return):
            allowed = (
                ast.parse("return load_pinned_fixture_helper(path, name)").body[0],
                ast.parse("return load_pinned_fixture_guard(path, name)").body[0],
            )
            require(any(ast.dump(module_body[0], include_attributes=False)
                        == ast.dump(node, include_attributes=False)
                        for node in allowed),
                    "canonical module import not pinned")
    # Decorators execute while the module is initialized and may replace the
    # checked callable without a later assignment or explicit namespace write.
    for guarded_function in (main, proof, pin, loaders[0]):
        require(not guarded_function.decorator_list,
                f"decorated guarded function: {guarded_function.name}")
    # A later module-level assignment can replace an otherwise valid checked
    # function before the canonical __main__ dispatcher executes.
    for guarded_name in ("main", PROOF, PIN, loaders[0].name):
        shadowed = any(
            (isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
             and any(
                 isinstance(target, ast.Name) and target.id == guarded_name
                 for target in (
                     node.targets if isinstance(node, ast.Assign) else [node.target]
                 )
             ))
            or (isinstance(node, ast.Delete)
                and any(isinstance(target, ast.Name) and target.id == guarded_name
                        for target in node.targets))
            or (isinstance(node, ast.AsyncFunctionDef) and node.name == guarded_name)
            or (isinstance(node, (ast.Import, ast.ImportFrom))
                and any(
                    (alias.asname or
                     (alias.name.split(".")[0] if isinstance(node, ast.Import)
                      else alias.name)) == guarded_name
                    for alias in node.names
                ))
            for node in tree.body
        )
        require(not shadowed, f"module binding shadowed: {guarded_name}")
    # Module-scope control flow, decorators and default arguments execute before
    # the canonical dispatcher. Direct top-level assignment checks alone miss
    # nested stores, destructuring, and dynamic namespace replacement.
    guarded_names = ("main", PROOF, PIN, loaders[0].name)
    for statement in tree.body:
        for node in module_effect_nodes(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                require(node.id not in guarded_names,
                        f"module binding shadowed: {node.id}")
            if (isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef))
                    and node.name in guarded_names):
                raise GuardFailure(f"module binding shadowed: {node.name}")
            if (isinstance(node, ast.FunctionDef)
                    and node not in tree.body and node.name in guarded_names):
                raise GuardFailure(f"module binding shadowed: {node.name}")
            require(not is_module_namespace_mutation(node, guarded_names),
                    "module dynamic binding mutation")
    require(direct_call_count(main, PROOF) == 1, "main missing direct ancestor proof")
    proof_index = next(
        index for index, statement in enumerate(main.body)
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Name)
        and statement.value.func.id == PROOF
    )
    require(
        not any(
            isinstance(statement, (ast.Return, ast.Raise))
            or (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and (
                    (isinstance(statement.value.func, ast.Name)
                     and statement.value.func.id in {"exit", "quit"})
                    or (isinstance(statement.value.func, ast.Attribute)
                        and isinstance(statement.value.func.value, ast.Name)
                        and statement.value.func.value.id == "sys"
                        and statement.value.func.attr == "exit")
                )
            )
            for statement in main.body[:proof_index]
        ),
        "main exits before ancestor proof",
    )
    # The canonical proof call can still be shadowed from inside main()
    # before execution, even if its module-level binding was initially safe.
    for statement in main.body[:proof_index]:
        for node in ast.walk(statement):
            if (isinstance(node, ast.Name)
                    and isinstance(node.ctx, (ast.Store, ast.Del))
                    and node.id in guarded_names):
                raise GuardFailure("main pre-proof binding mutation")
            if is_module_namespace_mutation(node, guarded_names):
                raise GuardFailure("main pre-proof binding mutation")
    dispatches = [
        node for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "__main__"
    ]
    require(len(dispatches) == 1, "missing canonical __main__ dispatch")
    require(
        any(
            isinstance(statement, ast.Try)
            and any(
                isinstance(inner, ast.Raise)
                and isinstance(inner.exc, ast.Call)
                and isinstance(inner.exc.func, ast.Name)
                and inner.exc.func.id == "SystemExit"
                and len(inner.exc.args) == 1
                and isinstance(inner.exc.args[0], ast.Call)
                and isinstance(inner.exc.args[0].func, ast.Name)
                and inner.exc.args[0].func.id == "main"
                for inner in statement.body
            )
            for statement in dispatches[0].body
        ),
        "canonical __main__ dispatch does not execute main",
    )
    # A syntactically present main() call does not prove fail-closed dispatch
    # when a preceding statement or broad exception handler can swallow it.
    dispatch_body = dispatches[0].body
    require(
        len(dispatch_body) == 1
        and isinstance(dispatch_body[0], ast.Try)
        and len(dispatch_body[0].body) == 1,
        "canonical __main__ dispatch shape drift",
    )
    dispatch_try = dispatch_body[0]
    require(
        len(dispatch_try.handlers) == 1
        and isinstance(dispatch_try.handlers[0].type, ast.Name)
        and dispatch_try.handlers[0].type.id == "Fail"
        and not dispatch_try.orelse
        and not dispatch_try.finalbody
        and bool(dispatch_try.handlers[0].body)
        and isinstance(dispatch_try.handlers[0].body[-1], ast.Raise)
        and isinstance(dispatch_try.handlers[0].body[-1].exc, ast.Call)
        and isinstance(dispatch_try.handlers[0].body[-1].exc.func, ast.Name)
        and dispatch_try.handlers[0].body[-1].exc.func.id == "SystemExit"
        and len(dispatch_try.handlers[0].body[-1].exc.args) == 1
        and isinstance(dispatch_try.handlers[0].body[-1].exc.args[0], ast.Constant)
        and dispatch_try.handlers[0].body[-1].exc.args[0].value == 1,
        "canonical __main__ dispatch handler drift",
    )
    require(
        any(isinstance(node, ast.Constant) and node.value == expected_diagnostic for node in ast.walk(proof)),
        "ancestor proof missing exact diagnostic",
    )
    require(has_call(loaders[0], PIN), "loader missing pinned parent call")
    # A dead pin_checked_helper_parent() call must not authenticate an
    # unchecked full-path open. Bind the live first loader assignment and leaf.
    live_statements = [
        node for node in loaders[0].body
        if not (isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str))
    ]
    first = live_statements[0] if live_statements else None
    require(
        isinstance(first, ast.Assign)
        and len(first.targets) == 1
        and isinstance(first.targets[0], ast.Name)
        and first.targets[0].id == "parent_fd"
        and isinstance(first.value, ast.Call)
        and isinstance(first.value.func, ast.Name)
        and first.value.func.id == PIN
        and len(first.value.args) == 1
        and isinstance(first.value.args[0], ast.Name)
        and first.value.args[0].id == "path",
        "loader parent FD not bound to checked ancestors",
    )
    require(
        len(live_statements) >= 2
        and isinstance(live_statements[1], ast.Try)
        and live_statements[1].body
        and isinstance(live_statements[1].body[0], ast.Try)
        and live_statements[1].body[0].body
        and isinstance(live_statements[1].body[0].body[0], ast.Assign)
        and len(live_statements[1].body[0].body[0].targets) == 1
        and isinstance(live_statements[1].body[0].body[0].targets[0], ast.Name)
        and live_statements[1].body[0].body[0].targets[0].id == "fd"
        and isinstance(live_statements[1].body[0].body[0].value, ast.Call)
        and isinstance(live_statements[1].body[0].body[0].value.func, ast.Attribute)
        and isinstance(live_statements[1].body[0].body[0].value.func.value, ast.Name)
        and live_statements[1].body[0].body[0].value.func.value.id == "os"
        and live_statements[1].body[0].body[0].value.func.attr == "open"
        and live_statements[1].body[0].body[0].value.args
        and isinstance(live_statements[1].body[0].body[0].value.args[0], ast.Attribute)
        and isinstance(live_statements[1].body[0].body[0].value.args[0].value, ast.Name)
        and live_statements[1].body[0].body[0].value.args[0].value.id == "path"
        and live_statements[1].body[0].body[0].value.args[0].attr == "name"
        and any(
            keyword.arg == "dir_fd"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "parent_fd"
            for keyword in live_statements[1].body[0].body[0].value.keywords
        ),
        "loader leaf open not bound to checked parent FD",
    )
    # Nonblocking leaf open is mandatory: a FIFO must never stall a proof.
    expected_leaf_flags = ast.parse(
        "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK", mode="eval"
    ).body
    leaf_open_call = live_statements[1].body[0].body[0].value
    require(
        len(leaf_open_call.args) == 2
        and ast.dump(leaf_open_call.args[1], include_attributes=False)
            == ast.dump(expected_leaf_flags, include_attributes=False),
        "loader leaf open lacks nonblocking nofollow flags",
    )
    descriptor_open = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "os"
        and node.func.attr == "open"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "part"
        and any(key.arg == "dir_fd" for key in node.keywords)
        for node in ast.walk(pin)
    )
    require(descriptor_open, "ancestor walk missing descriptor-relative open")
    require(has_method(pin, "fstat") and has_method(pin, "lstat"), "ancestor walk missing identity check")
    require(has_method(pin, "close"), "ancestor walk missing FD cleanup")
    # AST presence of an os.open(part, dir_fd=fd) call is insufficient:
    # a preceding return or a dead branch can leave the walk unreachable.
    pin_body = [
        statement for statement in pin.body
        if not (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str))
    ]
    require(
        bool(pin_body)
        and not any(isinstance(statement, (ast.Return, ast.Raise))
                    for statement in pin_body[:-1]),
        "ancestor pin exits before checked walk",
    )
    walk_try = pin_body[-1]
    require(
        isinstance(walk_try, ast.Try)
        and len(walk_try.body) >= 2
        and isinstance(walk_try.body[-2], ast.For)
        and isinstance(walk_try.body[-1], ast.Return)
        and isinstance(walk_try.body[-1].value, ast.Name)
        and walk_try.body[-1].value.id == "fd"
        and isinstance(walk_try.body[-2].iter, ast.Attribute)
        and isinstance(walk_try.body[-2].iter.value, ast.Name)
        and walk_try.body[-2].iter.value.id == "relative"
        and walk_try.body[-2].iter.attr == "parts",
        "ancestor pin missing live relative-parts walk",
    )
    require(
        not any(isinstance(statement, (ast.Return, ast.Raise))
                for statement in walk_try.body[:-2]),
        "ancestor pin exits before checked walk",
    )
    expected_anchor_metadata = ast.parse("""try:
    opened = os.fstat(fd)
    entry = anchor.lstat()
except (OSError, RuntimeError):
    raise Fail("fixture guard parent metadata read failed") from None
""").body[0]
    expected_cursor_metadata = ast.parse("""try:
    opened = os.fstat(fd)
    entry = cursor.lstat()
except (OSError, RuntimeError):
    raise Fail("fixture guard parent metadata read failed") from None
""").body[0]
    require(
        len(walk_try.body) >= 3
        and ast.dump(walk_try.body[0], include_attributes=False)
            == ast.dump(expected_anchor_metadata, include_attributes=False),
        "loader anchor metadata fault not private",
    )
    walk_loop = walk_try.body[-2]
    expected_cursor_condition = ast.parse(
        "cursor.is_dir() and not cursor.is_symlink()", mode="eval"
    ).body
    expected_cursor_handler = ast.parse("""try:
    pass
except (OSError, RuntimeError):
    raise Fail("fixture guard ancestor predicate check failed") from None
""").body[0].handlers[0]
    cursor_try = walk_loop.body[1]
    cursor_require = walk_loop.body[2]
    require(
        isinstance(cursor_try, ast.Try)
        and len(cursor_try.body) == 1
        and isinstance(cursor_try.body[0], ast.Assign)
        and len(cursor_try.body[0].targets) == 1
        and isinstance(cursor_try.body[0].targets[0], ast.Name)
        and cursor_try.body[0].targets[0].id == "cursor_ok"
        and ast.dump(cursor_try.body[0].value, include_attributes=False)
            == ast.dump(expected_cursor_condition, include_attributes=False)
        and len(cursor_try.handlers) == 1
        and ast.dump(cursor_try.handlers[0], include_attributes=False)
            == ast.dump(expected_cursor_handler, include_attributes=False)
        and not cursor_try.orelse and not cursor_try.finalbody
        and isinstance(cursor_require, ast.Expr)
        and isinstance(cursor_require.value, ast.Call)
        and isinstance(cursor_require.value.func, ast.Name)
        and cursor_require.value.func.id == "require"
        and len(cursor_require.value.args) == 2
        and isinstance(cursor_require.value.args[0], ast.Name)
        and cursor_require.value.args[0].id == "cursor_ok",
        "loader ancestor predicate fault not private",
    )
    require(
        len(walk_loop.body) >= 4
        and isinstance(walk_loop.body[3], ast.Assign)
        and len(walk_loop.body[3].targets) == 1
        and isinstance(walk_loop.body[3].targets[0], ast.Name)
        and walk_loop.body[3].targets[0].id == "next_fd"
        and isinstance(walk_loop.body[3].value, ast.Call)
        and isinstance(walk_loop.body[3].value.func, ast.Attribute)
        and isinstance(walk_loop.body[3].value.func.value, ast.Name)
        and walk_loop.body[3].value.func.value.id == "os"
        and walk_loop.body[3].value.func.attr == "open"
        and walk_loop.body[3].value.args
        and isinstance(walk_loop.body[3].value.args[0], ast.Name)
        and walk_loop.body[3].value.args[0].id == "part"
        and any(keyword.arg == "dir_fd"
                and isinstance(keyword.value, ast.Name)
                and keyword.value.id == "fd"
                for keyword in walk_loop.body[3].value.keywords),
        "ancestor pin descriptor open not live",
    )
    require(
        len(walk_loop.body) >= 9
        and ast.dump(walk_loop.body[7], include_attributes=False)
            == ast.dump(expected_cursor_metadata, include_attributes=False),
        "loader ancestor metadata fault not private",
    )
    expected_handoff = ast.parse("""next_fd = os.open(part, flags, dir_fd=fd)
previous_fd = fd
fd = next_fd
try:
    os.close(previous_fd)
except (Exception, SystemExit):
    raise Fail("fixture guard pinned descriptor cleanup failed") from None
""").body
    require(
        len(walk_loop.body) >= 7
        and all(
            ast.dump(actual, include_attributes=False)
            == ast.dump(expected, include_attributes=False)
            for actual, expected in zip(walk_loop.body[3:7], expected_handoff)
        ),
        "ancestor pin handoff not cleanup-safe",
    )
    # The checked leaf FD must supply the executed bytes; merely opening a
    # pinned FD before a later pathname read does not prevent import TOCTOU.
    loader_try = live_statements[1]
    source_open_try = loader_try.body[0]
    source_open_handlers = source_open_try.handlers if isinstance(source_open_try, ast.Try) else []
    require(
        len(source_open_handlers) == 2
        and isinstance(source_open_handlers[0].type, ast.Name)
        and source_open_handlers[0].type.id == "OSError"
        and source_open_handlers[0].name is None
        and len(source_open_handlers[0].body) == 1
        and isinstance(source_open_handlers[0].body[0], ast.Raise)
        and isinstance(source_open_handlers[0].body[0].cause, ast.Constant)
        and source_open_handlers[0].body[0].cause.value is None
        and isinstance(source_open_handlers[0].body[0].exc, ast.Call)
        and isinstance(source_open_handlers[0].body[0].exc.func, ast.Name)
        and source_open_handlers[0].body[0].exc.func.id == "Fail"
        and len(source_open_handlers[0].body[0].exc.args) == 1
        and isinstance(source_open_handlers[0].body[0].exc.args[0], ast.Constant)
        and isinstance(source_open_handlers[0].body[0].exc.args[0].value, str)
        and source_open_handlers[0].body[0].exc.args[0].value.endswith(
            "fixture guard source open failed")
        and not source_open_try.orelse and not source_open_try.finalbody,
        "loader source open failure not private",
    )
    expected_runtime_open = (
        "try:\n"
        "    pass\n"
        "except RuntimeError as exc:\n"
        "    if isinstance(exc, Fail):\n"
        "        raise\n"
        f"    raise Fail({source_open_handlers[0].body[0].exc.args[0].value!r}) from None\n"
    )
    require(
        ast.dump(source_open_handlers[1], include_attributes=False)
        == ast.dump(ast.parse(expected_runtime_open).body[0].handlers[0],
                    include_attributes=False),
        "loader source runtime open failure not private",
    )
    read_try = loader_try.body[1] if len(loader_try.body) > 1 else None
    expected_owned_duplicate = ast.parse("""duplicated_fd = os.dup(fd)
try:
    with os.fdopen(duplicated_fd, "rb") as stream:
        duplicated_fd = -1
        source = stream.read(MAX_HELPER_SOURCE_BYTES + 1)
finally:
    if duplicated_fd >= 0:
        try:
            os.close(duplicated_fd)
        except (Exception, SystemExit):
            raise Fail("fixture guard pinned descriptor cleanup failed") from None
""").body
    require(
        isinstance(read_try, ast.Try)
        and len(read_try.body) >= 6
        and len(expected_owned_duplicate) == 2
        and all(ast.dump(actual, include_attributes=False)
                == ast.dump(expected, include_attributes=False)
                for actual, expected in zip(read_try.body[3:5], expected_owned_duplicate))
        and ast.dump(read_try.body[-2], include_attributes=False)
        == ast.dump(ast.parse("""try:
    spec.loader.exec_module(module)
except Fail:
    raise
except (Exception, SystemExit):
    raise Fail("fixture guard pinned module execution failed") from None
""").body[0], include_attributes=False)
        and ast.dump(read_try.body[5], include_attributes=False)
        == ast.dump(ast.parse(
            "require(len(source) <= MAX_HELPER_SOURCE_BYTES, 'fixture guard pinned source oversized')"
        ).body[0], include_attributes=False)
        and isinstance(read_try.body[-1], ast.Return)
        and isinstance(read_try.body[-1].value, ast.Name)
        and read_try.body[-1].value.id == "module",
        "loader source execution not pinned to FD",
    )
    loader_text = ast.get_source_segment(source, loaders[0]) or ""
    for token in (
        "class PinnedSourceLoader(importlib.machinery.SourceFileLoader):",
        "def get_code(self, fullname):",
        'require(fullname == name, "fixture guard module identity drift")',
        'return compile(source, str(path), "exec")',
        "loader=PinnedSourceLoader(name, str(path))",
        "spec.loader.exec_module(module)",
    ):
        require(token in loader_text, "loader source execution not pinned to FD")
    # A malformed helper cannot leak source/path details through compile().
    pinned_classes = [node for node in ast.walk(loaders[0])
                      if isinstance(node, ast.ClassDef) and node.name == "PinnedSourceLoader"]
    require(len(pinned_classes) == 1, "loader compilation failure not private")
    get_code_methods = [node for node in pinned_classes[0].body
                        if isinstance(node, ast.FunctionDef) and node.name == "get_code"]
    require(len(get_code_methods) == 1 and len(get_code_methods[0].body) == 2,
            "loader compilation failure not private")
    compile_try = get_code_methods[0].body[1]
    require(
        isinstance(compile_try, ast.Try)
        and len(compile_try.body) == 1
        and ast.dump(compile_try.body[0], include_attributes=False)
        == ast.dump(ast.parse('return compile(source, str(path), "exec")').body[0], include_attributes=False)
        and len(compile_try.handlers) == 1
        and isinstance(compile_try.handlers[0].type, ast.Tuple)
        and len(compile_try.handlers[0].type.elts) == 2
        and [elt.id for elt in compile_try.handlers[0].type.elts
             if isinstance(elt, ast.Name)] == ["Exception", "SystemExit"]
        and len(compile_try.handlers[0].body) == 1
        and ast.dump(compile_try.handlers[0].body[0], include_attributes=False)
        == ast.dump(ast.parse('raise Fail("fixture guard pinned source compilation failed") from None').body[0], include_attributes=False)
        and not compile_try.orelse and not compile_try.finalbody,
        "loader compilation failure not private",
    )
    expected_leaf_cleanup = ast.parse("""try:
    os.close(fd)
except (Exception, SystemExit):
    raise Fail("fixture guard pinned descriptor cleanup failed") from None
""").body[0]
    expected_parent_cleanup = ast.parse("""try:
    os.close(parent_fd)
except (Exception, SystemExit):
    raise Fail("fixture guard pinned descriptor cleanup failed") from None
""").body[0]
    setup_try = read_try.body[-3]
    expected_spec_assignment = ast.parse(
        'spec = importlib.util.spec_from_file_location(name, path, loader=PinnedSourceLoader(name, str(path)))'
    ).body[0]
    expected_module_assignment = ast.parse(
        'module = importlib.util.module_from_spec(spec)'
    ).body[0]
    expected_setup_condition = ast.parse(
        'spec is not None and spec.loader is not None', mode='eval'
    ).body
    require(
        isinstance(setup_try, ast.Try)
        and len(setup_try.body) == 3
        and ast.dump(setup_try.body[0], include_attributes=False)
            == ast.dump(expected_spec_assignment, include_attributes=False)
        and ast.dump(setup_try.body[2], include_attributes=False)
            == ast.dump(expected_module_assignment, include_attributes=False)
        and isinstance(setup_try.body[1], ast.Expr)
        and isinstance(setup_try.body[1].value, ast.Call)
        and isinstance(setup_try.body[1].value.func, ast.Name)
        and setup_try.body[1].value.func.id == "require"
        and len(setup_try.body[1].value.args) == 2
        and not setup_try.body[1].value.keywords
        and ast.dump(setup_try.body[1].value.args[0], include_attributes=False)
            == ast.dump(expected_setup_condition, include_attributes=False)
        and isinstance(setup_try.body[1].value.args[1], ast.Constant)
        and isinstance(setup_try.body[1].value.args[1].value, str)
        and setup_try.body[1].value.args[1].value.endswith("fixture guard cannot load"),
        "loader module setup binding drift",
    )
    expected_setup_handlers = ast.parse("""try:
    pass
except Fail:
    raise
except (Exception, SystemExit):
    raise Fail("fixture guard pinned module setup failed") from None
""").body[0].handlers
    require(
        isinstance(setup_try, ast.Try)
        and len(setup_try.body) == 3
        and isinstance(setup_try.body[0], ast.Assign)
        and len(setup_try.body[0].targets) == 1
        and isinstance(setup_try.body[0].targets[0], ast.Name)
        and setup_try.body[0].targets[0].id == "spec"
        and isinstance(setup_try.body[1], ast.Expr)
        and isinstance(setup_try.body[1].value, ast.Call)
        and isinstance(setup_try.body[1].value.func, ast.Name)
        and setup_try.body[1].value.func.id == "require"
        and isinstance(setup_try.body[2], ast.Assign)
        and len(setup_try.body[2].targets) == 1
        and isinstance(setup_try.body[2].targets[0], ast.Name)
        and setup_try.body[2].targets[0].id == "module"
        and len(setup_try.handlers) == 2
        and all(ast.dump(actual, include_attributes=False)
                == ast.dump(expected, include_attributes=False)
                for actual, expected in zip(setup_try.handlers, expected_setup_handlers))
        and not setup_try.orelse and not setup_try.finalbody,
        "loader module setup failure not private",
    )
    require(
        len(read_try.finalbody) == 1
        and ast.dump(read_try.finalbody[0], include_attributes=False)
        == ast.dump(expected_leaf_cleanup, include_attributes=False)
        and len(loader_try.finalbody) == 1
        and ast.dump(loader_try.finalbody[0], include_attributes=False)
        == ast.dump(expected_parent_cleanup, include_attributes=False),
        "loader FD cleanup not guaranteed",
    )
    read_handlers = read_try.handlers
    require(
        len(read_handlers) == 2
        and isinstance(read_handlers[0].type, ast.Name)
        and read_handlers[0].type.id == "OSError"
        and read_handlers[0].name is None
        and len(read_handlers[0].body) == 1
        and isinstance(read_handlers[0].body[0], ast.Raise)
        and isinstance(read_handlers[0].body[0].cause, ast.Constant)
        and read_handlers[0].body[0].cause.value is None
        and isinstance(read_handlers[0].body[0].exc, ast.Call)
        and isinstance(read_handlers[0].body[0].exc.func, ast.Name)
        and read_handlers[0].body[0].exc.func.id == "Fail"
        and len(read_handlers[0].body[0].exc.args) == 1
        and isinstance(read_handlers[0].body[0].exc.args[0], ast.Constant)
        and isinstance(read_handlers[0].body[0].exc.args[0].value, str)
        and read_handlers[0].body[0].exc.args[0].value.endswith("pinned source read failed"),
        "loader read failure not private",
    )
    expected_runtime_read = (
        "try:\n"
        "    pass\n"
        "except RuntimeError as exc:\n"
        "    if isinstance(exc, Fail):\n"
        "        raise\n"
        f"    raise Fail({read_handlers[0].body[0].exc.args[0].value!r}) from None\n"
    )
    require(
        ast.dump(read_handlers[1], include_attributes=False)
        == ast.dump(ast.parse(expected_runtime_read).body[0].handlers[0],
                    include_attributes=False),
        "loader runtime read failure not private",
    )
    # Classify untrusted parent paths before any descriptor is opened.
    # Intentional outside-root ValueError remains a distinct domain failure.
    expected_classification = ast.parse("""try:
    anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
except (OSError, RuntimeError):
    raise Fail("fixture guard parent classification failed") from None
""").body[0]
    expected_relative_assignment = ast.parse(
        "relative = path.parent.relative_to(anchor)"
    ).body[0]
    expected_relative_handler = ast.parse("""try:
    pass
except (OSError, RuntimeError):
    raise Fail("fixture guard parent classification failed") from None
""").body[0].handlers[0]
    pin_live = [
        node for node in pin.body
        if not (isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str))
    ]
    relative_guard = pin_live[2] if len(pin_live) > 2 else None
    require(
        len(pin_live) >= 4
        and ast.dump(pin_live[1], include_attributes=False)
            == ast.dump(expected_classification, include_attributes=False)
        and isinstance(relative_guard, ast.Try)
        and len(relative_guard.body) == 1
        and ast.dump(relative_guard.body[0], include_attributes=False)
            == ast.dump(expected_relative_assignment, include_attributes=False)
        and len(relative_guard.handlers) == 2
        and isinstance(relative_guard.handlers[0].type, ast.Name)
        and relative_guard.handlers[0].type.id == "ValueError"
        and ast.dump(relative_guard.handlers[1], include_attributes=False)
            == ast.dump(expected_relative_handler, include_attributes=False)
        and not relative_guard.orelse and not relative_guard.finalbody,
        "loader parent classification fault not private",
    )
    # A present but zeroed platform flag is not a no-follow/directory guard.
    expected_flags = ast.parse(
        "type(getattr(os, 'O_NOFOLLOW', None)) is int"
        " and os.O_NOFOLLOW > 0"
        " and type(getattr(os, 'O_DIRECTORY', None)) is int"
        " and os.O_DIRECTORY > 0"
        " and type(getattr(os, 'O_NONBLOCK', None)) is int"
        " and os.O_NONBLOCK > 0", mode="eval"
    ).body
    first_pin_statement = pin_live[0] if pin_live else None
    require(
        isinstance(first_pin_statement, ast.Expr)
        and isinstance(first_pin_statement.value, ast.Call)
        and isinstance(first_pin_statement.value.func, ast.Name)
        and first_pin_statement.value.func.id == "require"
        and len(first_pin_statement.value.args) == 2
        and ast.dump(first_pin_statement.value.args[0], include_attributes=False)
            == ast.dump(expected_flags, include_attributes=False)
        and isinstance(first_pin_statement.value.args[1], ast.Constant)
        and isinstance(first_pin_statement.value.args[1].value, str)
        and first_pin_statement.value.args[1].value.endswith(
            "no-follow directory open unsupported"),
        "loader unsupported platform flags accepted",
    )
    require(
        has_method(proof, "rename") and has_method(proof, "symlink_to"),
        "ancestor proof missing deterministic substitution",
    )


def negative_cases(source: str, diagnostic: str) -> int:
    original_proof_diagnostic = diagnostic
    replacements = (
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    pass  # synthetic dropped proof\n", "main missing direct ancestor proof"),
        (f'"{diagnostic}"', '"synthetic wrong ancestor diagnostic"',
         "ancestor proof missing exact diagnostic"),
        ("    parent_fd = pin_checked_helper_parent(path)\n",
         "    parent_fd = -1\n", "loader missing pinned parent call"),
        ("            next_fd = os.open(part, flags, dir_fd=fd)\n",
         "            next_fd = os.open(cursor, flags)\n",
         "ancestor walk missing descriptor-relative open"),
    )
    replacements += (
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    return 0  # synthetic early exit\n"
         "    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "main exits before ancestor proof"),
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    raise SystemExit(0)  # synthetic early exit\n"
         "    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "main exits before ancestor proof"),
        ('if __name__ == "__main__":',
         'if False:  # synthetic disabled dispatch',
         "missing canonical __main__ dispatch"),
        ("        raise SystemExit(main())\n",
         "        raise SystemExit(0)  # synthetic skipped main\n",
         "canonical __main__ dispatch does not execute main"),
        ("    parent_fd = pin_checked_helper_parent(path)\n",
         "    if False: pin_checked_helper_parent(path)  # dead pin call\n"
         "    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)\n",
         "loader parent FD not bound to checked ancestors"),
        ("            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)\n",
         "            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)\n",
         "loader leaf open not bound to checked parent FD"),
        ('if __name__ == "__main__":',
         'main = lambda: 0  # synthetic shadowed main\n\nif __name__ == "__main__":',
         "module binding shadowed: main"),
        ('if __name__ == "__main__":',
         'prove_helper_ancestor_swap_during_fd_walk_rejected = lambda: None\n\nif __name__ == "__main__":',
         "module binding shadowed: prove_helper_ancestor_swap_during_fd_walk_rejected"),
        ('if __name__ == "__main__":',
         'pin_checked_helper_parent = lambda path: -1\n\nif __name__ == "__main__":',
         "module binding shadowed: pin_checked_helper_parent"),
    )
    replacements += tuple(
        ('if __name__ == "__main__":',
         injection + '\n\nif __name__ == "__main__":', expected)
        for injection, expected in (
            ("if False: main = lambda: 0  # synthetic nested shadow",
             "module binding shadowed: main"),
            ("main, synthetic_unused = (lambda: 0), None",
             "module binding shadowed: main"),
            ('globals()["main"] = None', "module dynamic binding mutation"),
            ("globals().update(main=None)", "module dynamic binding mutation"),
            ('exec("main = None")', "module dynamic binding mutation"),
            ('setattr(sys.modules[__name__], "main", None)',
             "module dynamic binding mutation"),
            ("class main: pass", "module binding shadowed: main"),
            ('globals().pop("main")', "module dynamic binding mutation"),
        )
    )
    replacements += tuple(
        ("    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "    " + injection + "\n"
         "    prove_helper_ancestor_swap_during_fd_walk_rejected()\n",
         "main pre-proof binding mutation")
        for injection in (
            'globals()["prove_helper_ancestor_swap_during_fd_walk_rejected"] = lambda: None',
            'globals().update(prove_helper_ancestor_swap_during_fd_walk_rejected=lambda: None)',
            'exec("prove_helper_ancestor_swap_during_fd_walk_rejected = lambda: None")',
            'prove_helper_ancestor_swap_during_fd_walk_rejected = lambda: None',
            'setattr(sys.modules[__name__], "prove_helper_ancestor_swap_during_fd_walk_rejected", lambda: None)',
        )
    )
    loader_definition = (
        "def load_pinned_fixture_helper(path: Path, name: str):"
        if "def load_pinned_fixture_helper(path: Path, name: str):" in source
        else "def load_pinned_fixture_guard(path: Path, name: str):"
    )
    replacements += tuple(
        (definition, "@property\n" + definition,
         "decorated guarded function: " + name)
        for definition, name in (
            ("def main() -> int:", "main"),
            ("def prove_helper_ancestor_swap_during_fd_walk_rejected() -> None:", PROOF),
            ("def pin_checked_helper_parent(path: Path) -> int:", PIN),
            (loader_definition, loader_definition.split("(")[0].removeprefix("def ")),
        )
    )
    dispatch_anchor = (
        'if __name__ == "__main__":\n'
        '    try:\n'
        '        raise SystemExit(main())\n'
        '    except Fail as exc:\n'
    )
    replacements += (
        (dispatch_anchor,
         dispatch_anchor.replace('    try:\n', '    pass\n    try:\n'),
         "canonical __main__ dispatch shape drift"),
        (dispatch_anchor,
         dispatch_anchor.replace('    except Fail as exc:\n',
                                 '    except BaseException as exc:\n'),
         "canonical __main__ dispatch handler drift"),
        (dispatch_anchor,
         dispatch_anchor.replace('    except Fail as exc:\n',
                                 '    except BaseException:\n        pass\n    except Fail as exc:\n'),
         "canonical __main__ dispatch handler drift"),
        (dispatch_anchor,
         dispatch_anchor.replace('        raise SystemExit(main())\n',
                                 '        print("synthetic bypass")\n        raise SystemExit(main())\n'),
         "canonical __main__ dispatch shape drift"),
        ("        raise SystemExit(1)\n",
         "        pass  # synthetic swallowed failure\n",
         "canonical __main__ dispatch handler drift"),
    )
    replacements += (
        ('    require(\n        type(getattr(os, "O_NOFOLLOW", None)) is int\n',
         '    return os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)\n'
         '    require(\n        type(getattr(os, "O_NOFOLLOW", None)) is int\n',
         "ancestor pin exits before checked walk"),
        ("        for part in relative.parts:\n",
         "        return fd  # synthetic skipped ancestor walk\n"
         "        for part in relative.parts:\n",
         "ancestor pin exits before checked walk"),
        ("        for part in relative.parts:\n",
         "        for part in ():\n",
         "ancestor pin missing live relative-parts walk"),
        ("            next_fd = os.open(part, flags, dir_fd=fd)\n",
         "            if False:\n"
         "                next_fd = os.open(part, flags, dir_fd=fd)\n",
         "ancestor pin descriptor open not live"),
        ("        return fd\n",
         "        return -1  # synthetic unbound return\n",
         "ancestor pin missing live relative-parts walk"),
    )
    replacements += (
        ("                    source = stream.read(MAX_HELPER_SOURCE_BYTES + 1)\n",
         "                    source = path.read_bytes()\n",
         "loader source execution not pinned to FD"),
        ('                with os.fdopen(duplicated_fd, "rb") as stream:\n',
         '                with open(path, "rb") as stream:\n',
         "loader source execution not pinned to FD"),
        ("            duplicated_fd = os.dup(fd)\n",
         "            duplicated_fd = fd\n",
         "loader source execution not pinned to FD"),
        ("                    duplicated_fd = -1\n",
         "                    duplicated_fd = fd\n",
         "loader source execution not pinned to FD"),
        ("                if duplicated_fd >= 0:\n",
         "                if False:\n",
         "loader source execution not pinned to FD"),
        ("                        os.close(duplicated_fd)\n",
         "                        pass  # synthetic duplicate FD leak\n",
         "loader source execution not pinned to FD"),
        ('                        raise Fail("fixture guard pinned descriptor cleanup failed") from None\n',
         '                        raise Fail("fixture guard pinned descriptor cleanup failed")\n',
         "loader source execution not pinned to FD"),
        ('                    return compile(source, str(path), "exec")\n',
         '                    return compile(path.read_bytes(), str(path), "exec")\n',
         "loader source execution not pinned to FD"),
        ('            spec.loader.exec_module(module)\n',
         '            pass  # synthetic skipped pinned loader execution\n',
         "loader source execution not pinned to FD"),
        ('            spec = importlib.util.spec_from_file_location(name, path, loader=PinnedSourceLoader(name, str(path)))\n',
         '            spec = importlib.util.spec_from_file_location(name, path)\n',
         "loader source execution not pinned to FD"),
        ('                    require(fullname == name, "fixture guard module identity drift")\n',
         '                    require(True, "fixture guard module identity drift")\n',
         "loader source execution not pinned to FD"),
        ("            require(len(source) <= MAX_HELPER_SOURCE_BYTES,\n",
         "            require(True,\n",
         "loader source execution not pinned to FD"),
        ("MAX_HELPER_SOURCE_BYTES = 1024 * 1024\n",
         "MAX_HELPER_SOURCE_BYTES = 1024 * 1024 * 1024\n",
         "loader source execution not pinned to FD"),
        ("        finally:\n            try:\n                os.close(fd)\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None\n    finally:\n",
         "        finally:\n            pass  # synthetic leaked leaf FD\n    finally:\n",
         "loader FD cleanup not guaranteed"),
        ("    finally:\n        try:\n            os.close(parent_fd)\n        except (Exception, SystemExit):\n            raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None",
         "    finally:\n        pass  # synthetic leaked parent FD\n",
         "loader FD cleanup not guaranteed"),
        ("        finally:\n            try:\n                os.close(fd)\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None\n    finally:\n",
         "        finally:\n            try:\n                os.close(fd)\n            except OSError:\n                raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None\n    finally:\n",
         "loader FD cleanup not guaranteed"),
        ("    finally:\n        try:\n            os.close(parent_fd)\n        except (Exception, SystemExit):\n            raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None",
         "    finally:\n        try:\n            os.close(parent_fd)\n        except OSError:\n            raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None",
         "loader FD cleanup not guaranteed"),
        ("        finally:\n            try:\n                os.close(fd)\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None\n    finally:\n",
         "        finally:\n            try:\n                os.close(fd)\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned descriptor cleanup failed\")\n    finally:\n",
         "loader FD cleanup not guaranteed"),
        ("    finally:\n        try:\n            os.close(parent_fd)\n        except (Exception, SystemExit):\n            raise Fail(\"fixture guard pinned descriptor cleanup failed\") from None",
         "    finally:\n        try:\n            os.close(parent_fd)\n        except (Exception, SystemExit):\n            raise Fail(\"fixture guard pinned descriptor cleanup failed\")",
         "loader FD cleanup not guaranteed"),
    )
    replacements += (
        ('                    try:\n                        return compile(source, str(path), "exec")\n                    except (Exception, SystemExit):\n',
         '                    try:\n                        return compile(source, str(path), "exec")\n                    except SyntaxError:\n',
         "loader compilation failure not private"),
        ('                    try:\n                        return compile(source, str(path), "exec")\n                    except (Exception, SystemExit):\n',
         '                    try:\n                        return compile(source, str(path), "exec")\n                    except Exception:\n',
         "loader compilation failure not private"),
        ('                        raise Fail("fixture guard pinned source compilation failed") from None\n',
         '                        raise Fail("fixture guard pinned source compilation failed")\n',
         "loader compilation failure not private"),
        ('                        raise Fail("fixture guard pinned source compilation failed") from None\n',
         '                        raise Fail("synthetic raw compilation failure") from None\n',
         "loader compilation failure not private"),
    )
    source_open_privacy_anchors = re.findall(
        r'        except OSError:\n            raise Fail\("[^"]+ fixture guard source open failed"\) from None\n',
        source,
    )
    require(len(source_open_privacy_anchors) == 1,
            "loader source open failure not private")
    source_open_privacy = source_open_privacy_anchors[0]
    replacements += (
        (source_open_privacy, source_open_privacy.replace(" from None", ""),
         "loader source open failure not private"),
        (source_open_privacy, source_open_privacy.replace(
            "except OSError:", "except FileNotFoundError:"),
         "loader source open failure not private"),
    )
    source_runtime_open_privacy = source_open_privacy.replace(
        "        except OSError:\n",
        "        except RuntimeError as exc:\n"
        "            if isinstance(exc, Fail):\n"
        "                raise\n",
    )
    require(source.count(source_runtime_open_privacy) == 1,
            "loader source runtime open failure not private")
    replacements += (
        (source_runtime_open_privacy, source_runtime_open_privacy.replace(
            "except RuntimeError as exc:", "except ValueError as exc:"),
         "loader source runtime open failure not private"),
        (source_runtime_open_privacy, source_runtime_open_privacy.replace(
            "if isinstance(exc, Fail):", "if False:"),
         "loader source runtime open failure not private"),
        (source_runtime_open_privacy, source_runtime_open_privacy.replace(
            " from None", ""),
         "loader source runtime open failure not private"),
    )
    read_privacy_anchors = re.findall(
        r'        except OSError:\n            raise Fail\("[^"]+ pinned source read failed"\) from None\n',
        source,
    )
    require(len(read_privacy_anchors) == 1, "loader read failure not private")
    read_privacy = read_privacy_anchors[0]
    replacements += (
        (read_privacy, read_privacy.replace(" from None", ""),
         "loader read failure not private"),
        (read_privacy, read_privacy.replace("except OSError:", "except FileNotFoundError:"),
         "loader read failure not private"),
    )
    runtime_read_privacy = read_privacy.replace(
        "        except OSError:\n",
        "        except RuntimeError as exc:\n"
        "            if isinstance(exc, Fail):\n"
        "                raise\n",
    )
    require(source.count(runtime_read_privacy) == 1,
            "loader runtime read failure not private")
    replacements += (
        (runtime_read_privacy, runtime_read_privacy.replace(
            "except RuntimeError as exc:", "except ValueError as exc:"),
         "loader runtime read failure not private"),
        (runtime_read_privacy, runtime_read_privacy.replace(
            "if isinstance(exc, Fail):", "if False:"),
         "loader runtime read failure not private"),
        (runtime_read_privacy, runtime_read_privacy.replace(
            " from None", ""),
         "loader runtime read failure not private"),
    )
    replacements += (
        ("            try:\n                spec.loader.exec_module(module)\n            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module execution failed\") from None\n",
         "            try:\n                spec.loader.exec_module(module)\n            except Fail:\n                raise\n            except Exception:\n                raise Fail(\"fixture guard pinned module execution failed\") from None\n",
         "loader source execution not pinned to FD"),
        ("            try:\n                spec.loader.exec_module(module)\n            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module execution failed\") from None\n",
         "            try:\n                spec.loader.exec_module(module)\n            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module execution failed\")\n",
         "loader source execution not pinned to FD"),
        ("            try:\n                spec.loader.exec_module(module)\n            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module execution failed\") from None\n",
         "            try:\n                spec.loader.exec_module(module)\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module execution failed\") from None\n",
         "loader source execution not pinned to FD"),
    )
    replacements += (
        ("            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module setup failed\") from None\n",
         "            except Fail:\n                raise\n            except Exception:\n                raise Fail(\"fixture guard pinned module setup failed\") from None\n",
         "loader module setup failure not private"),
        ("            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module setup failed\") from None\n",
         "            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module setup failed\")\n",
         "loader module setup failure not private"),
        ("            except Fail:\n                raise\n            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module setup failed\") from None\n",
         "            except (Exception, SystemExit):\n                raise Fail(\"fixture guard pinned module setup failed\") from None\n",
         "loader module setup failure not private"),
    )
    pin_privacy_cases = (
        (r'    except ValueError:\n        raise Fail\("[^"]+ fixture guard parent outside trusted roots"\) from None\n',
         "except ValueError:", "except TypeError:"),
        (r'    except \(OSError, RuntimeError\):\n        raise Fail\("[^"]+ fixture guard anchor open failed"\) from None\n',
         "except (OSError, RuntimeError):", "except OSError:"),
        (r'    except OSError:\n        try:\n            os.close\(fd\)\n        except \(Exception, SystemExit\):\n            raise Fail\("fixture guard pinned descriptor cleanup failed"\) from None\n        raise Fail\("[^"]+ fixture guard parent open failed"\) from None\n',
         "except OSError:", "except FileNotFoundError:"),
    )
    for pattern, original_handler, narrowed_handler in pin_privacy_cases:
        anchors = re.findall(pattern, source)
        require(len(anchors) == 1, "loader parent pin failure not private")
        anchor = anchors[0]
        replacements += (
            (anchor, anchor.replace(" from None", ""),
             "loader parent pin failure not private"),
            (anchor, anchor.replace(original_handler, narrowed_handler),
             "loader parent pin failure not private"),
        )
        if "fixture guard anchor open failed" in anchor:
            replacements += (
                (anchor, anchor.replace(
                    "except (OSError, RuntimeError):", "except RuntimeError:"),
                 "loader parent pin failure not private"),
            )
        if "fixture guard parent open failed" in anchor:
            cleanup = (
                "        try:\n"
                "            os.close(fd)\n"
                "        except (Exception, SystemExit):\n"
                '            raise Fail("fixture guard pinned descriptor cleanup failed") from None\n'
            )
            require(cleanup in anchor, "loader parent pin failure not private")
            replacements += (
                (anchor, anchor.replace("except (Exception, SystemExit):",
                                        "except OSError:"),
                 "loader parent pin failure not private"),
                (anchor, anchor.replace(
                    'raise Fail("fixture guard pinned descriptor cleanup failed") from None',
                    'raise Fail("fixture guard pinned descriptor cleanup failed")'),
                 "loader parent pin failure not private"),
                (anchor, anchor.replace(cleanup, "        os.close(fd)\n"),
                 "loader parent pin failure not private"),
            )
    handoff_anchor = (
        "            next_fd = os.open(part, flags, dir_fd=fd)\n"
        "            previous_fd = fd\n"
        "            fd = next_fd\n"
        "            try:\n"
        "                os.close(previous_fd)\n"
        "            except (Exception, SystemExit):\n"
        '                raise Fail("fixture guard pinned descriptor cleanup failed") from None\n'
    )
    require(source.count(handoff_anchor) == 1,
            "ancestor pin handoff not cleanup-safe")
    replacements += (
        (handoff_anchor, handoff_anchor.replace(
            "            fd = next_fd\n", "            fd = previous_fd\n"),
         "ancestor pin handoff not cleanup-safe"),
        (handoff_anchor, handoff_anchor.replace(
            "os.close(previous_fd)", "os.close(fd)"),
         "ancestor pin handoff not cleanup-safe"),
        (handoff_anchor, handoff_anchor.replace(
            "except (Exception, SystemExit):", "except OSError:"),
         "ancestor pin handoff not cleanup-safe"),
        (handoff_anchor, handoff_anchor.replace(" from None", ""),
         "ancestor pin handoff not cleanup-safe"),
    )
    anchor_start = """    try:
        anchor_ok = anchor.is_dir() and not anchor.is_symlink()
"""
    anchor_end = """    except (OSError, RuntimeError):
        raise Fail("fixture guard trusted anchor check failed") from None
"""
    require(source.count(anchor_start) == 1 and source.count(anchor_end) == 1,
            "loader anchor predicate fault not private")
    anchor_begin = source.index(anchor_start)
    anchor_finish = source.index(anchor_end, anchor_begin) + len(anchor_end)
    anchor_guard = source[anchor_begin:anchor_finish]
    replacements += (
        (anchor_guard, anchor_guard.replace(
            "except (OSError, RuntimeError):", "except OSError:"),
         "loader anchor predicate fault not private"),
        (anchor_guard, anchor_guard.replace(" from None", ""),
         "loader anchor predicate fault not private"),
        (anchor_guard, anchor_guard.replace("anchor.is_dir()", "True"),
         "loader anchor predicate fault not private"),
        (anchor_guard, anchor_guard.replace("not anchor.is_symlink()", "True"),
         "loader anchor predicate fault not private"),
    )
    cursor_start = """            try:
                cursor_ok = cursor.is_dir() and not cursor.is_symlink()
"""
    cursor_end = """            except (OSError, RuntimeError):
                raise Fail("fixture guard ancestor predicate check failed") from None
            require(cursor_ok,
"""
    require(source.count(cursor_start) == 1 and source.count(cursor_end) == 1,
            "loader ancestor predicate fault not private")
    cursor_begin = source.index(cursor_start)
    cursor_finish = source.index(cursor_end, cursor_begin) + len(cursor_end)
    cursor_guard = source[cursor_begin:cursor_finish]
    replacements += (
        (cursor_guard, cursor_guard.replace(
            "except (OSError, RuntimeError):", "except OSError:"),
         "loader ancestor predicate fault not private"),
        (cursor_guard, cursor_guard.replace(" from None", ""),
         "loader ancestor predicate fault not private"),
        (cursor_guard, cursor_guard.replace("cursor.is_dir()", "True"),
         "loader ancestor predicate fault not private"),
        (cursor_guard, cursor_guard.replace("not cursor.is_symlink()", "True"),
         "loader ancestor predicate fault not private"),
    )
    anchor_metadata = """        try:
            opened = os.fstat(fd)
            entry = anchor.lstat()
        except (OSError, RuntimeError):
            raise Fail("fixture guard parent metadata read failed") from None
"""
    cursor_metadata = """            try:
                opened = os.fstat(fd)
                entry = cursor.lstat()
            except (OSError, RuntimeError):
                raise Fail("fixture guard parent metadata read failed") from None
"""
    require(source.count(anchor_metadata) == 1
            and source.count(cursor_metadata) == 1,
            "loader parent metadata fault not private")
    for metadata, metadata_diagnostic in (
        (anchor_metadata, "loader anchor metadata fault not private"),
        (cursor_metadata, "loader ancestor metadata fault not private"),
    ):
        replacements += (
            (metadata, metadata.replace(
                "except (OSError, RuntimeError):", "except OSError:"),
             metadata_diagnostic),
            (metadata, metadata.replace(" from None", ""), metadata_diagnostic),
            (metadata, metadata.replace("os.fstat(fd)", "os.stat(fd)"),
             metadata_diagnostic),
            (metadata, metadata.replace(".lstat()", ".stat()"), metadata_diagnostic),
        )
    anchor_classification = """    try:
        anchor = ROOT if path.is_relative_to(ROOT) else Path(tempfile.gettempdir())
    except (OSError, RuntimeError):
        raise Fail("fixture guard parent classification failed") from None
"""
    relative_start = "    try:\n        relative = path.parent.relative_to(anchor)\n"
    relative_end = "    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW\n"
    require(source.count(anchor_classification) == 1
            and source.count(relative_start) == 1
            and source.count(relative_end) == 1,
            "loader parent classification fault not private")
    relative_begin = source.index(relative_start)
    relative_finish = source.index(relative_end, relative_begin)
    relative_classification = source[relative_begin:relative_finish]
    require(relative_classification.count(
        'raise Fail("fixture guard parent classification failed") from None'
    ) == 1, "loader parent classification fault not private")
    replacements += (
        (anchor_classification, anchor_classification.replace(
            "except (OSError, RuntimeError):", "except OSError:"),
         "loader parent classification fault not private"),
        (anchor_classification, anchor_classification.replace(" from None", ""),
         "loader parent classification fault not private"),
        (anchor_classification, anchor_classification.replace(
            "path.is_relative_to(ROOT)", "True"),
         "loader parent classification fault not private"),
        (relative_classification, relative_classification.replace(
            "except (OSError, RuntimeError):", "except OSError:"),
         "loader parent classification fault not private"),
        (relative_classification, relative_classification.replace(
            'raise Fail("fixture guard parent classification failed") from None',
            'raise Fail("fixture guard parent classification failed")'),
         "loader parent classification fault not private"),
        (relative_classification, relative_classification.replace(
            "path.parent.relative_to(anchor)", "Path('.')"),
         "loader parent classification fault not private"),
    )
    leaf_open_anchor = (
        "            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)\n"
    )
    require(source.count(leaf_open_anchor) == 1,
            "loader leaf open lacks nonblocking nofollow flags")
    replacements += (
        (leaf_open_anchor, leaf_open_anchor.replace(
            " | os.O_NONBLOCK", ""),
         "loader leaf open lacks nonblocking nofollow flags"),
    )
    platform_flag_guard = """    require(
        type(getattr(os, "O_NOFOLLOW", None)) is int
        and os.O_NOFOLLOW > 0
        and type(getattr(os, "O_DIRECTORY", None)) is int
        and os.O_DIRECTORY > 0
        and type(getattr(os, "O_NONBLOCK", None)) is int
        and os.O_NONBLOCK > 0,
"""
    require(source.count(platform_flag_guard) == 1,
            "loader unsupported platform flags accepted")
    replacements += (
        (platform_flag_guard, platform_flag_guard.replace(
            "os.O_NOFOLLOW > 0", "os.O_NOFOLLOW >= 0"),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            "os.O_DIRECTORY > 0", "os.O_DIRECTORY >= 0"),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            'type(getattr(os, "O_NOFOLLOW", None)) is int', "True"),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            'type(getattr(os, "O_DIRECTORY", None)) is int', "True"),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            "os.O_NONBLOCK > 0", "os.O_NONBLOCK >= 0"),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            'type(getattr(os, "O_NONBLOCK", None)) is int', "True"),
         "loader unsupported platform flags accepted"),
        # An isinstance regression would accept bool (True) as an OS flag.
        (platform_flag_guard, platform_flag_guard.replace(
            'type(getattr(os, "O_NOFOLLOW", None)) is int',
            'isinstance(getattr(os, "O_NOFOLLOW", None), int)'),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            'type(getattr(os, "O_DIRECTORY", None)) is int',
            'isinstance(getattr(os, "O_DIRECTORY", None), int)'),
         "loader unsupported platform flags accepted"),
        (platform_flag_guard, platform_flag_guard.replace(
            'type(getattr(os, "O_NONBLOCK", None)) is int',
            'isinstance(getattr(os, "O_NONBLOCK", None), int)'),
         "loader unsupported platform flags accepted"),
    )
    base_cleanup_anchor = (
        "    except BaseException as exc:\n"
        "        try:\n"
        "            os.close(fd)\n"
        "        except (Exception, SystemExit):\n"
        '            raise Fail("fixture guard pinned descriptor cleanup failed") from None\n'
        "        if isinstance(exc, RuntimeError) and not isinstance(exc, Fail):\n"
        '            raise Fail("fixture guard parent runtime open failed") from None\n'
        "        raise\n"
    )
    require(source.count(base_cleanup_anchor) == 1,
            "loader parent unexpected cleanup not private")
    base_cleanup_block = (
        "        try:\n"
        "            os.close(fd)\n"
        "        except (Exception, SystemExit):\n"
        '            raise Fail("fixture guard pinned descriptor cleanup failed") from None\n'
    )
    replacements += (
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            "except (Exception, SystemExit):", "except OSError:"),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(" from None", ""),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            base_cleanup_block, "        os.close(fd)\n"),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            "        raise\n", "        return fd\n"),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            "not isinstance(exc, Fail)", "True"),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            "isinstance(exc, RuntimeError)", "False"),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            'raise Fail("fixture guard parent runtime open failed") from None',
            'raise Fail("fixture guard parent runtime open failed")'),
         "loader parent unexpected cleanup not private"),
        (base_cleanup_anchor, base_cleanup_anchor.replace(
            'raise Fail("fixture guard parent runtime open failed") from None',
            'raise'),
         "loader parent unexpected cleanup not private"),
    )
    setup_start = (
        "                spec = importlib.util.spec_from_file_location("
        "name, path, loader=PinnedSourceLoader(name, str(path)))\n"
    )
    setup_end = "                module = importlib.util.module_from_spec(spec)\n"
    require(source.count(setup_start) == 1,
            "loader module setup binding drift")
    setup_tail = source.split(setup_start, 1)[1]
    require(setup_end in setup_tail,
            "loader module setup binding drift")
    setup_anchor = setup_start + setup_tail.split(setup_end, 1)[0] + setup_end
    require(setup_anchor.count(
        "                require(spec is not None and spec.loader is not None,") == 1,
        "loader module setup binding drift")
    replacements += (
        (setup_anchor, setup_anchor.replace(
            "spec_from_file_location(name, path, loader=",
            'spec_from_file_location("synthetic_wrong_name", path, loader='),
         "loader module setup binding drift"),
        (setup_anchor, setup_anchor.replace(
            "require(spec is not None and spec.loader is not None,",
            "require(True,"),
         "loader module setup binding drift"),
        (setup_anchor, setup_anchor.replace(
            "module = importlib.util.module_from_spec(spec)",
            "module = object()"),
         "loader module setup binding drift"),
    )
    delegate_anchor = None
    if "typed transport fixture guard source open failed" in source:
        delegate_anchor = "    return load_pinned_fixture_helper(path, name)\n"
    elif "admission-chain fixture guard source open failed" in source:
        delegate_anchor = "    return load_pinned_fixture_guard(path, name)\n"
    if delegate_anchor is not None:
        require(source.count(delegate_anchor) == 1,
                "canonical module import not pinned")
        replacements += (
            (delegate_anchor, "    return object()\n",
             "canonical module import not pinned"),
            (delegate_anchor,
             "    return importlib.util.spec_from_file_location(name, path)\n",
             "canonical module import not pinned"),
        )
    if delegate_anchor is not None:
        marker = (
            "typed transport fixture guard source open failed"
            if "typed transport fixture guard source open failed" in source
            else "admission-chain fixture guard source open failed"
        )
        require(source.count(marker) >= 1,
                "canonical module import not pinned")
        weakened = source.replace(
            delegate_anchor,
            "    return importlib.util.spec_from_file_location(name, path)\n", 1
        ).replace(marker, "synthetic fixture guard source open failed", 1)
        try:
            validate_source(weakened, diagnostic)
        except GuardFailure as exc:
            require(str(exc) == "canonical module import not pinned",
                    "combined import/marker mutation rejected at wrong boundary")
        else:
            raise GuardFailure("combined import/marker mutation unexpectedly accepted")
    require(diagnostic == original_proof_diagnostic,
            "negative proof diagnostic shadowed")
    count = 0
    for case_index, (original, mutation, expected) in enumerate(replacements):
        require(original in source, f"negative mutation anchor absent: {expected}")
        if (expected == "canonical __main__ dispatch handler drift"
                and original == "        raise SystemExit(1)\n"):
            # A harness may contain earlier SystemExit(1) calls; mutate only
            # the final canonical dispatch handler.
            position = source.rfind(original)
            require(position >= 0, "dispatch handler mutation anchor absent")
            mutated = source[:position] + mutation + source[position + len(original):]
        elif expected == "ancestor proof missing exact diagnostic":
            # The loader guard also contains this diagnostic; mutate the proof,
            # not the earlier guard declaration, to test the intended boundary.
            position = source.rfind(original)
            require(position >= 0, "negative diagnostic mutation anchor absent")
            mutated = source[:position] + mutation + source[position + len(original):]
        else:
            mutated = source.replace(original, mutation, 1)
        try:
            validate_source(mutated, diagnostic)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"negative rejected at wrong boundary: case={case_index} expected={expected}; observed={exc}")
        else:
            raise GuardFailure(f"negative unexpectedly accepted: {expected}")
        count += 1
    return count + (1 if delegate_anchor is not None else 0)


def target_matrix_negative_cases(workflow_source: str) -> int:
    validate_target_matrix(TARGETS, workflow_source)
    first = next(iter(TARGETS))
    dropped = dict(TARGETS)
    dropped.pop(first)
    expanded = dict(TARGETS)
    expanded["synthetic-extra-negative.py"] = "synthetic ancestor identity drift"
    untriggered = workflow_source.replace(
        f'"scripts/{first}"', '"scripts/synthetic-untracked-negative.py"'
    )
    anchor = f'      - "scripts/{first}"'
    require(workflow_source.count(anchor) == 2,
            "ancestor trigger fixture must cover push and pull_request")
    position = workflow_source.rfind(anchor)
    untriggered_pr = (
        workflow_source[:position]
        + '      - "scripts/synthetic-untracked-negative.py"'
        + workflow_source[position + len(anchor):]
    )
    wrong_branch = workflow_source.replace(
        "    branches: [so]\n", "    branches: [main]\n", 1
    )
    wrong_pr_branch = workflow_source.replace(
        "  pull_request:\n    branches: [so]\n",
        "  pull_request:\n    branches: [main]\n", 1,
    )
    missing_pr_branch = workflow_source.replace(
        "  pull_request:\n    branches: [so]\n",
        "  pull_request:\n", 1,
    )
    learning_anchor = '      - ".github/workflows/autonomous-learning-guard.yml"\n'
    require(workflow_source.count(learning_anchor) == 2,
            "ancestor learning trigger fixture must cover push and pull_request")
    untriggered_learning_push = workflow_source.replace(learning_anchor, "", 1)
    last_learning_trigger = workflow_source.rfind(learning_anchor)
    untriggered_learning_pr = (
        workflow_source[:last_learning_trigger]
        + workflow_source[last_learning_trigger + len(learning_anchor):]
    )
    cases = (
        (dropped, workflow_source,
         "ancestor target matrix below seven canonical harnesses"),
        (expanded, workflow_source,
         "ancestor target matrix workflow trigger drift"),
        (TARGETS, untriggered,
         "ancestor target matrix workflow trigger drift"),
        (TARGETS, untriggered_pr,
         "ancestor target matrix workflow trigger drift"),
        (TARGETS, wrong_branch,
         "ancestor workflow so push trigger drift"),
        (TARGETS, wrong_pr_branch,
         "ancestor workflow so PR trigger drift"),
        (TARGETS, missing_pr_branch,
         "ancestor workflow so PR trigger drift"),
        (TARGETS, untriggered_learning_push,
         "ancestor independent learning workflow trigger drift"),
        (TARGETS, untriggered_learning_pr,
         "ancestor independent learning workflow trigger drift"),
    )
    authority_path = '      - ".github/workflows/backup-restore-helper-ancestor-reachability.yml"\n'
    validator_path = '      - "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py"\n'
    require(workflow_source.count(authority_path) == 2 and workflow_source.count(validator_path) == 2,
            "ancestor authority trigger negative anchor missing")
    cases += (
        (TARGETS, workflow_source.replace(authority_path, "", 1),
         "ancestor workflow authority trigger drift"),
        (TARGETS, workflow_source[:workflow_source.rfind(validator_path)]
         + workflow_source[workflow_source.rfind(validator_path) + len(validator_path):],
         "ancestor workflow authority trigger drift"),
        (TARGETS, workflow_source.replace(authority_path,
         authority_path + '      - "scripts/synthetic-unreviewed-trigger.py"\n', 1),
         "ancestor workflow authority trigger drift"),
    )
    cases += (
        (TARGETS, workflow_source.replace("    branches: [so]\n    paths:\n",
         "    branches: [so]\n    types: [created]\n    paths:\n", 1),
         "ancestor workflow event options drift"),
        (TARGETS, workflow_source.replace("  pull_request:\n    branches: [so]\n    paths:\n",
         "  pull_request:\n    branches: [so]\n    types: [opened]\n    paths:\n", 1),
         "ancestor workflow event options drift"),
        (TARGETS, workflow_source.replace("  pull_request:\n    branches: [so]\n    paths:\n",
         "  pull_request:\n    branches: [so]\n    paths: []\n    paths:\n", 1),
         "ancestor workflow event options drift"),
    )
    commented_validator = "    # " + validator_path.strip() + "\n"
    last_validator_position = workflow_source.rfind(validator_path)
    cases += (
        (TARGETS, workflow_source.replace(validator_path, commented_validator, 1),
         "ancestor workflow authority trigger drift"),
        (TARGETS, workflow_source[:last_validator_position] + commented_validator
         + workflow_source[last_validator_position + len(validator_path):],
         "ancestor workflow authority trigger drift"),
    )
    for targets, workflow, expected in cases:
        try:
            validate_target_matrix(targets, workflow)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"ancestor matrix rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"ancestor matrix mutation accepted: {expected}")
    return len(cases)


def workflow_runtime_negative_cases(workflow_source: str) -> int:
    """Mutate workflow invocation, not just the Python harness AST."""
    validate_workflow_runtime_reachability(workflow_source)
    pattern = (
        r"(?m)^      - name: Prove every canonical helper ancestor race from the validator target set"
        r"\n        run: \|\n(?:          [^\n]*\n)+"
    )
    match = re.search(pattern, workflow_source)
    require(match is not None, "runtime workflow negative anchor absent")
    step = match.group(0)
    cases = (
        (step, "", "ancestor runtime workflow step missing or duplicate"),
        (step, step + step, "ancestor runtime workflow step missing or duplicate"),
        ("          for filename in targets:\n",
         "          for filename in ():\n",
         "ancestor runtime workflow proof invocation drift"),
        ("          targets = runpy.run_path(\n",
         "          targets = dict(\n",
         "ancestor runtime workflow proof invocation drift"),
        ('              "scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py"\n',
         '              "scripts/synthetic-wrong-targets.py"\n',
         "ancestor runtime workflow proof invocation drift"),
        ('          proof = runpy.run_path(f"scripts/{filename}")\n',
         '          proof = {}\n',
         "ancestor runtime workflow proof invocation drift"),
        ('          proof["prove_helper_ancestor_swap_during_fd_walk_rejected"]()\n',
         '          pass\n',
         "ancestor runtime workflow proof invocation drift"),
        ("          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n",
         "          python scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py\n",
         "ancestor validator workflow invocation drift"),
        ("      - name: Prove seven canonical ancestor negatives remain reachable\n",
         "      - name: Disabled ancestor negatives\n",
         "ancestor validator workflow invocation drift"),
        ("  verify:\n    runs-on: ubuntu-latest\n",
         "  verify:\n    if: false\n    runs-on: ubuntu-latest\n",
         "ancestor workflow conditional bypass"),
        ("      - name: Verify read-only postcondition\n",
         "      - name: Verify read-only postcondition\n        continue-on-error: true\n",
         "ancestor workflow conditional bypass"),
    )
    cases += (
        ("      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
         "      - uses: actions/upload-artifact@v4\n      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
         "ancestor workflow step allowlist drift"),
        ("      - name: Verify read-only postcondition\n",
         "      - name: Synthetic unreviewed command\n        run: echo bypass\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step allowlist drift"),
        ("      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n",
         "      - uses: actions/setup-python@v4\n",
         "ancestor workflow checkout/setup drift"),
        ("          python-version: \"3.12\"\n",
         "          python-version: \"3.11\"\n",
         "ancestor workflow checkout/setup drift"),
        ("          persist-credentials: false\n",
         "          persist-credentials: true\n",
         "ancestor workflow checkout/setup drift"),
        ("          fetch-depth: 0\n",
         "          fetch-depth: 1\n",
         "ancestor workflow checkout/setup drift"),
        ("permissions:\n  contents: read\n",
         "permissions:\n  contents: write\n",
         "ancestor workflow job or permissions drift"),
        ("jobs:\n  verify:\n",
         "jobs:\n  synthetic:\n    runs-on: ubuntu-latest\n    steps: []\n  verify:\n",
         "ancestor workflow job or permissions drift"),
    )
    cases += (
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"synthetic_missing_proof\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              pass  # synthetic skipped proof\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/synthetic.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"prove_helper_parent_swap_after_pin_uses_original_source\",\n                        ):\n              proof[name]()\n          PY\n",
         "      - name: Prove preflight reconcile helper races without downstream source-binding dependency\n        run: |\n          set -euo pipefail\n          python - <<'PY'\n          import runpy\n          proof = runpy.run_path(\"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\")\n          for name in (\n              \"prove_helper_source_symlink_rejected\",\n              \"prove_helper_source_swap_during_import_is_pinned\",\n              \"synthetic_wrong_parent_proof\",\n                        ):\n              proof[name]()\n          PY\n",
         "ancestor preflight runtime proof drift"),
        ("      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"workflow_dispatch\" ]; then\n            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n              echo \"ANCESTOR DISPATCH REF REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"pull_request\" ]; then\n            pr_head=\"${{ github.event.pull_request.head.sha }}\"\n            if [[ ! \"$pr_head\" =~ ^[0-9a-f]{40}$ ]]; then\n              echo \"ANCESTOR PR HEAD SHA REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"\n",
         "      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"workflow_dispatch\" ]; then\n            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n              echo \"ANCESTOR DISPATCH REF REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"pull_request\" ]; then\n            pr_head=\"${{ github.event.pull_request.head.sha }}\"\n            if [[ ! \"$pr_head\" =~ ^[0-9a-f]{40}$ ]]; then\n              echo \"ANCESTOR PR HEAD SHA REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          echo synthetic-source-bypass\n          test -z \"$(git status --porcelain)\"\n",
         "ancestor exact-source workflow check drift"),
        ("      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"workflow_dispatch\" ]; then\n            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n              echo \"ANCESTOR DISPATCH REF REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"pull_request\" ]; then\n            pr_head=\"${{ github.event.pull_request.head.sha }}\"\n            if [[ ! \"$pr_head\" =~ ^[0-9a-f]{40}$ ]]; then\n              echo \"ANCESTOR PR HEAD SHA REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          test -z \"$(git status --porcelain)\"\n",
         "      - name: Confirm exact clean source\n        run: |\n          set -euo pipefail\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"workflow_dispatch\" ]; then\n            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n              echo \"ANCESTOR DISPATCH REF REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          if [ \"${GITHUB_EVENT_NAME:-}\" = \"pull_request\" ]; then\n            pr_head=\"${{ github.event.pull_request.head.sha }}\"\n            if [[ ! \"$pr_head\" =~ ^[0-9a-f]{40}$ ]]; then\n              echo \"ANCESTOR PR HEAD SHA REJECTED\" >&2\n              exit 1\n            fi\n          fi\n          expected=\"${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\"\n          test -n \"$expected\"\n          test \"$(git rev-parse HEAD)\" = \"$expected\"\n          echo synthetic-clean-bypass\n",
         "ancestor exact-source workflow check drift"),
        ("      - name: Verify read-only postcondition\n        run: |\n          git diff --check\n          git diff --exit-code\n          test -z \"$(git status --porcelain)\"\n",
         "      - name: Verify read-only postcondition\n        run: |\n          git diff --check\n          echo synthetic-readonly-bypass\n          test -z \"$(git status --porcelain)\"\n",
         "ancestor read-only workflow postcondition drift"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    permissions:\n      contents: write\n    runs-on: ubuntu-latest\n", "ancestor workflow job-level permissions override"),
    )
    cases += (
        ("permissions:\n", "env:\n  BASH_ENV: /tmp/synthetic-env\npermissions:\n", "ancestor workflow execution context override"),
        ("permissions:\n", "defaults:\n  run:\n    shell: sh\npermissions:\n", "ancestor workflow execution context override"),
        ("permissions:\n", "strategy:\n  fail-fast: false\npermissions:\n", "ancestor workflow execution context override"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    env:\n      BASH_ENV: /tmp/synthetic-env\n    runs-on: ubuntu-latest\n", "ancestor workflow execution context override"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    defaults:\n      run:\n        shell: sh\n    runs-on: ubuntu-latest\n", "ancestor workflow execution context override"),
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    strategy:\n      fail-fast: false\n    runs-on: ubuntu-latest\n", "ancestor workflow execution context override"),
    )
    cases += (
        ("  verify:\n    runs-on: ubuntu-latest\n", "  verify:\n    runs-on: self-hosted\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n", "    timeout-minutes: 120\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    container: synthetic/unreviewed:latest\n    steps:\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    services:\n      synthetic:\n        image: synthetic/unreviewed:latest\n    steps:\n", "ancestor workflow job execution drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    environment: production\n    steps:\n", "ancestor workflow job execution drift"),
    )
    cases += (
        ("permissions:\n", "concurrency:\n  group: synthetic-unreviewed\n  cancel-in-progress: true\npermissions:\n", "ancestor workflow concurrency drift"),
        ("    timeout-minutes: 5\n    steps:\n", "    timeout-minutes: 5\n    concurrency:\n      group: synthetic-unreviewed\n    steps:\n", "ancestor workflow job execution drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "  pull_request_target:\n  workflow_dispatch:\n", "ancestor workflow event inventory drift"),
        ("  workflow_dispatch:\n", "  schedule:\n    - cron: '0 * * * *'\n  workflow_dispatch:\n", "ancestor workflow event inventory drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "  workflow_dispatch:\n    inputs:\n      synthetic:\n        type: boolean\n", "ancestor workflow dispatch options drift"),
    )
    cases += (
        ("      - name: Verify read-only postcondition\n",
         "        env:\n          BASH_ENV: /tmp/synthetic\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        working-directory: /tmp\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        timeout-minutes: 99\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        run: echo synthetic-override\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
    )
    cases += (
        ("      - name: Verify read-only postcondition\n",
         "        \"env\":\n          BASH_ENV: /tmp/synthetic\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
        ("      - name: Verify read-only postcondition\n",
         "        'working-directory': /tmp\n      - name: Verify read-only postcondition\n",
         "ancestor workflow step authority drift"),
    )
    cases += (
        ("          if [ \"${GITHUB_EVENT_NAME:-}\" = \"workflow_dispatch\" ]; then\n",
         "          if false; then\n",
         "ancestor exact-source workflow check drift"),
        ("            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n",
         "            if [ \"${GITHUB_REF:-}\" != \"refs/heads/main\" ]; then\n",
         "ancestor exact-source workflow check drift"),
        ("            if [ \"${GITHUB_REF:-}\" != \"refs/heads/so\" ]; then\n",
         "            if [ \"${UNTRUSTED_REF:-}\" != \"refs/heads/so\" ]; then\n",
         "ancestor exact-source workflow check drift"),
    )
    cases += (
        ('          if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ]; then\n',
         '          if false; then\n',
         "ancestor exact-source workflow check drift"),
        ('            if [[ ! "$pr_head" =~ ^[0-9a-f]{40}$ ]]; then\n',
         '            if false; then\n',
         "ancestor exact-source workflow check drift"),
    )
    cases += (
        ("      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
         "      - uses: actions/checkout@v4\n",
         "ancestor workflow checkout/setup drift"),
        ("      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n",
         "      - uses: actions/setup-python@v5\n",
         "ancestor workflow checkout/setup drift"),
    )
    cases += (
        ("      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
         "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677263\n",
         "ancestor workflow checkout/setup drift"),
        ("      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n",
         "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87066\n",
         "ancestor workflow checkout/setup drift"),
    )
    for original, replacement, expected in cases:
        require(workflow_source.count(original) == 1,
                f"workflow negative anchor not unique: {expected}")
        mutated = workflow_source.replace(original, replacement, 1)
        try:
            validate_workflow_runtime_reachability(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"workflow negative rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"workflow runtime negative accepted: {expected}")
    duplicate_root_cases = (
        (workflow_source + "\npermissions:\n  contents: write\n",
         "ancestor workflow duplicate root authority"),
        (workflow_source + "\non:\n  workflow_dispatch:\n",
         "ancestor workflow duplicate root authority"),
        (workflow_source + '\n"permissions":\n  contents: write\n',
         "ancestor workflow root key inventory drift"),
        (workflow_source + '\n"on":\n  workflow_dispatch:\n',
         "ancestor workflow root key inventory drift"),
        (workflow_source + '\n"jobs":\n  verify:\n    runs-on: self-hosted\n',
         "ancestor workflow root key inventory drift"),
        (workflow_source.replace(
             "  pull_request:\n",
             '    "branches": [main]\n  pull_request:\n', 1),
         "ancestor workflow event key inventory drift"),
        (workflow_source.replace(
             "  workflow_dispatch:\n",
             '    "paths": []\n  workflow_dispatch:\n', 1),
         "ancestor workflow event key inventory drift"),
        (workflow_source.replace(
             "  workflow_dispatch:\n",
             '  "pull_request":\n  workflow_dispatch:\n', 1),
         "ancestor workflow event key inventory drift"),
        (workflow_source.replace(
             "  pull_request:\n",
             "      - '!**'\n  pull_request:\n", 1),
         "ancestor workflow trigger path inventory drift"),
        (workflow_source.replace(
             "  workflow_dispatch:\n",
             "      - '!**'\n  workflow_dispatch:\n", 1),
         "ancestor workflow trigger path inventory drift"),
        (workflow_source.replace(
             '          python-version: "3.12"\n',
             '          python-version: "3.12"\n          "python-version": "3.9"\n', 1),
         "ancestor workflow setup-python input inventory drift"),
        (workflow_source.replace(
             '          python-version: "3.12"\n',
             '          python-version: "3.12"\n          cache: pip\n', 1),
         "ancestor workflow setup-python input inventory drift"),
        (workflow_source + '\n      - "uses": synthetic/unreviewed@v1\n',
         "ancestor workflow step authority drift"),
        (workflow_source + "\n      - 'uses': synthetic/unreviewed@v1\n",
         "ancestor workflow step authority drift"),
    )
    duplicate_root_cases += tuple(
        (workflow_source.replace(last + next_step,
                                 last + "          echo synthetic bypass\n" + next_step, 1),
         "ancestor workflow run boundary drift")
        for last, next_step in (
            ANCESTOR_RUN_BOUNDARIES[0],
            ANCESTOR_RUN_BOUNDARIES[1],
            ANCESTOR_RUN_BOUNDARIES[3],
        )
    )
    duplicate_root_cases += (
        (workflow_source + "          echo synthetic bypass\n",
         "ancestor workflow run boundary drift"),
    )
    duplicate_root_cases += (
        (workflow_source.replace(
             "name: Backup Restore Helper Ancestor Reachability\n",
             "name: Synthetic Unreviewed Workflow\n", 1),
         "ancestor workflow identity drift"),
    )
    for mutated, expected in duplicate_root_cases:
        try:
            validate_workflow_runtime_reachability(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"ancestor duplicate-root mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"ancestor duplicate-root mutation accepted: {expected}")
    duplicate_job_cases = (
        (workflow_source + "\n    runs-on: self-hosted\n", "ancestor workflow duplicate job authority"),
        (workflow_source + "\n    timeout-minutes: 120\n", "ancestor workflow duplicate job authority"),
        (workflow_source + "\n    steps: []\n", "ancestor workflow duplicate job authority"),
        (workflow_source + '\n    "permissions":\n      contents: write\n',
         "ancestor workflow job key inventory drift"),
        (workflow_source + "\n    'if': false\n",
         "ancestor workflow job key inventory drift"),
        (workflow_source + '\n    "steps": []\n',
         "ancestor workflow job key inventory drift"),
    )
    for mutated, expected in duplicate_job_cases:
        try:
            validate_workflow_runtime_reachability(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"duplicate-job mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"duplicate-job mutation accepted: {expected}")
    return len(cases) + len(duplicate_root_cases) + len(duplicate_job_cases)



def independent_learning_workflow_negative_cases(source: str) -> int:
    validate_independent_learning_workflow(source)
    cases = (
        ("      - \".github/workflows/backup-restore-helper-ancestor-reachability.yml\"\n", "", "independent learning workflow trigger drift"),
        ("    branches: [so]\n", "    branches: [main]\n", "independent learning workflow trigger drift"),
        ("  workflow_dispatch:\n", "  disabled_dispatch:\n", "independent learning workflow trigger drift"),
        ("          python -B scripts/validate-autonomous-learning-system-negative.py\n", "          echo bypass\n", "independent learning workflow learning validation drift"),
        ("          python -B scripts/validate-memory-os-backup-restore-helper-ancestor-reachability.py --negative\n", "          echo bypass\n", "independent learning workflow ancestor invocation drift"),
        ("          if not current.startswith(previous):\n", "          if False:\n", "independent learning workflow append-only drift"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    if: false\n    runs-on: ubuntu-latest\n", "independent learning workflow conditional bypass"),
        ("      - name: Confirm read-only execution\n", "      - name: Confirm read-only execution\n        continue-on-error: true\n", "independent learning workflow conditional bypass"),
        ("          persist-credentials: false\n", "          persist-credentials: true\n", "independent learning workflow checkout/setup drift"),
        ("permissions:\n  contents: read\n", "permissions:\n  contents: write\n", "independent learning workflow job or permissions drift"),
        ("jobs:\n  validate:\n", "jobs:\n  extra:\n    runs-on: ubuntu-latest\n    steps: []\n  validate:\n", "independent learning workflow job or permissions drift"),
        ("      - name: Confirm read-only execution\n", "      - name: Extra command\n        run: echo bypass\n      - name: Confirm read-only execution\n", "independent learning workflow step allowlist drift"),
        ("          test \"$(git rev-parse HEAD)\" = \"${{ github.sha }}\"\n", "          echo bypass\n", "independent learning workflow exact-source drift"),
        ("          git diff --exit-code\n", "          echo bypass\n", "independent learning workflow read-only drift"),
        ("      - \"scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py\"\n", "", "independent learning workflow target trigger drift"),
        ("      - \"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py\"\n", "", "independent learning workflow target trigger drift"),
        ("      - \"scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py\"\n", "      - \"scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py\"\n      - \"scripts/validate-memory-os-backup-restore-synthetic-negative.py\"\n", "independent learning workflow target trigger drift"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    permissions:\n      contents: write\n    runs-on: ubuntu-latest\n", "independent learning workflow job-level permissions override"),
    )
    cases += (
        ("permissions:\n", "env:\n  BASH_ENV: /tmp/synthetic-env\npermissions:\n", "independent learning workflow execution context override"),
        ("permissions:\n", "defaults:\n  run:\n    shell: sh\npermissions:\n", "independent learning workflow execution context override"),
        ("permissions:\n", "strategy:\n  fail-fast: false\npermissions:\n", "independent learning workflow execution context override"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    env:\n      BASH_ENV: /tmp/synthetic-env\n    runs-on: ubuntu-latest\n", "independent learning workflow execution context override"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    defaults:\n      run:\n        shell: sh\n    runs-on: ubuntu-latest\n", "independent learning workflow execution context override"),
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    strategy:\n      fail-fast: false\n    runs-on: ubuntu-latest\n", "independent learning workflow execution context override"),
    )
    cases += (
        ("  validate:\n    runs-on: ubuntu-latest\n", "  validate:\n    runs-on: self-hosted\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n", "    timeout-minutes: 120\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    container: synthetic/unreviewed:latest\n    steps:\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    services:\n      synthetic:\n        image: synthetic/unreviewed:latest\n    steps:\n", "independent learning workflow job execution drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    environment: production\n    steps:\n", "independent learning workflow job execution drift"),
    )
    cases += (
        ("  cancel-in-progress: false\n", "  cancel-in-progress: true\n", "independent learning workflow concurrency drift"),
        ("  group: autonomous-learning-guard-${{ github.sha }}\n", "  group: synthetic-unreviewed\n", "independent learning workflow concurrency drift"),
        ("    timeout-minutes: 10\n    steps:\n", "    timeout-minutes: 10\n    concurrency:\n      group: synthetic-unreviewed\n    steps:\n", "independent learning workflow job execution drift"),
    )
    cases += (
        ('      - "scripts/validate-autonomous-learning-system.py"\n', "", "independent learning workflow source trigger drift"),
        ('      - "scripts/validate-autonomous-learning-system-negative.py"\n', "", "independent learning workflow source trigger drift"),
        ('      - "scripts/validate-memory-os-entry-docs.py"\n', "", "independent learning workflow source trigger drift"),
    )
    cases += (
        ("  workflow_dispatch:\n", "  pull_request_target:\n  workflow_dispatch:\n", "independent learning workflow event inventory drift"),
        ("  workflow_dispatch:\n", "  schedule:\n    - cron: '0 * * * *'\n  workflow_dispatch:\n", "independent learning workflow event inventory drift"),
    )
    cases += (
        ("  pull_request:\n", "    tags: [synthetic]\n  pull_request:\n", "independent learning workflow push options drift"),
        ("  pull_request:\n", "    paths: []\n  pull_request:\n", "independent learning workflow push options drift"),
        ("  workflow_dispatch:\n", "  workflow_dispatch:\n    inputs:\n      synthetic:\n        type: boolean\n", "independent learning workflow dispatch options drift"),
    )
    cases += (
        ("      - name: Confirm read-only execution\n",
         "        env:\n          BASH_ENV: /tmp/synthetic\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        working-directory: /tmp\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        timeout-minutes: 99\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        run: echo synthetic-override\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
    )
    cases += (
        ("          if os.environ.get(\"GITHUB_REF\") != \"refs/heads/so\":\n",
         "          if False:\n",
         "independent learning workflow append-only drift"),
        ("          if os.environ.get(\"GITHUB_REF\") != \"refs/heads/so\":\n",
         "          if os.environ.get(\"GITHUB_REF\") != \"refs/heads/main\":\n",
         "independent learning workflow append-only drift"),
        ("          if os.environ.get(\"GITHUB_REF\") != \"refs/heads/so\":\n",
         "          if os.environ.get(\"UNTRUSTED_REF\") != \"refs/heads/so\":\n",
         "independent learning workflow append-only drift"),
    )
    cases += (
        ("          baseline = before\n", "          baseline = \"HEAD^\"\n",
         "independent learning workflow append-only drift"),
        ("          baseline = \"77b4b4a7f5d6282524ecb5e6dba4b614622d28e3\"\n",
         "          baseline = \"HEAD^\"\n",
         "independent learning workflow append-only drift"),
        ("          baseline = \"77b4b4a7f5d6282524ecb5e6dba4b614622d28e3\"\n",
         "          baseline = \"0000000000000000000000000000000000000000\"\n",
         "independent learning workflow append-only drift"),
        ("          event_name = \"${{ github.event_name }}\"\n",
         "          event_name = \"workflow_dispatch\"\n",
         "independent learning workflow append-only drift"),
        ("          baseline = \"${{ github.event.pull_request.base.sha }}\"\n",
         "          baseline = \"${{ github.event.pull_request.head.sha }}\"\n",
         "independent learning workflow append-only drift"),
        ("          baseline = \"${{ github.event.pull_request.base.sha }}\"\n",
         "          baseline = \"${{ github.event.sha }}\"\n",
         "independent learning workflow append-only drift"),
        ("          baseline = \"${{ github.event.pull_request.base.sha }}\"\n",
         "          baseline = \"HEAD^\"\n",
         "independent learning workflow append-only drift"),
        ("          if parents != [merge_sha, baseline, head_sha]:\n", "          if False:\n", "independent learning workflow append-only drift"),
        ("          head_sha = \"${{ github.event.pull_request.head.sha }}\"\n", "          head_sha = baseline\n", "independent learning workflow append-only drift"),
        ("          merge_sha = \"${{ github.sha }}\"\n", "          merge_sha = baseline\n", "independent learning workflow append-only drift"),
        ("          ref: ${{ github.sha }}\n",
         "          ref: ${{ github.event.pull_request.head.sha }}\n",
         "independent learning workflow checkout/setup drift"),
        ("          test \"$(git rev-parse HEAD)\" = \"${{ github.sha }}\"\n",
         "          test \"$(git rev-parse HEAD)\" = \"${{ github.ref }}\"\n",
         "independent learning workflow exact-source drift"),
        ("          if subprocess.run(\n",
         "          if False and subprocess.run(\n",
         "independent learning workflow append-only drift"),
        ("          fetch-depth: 0\n", "          fetch-depth: 2\n",
         "independent learning workflow checkout/setup drift"),
    )
    cases += (
        ("      - name: Confirm read-only execution\n",
         "        \"env\":\n          BASH_ENV: /tmp/synthetic\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
        ("      - name: Confirm read-only execution\n",
         "        'working-directory': /tmp\n      - name: Confirm read-only execution\n",
         "independent learning workflow step authority drift"),
    )
    cases += (
        ("  pull_request:\n", "  disabled_pull_request:\n",
         "independent learning workflow event inventory drift"),
        ("  pull_request:\n    branches: [so]\n",
         "  pull_request:\n    branches: [main]\n",
         "independent learning workflow PR trigger drift"),
        ("  pull_request:\n    branches: [so]\n    paths:\n      - \".github/workflows/autonomous-learning-guard.yml\"\n",
         "  pull_request:\n    branches: [so]\n    paths:\n",
         "independent learning workflow PR source trigger drift"),
        ("  workflow_dispatch:\n",
         "    types: [opened]\n  workflow_dispatch:\n",
         "independent learning workflow PR options drift"),
    )
    cases += (
        ("      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
         "      - uses: actions/checkout@v4\n",
         "independent learning workflow checkout/setup drift"),
        ("      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n",
         "      - uses: actions/setup-python@v5\n",
         "independent learning workflow checkout/setup drift"),
    )
    cases += (
        ("      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
         "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677263\n",
         "independent learning workflow checkout/setup drift"),
        ("      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n",
         "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87066\n",
         "independent learning workflow checkout/setup drift"),
    )
    for original, replacement, expected in cases:
        # Push and PR now share several trigger paths and the so branch
        # filter. Preserve one occurrence in each event, then mutate the
        # push occurrence; independent PR cases exercise PR-only drift.
        occurrences = source.count(original)
        if occurrences == 2:
            push_body = source.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
            pr_body = source.split("  pull_request:\n", 1)[1].split(
                "  workflow_dispatch:\n", 1
            )[0]
            require(push_body.count(original) == 1 and pr_body.count(original) == 1,
                    f"independent workflow negative anchor not unique: {expected}")
        else:
            require(occurrences == 1,
                    f"independent workflow negative anchor not unique: {expected}")
        mutated = source.replace(original, replacement, 1)
        try:
            validate_independent_learning_workflow(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"independent workflow negative rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"independent workflow negative accepted: {expected}")
    duplicate_root_cases = (
        (source + "\npermissions:\n  contents: write\n",
         "independent learning workflow duplicate root authority"),
        (source + "\non:\n  workflow_dispatch:\n",
         "independent learning workflow duplicate root authority"),
        (source + '\n"permissions":\n  contents: write\n',
         "independent learning workflow root key inventory drift"),
        (source + '\n"on":\n  workflow_dispatch:\n',
         "independent learning workflow root key inventory drift"),
        (source + '\n"jobs":\n  validate:\n    runs-on: self-hosted\n',
         "independent learning workflow root key inventory drift"),
        (source.replace(
             "  pull_request:\n",
             '    "branches": [main]\n  pull_request:\n', 1),
         "independent learning workflow event key inventory drift"),
        (source.replace(
             "  workflow_dispatch:\n",
             '    "paths": []\n  workflow_dispatch:\n', 1),
         "independent learning workflow event key inventory drift"),
        (source.replace(
             "  workflow_dispatch:\n",
             '  "pull_request":\n  workflow_dispatch:\n', 1),
         "independent learning workflow event key inventory drift"),
        (source.replace(
             "  pull_request:\n",
             "      - '!**'\n  pull_request:\n", 1),
         "independent learning workflow trigger path inventory drift"),
        (source.replace(
             "  workflow_dispatch:\n",
             "      - '!**'\n  workflow_dispatch:\n", 1),
         "independent learning workflow trigger path inventory drift"),
        (source.replace(
             '          python-version: "3.12"\n',
             '          python-version: "3.12"\n          "python-version": "3.9"\n', 1),
         "independent learning workflow setup-python input inventory drift"),
        (source.replace(
             '          python-version: "3.12"\n',
             '          python-version: "3.12"\n          cache: pip\n', 1),
         "independent learning workflow setup-python input inventory drift"),
        (source + '\n      - "uses": synthetic/unreviewed@v1\n',
         "independent learning workflow step authority drift"),
        (source + "\n      - 'uses': synthetic/unreviewed@v1\n",
         "independent learning workflow step authority drift"),
    )
    duplicate_root_cases += tuple(
        (source.replace(last + next_step,
                        last + "          echo synthetic bypass\n" + next_step, 1),
         "independent learning workflow run boundary drift")
        for last, next_step in LEARNING_RUN_BOUNDARIES
    )
    duplicate_root_cases += (
        (source + "          echo synthetic bypass\n",
         "independent learning workflow run boundary drift"),
    )
    duplicate_root_cases += (
        (source.replace(
             "  contents: read\n\nconcurrency:",
             "  contents: read\n  actions: write\n\nconcurrency:", 1),
         "independent learning workflow root mapping drift"),
        (source.replace(
             "  contents: read\n\nconcurrency:",
             '  contents: read\n  "contents": write\n\nconcurrency:', 1),
         "independent learning workflow root mapping drift"),
        (source.replace(
             "  cancel-in-progress: false\n\njobs:",
             "  cancel-in-progress: false\n  cancel-in-progress: true\n\njobs:", 1),
         "independent learning workflow root mapping drift"),
        (source.replace(
             "  cancel-in-progress: false\n\njobs:",
             '  cancel-in-progress: false\n  "group": synthetic\n\njobs:', 1),
         "independent learning workflow root mapping drift"),
    )
    duplicate_root_cases += (
        (source.replace(
             "name: Autonomous Learning Guard\n",
             "name: Synthetic Unreviewed Workflow\n", 1),
         "independent learning workflow identity drift"),
    )
    for mutated, expected in duplicate_root_cases:
        try:
            validate_independent_learning_workflow(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"independent duplicate-root mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"independent duplicate-root mutation accepted: {expected}")
    duplicate_job_cases = (
        (source + "\n    runs-on: self-hosted\n", "independent learning workflow duplicate job authority"),
        (source + "\n    timeout-minutes: 120\n", "independent learning workflow duplicate job authority"),
        (source + "\n    steps: []\n", "independent learning workflow duplicate job authority"),
        (source + '\n    "permissions":\n      contents: write\n',
         "independent learning workflow job key inventory drift"),
        (source + "\n    'if': false\n",
         "independent learning workflow job key inventory drift"),
        (source + '\n    "steps": []\n',
         "independent learning workflow job key inventory drift"),
    )
    for mutated, expected in duplicate_job_cases:
        try:
            validate_independent_learning_workflow(mutated)
        except GuardFailure as exc:
            require(str(exc) == expected,
                    f"duplicate-job mutation rejected at wrong boundary: {exc}")
        else:
            raise GuardFailure(f"duplicate-job mutation accepted: {expected}")
    return len(cases) + len(duplicate_root_cases) + len(duplicate_job_cases)


def prove_push_baseline_append_only_negative() -> None:
    """A final append cannot hide a rewrite earlier in one pushed commit range."""
    with tempfile.TemporaryDirectory(prefix="learning-push-range-negative-") as tmp:
        root = Path(tmp)
        authority = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
        target = root / authority
        target.parent.mkdir(parents=True, exist_ok=True)

        def git(*args: str) -> bytes:
            return subprocess.check_output(
                ["git", *args], cwd=root, stderr=subprocess.STDOUT
            )

        def commit(message: str) -> None:
            git("add", str(authority))
            git("-c", "user.name=Synthetic Test",
                "-c", "user.email=synthetic@example.invalid",
                "commit", "-qm", message)

        git("init", "-q")
        target.write_bytes(b"original\n")
        commit("baseline")
        before = git("rev-parse", "HEAD").decode("ascii").strip()
        require(bool(re.fullmatch(r"[0-9a-f]{40}", before)),
                "push-baseline synthetic commit invalid")

        target.write_bytes(b"rewritten\n")
        commit("rewrite earlier in push")
        target.write_bytes(b"rewritten\nappended\n")
        commit("append at final push commit")

        current = target.read_bytes()
        parent = git("show", f"HEAD^:{authority}")
        baseline = git("show", f"{before}:{authority}")
        require(current.startswith(parent),
                "push-baseline control did not reproduce HEAD-parent bypass")
        git("merge-base", "--is-ancestor", before, "HEAD")
        require(not current.startswith(baseline),
                "push-baseline failed to reject earlier rewrite")

        # Positive control: a genuine extension of the pre-push bytes is safe.
        target.write_bytes(b"original\nsafe extension\n")
        require(target.read_bytes().startswith(baseline),
                "push-baseline rejected genuine append-only extension")


def prove_pr_base_append_only_negative(source: str) -> int:
    """PR merge SHA must be checked against the actual reviewed base SHA."""
    with tempfile.TemporaryDirectory(prefix="learning-pr-base-negative-") as tmp:
        root = Path(tmp)
        authority = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
        target = root / authority
        target.parent.mkdir(parents=True, exist_ok=True)

        def git(*args: str) -> bytes:
            return subprocess.check_output(
                ["git", *args], cwd=root, stderr=subprocess.STDOUT
            )

        def commit(message: str) -> None:
            git("add", str(authority))
            git("-c", "user.name=Synthetic Test",
                "-c", "user.email=synthetic@example.invalid",
                "commit", "-qm", message)

        def merge(branch: str) -> None:
            git("-c", "user.name=Synthetic Test",
                "-c", "user.email=synthetic@example.invalid",
                "merge", "--no-ff", "-qm", f"merge {branch}", branch)

        git("init", "-q")
        base_branch = git("branch", "--show-current").decode("ascii").strip()
        target.write_bytes(b"original\n")
        commit("reviewed PR base")
        base = git("rev-parse", "HEAD").decode("ascii").strip()
        require(bool(re.fullmatch(r"[0-9a-f]{40}", base)),
                "PR-base synthetic commit invalid")
        original = git("show", f"{base}:{authority}")

        def run_reviewed_pr_step(
            *, base_override: str | None = None,
            head_override: str | None = None,
            merge_override: str | None = None,
        ) -> subprocess.CompletedProcess[str]:
            script = reviewed_learning_append_only_script(source)
            markers = (
                ("${{ github.event.pull_request.base.sha }}",
                 base if base_override is None else base_override),
                ("${{ github.event.pull_request.head.sha }}",
                 git("rev-parse", "HEAD^2").decode("ascii").strip()
                 if head_override is None else head_override),
                ("${{ github.sha }}",
                 git("rev-parse", "HEAD").decode("ascii").strip()
                 if merge_override is None else merge_override),
            )
            script = script.replace("${{ github.event_name }}", "pull_request")
            for marker, value in markers:
                require(script.count(marker) == 1,
                        "PR-base reviewed workflow source binding drift")
                script = script.replace(marker, value)
            return subprocess.run(
                [sys.executable, "-c", script],
                cwd=root, capture_output=True, text=True,
                timeout=10, check=False,
            )

        git("checkout", "-qb", "feature-bad")
        target.write_bytes(b"rewritten\n")
        commit("rewrite on feature")
        target.write_bytes(b"rewritten\nappended\n")
        commit("append on feature")
        git("checkout", "-q", base_branch)
        merge("feature-bad")
        require(git("rev-parse", "HEAD^1").decode("ascii").strip() == base,
                "PR-base negative merge parent drift")
        git("merge-base", "--is-ancestor", base, "HEAD")
        require(not target.read_bytes().startswith(original),
                "PR-base failed to reject rewritten merge result")
        rejected = run_reviewed_pr_step()
        require(rejected.returncode != 0 and
                "AUTONOMOUS LEARNING APPEND-ONLY FAILED: previous authority bytes changed"
                in rejected.stderr,
                "PR-base reviewed workflow accepted rewritten merge result")

        # A clean append from the same reviewed base must remain admissible.
        git("reset", "--hard", "-q", base)
        git("checkout", "-qb", "feature-good")
        target.write_bytes(b"original\nsafe extension\n")
        commit("append on feature")
        git("checkout", "-q", base_branch)
        merge("feature-good")
        require(git("rev-parse", "HEAD^1").decode("ascii").strip() == base,
                "PR-base positive merge parent drift")
        git("merge-base", "--is-ancestor", base, "HEAD")
        require(target.read_bytes().startswith(original),
                "PR-base rejected genuine append-only merge result")
        accepted = run_reviewed_pr_step()
        require(accepted.returncode == 0 and
                "Autonomous learning append-only PASS" in accepted.stdout,
                "PR-base reviewed workflow rejected valid merge result")

        for label, kwargs, diagnostic in (
            ("wrong PR base", {"base_override": "f" * 40},
             "PR merge parent mismatch"),
            ("wrong PR head", {"head_override": base},
             "PR merge parent mismatch"),
            ("wrong merge SHA", {"merge_override": base},
             "PR merge parent mismatch"),
            ("nonhex PR head", {"head_override": "z" * 40},
             "invalid PR source SHA"),
            ("short PR head", {"head_override": "f" * 39},
             "invalid PR source SHA"),
            ("reversed parent identity",
             {"base_override": git("rev-parse", "HEAD^2").decode("ascii").strip(),
              "head_override": base}, "PR merge parent mismatch"),
        ):
            rejected = run_reviewed_pr_step(**kwargs)
            require(rejected.returncode != 0 and diagnostic in rejected.stderr,
                    f"PR merge runtime proof accepted {label}")
    return 8



def reviewed_learning_append_only_script(source: str) -> str:
    """Extract the exact validated Actions Python body for event runtime tests."""
    step_name = "      - name: Enforce append-only learning authority against parent\n"
    next_step = "      - name: Validate learning contract and executable negatives\n"
    require(source.count(step_name) == 1 and source.count(next_step) == 1,
            "learning runtime proof step boundary drift")
    body = source.split(step_name, 1)[1].split(next_step, 1)[0]
    begin = "          python - <<'PY'\n"
    end = "          PY\n"
    require(body.count(begin) == 1 and body.count(end) == 1,
            "learning runtime proof here-doc boundary drift")
    script = body.split(begin, 1)[1].split(end, 1)[0]
    lines = script.splitlines()
    require(all(not line or line.startswith("          ") for line in lines),
            "learning runtime proof indentation drift")
    script = "\n".join(line[10:] if line else "" for line in lines) + "\n"
    require(script.count("${{ github.event_name }}") == 1,
            "learning runtime proof event binding drift")
    return script


def prove_manual_dispatch_ref_negative(source: str) -> int:
    """Execute the actual reviewed dispatch script with unapproved refs."""
    script = reviewed_learning_append_only_script(source).replace(
        "${{ github.event_name }}", "workflow_dispatch"
    )
    for selected_ref in ("refs/heads/main", "refs/tags/v1",
                         "refs/pull/123/merge", None):
        env = {} if selected_ref is None else {"GITHUB_REF": selected_ref}
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=10, check=False,
        )
        require(result.returncode != 0 and
                "AUTONOMOUS LEARNING APPEND-ONLY FAILED: unreviewed dispatch ref"
                in result.stderr,
                f"dispatch runtime proof did not reject {selected_ref!r}")
    return 4


def prove_ancestor_dispatch_ref_negative(source: str) -> int:
    """Run the reviewed ancestor clean-source step under non-so dispatch refs."""
    step_name = "      - name: Confirm exact clean source\n"
    next_step = "      - name: Prove seven canonical ancestor negatives remain reachable\n"
    require(source.count(step_name) == 1 and source.count(next_step) == 1,
            "ancestor dispatch runtime step boundary drift")
    block = source.split(step_name, 1)[1].split(next_step, 1)[0]
    require(block.count("        run: |\n") == 1,
            "ancestor dispatch runtime run body drift")
    body = block.split("        run: |\n", 1)[1]
    lines = body.splitlines()
    require(all(not line or line.startswith("          ") for line in lines),
            "ancestor dispatch runtime indentation drift")
    script = "\n".join(line[10:] if line else "" for line in lines) + "\n"
    for selected_ref in ("refs/heads/main", "refs/tags/v1",
                         "refs/pull/123/merge", None):
        env = {"GITHUB_EVENT_NAME": "workflow_dispatch"}
        if selected_ref is not None:
            env["GITHUB_REF"] = selected_ref
        result = subprocess.run(
            ["bash", "-c", script],
            cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=10, check=False,
        )
        require(result.returncode != 0 and
                "ANCESTOR DISPATCH REF REJECTED" in result.stderr,
                f"ancestor dispatch runtime proof did not reject {selected_ref!r}")
    return 4



def prove_ancestor_pr_head_negative(source: str) -> int:
    """A missing or malformed PR head must not fall back to github.sha."""
    step_name = "      - name: Confirm exact clean source\n"
    next_step = "      - name: Prove seven canonical ancestor negatives remain reachable\n"
    require(source.count(step_name) == 1 and source.count(next_step) == 1,
            "ancestor PR runtime step boundary drift")
    block = source.split(step_name, 1)[1].split(next_step, 1)[0]
    require(block.count("        run: |\n") == 1,
            "ancestor PR runtime run body drift")
    lines = block.split("        run: |\n", 1)[1].splitlines()
    require(all(not line or line.startswith("          ") for line in lines),
            "ancestor PR runtime indentation drift")
    script = "\n".join(line[10:] if line else "" for line in lines) + "\n"
    pr_marker = "${{ github.event.pull_request.head.sha }}"
    expected_marker = "${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}"
    require(script.count(pr_marker) == 1 and script.count(expected_marker) == 1,
            "ancestor PR runtime SHA binding drift")
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    require(re.fullmatch(r"[0-9a-f]{40}", actual) is not None,
            "ancestor PR runtime positive SHA invalid")
    for malformed in ("", "f" * 39, "g" * 40, "f" * 41):
        candidate = script.replace(pr_marker, malformed)
        result = subprocess.run(
            ["bash", "-c", candidate],
            cwd=ROOT, env={"GITHUB_EVENT_NAME": "pull_request"},
            capture_output=True, text=True, timeout=10, check=False,
        )
        require(result.returncode != 0 and
                "ANCESTOR PR HEAD SHA REJECTED" in result.stderr,
                f"ancestor PR head runtime proof accepted {malformed!r}")
    accepted = script.replace(pr_marker, actual).replace(expected_marker, actual)
    result = subprocess.run(
        ["bash", "-c", accepted],
        cwd=ROOT, env={"GITHUB_EVENT_NAME": "pull_request"},
        capture_output=True, text=True, timeout=10, check=False,
    )
    require(result.returncode == 0,
            f"ancestor PR head runtime positive control failed: {result.stderr}")
    return 4


def prove_compilation_failure_runtime(filename: str) -> None:
    """Run the actual canonical pinned loader on valid and malformed fixtures."""
    script = """
import runpy
import errno
import sys
import tempfile
from pathlib import Path

namespace = runpy.run_path(sys.argv[1], run_name="__pinned_fixture_compile_probe__")
loader = namespace.get("load_pinned_fixture_guard") or namespace.get("load_pinned_fixture_helper")
assert callable(loader)
Fail = namespace["Fail"]
with tempfile.TemporaryDirectory(prefix=".pinned-compile-probe-", dir=sys.argv[2]) as raw:
    parent = Path(raw)
    good = parent / "valid.py"
    good.write_text("VALUE = 7" + chr(10), encoding="utf-8")
    assert loader(good, "pinned_fixture_positive").VALUE == 7
    malformed = parent / "malformed.py"
    malformed.write_text("def broken(" + chr(10) + "PRIVATE_COMPILE_CANARY = 1" + chr(10), encoding="utf-8")
    try:
        loader(malformed, "pinned_fixture_negative")
    except Fail as exc:
        assert str(exc) == "fixture guard pinned source compilation failed"
        assert exc.__cause__ is None and exc.__suppress_context__
        assert "PRIVATE_COMPILE_CANARY" not in str(exc)
    else:
        raise AssertionError("malformed helper was executed")

    import builtins
    original_compile = builtins.compile
    def fault_compile_exit(source, filename, mode, *args, **kwargs):
        if filename == str(good) and mode == "exec":
            raise SystemExit("PRIVATE_COMPILE_EXIT_CANARY")
        return original_compile(source, filename, mode, *args, **kwargs)
    builtins.compile = fault_compile_exit
    try:
        try:
            loader(good, "pinned_compile_exit_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard pinned source compilation failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_COMPILE_EXIT_CANARY" not in str(exc)
        else:
            raise AssertionError("compile SystemExit was accepted")
    finally:
        builtins.compile = original_compile

    import os
    original_open, original_close = os.open, os.close
    for fault in ("leaf", "parent"):
        tracked = {}
        def watched_open(file, flags, *args, **kwargs):
            descriptor = original_open(file, flags, *args, **kwargs)
            if file == good.name and kwargs.get("dir_fd") is not None:
                tracked["leaf"] = descriptor
                tracked["parent"] = kwargs["dir_fd"]
            return descriptor
        def fault_close(descriptor):
            original_close(descriptor)
            if descriptor == tracked.get(fault):
                raise OSError("PRIVATE_CLOSE_CANARY")
        os.open, os.close = watched_open, fault_close
        try:
            try:
                loader(good, "pinned_close_negative_" + fault)
            except Fail as exc:
                assert str(exc) == "fixture guard pinned descriptor cleanup failed"
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_CLOSE_CANARY" not in str(exc)
            else:
                raise AssertionError("descriptor close failure accepted")
        finally:
            os.open, os.close = original_open, original_close
        assert "leaf" in tracked and "parent" in tracked

    original_is_relative_to, original_relative_to = Path.is_relative_to, Path.relative_to
    for fault in ("is_relative_to", "relative_to"):
        def fault_classification(self, *args, **kwargs):
            if ((fault == "is_relative_to" and self == good)
                    or (fault == "relative_to" and self == parent)):
                raise RuntimeError("PRIVATE_PARENT_CLASSIFICATION_CANARY")
            return (original_is_relative_to(self, *args, **kwargs)
                    if fault == "is_relative_to"
                    else original_relative_to(self, *args, **kwargs))
        setattr(Path, fault, fault_classification)
        try:
            try:
                loader(good, "pinned_classification_negative_" + fault)
            except Fail as exc:
                assert str(exc) == "fixture guard parent classification failed"
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_PARENT_CLASSIFICATION_CANARY" not in str(exc)
            else:
                raise AssertionError("parent classification fault accepted")
        finally:
            setattr(Path, fault, original_is_relative_to
                    if fault == "is_relative_to" else original_relative_to)

    original_is_dir, original_is_symlink = Path.is_dir, Path.is_symlink
    for fault in ("is_dir", "is_symlink"):
        def fault_anchor_predicate(self):
            if self == Path(sys.argv[2]):
                raise RuntimeError("PRIVATE_ANCHOR_PREDICATE_CANARY")
            return (original_is_dir(self) if fault == "is_dir"
                    else original_is_symlink(self))
        if fault == "is_dir":
            Path.is_dir = fault_anchor_predicate
        else:
            Path.is_symlink = fault_anchor_predicate
        try:
            try:
                loader(good, "pinned_anchor_predicate_negative_" + fault)
            except Fail as exc:
                assert str(exc) == "fixture guard trusted anchor check failed"
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_ANCHOR_PREDICATE_CANARY" not in str(exc)
            else:
                raise AssertionError("anchor predicate failure accepted")
        finally:
            Path.is_dir, Path.is_symlink = original_is_dir, original_is_symlink

    original_is_dir, original_is_symlink = Path.is_dir, Path.is_symlink
    for fault in ("is_dir", "is_symlink"):
        def fault_cursor_predicate(self):
            if self == parent:
                raise RuntimeError("PRIVATE_CURSOR_PREDICATE_CANARY")
            return (original_is_dir(self) if fault == "is_dir"
                    else original_is_symlink(self))
        if fault == "is_dir":
            Path.is_dir = fault_cursor_predicate
        else:
            Path.is_symlink = fault_cursor_predicate
        try:
            try:
                loader(good, "pinned_cursor_predicate_negative_" + fault)
            except Fail as exc:
                assert str(exc) == "fixture guard ancestor predicate check failed"
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_CURSOR_PREDICATE_CANARY" not in str(exc)
            else:
                raise AssertionError("cursor predicate failure accepted")
        finally:
            Path.is_dir, Path.is_symlink = original_is_dir, original_is_symlink

    original_fstat, original_lstat = os.fstat, Path.lstat
    def fault_anchor_metadata(descriptor):
        raise RuntimeError("PRIVATE_ANCHOR_METADATA_CANARY")
    os.fstat = fault_anchor_metadata
    try:
        try:
            loader(good, "pinned_anchor_metadata_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard parent metadata read failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_ANCHOR_METADATA_CANARY" not in str(exc)
        else:
            raise AssertionError("anchor metadata failure accepted")
    finally:
        os.fstat = original_fstat

    cursor_metadata_calls = {"count": 0}
    def fault_cursor_metadata(self):
        if self == parent:
            cursor_metadata_calls["count"] += 1
            if cursor_metadata_calls["count"] == 2:
                raise RuntimeError("PRIVATE_CURSOR_METADATA_CANARY")
        return original_lstat(self)
    Path.lstat = fault_cursor_metadata
    try:
        try:
            loader(good, "pinned_cursor_metadata_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard parent metadata read failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_CURSOR_METADATA_CANARY" not in str(exc)
        else:
            raise AssertionError("cursor metadata failure accepted")
    finally:
        Path.lstat = original_lstat
    assert cursor_metadata_calls["count"] >= 2

    outside = Path("/PRIVATE_OUTSIDE_CANARY/fixture.py")
    try:
        loader(outside, "pinned_outside_negative")
    except Fail as exc:
        assert str(exc).endswith("fixture guard parent outside trusted roots")
        assert exc.__cause__ is None and exc.__suppress_context__
        assert "PRIVATE_OUTSIDE_CANARY" not in str(exc)
    else:
        raise AssertionError("outside parent accepted")

    for flag_name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"):
        original_flag = getattr(os, flag_name)
        for unsafe_value in (0, None, True, -1):
            setattr(os, flag_name, unsafe_value)
            try:
                try:
                    loader(good, "pinned_unsupported_flag_" + flag_name)
                except Fail as exc:
                    assert str(exc).endswith("no-follow directory open unsupported")
                    assert exc.__cause__ is None
                else:
                    raise AssertionError("unsupported platform flag accepted")
            finally:
                setattr(os, flag_name, original_flag)

    fifo = parent / "blocked-source.pipe"
    import os
    os.mkfifo(fifo)
    try:
        loader(fifo, "pinned_fifo_nonblocking_negative")
    except Fail as exc:
        assert str(exc).endswith("fixture guard source identity drift")
    else:
        raise AssertionError("FIFO source accepted")

    def fault_parent_runtime_open(file, flags, *args, **kwargs):
        if file == parent.name and kwargs.get("dir_fd") is not None:
            raise RuntimeError("PRIVATE_PARENT_RUNTIME_CANARY")
        return original_open(file, flags, *args, **kwargs)
    os.open = fault_parent_runtime_open
    try:
        try:
            loader(good, "pinned_parent_runtime_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard parent runtime open failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_PARENT_RUNTIME_CANARY" not in str(exc)
        else:
            raise AssertionError("parent runtime fault accepted")
    finally:
        os.open = original_open

    original_is_dir = Path.is_dir
    def deny_ancestor(self):
        if self == parent:
            return False
        return original_is_dir(self)
    Path.is_dir = deny_ancestor
    try:
        try:
            loader(good, "pinned_parent_domain_negative")
        except Fail as exc:
            assert str(exc).endswith("fixture guard ancestor missing or symlinked")
        else:
            raise AssertionError("missing ancestor accepted")
    finally:
        Path.is_dir = original_is_dir

    def fault_anchor_runtime_open(file, flags, *args, **kwargs):
        if Path(file) == Path(sys.argv[2]):
            raise RuntimeError("PRIVATE_ANCHOR_RUNTIME_CANARY")
        return original_open(file, flags, *args, **kwargs)
    os.open = fault_anchor_runtime_open
    try:
        try:
            loader(good, "pinned_anchor_runtime_negative")
        except Fail as exc:
            assert str(exc).endswith("fixture guard anchor open failed")
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_ANCHOR_RUNTIME_CANARY" not in str(exc)
        else:
            raise AssertionError("anchor runtime fault accepted")
    finally:
        os.open = original_open

    for fault, suffix in (
        ("anchor", "fixture guard anchor open failed"),
        ("parent", "fixture guard parent open failed"),
    ):
        def fault_parent_open(file, flags, *args, **kwargs):
            if fault == "anchor" and Path(file) == Path(sys.argv[2]):
                raise OSError("PRIVATE_ANCHOR_OPEN_CANARY")
            if fault == "parent" and file == parent.name and kwargs.get("dir_fd") is not None:
                raise OSError("PRIVATE_PARENT_OPEN_CANARY")
            return original_open(file, flags, *args, **kwargs)
        os.open = fault_parent_open
        try:
            try:
                loader(good, "pinned_parent_negative_" + fault)
            except Fail as exc:
                assert str(exc).endswith(suffix)
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_" not in str(exc)
            else:
                raise AssertionError("parent open failure accepted")
        finally:
            os.open = original_open

    injected_parent_close = {"done": False}
    def fault_parent_cleanup_open(file, flags, *args, **kwargs):
        if file == parent.name and kwargs.get("dir_fd") is not None:
            raise OSError("PRIVATE_PARENT_OPEN_CANARY")
        return original_open(file, flags, *args, **kwargs)
    def fault_parent_cleanup_close(descriptor):
        original_close(descriptor)
        injected_parent_close["done"] = True
        raise OSError("PRIVATE_PARENT_CLOSE_CANARY")
    os.open, os.close = fault_parent_cleanup_open, fault_parent_cleanup_close
    try:
        try:
            loader(good, "pinned_parent_cleanup_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard pinned descriptor cleanup failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_PARENT_CLOSE_CANARY" not in str(exc)
        else:
            raise AssertionError("parent cleanup failure accepted")
    finally:
        os.open, os.close = original_open, original_close
    assert injected_parent_close["done"]

    for fault_class in (OSError, RuntimeError):
        def fault_source_open(file, flags, *args, **kwargs):
            if file == good.name and kwargs.get("dir_fd") is not None:
                raise fault_class("PRIVATE_SOURCE_OPEN_CANARY")
            return original_open(file, flags, *args, **kwargs)
        os.open = fault_source_open
        try:
            try:
                loader(good, "pinned_source_open_negative_" + fault_class.__name__)
            except Fail as exc:
                assert str(exc).endswith("fixture guard source open failed")
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_SOURCE_OPEN_CANARY" not in str(exc)
            else:
                raise AssertionError("source open failure accepted")
        finally:
            os.open = original_open

    def fault_source_domain(file, flags, *args, **kwargs):
        if file == good.name and kwargs.get("dir_fd") is not None:
            raise Fail("intentional source-open domain")
        return original_open(file, flags, *args, **kwargs)
    os.open = fault_source_domain
    try:
        try:
            loader(good, "pinned_source_open_domain_negative")
        except Fail as exc:
            assert str(exc) == "intentional source-open domain"
        else:
            raise AssertionError("source-open domain Fail was masked")
    finally:
        os.open = original_open

    original_dup = os.dup
    for fault_class in (OSError, RuntimeError):
        def fault_source_dup(descriptor):
            raise fault_class("PRIVATE_SOURCE_DUP_CANARY")
        os.dup = fault_source_dup
        try:
            try:
                loader(good, "pinned_source_dup_negative_" + fault_class.__name__)
            except Fail as exc:
                assert str(exc).endswith("pinned source read failed")
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_SOURCE_DUP_CANARY" not in str(exc)
            else:
                raise AssertionError("source duplicate failure accepted")
        finally:
            os.dup = original_dup

    def fault_source_dup_domain(descriptor):
        raise Fail("intentional source-dup domain")
    os.dup = fault_source_dup_domain
    try:
        try:
            loader(good, "pinned_source_dup_domain_negative")
        except Fail as exc:
            assert str(exc) == "intentional source-dup domain"
        else:
            raise AssertionError("source-dup domain Fail was masked")
    finally:
        os.dup = original_dup

    original_dup, original_fdopen, original_close = os.dup, os.fdopen, os.close
    for cleanup_fault in (False, True):
        tracked_duplicate = {}
        def watch_duplicate(descriptor):
            duplicate = original_dup(descriptor)
            tracked_duplicate["fd"] = duplicate
            return duplicate
        def fail_preownership_fdopen(descriptor, *args, **kwargs):
            if descriptor == tracked_duplicate.get("fd"):
                raise OSError("PRIVATE_FDOPEN_PREOWNERSHIP_CANARY")
            return original_fdopen(descriptor, *args, **kwargs)
        def fail_duplicate_cleanup(descriptor):
            original_close(descriptor)
            if cleanup_fault and descriptor == tracked_duplicate.get("fd"):
                raise OSError("PRIVATE_DUPLICATE_CLOSE_CANARY")
        os.dup, os.fdopen, os.close = watch_duplicate, fail_preownership_fdopen, fail_duplicate_cleanup
        try:
            try:
                loader(good, "pinned_fdopen_preownership_negative_" + str(cleanup_fault))
            except Fail as exc:
                expected = ("fixture guard pinned descriptor cleanup failed"
                            if cleanup_fault else "pinned source read failed")
                assert str(exc).endswith(expected)
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_" not in str(exc)
            else:
                raise AssertionError("preownership fdopen failure accepted")
        finally:
            os.dup, os.fdopen, os.close = original_dup, original_fdopen, original_close
        assert "fd" in tracked_duplicate
        try:
            os.fstat(tracked_duplicate["fd"])
        except OSError as exc:
            assert exc.errno == errno.EBADF
        else:
            raise AssertionError("fdopen failure leaked duplicate descriptor")

    original_fstat = os.fstat
    injected_unexpected_parent_close = {"done": False}
    def fault_unexpected_parent_stat(descriptor):
        raise RuntimeError("PRIVATE_PARENT_VERIFY_CANARY")
    def fault_unexpected_parent_close(descriptor):
        original_close(descriptor)
        injected_unexpected_parent_close["done"] = True
        raise OSError("PRIVATE_PARENT_VERIFY_CLOSE_CANARY")
    os.fstat, os.close = fault_unexpected_parent_stat, fault_unexpected_parent_close
    try:
        try:
            loader(good, "pinned_parent_unexpected_cleanup_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard pinned descriptor cleanup failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_PARENT_VERIFY_CLOSE_CANARY" not in str(exc)
        else:
            raise AssertionError("unexpected parent cleanup failure accepted")
    finally:
        os.fstat, os.close = original_fstat, original_close
    assert injected_unexpected_parent_close["done"]

    tracked_handoff = {"child": None, "old": None, "faulted": False}
    def watch_handoff_open(file, flags, *args, **kwargs):
        descriptor = original_open(file, flags, *args, **kwargs)
        if file == parent.name and kwargs.get("dir_fd") is not None:
            tracked_handoff["child"] = descriptor
            tracked_handoff["old"] = kwargs["dir_fd"]
        return descriptor
    def fault_handoff_close(descriptor):
        if descriptor == tracked_handoff["old"] and not tracked_handoff["faulted"]:
            original_close(descriptor)
            tracked_handoff["faulted"] = True
            raise OSError("PRIVATE_HANDOFF_CLOSE_CANARY")
        return original_close(descriptor)
    os.open, os.close = watch_handoff_open, fault_handoff_close
    try:
        try:
            loader(good, "pinned_handoff_cleanup_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard pinned descriptor cleanup failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_HANDOFF_CLOSE_CANARY" not in str(exc)
        else:
            raise AssertionError("handoff close failure accepted")
    finally:
        os.open, os.close = original_open, original_close
    assert tracked_handoff["faulted"] and tracked_handoff["child"] is not None
    try:
        os.fstat(tracked_handoff["child"])
    except OSError:
        pass
    else:
        raise AssertionError("handoff child descriptor leaked")

    # A close that raises before closing has ambiguous ownership. Never
    # blindly retry an FD number: it may already have been reused. Verify the
    # fixed fail-closed diagnostic and child cleanup, then explicitly reclaim
    # the still-open old FD in this isolated, single-threaded fault fixture.
    tracked_preclose = {"child": None, "old": None, "faulted": False, "calls": 0}
    def watch_preclose_open(file, flags, *args, **kwargs):
        descriptor = original_open(file, flags, *args, **kwargs)
        if file == parent.name and kwargs.get("dir_fd") is not None:
            tracked_preclose["child"] = descriptor
            tracked_preclose["old"] = kwargs["dir_fd"]
        return descriptor
    def fault_preclose_close(descriptor):
        if descriptor == tracked_preclose["old"]:
            tracked_preclose["calls"] += 1
            if not tracked_preclose["faulted"]:
                tracked_preclose["faulted"] = True
                raise RuntimeError("PRIVATE_PRECLOSE_HANDOFF_CANARY")
        return original_close(descriptor)
    os.open, os.close = watch_preclose_open, fault_preclose_close
    try:
        try:
            loader(good, "pinned_handoff_preclose_negative")
        except Fail as exc:
            assert str(exc) == "fixture guard pinned descriptor cleanup failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_PRECLOSE_HANDOFF_CANARY" not in str(exc)
        else:
            raise AssertionError("pre-close handoff failure accepted")
    finally:
        os.open, os.close = original_open, original_close
        old_fd = tracked_preclose["old"]
        if old_fd is not None:
            try:
                os.fstat(old_fd)
            except OSError as exc:
                assert exc.errno == errno.EBADF
            else:
                # The fixture owns this FD and is single-threaded; this is
                # test cleanup, not an unsafe retry in the production walker.
                original_close(old_fd)
    assert tracked_preclose["faulted"] and tracked_preclose["calls"] == 1
    assert tracked_preclose["child"] is not None
    try:
        os.fstat(tracked_preclose["child"])
    except OSError as exc:
        assert exc.errno == errno.EBADF
    else:
        raise AssertionError("pre-close handoff child descriptor leaked")

    tracked_read = {}
    def watch_read_open(file, flags, *args, **kwargs):
        descriptor = original_open(file, flags, *args, **kwargs)
        if file == good.name and kwargs.get("dir_fd") is not None:
            tracked_read["leaf"] = descriptor
        return descriptor
    def fault_fstat(descriptor):
        if descriptor == tracked_read.get("leaf"):
            raise OSError("PRIVATE_READ_CANARY")
        return original_fstat(descriptor)
    os.open, os.fstat = watch_read_open, fault_fstat
    try:
        try:
            loader(good, "pinned_read_negative")
        except Fail as exc:
            assert str(exc).endswith("pinned source read failed")
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_READ_CANARY" not in str(exc)
        else:
            raise AssertionError("descriptor read failure accepted")
    finally:
        os.open, os.fstat = original_open, original_fstat
    assert "leaf" in tracked_read

    import importlib.util
    original_spec = importlib.util.spec_from_file_location
    original_module = importlib.util.module_from_spec
    def fail_spec(name, location, *args, **kwargs):
        if name == "pinned_setup_spec":
            raise RuntimeError("PRIVATE_SETUP_SPEC_CANARY")
        return original_spec(name, location, *args, **kwargs)
    def fail_module(spec):
        if spec.name == "pinned_setup_module":
            raise SystemExit("PRIVATE_SETUP_MODULE_CANARY")
        return original_module(spec)
    importlib.util.spec_from_file_location = fail_spec
    importlib.util.module_from_spec = fail_module
    try:
        for name in ("pinned_setup_spec", "pinned_setup_module"):
            try:
                loader(good, name)
            except Fail as exc:
                assert str(exc) == "fixture guard pinned module setup failed"
                assert exc.__cause__ is None and exc.__suppress_context__
                assert "PRIVATE_" not in str(exc)
            else:
                raise AssertionError("unsafe module setup accepted")
    finally:
        importlib.util.spec_from_file_location = original_spec
        importlib.util.module_from_spec = original_module

    for filename, payload in (
        ("runtime-error.py", "raise RuntimeError('PRIVATE_EXEC_CANARY')"),
        ("system-exit.py", "raise SystemExit('PRIVATE_EXIT_CANARY')"),
    ):
        throwing = parent / filename
        throwing.write_text(payload + chr(10), encoding="utf-8")
        try:
            loader(throwing, "pinned_exec_negative_" + filename.replace("-", "_"))
        except Fail as exc:
            assert str(exc) == "fixture guard pinned module execution failed"
            assert exc.__cause__ is None and exc.__suppress_context__
            assert "PRIVATE_" not in str(exc)
        else:
            raise AssertionError("throwing helper was accepted")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(ROOT / "scripts" / filename), str(ROOT)],
        cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
    )
    require(result.returncode == 0,
            f"pinned helper compilation runtime negative failed: {filename}")


def prove_private_entrypoint_failures() -> int:
    """Unexpected parser/read errors must never print source or path canaries."""
    script = """
import ast
import contextlib
import io
import runpy
import sys
from pathlib import Path

target = sys.argv[1]
for fault in ("syntax", "read"):
    original_parse, original_read_text = ast.parse, Path.read_text
    if fault == "syntax":
        def fault_parse(*args, **kwargs):
            raise SyntaxError("PRIVATE_VALIDATOR_SYNTAX_CANARY")
        ast.parse = fault_parse
    else:
        def fault_read_text(self, *args, **kwargs):
            if self.name == "backup-restore-helper-ancestor-reachability.yml":
                raise OSError("PRIVATE_VALIDATOR_PATH_CANARY")
            return original_read_text(self, *args, **kwargs)
        Path.read_text = fault_read_text
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                runpy.run_path(target, run_name="__main__")
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("unexpected validator fault was accepted")
    finally:
        ast.parse, Path.read_text = original_parse, original_read_text
    combined = stdout.getvalue() + stderr.getvalue()
    assert stdout.getvalue().strip() == (
        "HELPER ANCESTOR REACHABILITY FAILED: unexpected validator input failure"
    ), repr(combined)
    assert "PRIVATE_VALIDATOR_" not in combined
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(ROOT / "scripts" /
                                          "validate-memory-os-backup-restore-helper-ancestor-reachability.py")],
        cwd=ROOT, capture_output=True, text=True, timeout=15, check=False,
    )
    require(result.returncode == 0,
            "helper ancestor private entrypoint fault proof failed")
    return 2


def main() -> int:
    workflow_source = (
        ROOT / ".github/workflows/backup-restore-helper-ancestor-reachability.yml"
    ).read_text(encoding="utf-8")
    validate_target_matrix(TARGETS, workflow_source)
    validate_workflow_runtime_reachability(workflow_source)
    learning_workflow_source = (
        ROOT / ".github/workflows/autonomous-learning-guard.yml"
    ).read_text(encoding="utf-8")
    validate_independent_learning_workflow(learning_workflow_source)
    total = 0
    for filename, diagnostic in TARGETS.items():
        source = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
        validate_source(source, diagnostic)
        prove_compilation_failure_runtime(filename)
        if "--negative" in sys.argv[1:]:
            total += negative_cases(source, diagnostic)
    if "--negative" in sys.argv[1:]:
        total += prove_private_entrypoint_failures()
        total += target_matrix_negative_cases(workflow_source)
        total += workflow_runtime_negative_cases(workflow_source)
        total += independent_learning_workflow_negative_cases(learning_workflow_source)
        prove_push_baseline_append_only_negative()
        total += 1
        total += prove_pr_base_append_only_negative(learning_workflow_source)
        total += prove_manual_dispatch_ref_negative(learning_workflow_source)
        total += prove_ancestor_dispatch_ref_negative(workflow_source)
        total += prove_ancestor_pr_head_negative(workflow_source)
    print(f"Helper ancestor reachability PASS ({len(TARGETS)} canonical harnesses)")
    if "--negative" in sys.argv[1:]:
        require(total == 136 * len(TARGETS) + 230, "ancestor negative count mismatch")
        print(f"Helper ancestor reachability negative PASS ({total} fail-closed mutations)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GuardFailure as exc:
        print(f"HELPER ANCESTOR REACHABILITY FAILED: {exc}")
        raise SystemExit(1)
    except (SyntaxError, OSError):
        print("HELPER ANCESTOR REACHABILITY FAILED: unexpected validator input failure")
        raise SystemExit(1)
