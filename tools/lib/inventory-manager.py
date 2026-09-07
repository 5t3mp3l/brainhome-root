#!/usr/bin/env python3
"""
inventory-manager.py - Central infrastructure inventory for BrainHome

Builds a consolidated inventory JSON under the dynamic tools/config path from:
- Proxmox live data (pvesh)
- tools modules registry (modules.json)
- operator-maintained overrides (inventory-overrides.json)
"""

from __future__ import annotations

import argparse
import os
from fnmatch import fnmatchcase
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from paths import resolve_tools_root

TOOLS_ROOT = resolve_tools_root()
MODULES_JSON = TOOLS_ROOT / "config" / "modules.json"
OVERRIDES_JSON = TOOLS_ROOT / "config" / "inventory-overrides.json"
DEFAULT_OUT = TOOLS_ROOT / "config" / "infrastructure-inventory.json"
INVENTORY_LOG_DIR = TOOLS_ROOT / "logs" / "inventory"
INVENTORY_STATUS_JSON = INVENTORY_LOG_DIR / "preflight-last.json"
INVENTORY_LAST_LOG = INVENTORY_LOG_DIR / "preflight-last.log"
INVENTORY_CRON_LOG = INVENTORY_LOG_DIR / "cron.log"
INVENTORY_BASELINE_LAST_JSON = INVENTORY_LOG_DIR / "baseline-last.json"
INVENTORY_DRIFT_LAST_JSON = INVENTORY_LOG_DIR / "drift-last.json"
INVENTORY_DRIFT_ALLOWLIST_JSON = TOOLS_ROOT / "config" / "inventory-drift-allowlist.json"
CRON_MARKER = "# brainhome-inventory-cron"
EXPORT_CRON_MARKER = "# brainhome-inventory-export-cron"
BRAINHOME_INVENTORY_BIN = TOOLS_ROOT / "bin" / "brainhome-inventory"


def run_cmd(cmd: List[str], timeout: int = 12) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as exc:  # pylint: disable=broad-except
        return 1, "", str(exc)


def run_json(cmd: List[str], timeout: int = 12) -> Tuple[bool, Any, str]:
    rc, out, err = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        return False, None, err.strip() or f"command failed: {' '.join(cmd)}"
    try:
        return True, json.loads(out), ""
    except json.JSONDecodeError as exc:
        return False, None, f"invalid json output: {exc}"


def load_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pylint: disable=broad-except
        return fallback


def save_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_ip_from_keyval_blob(blob: str) -> str:
    """Extract static IP from strings like 'ip=192.168.1.10/24,gw=...'"""
    if not blob:
        return ""
    match = re.search(r"(?:^|,)ip=([^,]+)", blob)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.lower() == "dhcp":
        return "dhcp"
    return value


def normalize_ip(ip_value: str) -> str:
    value = (ip_value or "").strip()
    if "/" in value:
        value = value.split("/", 1)[0]
    return value


def normalize_host_to_ip(host: str) -> str:
    # root@192.168.188.107 -> 192.168.188.107
    if "@" in host:
        host = host.split("@", 1)[1]
    return host.strip()


def load_modules() -> Dict[str, Any]:
    data = load_json_file(MODULES_JSON, {})
    modules = data.get("modules", {}) if isinstance(data, dict) else {}
    return modules if isinstance(modules, dict) else {}


def build_module_section(modules: Dict[str, Any], overrides: Dict[str, Any]) -> List[Dict[str, Any]]:
    module_overrides = overrides.get("modules", {}) if isinstance(overrides, dict) else {}
    result = []

    for name, mod in sorted(modules.items()):
        container = mod.get("container", {}) or {}
        hosts = []
        if container.get("type") == "ssh":
            hosts = [normalize_host_to_ip(h) for h in (container.get("hosts") or [])]

        ports = []
        for svc in mod.get("dev_services", []) or []:
            port = svc.get("port")
            if isinstance(port, int):
                ports.append(port)

        ports = sorted(set(ports + (module_overrides.get(name, {}).get("ports", []) or [])))

        result.append(
            {
                "name": name,
                "path": mod.get("path", ""),
                "category": mod.get("category", ""),
                "module_type": mod.get("module_type", ""),
                "container_type": container.get("type", ""),
                "container_hosts": hosts,
                "ports": ports,
                "dependencies": mod.get("dependencies", []) or [],
            }
        )

    return result


