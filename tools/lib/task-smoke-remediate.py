#!/usr/bin/env python3
"""BrainHome smoke test remediation helper.

Analyzes strict smoke test failures and proposes/executes targeted remediation.
Default mode is dry-run; use --apply to run actions.

Usage:
    task-smoke-remediate.py [module|all] [--timeout SEC] [--lines N] [--apply]
                            [--remote-host HOST] [--remote-path PATH]
                            [--remote-bootstrap] [--repo-url URL] [--repo-branch BRANCH]
                            [--repo-ssh-key PATH]
                            [--auto-remote] [--candidates CSV] [--json]
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from paths import resolve_tools_root

TOOLS_ROOT = resolve_tools_root()
MODULES_JSON = TOOLS_ROOT / "config/modules.json"
SMOKETEST_BIN = str(TOOLS_ROOT / "bin/brainhome-smoketest")
BRAINHOME_BIN = str(TOOLS_ROOT / "bin/brainhome")


@dataclass
class ActionResult:
    module: str
    action: str
    command: str
    applied: bool
    ok: bool
    output: str


def load_modules() -> Dict[str, Any]:
    if not MODULES_JSON.exists():
        raise FileNotFoundError(f"Registry missing: {MODULES_JSON}")
    data = json.loads(MODULES_JSON.read_text(encoding="utf-8"))
    return data.get("modules", {})


def run_cmd(cmd: List[str], timeout_sec: int) -> tuple[bool, str, int]:
    try:
        cp = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        out = (cp.stdout or "").strip()
        short = "\n".join(out.splitlines()[:12])
        return cp.returncode == 0, short, cp.returncode
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        short = "\n".join(out.splitlines()[:12])
        return False, short, 124


def clean_noise_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    filtered: List[str] = []
    for ln in lines:
        low = ln.lower()
        if low.startswith("warning: permanently added"):
            continue
        if low.startswith("bash: warning: setlocale"):
            continue
        filtered.append(ln)
    return filtered


def clean_output_text(text: str) -> str:
    """Remove known SSH noise lines from command output."""
    lines = clean_noise_lines(text)
    return "\n".join(lines)


def has_command(name: str) -> bool:
    ok, _, _ = run_cmd(["bash", "-lc", f"command -v {shlex.quote(name)} >/dev/null"], timeout_sec=5)
    return ok


def has_remote_command(host: str, name: str) -> bool:
    if not host:
        return False
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        host,
        f"command -v {shlex.quote(name)} >/dev/null",
    ]
    ok, _, _ = run_cmd(cmd, timeout_sec=8)
    return ok


def remote_file_exists(host: str, path: str) -> bool:
    if not host or not path:
        return False
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        host,
        f"test -f {shlex.quote(path)}",
    ]
    ok, _, _ = run_cmd(cmd, timeout_sec=8)
    return ok


def remote_repo_access_check(host: str, repo_url: str, repo_branch: str, repo_ssh_key: str = "") -> tuple[bool, str]:
    """Verify non-interactive read access to remote Git repository."""
    if not host or not repo_url:
        return False, "missing host/repo"
    git_env = ""
    if repo_ssh_key:
        git_env = (
            "GIT_SSH_COMMAND=\"ssh -i "
            + shlex.quote(repo_ssh_key)
            + " -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null\" "
        )

    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        host,
        (
            f"{git_env}git ls-remote --heads {shlex.quote(repo_url)} "
            f"{shlex.quote(repo_branch)} >/dev/null"
        ),
    ]
    ok, out, _ = run_cmd(cmd, timeout_sec=20)
    return ok, clean_output_text(out)


def remote_path_exists(host: str, path: str) -> bool:
    if not host or not path:
        return False
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        host,
        f"test -d {shlex.quote(path)}",
    ]
    ok, _, _ = run_cmd(cmd, timeout_sec=8)
    return ok


def find_remote_module_path(host: str, local_module_path: str) -> str:
    """Try to resolve module directory on remote host.

    Strategy:
    1) exact same absolute path
    2) /home/<basename>
    3) find by directory name under /home and /opt
    4) compose fingerprint: find docker-compose.yml or compose.yml files
       whose parent directory name or file content references the module name
    """
    if not host:
        return ""

    if remote_path_exists(host, local_module_path):
        return local_module_path

    base = Path(local_module_path).name
    candidate = f"/home/{base}"
    if remote_path_exists(host, candidate):
        return candidate

    ssh_prefix = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        host,
    ]

    # Strategy 3: find by directory name
    name_cmd = ssh_prefix + [
        f"find /home /opt -maxdepth 4 -type d -name {shlex.quote(base)} 2>/dev/null | head -1",
    ]
    ok, out, _ = run_cmd(name_cmd, timeout_sec=20)
    if ok and out.strip():
        lines = clean_noise_lines(out)
        if lines:
            return lines[0]

    # Strategy 4: compose fingerprint search
    # Find any docker-compose.yml / compose.yml whose parent dir name or
    # file content mentions the module base name (case-insensitive).
    compose_script = (
        f"base={shlex.quote(base)}; "
        "for f in $(find /home /opt -maxdepth 5 "
        r"    \( -name 'docker-compose.yml' -o -name 'compose.yml' \) "
        "    2>/dev/null); do "
        "  dir=$(dirname \"$f\"); "
        "  dname=$(basename \"$dir\"); "
        "  if echo \"$dname\" | grep -qi \"$base\"; then echo \"$dir\"; continue; fi; "
        "  if grep -qi \"$base\" \"$f\" 2>/dev/null; then echo \"$dir\"; fi; "
        "done | head -1"
    )
    compose_cmd = ssh_prefix + [compose_script]
    ok, out, _ = run_cmd(compose_cmd, timeout_sec=25)
    if ok and out.strip():
        lines = clean_noise_lines(out)
        if lines:
            return lines[0]

    return ""


def probe_remote(host: str) -> Tuple[bool, bool]:
    """Returns (ssh_ok, docker_ok)."""
    base = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        host,
    ]
    ssh_ok, _, _ = run_cmd(base + ["echo ok"], timeout_sec=8)
    if not ssh_ok:
        return False, False
    docker_ok, _, _ = run_cmd(base + ["command -v docker >/dev/null"], timeout_sec=8)
    return True, docker_ok


def pick_remote_host(auto_remote: bool, remote_host: str, candidates_csv: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    if remote_host:
        notes.append(f"remote_host provided: {remote_host}")
        return remote_host, notes
    if not auto_remote:
        return "", notes

    candidates = [c.strip() for c in candidates_csv.split(",") if c.strip()]
    for c in candidates:
        ssh_ok, docker_ok = probe_remote(c)
        notes.append(f"probe {c}: ssh_ok={ssh_ok} docker_ok={docker_ok}")
        if ssh_ok and docker_ok:
            notes.append(f"selected_remote={c}")
            return c, notes

    notes.append("selected_remote=<none>")
    return "", notes


def get_strict_failures(target: str, timeout_sec: int, lines: int) -> Dict[str, Any]:
    cmd = [
        SMOKETEST_BIN,
        target,
        "--strict",
        "--timeout",
        str(timeout_sec),
        "--lines",
        str(lines),
        "--json",
    ]
    try:
        cp = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=max(timeout_sec * 5, 60),
            check=False,
        )
        out = (cp.stdout or "").strip()
        payload = json.loads(out) if out.startswith("{") else {"modules": []}
        payload["_ok"] = cp.returncode == 0
        return payload
    except Exception:
        return {"modules": [], "_ok": False}


def remediate_module(
    module_name: str,
    module_info: Dict[str, Any],
    failure: Dict[str, Any],
    apply: bool,
    remote_host: str,
    remote_path: str = "",
    remote_bootstrap: bool = False,
    repo_url_override: str = "",
    repo_branch_override: str = "",
    repo_ssh_key: str = "",
) -> List[ActionResult]:
    actions: List[ActionResult] = []
    c = failure.get("collect_logs") or {}
    collect_ok = bool(c.get("ok", False))
    if collect_ok:
        return actions

    container_type = str(module_info.get("container", {}).get("type", "local"))
    module_path = str(module_info.get("path", ""))

    if container_type == "docker":
        local_cmd = ["bash", "-lc", f"cd {shlex.quote(module_path)} && docker compose up -d"]
        can_local = has_command("docker")
        can_remote = bool(remote_host)

        if not can_local and not can_remote:
            actions.append(
                ActionResult(
                    module=module_name,
                    action="start_docker_services",
                    command=" ".join(local_cmd),
                    applied=False,
                    ok=True,
                    output="docker CLI missing on this host; provide --remote-host or run on Docker-capable host",
                )
            )
            return actions

        if can_local:
            exec_cmd = local_cmd
            exec_hint = "local"
        else:
            if remote_path:
                remote_module_path = remote_path
            else:
                remote_module_path = find_remote_module_path(remote_host, module_path)
            if not remote_module_path:
                if not remote_bootstrap:
                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="start_docker_services",
                            command=" ".join(local_cmd),
                            applied=False,
                            ok=True,
                            output=(
                                f"module path not found on remote host {remote_host}; "
                                f"expected like {module_path}"
                            ),
                        )
                    )
                    return actions

                bootstrap_path = remote_path or module_path or f"/home/{module_name}"
                repo_url = repo_url_override or str(module_info.get("git_remote", "")).strip()
                repo_branch = repo_branch_override or str(module_info.get("git_branch", "main")).strip() or "main"

                if not repo_url:
                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="bootstrap_remote_repo",
                            command="--repo-url <URL> --repo-branch <BRANCH>",
                            applied=False,
                            ok=True,
                            output=(
                                "remote bootstrap requested but no repo URL available; "
                                "provide --repo-url (or configure modules.json git_remote)"
                            ),
                        )
                    )
                    return actions

                if not has_remote_command(remote_host, "git"):
                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="bootstrap_remote_repo",
                            command=f"ssh {remote_host} command -v git",
                            applied=False,
                            ok=True,
                            output=f"git CLI missing on remote host {remote_host}; cannot bootstrap repository",
                        )
                    )
                    return actions

                if repo_ssh_key and not remote_file_exists(remote_host, repo_ssh_key):
                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="bootstrap_repo_key",
                            command=f"ssh {remote_host} test -f {repo_ssh_key}",
                            applied=False,
                            ok=False,
                            output=(
                                f"specified --repo-ssh-key does not exist on remote host: {repo_ssh_key}; "
                                "copy a deploy key to that path or use tokenized HTTPS --repo-url"
                            ),
                        )
                    )
                    return actions

                can_access, access_out = remote_repo_access_check(remote_host, repo_url, repo_branch, repo_ssh_key)
                if not can_access:
                    hint = (
                        "remote host cannot read repo non-interactively; "
                        "use a tokenized HTTPS URL or configure SSH deploy key and use git@github.com:<owner>/<repo>.git"
                    )
                    if "could not read username" in access_out.lower():
                        hint = (
                            "remote host cannot authenticate to GitHub over HTTPS in batch mode; "
                            "use tokenized HTTPS URL or SSH repo URL with deploy key"
                        )
                    elif "permission denied (publickey)" in access_out.lower():
                        hint = (
                            "remote host has no GitHub SSH key access; "
                            "add deploy key and use git@github.com:<owner>/<repo>.git or use tokenized HTTPS URL"
                        )

                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="bootstrap_repo_access",
                            command=f"ssh {remote_host} git ls-remote --heads {repo_url} {repo_branch}",
                            applied=False,
                            ok=False,
                            output=f"{hint}\n{access_out}" if access_out else hint,
                        )
                    )
                    return actions

                bootstrap_inner = (
                    (
                        "export GIT_SSH_COMMAND=\"ssh -i "
                        + shlex.quote(repo_ssh_key)
                        + " -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null\" && "
                    )
                    if repo_ssh_key
                    else ""
                ) + (
                    f"mkdir -p {shlex.quote(str(Path(bootstrap_path).parent))} && "
                    f"if [ -d {shlex.quote(bootstrap_path)}/.git ]; then "
                    f"cd {shlex.quote(bootstrap_path)} && git pull --ff-only; "
                    "else "
                    f"git clone --depth 1 --branch {shlex.quote(repo_branch)} {shlex.quote(repo_url)} {shlex.quote(bootstrap_path)}; "
                    "fi"
                )
                bootstrap_cmd = [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "LogLevel=ERROR",
                    remote_host,
                    bootstrap_inner,
                ]

                if apply:
                    bok, bout, _ = run_cmd(bootstrap_cmd, timeout_sec=120)
                    bout = clean_output_text(bout)
                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="bootstrap_remote_repo",
                            command=" ".join(bootstrap_cmd),
                            applied=True,
                            ok=bok,
                            output=bout or f"bootstrapped {bootstrap_path}",
                        )
                    )
                    if not bok:
                        return actions
                else:
                    actions.append(
                        ActionResult(
                            module=module_name,
                            action="bootstrap_remote_repo",
                            command=" ".join(bootstrap_cmd),
                            applied=False,
                            ok=True,
                            output=f"dry-run: would clone/pull {repo_url}@{repo_branch} to {bootstrap_path}",
                        )
                    )

                remote_module_path = bootstrap_path

            ssh_inner = f"cd {shlex.quote(remote_module_path)} && docker compose up -d"
            exec_cmd = [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "LogLevel=ERROR",
                remote_host,
                ssh_inner,
            ]
            exec_hint = f"remote:{remote_host}:{remote_module_path}"

            if not has_remote_command(remote_host, "docker"):
                actions.append(
                    ActionResult(
                        module=module_name,
                        action="start_docker_services",
                        command=" ".join(exec_cmd),
                        applied=False,
                        ok=True,
                        output=f"docker CLI missing on remote host {remote_host}; run remediation on docker-capable target",
                    )
                )
                return actions

        if apply:
            ok, out, _ = run_cmd(exec_cmd, timeout_sec=90)
            actions.append(
                ActionResult(
                    module=module_name,
                    action="start_docker_services",
                    command=" ".join(exec_cmd),
                    applied=True,
                    ok=ok,
                    output=f"executor={exec_hint}\n{out}" if out else f"executor={exec_hint}",
                )
            )
        else:
            actions.append(
                ActionResult(
                    module=module_name,
                    action="start_docker_services",
                    command=" ".join(exec_cmd),
                    applied=False,
                    ok=True,
                    output=f"dry-run: would start docker compose services via {exec_hint}",
                )
            )

    elif container_type == "lxc":
        ct_id = str(module_info.get("container", {}).get("id", ""))
        # Check whether the container is simply stopped
        ct_running = False
        if ct_id:
            ok_s, out_s, _ = run_cmd(["pct", "status", ct_id], timeout_sec=8)
            ct_running = ok_s and "running" in out_s.lower()

        if ct_id and not ct_running:
            start_cmd = ["pct", "start", ct_id]
            if apply:
                ok, out, _ = run_cmd(start_cmd, timeout_sec=30)
                actions.append(
                    ActionResult(
                        module=module_name,
                        action="start_lxc_container",
                        command=" ".join(start_cmd),
                        applied=True,
                        ok=ok,
                        output=out or ("started" if ok else "start failed"),
                    )
                )
            else:
                actions.append(
                    ActionResult(
                        module=module_name,
                        action="start_lxc_container",
                        command=" ".join(start_cmd),
                        applied=False,
                        ok=True,
                        output=f"dry-run: LXC container {ct_id} is stopped; would run pct start {ct_id}",
                    )
                )
        else:
            actions.append(
                ActionResult(
                    module=module_name,
                    action="tune_lxc_collection",
                    command=f"{BRAINHOME_BIN} smoketest {module_name} --strict --timeout 45 --lines 10",
                    applied=False,
                    ok=True,
                    output="LXC container is running; collect-logs may still fail — check journalctl inside container",
                )
            )

    elif container_type == "ssh":
        actions.append(
            ActionResult(
                module=module_name,
                action="check_ssh_connectivity",
                command=f"{BRAINHOME_BIN} devctl {module_name} status",
                applied=False,
                ok=True,
                output="Verify SSH auth/connectivity if collect-logs keeps failing",
            )
        )

    else:
        actions.append(
            ActionResult(
                module=module_name,
                action="manual_review",
                command=f"{BRAINHOME_BIN} collect-logs {module_name} 20",
                applied=False,
                ok=True,
                output="No automatic remediation for this container type",
            )
        )

    return actions


def run(
    target: str,
    timeout_sec: int,
    lines: int,
    apply: bool,
    remote_host: str,
    remote_path: str,
    remote_bootstrap: bool,
    repo_url: str,
    repo_branch: str,
    repo_ssh_key: str,
    auto_remote: bool,
    candidates_csv: str,
    json_output: bool,
) -> int:
    modules = load_modules()
    resolved_remote, probe_notes = pick_remote_host(auto_remote, remote_host, candidates_csv)
    strict = get_strict_failures(target, timeout_sec, lines)
    failures = [m for m in strict.get("modules", []) if not m.get("ok", False)]

    actions: List[ActionResult] = []
    for f in failures:
        name = str(f.get("module", ""))
        if not name or name not in modules:
            continue
        actions.extend(
            remediate_module(
                name,
                modules[name],
                f,
                apply,
                resolved_remote,
                remote_path,
                remote_bootstrap,
                repo_url,
                repo_branch,
                repo_ssh_key,
            )
        )

    if json_output:
        payload = {
            "target": target,
            "apply": apply,
            "remote_host": resolved_remote,
            "remote_path": remote_path,
            "remote_bootstrap": remote_bootstrap,
            "repo_url": repo_url,
            "repo_branch": repo_branch,
            "repo_ssh_key": repo_ssh_key,
            "auto_remote": auto_remote,
            "probe_notes": probe_notes,
            "strict_failed": len(failures),
            "actions": [
                {
                    "module": a.module,
                    "action": a.action,
                    "command": a.command,
                    "applied": a.applied,
                    "ok": a.ok,
                    "output": a.output,
                }
                for a in actions
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"[INFO] strict_failures={len(failures)} apply={apply} remote_host={resolved_remote or '-'} auto_remote={auto_remote}")
    for n in probe_notes[:8]:
        print(f"[INFO] {n}")
    if not failures:
        print("[OK] No remediation needed")
        return 0

    for a in actions:
        state = "APPLIED" if a.applied else "PLAN"
        ok = "OK" if a.ok else "FAIL"
        print(f"[{state}/{ok}] {a.module}: {a.action}")
        print(f"  cmd: {a.command}")
        if a.output:
            for line in a.output.splitlines()[:4]:
                print(f"  out: {line}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest or apply remediation for strict smoketest failures")
    parser.add_argument("target", nargs="?", default="all", help="Module name or 'all'")
    parser.add_argument("--timeout", type=int, default=20, help="Strict smoketest timeout seconds")
    parser.add_argument("--lines", type=int, default=20, help="Strict smoketest collect-logs lines")
    parser.add_argument("--apply", action="store_true", help="Apply remediation actions where supported")
    parser.add_argument("--remote-host", default="", help="SSH host for remote docker remediation when local docker is unavailable")
    parser.add_argument("--remote-path", default="", help="Explicit module directory path on remote host (skips auto path search)")
    parser.add_argument("--remote-bootstrap", action="store_true", help="If remote docker module path is missing, prepare it via git clone/pull")
    parser.add_argument("--repo-url", default="", help="Git repository URL override for remote bootstrap")
    parser.add_argument("--repo-branch", default="", help="Git branch override for remote bootstrap")
    parser.add_argument("--repo-ssh-key", default="", help="Path to SSH private key on remote host for git@... access")
    parser.add_argument("--auto-remote", action="store_true", help="Auto-detect a docker-capable remote host via SSH probes")
    parser.add_argument(
        "--candidates",
        default="proxmox-dev,192.168.188.254,192.168.188.107,192.168.188.108,192.168.188.200",
        help="Comma-separated SSH host candidates for --auto-remote",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()
    return run(
        args.target,
        args.timeout,
        args.lines,
        args.apply,
        args.remote_host,
        args.remote_path,
        args.remote_bootstrap,
        args.repo_url,
        args.repo_branch,
        args.repo_ssh_key,
        args.auto_remote,
        args.candidates,
        args.json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
