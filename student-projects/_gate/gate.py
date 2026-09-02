#!/usr/bin/env python3
"""The gate: one script, one `gate.yaml` per project. Runs the 8 checks from
`student-projects/README.md` in order and halts on the first FAIL. An
automated PASS is the floor to merge, not the merge decision -- manual
review always follows (see README).

Usage:
    python student-projects/_gate/gate.py <slug> [--base curriculum-base] [--skip-venv]

`<slug>` is a directory name under `student-projects/`, e.g. `01-word-seg-pos`.
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib
import importlib.util
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# The reserved live-only pytest fixtures from tests/conftest.py -- reserved
# for the platform's own live-integration suite, never appropriate for an
# offline student deliverable (step 8).
_RESERVED_FIXTURES = ("live_db", "live_store", "live_silver_store", "live_deepseek_client")


class GateFailure(Exception):
    """Raised by a check to report a FAIL with a human-readable reason."""


@dataclass
class StepResult:
    name: str
    status: str  # PASS | FAIL | SKIP
    detail: str


def _import_installed(dotted_path: str, attr: str):
    """Imports an installed package module (e.g. `vietnlp.linguistics.segmentation`)."""
    mod = importlib.import_module(dotted_path)
    fn = getattr(mod, attr, None)
    if fn is None:
        raise GateFailure(f"module {dotted_path!r} has no attribute {attr!r}")
    return fn


def _import_from_file(loader_spec: str):
    """Imports `attr` from a file path not on the package path, e.g.
    `"student-projects/01-word-seg-pos/gate_input.py:build_inputs"`
    (path relative to the repo root)."""
    file_rel, _, attr = loader_spec.partition(":")
    file_path = REPO_ROOT / file_rel
    if not file_path.exists():
        raise GateFailure(f"loader file not found: {file_rel}")
    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    fn = getattr(module, attr, None)
    if fn is None:
        raise GateFailure(f"{file_rel} has no attribute {attr!r}")
    return fn


# ---------------------------------------------------------------------------
# Step 1: scope check
# ---------------------------------------------------------------------------
def step_scope(cfg: dict, base: str) -> StepResult:
    branch = cfg["branch"]

    def _ref_exists(ref: str) -> bool:
        r = subprocess.run(["git", "rev-parse", "--verify", ref], cwd=REPO_ROOT, capture_output=True, text=True)
        return r.returncode == 0

    if not _ref_exists(base):
        return StepResult("1. scope", "SKIP", f"base ref {base!r} not found yet -- expected before branches are cut")
    if not _ref_exists(branch):
        return StepResult("1. scope", "SKIP", f"branch {branch!r} not found -- cut it from {base!r} first")

    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{branch}"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    owned = cfg.get("owned_paths", [])
    forbidden = cfg.get("forbidden_paths", [])
    violations = []
    for f in diff:
        if any(fnmatch.fnmatch(f, pat) for pat in forbidden):
            violations.append(f"{f} (forbidden)")
        elif not any(fnmatch.fnmatch(f, pat) for pat in owned):
            violations.append(f"{f} (not in owned_paths)")
    if violations:
        return StepResult("1. scope", "FAIL", f"diff touches path(s) out of scope: {violations}")
    return StepResult("1. scope", "PASS", f"{len(diff)} changed file(s), all within owned_paths")


# ---------------------------------------------------------------------------
# Step 2: clean install + import check
# ---------------------------------------------------------------------------
def step_clean_install(skip: bool) -> StepResult:
    if skip:
        return StepResult("2. clean install", "SKIP", "--skip-venv passed")
    with tempfile.TemporaryDirectory() as tmp:
        venv_dir = Path(tmp) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, capture_output=True)
        pip = venv_dir / "bin" / "pip"
        r = subprocess.run([str(pip), "install", "--quiet", "-e", str(REPO_ROOT)], capture_output=True, text=True)
        if r.returncode != 0:
            return StepResult("2. clean install", "FAIL", f"pip install -e . failed:\n{r.stderr[-2000:]}")
        py = venv_dir / "bin" / "python"
        r2 = subprocess.run([str(py), "-c", "import vietnlp"], capture_output=True, text=True)
        if r2.returncode != 0:
            return StepResult("2. clean install", "FAIL", f"import vietnlp failed:\n{r2.stderr[-2000:]}")
    return StepResult("2. clean install", "PASS", "clean venv install + import vietnlp succeeded")


# ---------------------------------------------------------------------------
# Step 3 + 4: schema conformance + provenance (share the same producer run)
# ---------------------------------------------------------------------------
def _run_producer(producer_cfg: dict) -> list:
    build_inputs = _import_from_file(producer_cfg["inputs"]["loader"])
    inputs = build_inputs()

    try:
        fn = _import_installed(producer_cfg["module"], producer_cfg["function"])
    except ModuleNotFoundError as exc:
        raise GateFailure(f"producer {producer_cfg['module']}:{producer_cfg['function']} not found -- {exc}")

    call_mode = producer_cfg.get("call_mode", "per_item")
    returns = producer_cfg.get("returns", "single")
    outputs = []
    if call_mode == "batch":
        result = fn(inputs)
        outputs.extend(result) if returns == "list" else outputs.append(result)
    else:
        for unit in inputs:
            args = unit if isinstance(unit, tuple) else (unit,)
            result = fn(*args)
            outputs.extend(result) if returns == "list" else outputs.append(result)
    return outputs


def _validate_outputs(schema_cfg: dict, outputs: list) -> None:
    validator = _import_installed(schema_cfg["module"], schema_cfg["validator"])
    kwargs = {}
    if schema_cfg.get("validator_kwargs_loader"):
        kwargs = _import_from_file(schema_cfg["validator_kwargs_loader"])()
    if schema_cfg.get("validator_call_mode", "per_item") == "batch":
        validator(outputs, **kwargs)
    else:
        for o in outputs:
            validator(o, **kwargs)


def _run_extra_checks(producer_cfg: dict, outputs: list) -> None:
    for check in producer_cfg.get("extra_checks", []):
        fn = _import_installed(check["module"], check["function"])
        for o in outputs:
            if not fn(o):
                raise GateFailure(f"extra check {check['module']}.{check['function']} failed for {o!r}")


def step_schema_and_provenance(cfg: dict) -> tuple[StepResult, StepResult, dict[str, list]]:
    produced: dict[str, list] = {}
    try:
        for producer_cfg in cfg.get("producers", []):
            outputs = _run_producer(producer_cfg)
            _validate_outputs(producer_cfg["schema"], outputs)
            _run_extra_checks(producer_cfg, outputs)
            produced[producer_cfg["name"]] = outputs
    except GateFailure as exc:
        fail = StepResult("3. schema conformance", "FAIL", str(exc))
        return fail, StepResult("4. provenance", "SKIP", "schema check did not pass"), produced
    except Exception as exc:  # pandera SchemaError, ValueError from a validator, etc.
        fail = StepResult("3. schema conformance", "FAIL", f"{type(exc).__name__}: {exc}")
        return fail, StepResult("4. provenance", "SKIP", "schema check did not pass"), produced

    schema_result = StepResult(
        "3. schema conformance", "PASS",
        f"{sum(len(v) for v in produced.values())} output(s) across {len(produced)} producer(s) validate",
    )

    field = cfg.get("provenance_field", "source")
    bad = []
    for name, outputs in produced.items():
        for o in outputs:
            if getattr(o, field, None) != "real":
                bad.append((name, getattr(o, field, None)))
    if bad:
        prov_result = StepResult(
            "4. provenance", "FAIL",
            f"{len(bad)} output(s) do not carry {field}='real' (e.g. {bad[0]}) -- "
            f"a submission must produce real output, not stub",
        )
    else:
        prov_result = StepResult("4. provenance", "PASS", f"all outputs carry {field}='real'")
    return schema_result, prov_result, produced


# ---------------------------------------------------------------------------
# Step 5 + 6: pytest runs
# ---------------------------------------------------------------------------
def _run_pytest(paths: list[str]) -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *paths], cwd=REPO_ROOT, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout[-3000:] + r.stderr[-1000:])


def _own_test_paths(cfg: dict) -> list[Path]:
    """own_test_glob may be a single glob string or a list of them (a
    project spanning more than one test-file family, e.g. Project 3's
    NER + coref tests) -- normalize to a list and glob each, de-duplicated
    and order-preserving."""
    patterns = cfg["own_test_glob"]
    if isinstance(patterns, str):
        patterns = [patterns]
    seen: dict[Path, None] = {}
    for pattern in patterns:
        for p in REPO_ROOT.glob(pattern):
            seen[p] = None
    return list(seen)


def step_unit_tests(cfg: dict) -> StepResult:
    paths = [str(p) for p in _own_test_paths(cfg)]
    if not paths:
        return StepResult("5. unit tests", "FAIL", f"no test files matched {cfg['own_test_glob']!r}")
    ok, detail = _run_pytest(paths)
    return StepResult("5. unit tests", "PASS" if ok else "FAIL", detail)


def step_golden_test(cfg: dict) -> StepResult:
    golden = cfg.get("golden_test")
    if not golden:
        return StepResult("6. golden-file test", "SKIP", "no golden_test declared in gate.yaml")
    path = REPO_ROOT / golden
    if not path.exists():
        return StepResult("6. golden-file test", "SKIP", f"{golden} not yet authored")
    ok, detail = _run_pytest([str(path)])
    return StepResult("6. golden-file test", "PASS" if ok else "FAIL", detail)


# ---------------------------------------------------------------------------
# Step 7: own-suite presence
# ---------------------------------------------------------------------------
def step_own_suite_presence(cfg: dict) -> StepResult:
    paths = _own_test_paths(cfg)
    text = "\n".join(p.read_text(encoding="utf-8") for p in paths)
    n_tests = len(re.findall(r"^def test_", text, flags=re.MULTILINE))
    min_tests = cfg.get("min_own_tests", 1)
    if n_tests < min_tests:
        return StepResult("7. own-suite presence", "FAIL", f"only {n_tests} own tests found (min {min_tests})")
    # Heuristic only: checks the required input class is at least MENTIONED
    # (test name, docstring, or comment) -- not that it is meaningfully
    # exercised. Real coverage quality is a manual-review judgment call
    # (student-projects/README.md), this is just the presence floor.
    missing = [c for c in cfg.get("required_input_classes", []) if c.lower() not in text.lower()]
    if missing:
        return StepResult("7. own-suite presence", "FAIL", f"required input class(es) not mentioned anywhere: {missing}")
    return StepResult("7. own-suite presence", "PASS", f"{n_tests} own tests; all required input classes mentioned")


# ---------------------------------------------------------------------------
# Step 8: no reserved live-only fixtures
# ---------------------------------------------------------------------------
def step_no_reserved_fixtures(cfg: dict) -> StepResult:
    paths = _own_test_paths(cfg)
    hits = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        for name in _RESERVED_FIXTURES:
            if re.search(rf"\b{name}\b", text):
                hits.append(f"{p.name}: {name}")
    if hits:
        return StepResult("8. no reserved fixtures", "FAIL", f"reserved live-only fixture(s) used: {hits}")
    return StepResult("8. no reserved fixtures", "PASS", "no reserved live-only fixtures referenced")


def run_gate(slug: str, base: str, skip_venv: bool) -> int:
    gate_yaml = REPO_ROOT / "student-projects" / slug / "gate.yaml"
    if not gate_yaml.exists():
        print(f"FATAL: no gate.yaml at {gate_yaml}")
        return 2
    cfg = yaml.safe_load(gate_yaml.read_text(encoding="utf-8"))

    results: list[StepResult] = []
    results.append(step_scope(cfg, base))
    results.append(step_clean_install(skip_venv))

    if results[-1].status != "FAIL":
        schema_result, prov_result, _produced = step_schema_and_provenance(cfg)
        results.append(schema_result)
        results.append(prov_result)
    else:
        results.append(StepResult("3. schema conformance", "SKIP", "clean install failed"))
        results.append(StepResult("4. provenance", "SKIP", "clean install failed"))

    remaining_steps = [
        ("5. unit tests", step_unit_tests),
        ("6. golden-file test", step_golden_test),
        ("7. own-suite presence", step_own_suite_presence),
        ("8. no reserved fixtures", step_no_reserved_fixtures),
    ]
    halted = any(r.status == "FAIL" for r in results)
    for name, step_fn in remaining_steps:
        if halted:
            results.append(StepResult(name, "SKIP", "halted by an earlier FAIL"))
            continue
        result = step_fn(cfg)
        results.append(result)
        if result.status == "FAIL":
            halted = True

    print(f"\n=== Gate report: {slug} ===\n")
    for r in results:
        print(f"[{r.status:4}] {r.name}")
        if r.status != "PASS":
            for line in r.detail.splitlines():
                print(f"       {line}")
    overall = "FAIL" if any(r.status == "FAIL" for r in results) else "PASS"
    print(f"\n=== Overall: {overall} ===")
    print("Automated PASS is the floor to merge, not the merge decision -- manual review still follows.")
    return 0 if overall == "PASS" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="project directory name under student-projects/, e.g. 01-word-seg-pos")
    parser.add_argument("--base", default="curriculum-base", help="base ref for the scope diff (default: curriculum-base)")
    parser.add_argument("--skip-venv", action="store_true", help="skip the clean-venv install check (fast local dry runs only)")
    args = parser.parse_args()
    sys.exit(run_gate(args.slug, args.base, args.skip_venv))


if __name__ == "__main__":
    main()