def build_proxmox_guest_section(overrides: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []

    ok, cluster_items, err = run_json(["pvesh", "get", "/cluster/resources", "--type", "vm", "--output-format", "json"], timeout=20)
    if not ok:
        warnings.append(f"proxmox inventory unavailable: {err}")
        return [], warnings

    guest_overrides = overrides.get("guests", {}) if isinstance(overrides, dict) else {}
    guests: List[Dict[str, Any]] = []

    for item in cluster_items:
        vmid = item.get("vmid")
        node = item.get("node", "")
        vmtype = item.get("type", "")  # qemu or lxc
        if vmid is None or vmtype not in ("qemu", "lxc"):
            continue

        vmid_str = str(vmid)
        path = f"/nodes/{node}/{vmtype}/{vmid}/config"
        ok_cfg, cfg, err_cfg = run_json(["pvesh", "get", path, "--output-format", "json"], timeout=20)
        if not ok_cfg:
            cfg = {}
            warnings.append(f"config read failed for {vmtype}/{vmid} on {node}: {err_cfg}")

        ip_runtime = ""
        if vmtype == "qemu":
            ip_runtime = parse_ip_from_keyval_blob(str(cfg.get("ipconfig0", "")))
        elif vmtype == "lxc":
            ip_runtime = parse_ip_from_keyval_blob(str(cfg.get("net0", "")))

        ov = guest_overrides.get(vmid_str, {}) if isinstance(guest_overrides, dict) else {}
        ov = ov if isinstance(ov, dict) else {}
        ip_runtime_normalized = normalize_ip(ip_runtime)
        ip_override = normalize_ip(str(ov.get("ip", "")))

        guests.append(
            {
                "id": vmid,
                "type": vmtype,
                "name": item.get("name", ""),
                "node": node,
                "status": item.get("status", ""),
                "ip_runtime": ip_runtime,
                "ip_runtime_normalized": ip_runtime_normalized,
                "ip_override": ip_override,
                "ip": ip_override or ip_runtime_normalized,
                "agent_enabled": str(cfg.get("agent", "")).startswith("enabled=1") if vmtype == "qemu" else False,
                "module": ov.get("module", ""),
                "ports": ov.get("ports", []),
                "tags": [t for t in str(item.get("tags", "")).split(";") if t],
                "notes": ov.get("notes", ""),
            }
        )

    guests.sort(key=lambda x: (x.get("type", ""), int(x.get("id", 0))))
    return guests, warnings


def build_node_section(overrides: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    node_overrides = overrides.get("nodes", {}) if isinstance(overrides, dict) else {}

    ok, nodes, err = run_json(["pvesh", "get", "/nodes", "--output-format", "json"], timeout=12)
    if not ok:
        warnings.append(f"proxmox nodes unavailable: {err}")
        return [], warnings

    out = []
    for n in nodes:
        name = n.get("node", "")
        ov = node_overrides.get(name, {}) if isinstance(node_overrides, dict) else {}
        out.append(
            {
                "name": name,
                "status": "online" if n.get("status") == "online" else str(n.get("status", "unknown")),
                "ip": ov.get("ip", ""),
                "dns": ov.get("dns", []),
                "role": ov.get("role", ""),
                "notes": ov.get("notes", ""),
            }
        )

    out.sort(key=lambda x: x.get("name", ""))
    return out, warnings


def build_inventory() -> Dict[str, Any]:
    modules = load_modules()
    overrides = load_json_file(OVERRIDES_JSON, {})

    nodes, node_warnings = build_node_section(overrides)
    guests, guest_warnings = build_proxmox_guest_section(overrides)
    module_section = build_module_section(modules, overrides)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources": {
            "modules_registry": str(MODULES_JSON),
            "overrides": str(OVERRIDES_JSON),
            "proxmox_api": True,
            "architecture_docs_hint": [
                "/home/architektur/BRAINHOME-ARCHITEKTUR.md",
                "/home/pxe-boot/ENTWICKLER-WISSEN.md",
            ],
        },
        "warnings": node_warnings + guest_warnings,
        "nodes": nodes,
        "guests": guests,
        "modules": module_section,
    }


