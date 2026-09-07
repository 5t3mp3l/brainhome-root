#!/usr/bin/env python3
"""BrainHome task health checker.

Validates module tasks.json files for:
- file presence
- JSON/JSONC readability
- task shape (label + command)
- referenced absolute script/file paths existence

Usage:
  task-health-check.py [module|all] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from paths import resolve_tools_root

TOOLS_ROOT = resolve_tools_root()
MODULES_JSON = TOOLS_ROOT / "config/modules.json"


@dataclass
class CheckResult:
    module: str
    module_path: str
    tasks_path: str
    ok: bool
    errors: List[str]
    warnings: List[str]
    task_count: int
    fixed: int


def strip_jsonc(text: str) -> str:
    out: List[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue

        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        out.append(ch)
        i += 1

    cleaned = "".join(out)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def load_modules() -> Dict[str, Any]:
    if not MODULES_JSON.exists():
        raise FileNotFoundError(f"Registry missing: {MODULES_JSON}")
    data = json.loads(MODULES_JSON.read_text(encoding="utf-8"))
    return data.get("modules", {})


def parse_tasks_file(tasks_path: Path) -> Dict[str, Any]:
    text = tasks_path.read_text(encoding="utf-8")
    cleaned = strip_jsonc(text)
    return json.loads(cleaned)


def extract_abs_paths(command: str) -> List[str]:
    # Capture likely absolute file paths in command strings.
    candidates = re.findall(r"(/[^\s'\";&|()]+)", command)
    out: List[str] = []
    for cand in candidates:
        if "://" in cand:
            continue
        cleaned = cand.rstrip(",)")
        if cleaned.startswith("/home/") or cleaned.startswith("/usr/") or cleaned.startswith("/etc/"):
            out.append(cleaned)
    return sorted(set(out))


def likely_executable_path(path: Path) -> bool:
    if path.is_dir():
        return False
    if path.suffix in {".sh", ".bash", ".py", ".pl", ".rb"}:
        return True
    if "/bin/" in str(path):
        return True
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            first = f.readline(256)
        return first.startswith("#!")
    except Exception:
        return False


def add_user_execute(path: Path) -> bool:
    try:
        mode = path.stat().st_mode
        if mode & 0o100:
            return True
        path.chmod(mode | 0o100)
        return True
    except Exception:
        return False


def check_module(module: str, module_info: Dict[str, Any], fix: bool) -> CheckResult:
    module_path = str(module_info.get("path", ""))
    tasks_path = Path(module_path) / ".vscode/tasks.json"

    errors: List[str] = []
    warnings: List[str] = []
    task_count = 0
    fixed = 0

    if not tasks_path.exists():
        errors.append("tasks.json missing")
        return CheckResult(module, module_path, str(tasks_path), False, errors, warnings, task_count, fixed)

    try:
        obj = parse_tasks_file(tasks_path)
    except Exception as exc:
        errors.append(f"tasks.json parse error: {exc}")
        return CheckResult(module, module_path, str(tasks_path), False, errors, warnings, task_count, fixed)

    tasks = obj.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("tasks field is not a list")
        return CheckResult(module, module_path, str(tasks_path), False, errors, warnings, task_count, fixed)

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            warnings.append(f"task[{idx}] is not an object")
            continue

        label = str(task.get("label", "")).strip()
        command = str(task.get("command", "")).strip()

        if not label:
            warnings.append(f"task[{idx}] missing label")
        if not command:
            warnings.append(f"task[{idx}] missing command")
            continue

        task_count += 1

        for path in extract_abs_paths(command):
            p = Path(path)
            if not p.exists():
                errors.append(f"{label}: missing path: {path}")
                continue
            if p.is_dir():
                continue
            if likely_executable_path(p) and not os.access(p, os.X_OK):
                if fix and add_user_execute(p):
                    fixed += 1
                    warnings.append(f"{label}: fixed execute-bit on {path}")
                else:
                    errors.append(f"{label}: not executable: {path}")

    ok = len(errors) == 0
    return CheckResult(module, module_path, str(tasks_path), ok, errors, warnings, task_count, fixed)


def run(target: str, json_output: bool, fix: bool) -> int:
    modules = load_modules()
    names = sorted(modules.keys())

    if target != "all":
        if target not in modules:
            print(f"[ERR] Module not found: {target}")
            return 1
        names = [target]

    results = [check_module(name, modules[name], fix=fix) for name in names]

    if json_output:
        payload = {
            "count": len(results),
            "ok": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "fixed": sum(r.fixed for r in results),
            "modules": [
                {
                    "module": r.module,
                    "ok": r.ok,
                    "tasks_path": r.tasks_path,
                    "task_count": r.task_count,
                    "fixed": r.fixed,
                    "errors": r.errors,
                    "warnings": r.warnings,
                }
                for r in results
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0 if payload["failed"] == 0 else 2

    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"[{status}] {r.module}: tasks={r.task_count} fixed={r.fixed} file={r.tasks_path}")
        for e in r.errors[:8]:
            print(f"  ERR: {e}")
        if len(r.errors) > 8:
            print(f"  ERR: ... {len(r.errors) - 8} more")
        for w in r.warnings[:4]:
            print(f"  WARN: {w}")
        if len(r.warnings) > 4:
            print(f"  WARN: ... {len(r.warnings) - 4} more")

    ok_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - ok_count
    fixed_count = sum(r.fixed for r in results)
    print(f"[INFO] Summary: modules={len(results)} ok={ok_count} failed={fail_count} fixed={fixed_count}")
    return 0 if fail_count == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Check health of module VS Code tasks files")
    parser.add_argument("target", nargs="?", default="all", help="Module name or 'all'")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix missing execute bits on script paths")
    args = parser.parse_args()
    return run(args.target, args.json, args.fix)


if __name__ == "__main__":
    raise SystemExit(main())
