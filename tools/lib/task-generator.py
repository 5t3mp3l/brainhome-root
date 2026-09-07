#!/usr/bin/env python3
"""BrainHome VS Code task generator.

Generates module-scoped .vscode/tasks.json files from the dynamic tools/config path.
Default mode is dry-run. Use --write to persist.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from paths import resolve_tools_root

TOOLS_ROOT = resolve_tools_root()
MODULES_JSON = TOOLS_ROOT / "config/modules.json"
BRAINHOME_BIN = str(TOOLS_ROOT / "bin" / "brainhome")


@dataclass
class Result:
    module: str
    path: Path
    written: bool
    skipped: bool
    reason: str


def is_brainhome_task(task: Dict[str, Any]) -> bool:
    label = str(task.get("label", ""))
    command = str(task.get("command", ""))
    return ("BrainHome:" in label) or ("/bin/brainhome" in command)


def read_existing_tasks(tasks_path: Path) -> Dict[str, Any]:
    text = tasks_path.read_text(encoding="utf-8")
    cleaned = strip_jsonc(text)

    try:
        raw = json.loads(cleaned)
    except Exception as exc:
        raise ValueError(f"existing_tasks_parse_failed: {exc}") from exc

    if not isinstance(raw, dict):
        return {"version": "2.0.0", "tasks": []}
    tasks = raw.get("tasks", [])
    if not isinstance(tasks, list):
        raw["tasks"] = []
    return raw


def strip_jsonc(text: str) -> str:
    # Remove // line comments and /* */ block comments while preserving strings.
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
    # Remove trailing commas before closing objects/arrays.
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def merge_tasks(existing_obj: Dict[str, Any], generated_obj: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    existing_tasks = [t for t in existing_obj.get("tasks", []) if isinstance(t, dict)]
    generated_tasks = [t for t in generated_obj.get("tasks", []) if isinstance(t, dict)]

    preserved = [t for t in existing_tasks if not is_brainhome_task(t)]
    merged = preserved + generated_tasks

    out = dict(existing_obj)
    out["version"] = "2.0.0"
    out["tasks"] = merged
    replaced = len(existing_tasks) - len(preserved)
    return out, replaced


def load_modules() -> Dict[str, Any]:
    if not MODULES_JSON.exists():
        raise FileNotFoundError(f"Registry missing: {MODULES_JSON}")
    data = json.loads(MODULES_JSON.read_text(encoding="utf-8"))
    return data.get("modules", {})


def sanitize_service_name(name: str) -> str:
    return name.strip().replace(" ", "-")


def make_task(label: str, command: str, is_background: bool = False) -> Dict[str, Any]:
    task: Dict[str, Any] = {
        "label": label,
        "type": "shell",
        "command": command,
    }
    if is_background:
        task["isBackground"] = True
    return task


def build_tasks_for_module(module_name: str, module_info: Dict[str, Any]) -> Dict[str, Any]:
    tasks: List[Dict[str, Any]] = []

    tasks.append(
        make_task(
            f"🧭 BrainHome: {module_name} Status",
            f"{BRAINHOME_BIN} devctl {module_name} status",
        )
    )
    tasks.append(
        make_task(
            f"📦 BrainHome: {module_name} Collect Logs",
            f"{BRAINHOME_BIN} collect-logs {module_name} 120",
        )
    )
    tasks.append(
        make_task(
            f"📋 BrainHome: {module_name} Stream Logs",
            f"{BRAINHOME_BIN} devctl {module_name} logs",
            is_background=True,
        )
    )

    dev_services = module_info.get("dev_services", []) or []
    for service in dev_services:
        service_name = sanitize_service_name(service.get("name", "")).strip()
        if not service_name:
            continue

        service_type = str(service.get("type", "")).strip().lower()
        start_cmd = str(service.get("start_cmd", "")).strip()
        stop_cmd = str(service.get("stop_cmd", "")).strip()
        restart_cmd = str(service.get("restart_cmd", "")).strip()

        # Prefer explicit service commands from metadata. Fallback to unified devctl
        # only for runtimes where service names are meaningful.
        if not start_cmd and service_type in {"container", "systemd"}:
            start_cmd = f"{BRAINHOME_BIN} devctl {module_name} start {service_name}"
        if not stop_cmd and service_type in {"container", "systemd"}:
            stop_cmd = f"{BRAINHOME_BIN} devctl {module_name} stop {service_name}"
        if not restart_cmd and service_type in {"container", "systemd"}:
            restart_cmd = f"{BRAINHOME_BIN} devctl {module_name} restart {service_name}"

        if start_cmd:
            tasks.append(
                make_task(
                    f"▶️ BrainHome: {module_name} Start {service_name}",
                    start_cmd,
                    is_background=(service_type == "process"),
                )
            )
        if stop_cmd:
            tasks.append(
                make_task(
                    f"⏹️ BrainHome: {module_name} Stop {service_name}",
                    stop_cmd,
                )
            )
        if restart_cmd:
            tasks.append(
                make_task(
                    f"🔁 BrainHome: {module_name} Restart {service_name}",
                    restart_cmd,
                )
            )

        log_target = "" if service_type == "process" else service_name
        log_cmd = (
            f"{BRAINHOME_BIN} devctl {module_name} logs {log_target} 120".strip()
            if log_target
            else f"{BRAINHOME_BIN} devctl {module_name} logs"
        )
        tasks.append(
            make_task(
                f"📋 BrainHome: {module_name} Logs {service_name}",
                log_cmd,
                is_background=True,
            )
        )

    tasks.append(
        make_task(
            "🩺 BrainHome: Global Dashboard",
            f"{BRAINHOME_BIN} dashboard --refresh-logs --lines 120",
        )
    )

    return {
        "version": "2.0.0",
        "tasks": tasks,
    }


def write_tasks_file(
    module_name: str,
    module_path: Path,
    tasks_obj: Dict[str, Any],
    force: bool,
    merge: bool,
) -> Result:
    vscode_dir = module_path / ".vscode"
    tasks_path = vscode_dir / "tasks.json"

    if not module_path.exists():
        return Result(module_name, tasks_path, False, True, "module_path_missing")

    vscode_dir.mkdir(parents=True, exist_ok=True)

    if tasks_path.exists() and not force and not merge:
        return Result(module_name, tasks_path, False, True, "tasks_exists_use_force")

    if tasks_path.exists() and (force or merge):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = vscode_dir / f"tasks.json.bak-{stamp}"
        shutil.copy2(tasks_path, backup_path)

    write_obj = tasks_obj
    if tasks_path.exists() and merge:
        try:
            existing_obj = read_existing_tasks(tasks_path)
        except Exception:
            return Result(module_name, tasks_path, False, True, "merge_parse_failed_kept_existing")
        write_obj, replaced = merge_tasks(existing_obj, tasks_obj)
        reason = f"merged_replaced={replaced}"
    else:
        reason = "written"

    tasks_path.write_text(json.dumps(write_obj, indent=2) + "\n", encoding="utf-8")
    return Result(module_name, tasks_path, True, False, reason)


def generate_for_target(target: str, write: bool, force: bool, merge: bool) -> int:
    modules = load_modules()
    names = sorted(modules.keys())

    if target != "all":
        if target not in modules:
            print(f"[ERR] Module not found: {target}")
            return 1
        names = [target]

    results: List[Result] = []

    for name in names:
        info = modules[name]
        path = Path(info.get("path", ""))
        tasks_obj = build_tasks_for_module(name, info)
        if write:
            result = write_tasks_file(name, path, tasks_obj, force, merge)
        else:
            result = Result(name, path / ".vscode/tasks.json", False, False, "dry_run")
        results.append(result)

        if write:
            if result.written:
                print(f"[OK] {name}: wrote {result.path} ({result.reason})")
            elif result.skipped:
                print(f"[SKIP] {name}: {result.reason} ({result.path})")
        else:
            print(f"[DRY] {name}: would write {result.path} ({len(tasks_obj.get('tasks', []))} tasks)")

    wrote = sum(1 for r in results if r.written)
    skipped = sum(1 for r in results if r.skipped)
    print(f"[INFO] Summary: modules={len(results)} wrote={wrote} skipped={skipped} mode={'write' if write else 'dry'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate VS Code tasks for BrainHome modules")
    parser.add_argument("target", nargs="?", default="all", help="Module name or 'all'")
    parser.add_argument("--write", action="store_true", help="Write tasks.json files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing tasks.json (backup first)")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge BrainHome tasks into existing tasks.json (preserve non-BrainHome tasks)",
    )
    args = parser.parse_args()

    return generate_for_target(args.target, args.write, args.force, args.merge)


if __name__ == "__main__":
    raise SystemExit(main())