def save_inventory(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def print_summary(inv: Dict[str, Any], section: str) -> None:
    if section in ("all", "nodes"):
        print("\n[NODES]")
        for n in inv.get("nodes", []):
            print(f"- {n['name']}: status={n['status']} ip={n.get('ip','')} role={n.get('role','')}")

    if section in ("all", "guests"):
        print("\n[GUESTS]")
        for g in inv.get("guests", []):
            print(
                f"- {g['type']}/{g['id']} {g['name']} on {g['node']}: "
                f"status={g['status']} ip={g.get('ip','')} agent={g.get('agent_enabled', False)}"
            )

    if section in ("all", "modules"):
        print("\n[MODULES]")
        for m in inv.get("modules", []):
            print(
                f"- {m['name']}: type={m['module_type']} hosts={','.join(m['container_hosts'])} "
                f"ports={','.join(str(p) for p in m['ports'])}"
            )

    if inv.get("warnings"):
        print("\n[WARNINGS]")
        for w in inv["warnings"]:
            print(f"- {w}")


def export_markdown(inv: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# BrainHome Infrastructure Inventory")
    lines.append("")
    lines.append(f"Generated: {inv.get('generated_at', '')}")
    lines.append("")

    lines.append("## Nodes")
    lines.append("")
    lines.append("| Name | Status | IP | DNS | Role |")
    lines.append("|---|---|---|---|---|")
    for n in inv.get("nodes", []):
        dns = ", ".join(n.get("dns", []))
        lines.append(f"| {n.get('name','')} | {n.get('status','')} | {n.get('ip','')} | {dns} | {n.get('role','')} |")

    lines.append("")
    lines.append("## Guests (VM/CT)")
    lines.append("")
    lines.append("| ID | Type | Name | Node | Status | IP | Agent | Module | Ports |")
    lines.append("|---:|---|---|---|---|---|---|---|---|")
    for g in inv.get("guests", []):
        ports = ",".join(str(p) for p in g.get("ports", []))
        lines.append(
            f"| {g.get('id','')} | {g.get('type','')} | {g.get('name','')} | {g.get('node','')} | "
            f"{g.get('status','')} | {g.get('ip','')} | {g.get('agent_enabled', False)} | "
            f"{g.get('module','')} | {ports} |"
        )

    lines.append("")
    lines.append("## Modules")
    lines.append("")
    lines.append("| Name | Type | Category | Container Hosts | Ports | Dependencies |")
    lines.append("|---|---|---|---|---|---|")
    for m in inv.get("modules", []):
        hosts = ", ".join(m.get("container_hosts", []))
        ports = ", ".join(str(p) for p in m.get("ports", []))
        deps = ", ".join(m.get("dependencies", []))
        lines.append(
            f"| {m.get('name','')} | {m.get('module_type','')} | {m.get('category','')} | {hosts} | {ports} | {deps} |"
        )

    if inv.get("warnings"):
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        for w in inv["warnings"]:
            lines.append(f"- {w}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_preflight_findings(inv: Dict[str, Any], overrides: Dict[str, Any]) -> List[Tuple[str, str]]:
    findings: List[Tuple[str, str]] = []

    guests = inv.get("guests", []) if isinstance(inv.get("guests", []), list) else []
    nodes = inv.get("nodes", []) if isinstance(inv.get("nodes", []), list) else []
    guest_overrides = overrides.get("guests", {}) if isinstance(overrides, dict) else {}
    node_overrides = overrides.get("nodes", {}) if isinstance(overrides, dict) else {}

    live_guest_by_id = {str(g.get("id")): g for g in guests}
    live_node_names = {str(n.get("name", "")) for n in nodes}

    for node_name in node_overrides.keys():
        if node_name not in live_node_names:
            findings.append(("error", f"node override not found in live cluster: {node_name}"))

    for n in nodes:
        if not n.get("ip"):
            findings.append(("warn", f"node has no override IP metadata: {n.get('name','')}"))

    for guest_id, ov in guest_overrides.items():
        guest = live_guest_by_id.get(str(guest_id))
        if guest is None:
            findings.append(("error", f"guest override references unknown VM/CT id: {guest_id}"))
            continue

        expected_node = str(ov.get("node", "")).strip()
        if expected_node and expected_node != str(guest.get("node", "")):
            findings.append(
                ("error", f"node drift for id {guest_id}: expected={expected_node} live={guest.get('node','')}")
            )

        expected_ip = normalize_ip(str(ov.get("ip", "")).strip())
        runtime_ip_raw = str(guest.get("ip_runtime", "")).strip()
        runtime_ip = normalize_ip(runtime_ip_raw)
        if expected_ip and runtime_ip and runtime_ip_raw.lower() != "dhcp" and expected_ip != runtime_ip:
            findings.append(
                ("error", f"IP drift for id {guest_id}: expected={expected_ip} runtime={runtime_ip_raw}")
            )

        if guest.get("type") == "qemu" and str(guest.get("status", "")) == "running" and not guest.get("agent_enabled", False):
            findings.append(("warn", f"qemu guest without enabled agent flag: id {guest_id} ({guest.get('name','')})"))

    for guest in guests:
        gid = str(guest.get("id"))
        if gid not in guest_overrides:
            findings.append(("warn", f"live guest missing override metadata: id {gid} ({guest.get('name','')})"))

    for w in inv.get("warnings", []) or []:
        findings.append(("warn", f"inventory warning: {w}"))

    return findings


def run_preflight(inv: Dict[str, Any], overrides: Dict[str, Any], strict: bool) -> int:
    findings = collect_preflight_findings(inv, overrides)

    err_count = sum(1 for lvl, _ in findings if lvl == "error")
    warn_count = sum(1 for lvl, _ in findings if lvl == "warn")

    if findings:
        print("[PREFLIGHT]")
        for lvl, msg in findings:
            tag = "ERR" if lvl == "error" else "WARN"
            print(f"- [{tag}] {msg}")
    else:
        print("[PREFLIGHT] OK - no drift detected")

    print(f"[PREFLIGHT] summary: errors={err_count} warnings={warn_count}")

    if err_count > 0:
        return 2
    if strict and warn_count > 0:
        return 3
    return 0


def _guest_index(inv: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    guests = inv.get("guests", []) if isinstance(inv.get("guests", []), list) else []
    out: Dict[str, Dict[str, Any]] = {}
    for g in guests:
        gid = str(g.get("id", "")).strip()
        if not gid:
            continue
        out[gid] = {
            "name": str(g.get("name", "")),
            "type": str(g.get("type", "")),
            "node": str(g.get("node", "")),
            "status": str(g.get("status", "")),
            "ip": str(g.get("ip", "")),
            "module": str(g.get("module", "")),
        }
    return out


def _node_index(inv: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    nodes = inv.get("nodes", []) if isinstance(inv.get("nodes", []), list) else []
    out: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        name = str(n.get("name", "")).strip()
        if not name:
            continue
        out[name] = {
            "status": str(n.get("status", "")),
            "ip": str(n.get("ip", "")),
            "role": str(n.get("role", "")),
        }
    return out


def _append_change(changes: List[Dict[str, str]], scope: str, ident: str, field: str, from_v: str, to_v: str) -> None:
    if str(from_v) == str(to_v):
        return
    changes.append(
        {
            "scope": scope,
            "id": ident,
            "field": field,
            "from": str(from_v),
            "to": str(to_v),
        }
    )


def build_drift_report(current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    changes: List[Dict[str, str]] = []

    cur_guests = _guest_index(current)
    base_guests = _guest_index(baseline)
    all_guest_ids = sorted(set(cur_guests.keys()) | set(base_guests.keys()), key=lambda x: int(x) if x.isdigit() else x)
    for gid in all_guest_ids:
        c = cur_guests.get(gid)
        b = base_guests.get(gid)
        if b is None:
            _append_change(changes, "guest", gid, "_exists", "false", "true")
            continue
        if c is None:
            _append_change(changes, "guest", gid, "_exists", "true", "false")
            continue
        for field in ("name", "type", "node", "status", "ip", "module"):
            _append_change(changes, "guest", gid, field, b.get(field, ""), c.get(field, ""))

    cur_nodes = _node_index(current)
    base_nodes = _node_index(baseline)
    all_nodes = sorted(set(cur_nodes.keys()) | set(base_nodes.keys()))
    for node in all_nodes:
        c = cur_nodes.get(node)
        b = base_nodes.get(node)
        if b is None:
            _append_change(changes, "node", node, "_exists", "false", "true")
            continue
        if c is None:
            _append_change(changes, "node", node, "_exists", "true", "false")
            continue
        for field in ("status", "ip", "role"):
            _append_change(changes, "node", node, field, b.get(field, ""), c.get(field, ""))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "changes": changes,
        "change_count": len(changes),
    }


def _parse_expiry(value: str) -> Tuple[bool, datetime]:
    text = str(value or "").strip()
    if not text:
        return False, datetime.min.replace(tzinfo=timezone.utc)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        dt = datetime.fromisoformat(f"{text}T23:59:59+00:00")
        return True, dt
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return True, dt
    except ValueError:
        return False, datetime.min.replace(tzinfo=timezone.utc)


def _change_matches_rule(change: Dict[str, str], rule: Dict[str, str]) -> bool:
    for field in ("scope", "id", "field", "from", "to"):
        pattern = str(rule.get(field, "*") or "*")
        value = str(change.get(field, ""))
        if not fnmatchcase(value, pattern):
            return False
    return True


def load_drift_allowlist(path: Path) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload = load_json_file(path, {})
    rules_raw = payload.get("rules", []) if isinstance(payload, dict) else []
    rules = rules_raw if isinstance(rules_raw, list) else []

    active: List[Dict[str, str]] = []
    expired: List[Dict[str, str]] = []
    invalid_expiry: List[Dict[str, str]] = []

    for raw in rules:
        if not isinstance(raw, dict):
            continue
        rule = {k: str(raw.get(k, "")) for k in ("scope", "id", "field", "from", "to", "ticket_id", "expires_at")}
        expires_at = rule.get("expires_at", "").strip()
        if expires_at:
            ok, dt = _parse_expiry(expires_at)
            if not ok:
                invalid_expiry.append(rule)
                continue
            if dt < now:
                expired.append(rule)
                continue
        active.append(rule)

    return {
        "rules_total": len(rules),
        "rules_active": active,
        "rules_expired": expired,
        "rules_invalid_expiry": invalid_expiry,
    }


def apply_drift_allowlist(changes: List[Dict[str, str]], rules: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    effective: List[Dict[str, str]] = []
    ignored: List[Dict[str, str]] = []
    for change in changes:
        matched = any(_change_matches_rule(change, rule) for rule in rules)
        if matched:
            ignored.append(change)
        else:
            effective.append(change)
    return effective, ignored


def run_drift_diff(
    refresh: bool,
    as_json: bool,
    fail_on_change: bool,
    fail_on_expired_rules: bool,
    fail_on_invalid_expiry: bool,
    allowlist_path: str,
    no_allowlist: bool,
) -> int:
    if refresh:
        current = build_inventory()
        save_inventory(DEFAULT_OUT, current)
    else:
        current = load_json_file(DEFAULT_OUT, {})
        if not current:
            print(f"[ERR] inventory not found or empty: {DEFAULT_OUT}", file=sys.stderr)
            return 1

    baseline = load_json_file(INVENTORY_BASELINE_LAST_JSON, {})
    if not baseline:
        print(f"[ERR] baseline not found or empty: {INVENTORY_BASELINE_LAST_JSON}", file=sys.stderr)
        return 1

    drift = build_drift_report(current=current, baseline=baseline)
    raw_changes = drift.get("changes", []) if isinstance(drift.get("changes", []), list) else []

    allowlist_meta = {"rules_total": 0, "rules_active": [], "rules_expired": [], "rules_invalid_expiry": []}
    effective_changes = list(raw_changes)
    ignored_changes: List[Dict[str, str]] = []
    used_allowlist = ""

    if not no_allowlist:
        path = Path(allowlist_path) if allowlist_path else INVENTORY_DRIFT_ALLOWLIST_JSON
        used_allowlist = str(path)
        if path.exists():
            allowlist_meta = load_drift_allowlist(path)
            active_rules = allowlist_meta.get("rules_active", []) if isinstance(allowlist_meta.get("rules_active", []), list) else []
            effective_changes, ignored_changes = apply_drift_allowlist(raw_changes, active_rules)

    report = {
        "generated_at": drift.get("generated_at"),
        "baseline": str(INVENTORY_BASELINE_LAST_JSON),
        "inventory": str(DEFAULT_OUT),
        "changes": raw_changes,
        "change_count": len(raw_changes),
        "allowlist": {
            "path": used_allowlist,
            "rules_total": int(allowlist_meta.get("rules_total", 0) or 0),
            "rules_expired": len(allowlist_meta.get("rules_expired", []) or []),
            "rules_invalid_expiry": len(allowlist_meta.get("rules_invalid_expiry", []) or []),
            "ignored_changes": ignored_changes,
            "ignored_count": len(ignored_changes),
            "disabled": bool(no_allowlist),
        },
        "effective_changes": effective_changes,
        "effective_change_count": len(effective_changes),
    }

    INVENTORY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    save_json_file(INVENTORY_DRIFT_LAST_JSON, report)

    rc = 0
    if fail_on_invalid_expiry and report["allowlist"]["rules_invalid_expiry"] > 0:
        rc = 6
    elif fail_on_expired_rules and report["allowlist"]["rules_expired"] > 0:
        rc = 5
    elif fail_on_change and report["effective_change_count"] > 0:
        rc = 4

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(f"[DRIFT] raw_changes={report['change_count']} effective_changes={report['effective_change_count']}")
        print(
            "[DRIFT] allowlist="
            f"rules_total={report['allowlist']['rules_total']} "
            f"rules_expired={report['allowlist']['rules_expired']} "
            f"rules_invalid_expiry={report['allowlist']['rules_invalid_expiry']}"
        )
        print(f"[DRIFT] report={INVENTORY_DRIFT_LAST_JSON}")

    return rc


def run_baseline_save(refresh: bool) -> int:
    if refresh:
        inv = build_inventory()
        save_inventory(DEFAULT_OUT, inv)
    else:
        inv = load_json_file(DEFAULT_OUT, {})
        if not inv:
            print(f"[ERR] inventory not found or empty: {DEFAULT_OUT}", file=sys.stderr)
            return 1

    INVENTORY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    save_json_file(INVENTORY_BASELINE_LAST_JSON, inv)
    print(f"[OK] baseline saved: {INVENTORY_BASELINE_LAST_JSON}")
    print(f"[INFO] baseline_generated_at={inv.get('generated_at', '')}")
    return 0


def run_preflight_profile(profile: str, as_json: bool) -> int:
    profile_name = str(profile or "").strip().lower()
    if profile_name not in ("daily", "release"):
        print(f"[ERR] unknown preflight profile: {profile_name}", file=sys.stderr)
        return 1

    inv = build_inventory()
    save_inventory(DEFAULT_OUT, inv)
    overrides = load_json_file(OVERRIDES_JSON, {})

    strict = profile_name == "release"
    rc_inventory = run_preflight(inv, overrides, strict=strict)
    results: List[Dict[str, Any]] = [{"check": "inventory", "rc": rc_inventory}]

    if profile_name == "release":
        baseline = load_json_file(INVENTORY_BASELINE_LAST_JSON, {})
        if not baseline:
            drift_ci = {
                "check": "drift_ci",
                "rc": 1,
                "details": {
                    "baseline_loaded": False,
                    "reason": "baseline_missing_or_empty",
                    "effective_changes": None,
                    "rules_total": 0,
                    "rules_expired": 0,
                    "rules_invalid_expiry": 0,
                },
            }
        else:
            drift_report = build_drift_report(current=inv, baseline=baseline)
            raw_changes = drift_report.get("changes", []) if isinstance(drift_report.get("changes", []), list) else []
            allow_meta = load_drift_allowlist(INVENTORY_DRIFT_ALLOWLIST_JSON) if INVENTORY_DRIFT_ALLOWLIST_JSON.exists() else {
                "rules_total": 0,
                "rules_active": [],
                "rules_expired": [],
                "rules_invalid_expiry": [],
            }
            active_rules = allow_meta.get("rules_active", []) if isinstance(allow_meta.get("rules_active", []), list) else []
            effective_changes, _ = apply_drift_allowlist(raw_changes, active_rules)

            rules_expired = len(allow_meta.get("rules_expired", []) or [])
            rules_invalid_expiry = len(allow_meta.get("rules_invalid_expiry", []) or [])
            effective_total = len(effective_changes)

            rc_drift = 0
            if rules_invalid_expiry > 0:
                rc_drift = 6
            elif rules_expired > 0:
                rc_drift = 5
            elif effective_total > 0:
                rc_drift = 4

            drift_ci = {
                "check": "drift_ci",
                "rc": rc_drift,
                "details": {
                    "baseline_loaded": True,
                    "reason": "",
                    "effective_changes": effective_total,
                    "rules_total": int(allow_meta.get("rules_total", 0) or 0),
                    "rules_expired": rules_expired,
                    "rules_invalid_expiry": rules_invalid_expiry,
                },
            }
        results.append(drift_ci)

    overall_rc = max(int(item.get("rc", 0) or 0) for item in results)
    overall_rc_sources = [item.get("check", "") for item in results if int(item.get("rc", 0) or 0) == overall_rc and overall_rc > 0]
    failed_checks = [item for item in results if int(item.get("rc", 0) or 0) > 0]

    summary: Dict[str, Any] = {
        "profile": profile_name,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "results": results,
        "overall_rc": overall_rc,
        "overall_rc_sources": overall_rc_sources,
        "failed_checks": failed_checks,
    }
    if profile_name == "release":
        summary["release_vm_requirements"] = {"require_all_vms": False, "require_vm_ids": []}
        drift_ci_result = next((item for item in results if item.get("check") == "drift_ci"), None)
        if isinstance(drift_ci_result, dict):
            summary["drift_ci"] = {"rc": int(drift_ci_result.get("rc", 0) or 0), "details": drift_ci_result.get("details", {})}

    if as_json:
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    else:
        print(f"[PROFILE] {profile_name} overall_rc={overall_rc}")
        if overall_rc > 0 and overall_rc_sources:
            print(f"[PROFILE] overall_rc_sources={','.join(overall_rc_sources)}")
        for item in results:
            print(f"- {item.get('check', '')}: rc={item.get('rc', 0)}")

    return overall_rc


def run_monitor(strict: bool) -> int:
    INVENTORY_LOG_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    dated_log = INVENTORY_LOG_DIR / f"preflight-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.log"

    inv = build_inventory()
    save_inventory(DEFAULT_OUT, inv)
    overrides = load_json_file(OVERRIDES_JSON, {})
    findings = collect_preflight_findings(inv, overrides)

    err_count = sum(1 for lvl, _ in findings if lvl == "error")
    warn_count = sum(1 for lvl, _ in findings if lvl == "warn")
    rc = 0
    if err_count > 0:
        rc = 2
    elif strict and warn_count > 0:
        rc = 3

    lines: List[str] = []
    lines.append(f"[MONITOR] timestamp={ts}")
    lines.append(f"[MONITOR] summary errors={err_count} warnings={warn_count} strict={strict} rc={rc}")
    if findings:
        for lvl, msg in findings:
            tag = "ERR" if lvl == "error" else "WARN"
            lines.append(f"- [{tag}] {msg}")
    else:
        lines.append("[MONITOR] OK - no drift detected")

    log_text = "\n".join(lines) + "\n"
    INVENTORY_LAST_LOG.write_text(log_text, encoding="utf-8")
    dated_log.write_text(log_text, encoding="utf-8")

    status_payload = {
        "timestamp": ts,
        "strict": strict,
        "errors": err_count,
        "warnings": warn_count,
        "rc": rc,
        "latest_log": str(INVENTORY_LAST_LOG),
        "snapshot_log": str(dated_log),
    }
    INVENTORY_STATUS_JSON.write_text(json.dumps(status_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(log_text.rstrip())
    print(f"[MONITOR] wrote status: {INVENTORY_STATUS_JSON}")
    return rc


def install_cron(interval_min: int, strict: bool) -> int:
    if interval_min < 1 or interval_min > 59:
        print("[ERR] interval must be between 1 and 59", file=sys.stderr)
        return 1

    INVENTORY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    strict_flag = " --strict" if strict else ""
    cron_line = (
        f"*/{interval_min} * * * * {BRAINHOME_INVENTORY_BIN} monitor-run{strict_flag} "
        f">> {INVENTORY_CRON_LOG} 2>&1 {CRON_MARKER}"
    )

    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if proc.returncode == 0:
        current = proc.stdout.splitlines()
    else:
        stderr_l = (proc.stderr or "").lower()
        if "no crontab" in stderr_l:
            current = []
        else:
            print(f"[ERR] failed to read crontab: {proc.stderr.strip()}", file=sys.stderr)
            return 1

    kept = [line for line in current if CRON_MARKER not in line]
    kept.append(cron_line)
    new_content = "\n".join(kept).strip() + "\n"

    apply_proc = subprocess.run(["crontab", "-"], input=new_content, text=True, capture_output=True)
    if apply_proc.returncode != 0:
        print(f"[ERR] failed to install crontab entry: {apply_proc.stderr.strip()}", file=sys.stderr)
        return 1

    print("[OK] inventory cron installed")
    print(f"[INFO] line: {cron_line}")
    return 0


def install_export_cron(hour: int, minute: int) -> int:
    if hour < 0 or hour > 23:
        print("[ERR] hour must be between 0 and 23", file=sys.stderr)
        return 1
    if minute < 0 or minute > 59:
        print("[ERR] minute must be between 0 and 59", file=sys.stderr)
        return 1

    INVENTORY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    export_log = INVENTORY_LOG_DIR / "export-cron.log"
    cron_line = (
        f"{minute} {hour} * * * {BRAINHOME_INVENTORY_BIN} export-md "
        f">> {export_log} 2>&1 {EXPORT_CRON_MARKER}"
    )

    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if proc.returncode == 0:
        current = proc.stdout.splitlines()
    else:
        stderr_l = (proc.stderr or "").lower()
        if "no crontab" in stderr_l:
            current = []
        else:
            print(f"[ERR] failed to read crontab: {proc.stderr.strip()}", file=sys.stderr)
            return 1

    kept = [line for line in current if EXPORT_CRON_MARKER not in line]
    kept.append(cron_line)
    new_content = "\n".join(kept).strip() + "\n"

    apply_proc = subprocess.run(["crontab", "-"], input=new_content, text=True, capture_output=True)
    if apply_proc.returncode != 0:
        print(f"[ERR] failed to install export crontab entry: {apply_proc.stderr.strip()}", file=sys.stderr)
        return 1

    print("[OK] inventory export cron installed")
    print(f"[INFO] line: {cron_line}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BrainHome infrastructure inventory manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_refresh = sub.add_parser("refresh", help="refresh central inventory JSON")
    p_refresh.add_argument("--output", default=str(DEFAULT_OUT), help="output JSON path")

    p_show = sub.add_parser("show", help="show inventory summary")
    p_show.add_argument("--input", default=str(DEFAULT_OUT), help="input JSON path")
    p_show.add_argument("--section", choices=["all", "nodes", "guests", "modules"], default="all")

    p_md = sub.add_parser("export-md", help="export inventory markdown")
    p_md.add_argument("--input", default=str(DEFAULT_OUT), help="input JSON path")
    p_md.add_argument("--output", default=str(TOOLS_ROOT / "config" / "infrastructure-inventory.md"), help="output markdown path")

    p_pf = sub.add_parser("preflight", help="detect inventory drift and missing metadata")
    p_pf.add_argument("--input", default=str(DEFAULT_OUT), help="input JSON path")
    p_pf.add_argument("--refresh", action="store_true", help="refresh inventory from live data before checks")
    p_pf.add_argument("--strict", action="store_true", help="treat warnings as non-zero exit")

    p_monitor = sub.add_parser("monitor-run", help="run refresh + preflight and persist status/log files")
    p_monitor.add_argument("--strict", action="store_true", help="return non-zero when warnings exist")

    p_cron = sub.add_parser("install-cron", help="install idempotent cron job for inventory monitor")
    p_cron.add_argument("--interval", type=int, default=15, help="minutes between checks (1-59)")
    p_cron.add_argument("--strict", action="store_true", help="cron monitor returns non-zero on warnings")

    p_cron_export = sub.add_parser("install-cron-export", help="install daily idempotent cron job for inventory markdown export")
    p_cron_export.add_argument("--hour", type=int, default=2, help="hour of day (0-23)")
    p_cron_export.add_argument("--minute", type=int, default=10, help="minute (0-59)")

    p_baseline = sub.add_parser("baseline-save", help="save current inventory as drift baseline snapshot")
    p_baseline.add_argument("--refresh", action="store_true", help="refresh inventory from live data before snapshot")

    p_drift = sub.add_parser("drift-diff", help="compare current inventory against saved baseline")
    p_drift.add_argument("--refresh", action="store_true", help="refresh inventory from live data before diff")
    p_drift.add_argument("--json", action="store_true", help="emit machine-readable JSON output")
    p_drift.add_argument("--fail-on-change", action="store_true", help="return rc=4 if effective changes exist")
    p_drift.add_argument("--fail-on-expired-rules", action="store_true", help="return rc=5 if expired allowlist rules exist")
    p_drift.add_argument("--fail-on-invalid-expiry", action="store_true", help="return rc=6 if allowlist expiry values are invalid")
    p_drift.add_argument("--ci", action="store_true", help="enable all fail-on-* governance checks")
    p_drift.add_argument("--allowlist", default=str(INVENTORY_DRIFT_ALLOWLIST_JSON), help="path to allowlist json")
    p_drift.add_argument("--no-allowlist", action="store_true", help="disable allowlist filtering")

    p_profile = sub.add_parser("preflight-profile", help="run preflight profile bundle")
    p_profile.add_argument("profile", choices=["daily", "release"], help="profile name")
    p_profile.add_argument("--json", action="store_true", help="emit machine-readable JSON output")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.cmd == "refresh":
        inv = build_inventory()
        out = Path(args.output)
        save_inventory(out, inv)
        print(f"[OK] inventory refreshed: {out}")
        print(f"[INFO] guests={len(inv.get('guests', []))} nodes={len(inv.get('nodes', []))} modules={len(inv.get('modules', []))}")
        if inv.get("warnings"):
            print(f"[WARN] warnings={len(inv['warnings'])}")
        return 0

    if args.cmd == "show":
        inv = load_json_file(Path(args.input), {})
        if not inv:
            print(f"[ERR] inventory not found or empty: {args.input}", file=sys.stderr)
            return 1
        print_summary(inv, args.section)
        return 0

    if args.cmd == "export-md":
        inv = load_json_file(Path(args.input), {})
        if not inv:
            print(f"[ERR] inventory not found or empty: {args.input}", file=sys.stderr)
            return 1
        out = Path(args.output)
        export_markdown(inv, out)
        print(f"[OK] markdown exported: {out}")
        return 0

    if args.cmd == "preflight":
        if args.refresh:
            inv = build_inventory()
            save_inventory(Path(args.input), inv)
        else:
            inv = load_json_file(Path(args.input), {})
            if not inv:
                print(f"[ERR] inventory not found or empty: {args.input}", file=sys.stderr)
                return 1
        overrides = load_json_file(OVERRIDES_JSON, {})
        return run_preflight(inv, overrides, strict=args.strict)

    if args.cmd == "monitor-run":
        return run_monitor(strict=args.strict)

    if args.cmd == "install-cron":
        return install_cron(interval_min=args.interval, strict=args.strict)

    if args.cmd == "install-cron-export":
        return install_export_cron(hour=args.hour, minute=args.minute)

    if args.cmd == "baseline-save":
        return run_baseline_save(refresh=args.refresh)

    if args.cmd == "drift-diff":
        fail_on_change = bool(args.fail_on_change)
        fail_on_expired = bool(args.fail_on_expired_rules)
        fail_on_invalid = bool(args.fail_on_invalid_expiry)
        if args.ci:
            fail_on_change = True
            fail_on_expired = True
            fail_on_invalid = True
        return run_drift_diff(
            refresh=args.refresh,
            as_json=bool(args.json),
            fail_on_change=fail_on_change,
            fail_on_expired_rules=fail_on_expired,
            fail_on_invalid_expiry=fail_on_invalid,
            allowlist_path=str(args.allowlist),
            no_allowlist=bool(args.no_allowlist),
        )

    if args.cmd == "preflight-profile":
        return run_preflight_profile(profile=args.profile, as_json=bool(args.json))

    print("[ERR] unknown command", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
