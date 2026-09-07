#!/usr/bin/env python3
"""BrainHome task smoke test runner.

Runs safe commands for each module to verify command wiring:
- brainhome devctl <module> status
- brainhome collect-logs <module> <lines>

Usage:
  task-smoketest.py [module|all] [--timeout SEC] [--lines N] [--skip-logs] [--json]
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from paths import resolve_tools_root

TOOLS_ROOT = resolve_tools_root()
MODULES_JSON = TOOLS_ROOT / "config/modules.json"
BRAINHOME_BIN = str(TOOLS_ROOT / "bin/brainhome")


@dataclass
class CmdResult:
    command: str
    ok: bool
    exit_code: int
    timed_out: bool
    output: str


@dataclass
class ModuleResult:
    module: str
    status: CmdResult
    collect_logs: CmdResult | None
    ok: bool


def load_modules() -> Dict[str, Any]:
    if not MODULES_JSON.exists():
        raise FileNotFoundError(f"Registry missing: {MODULES_JSON}")
    data = json.loads(MODULES_JSON.read_text(encoding="utf-8"))
    return data.get("modules", {})


def run_cmd(cmd: List[str], timeout_sec: int) -> CmdResult:
    rendered = " ".join(shlex.quote(x) for x in cmd)
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        out = (completed.stdout or "").strip()
        short = "\n".join(out.splitlines()[:12])
        return CmdResult(rendered, completed.returncode == 0, completed.returncode, False, short)
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        short = "\n".join(out.splitlines()[:12])
        return CmdResult(rendered, False, 124, True, short)


def test_module(module: str, timeout_sec: int, lines: int, skip_logs: bool, strict: bool) -> ModuleResult:
    status_cmd = [BRAINHOME_BIN, "devctl", module, "status"]
    status_res = run_cmd(status_cmd, timeout_sec)

    logs_res: CmdResult | None = None
    if not skip_logs:
        logs_cmd = [BRAINHOME_BIN, "collect-logs", module, str(lines)]
        logs_res = run_cmd(logs_cmd, timeout_sec)

    module_ok = status_res.ok
    if strict and logs_res is not None and not logs_res.ok:
        module_ok = False

    return ModuleResult(module, status_res, logs_res, module_ok)


def run(target: str, timeout_sec: int, lines: int, skip_logs: bool, strict: bool, json_output: bool) -> int:
    modules = load_modules()
    names = sorted(modules.keys())

    if target != "all":
        if target not in modules:
            print(f"[ERR] Module not found: {target}")
            return 1
        names = [target]

    results = [test_module(name, timeout_sec, lines, skip_logs, strict) for name in names]

    if json_output:
        payload = {
            "count": len(results),
            "ok": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "modules": [
                {
                    "module": r.module,
                    "ok": r.ok,
                    "status": {
                        "ok": r.status.ok,
                        "exit_code": r.status.exit_code,
                        "timed_out": r.status.timed_out,
                        "command": r.status.command,
                        "output": r.status.output,
                    },
                    "collect_logs": None
                    if r.collect_logs is None
                    else {
                        "ok": r.collect_logs.ok,
                        "exit_code": r.collect_logs.exit_code,
                        "timed_out": r.collect_logs.timed_out,
                        "command": r.collect_logs.command,
                        "output": r.collect_logs.output,
                    },
                }
                for r in results
            ],
            "strict": strict,
        }
        print(json.dumps(payload, indent=2))
        return 0 if payload["failed"] == 0 else 2

    for r in results:
        state = "PASS" if r.ok else "FAIL"
        print(f"[{state}] {r.module}")
        s = r.status
        print(f"  status: ok={s.ok} code={s.exit_code} timeout={s.timed_out}")
        if s.output:
            for line in s.output.splitlines()[:3]:
                print(f"    {line}")
        if r.collect_logs is not None:
            c = r.collect_logs
            level = "ERR" if strict and not c.ok else ("WARN" if not c.ok else "OK")
            print(f"  collect-logs: ok={c.ok} code={c.exit_code} timeout={c.timed_out} level={level}")
            if c.output:
                for line in c.output.splitlines()[:3]:
                    print(f"    {line}")

    ok_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - ok_count
    print(f"[INFO] Summary: modules={len(results)} ok={ok_count} failed={fail_count}")
    return 0 if fail_count == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safe smoke tests for BrainHome module commands")
    parser.add_argument("target", nargs="?", default="all", help="Module name or 'all'")
    parser.add_argument("--timeout", type=int, default=25, help="Per-command timeout in seconds (default: 25)")
    parser.add_argument("--lines", type=int, default=30, help="collect-logs lines argument (default: 30)")
    parser.add_argument("--skip-logs", action="store_true", help="Skip collect-logs checks")
    parser.add_argument("--strict", action="store_true", help="Fail module if collect-logs check fails")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    return run(args.target, args.timeout, args.lines, args.skip_logs, args.strict, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
