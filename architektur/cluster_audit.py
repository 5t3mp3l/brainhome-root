#!/usr/bin/env python3
"""Join path manifests to physical assets and optionally audit Proxmox read-only."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tomllib


def load_toml(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def within(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes workspace: {relative}")
    return candidate


def declared_inventory(root: Path) -> dict:
    root_manifest = load_toml(root / "paths.toml")
    modules = root_manifest["modules"]
    external_roots = {
        (root / entry["relative_path"]).resolve()
        for entry in root_manifest.get("external_modules", {}).values()
    }
    physical = load_toml(root / "architektur/physical.toml")
    nodes = []
    guests = []
    seen_nodes = set()
    seen_guests = set()
    for asset_id, asset in sorted(physical["assets"].items()):
        node_dir = within(root, modules[asset["node_module"]])
        manifest = load_toml(node_dir / "paths.toml")
        node = manifest["proxmox"]["node"]
        if node in seen_nodes:
            raise ValueError(f"Duplicate physical node: {node}")
        seen_nodes.add(node)
        nodes.append({"asset_id": asset_id, **asset, **manifest["proxmox"]})
        for folder_key, guest_type, id_key in (
            ("vms", "qemu", "vm_id"),
            ("containers", "lxc", "container_id"),
        ):
            folder = within(root, str(node_dir.relative_to(root) / manifest["layout"][folder_key]))
            for guest_path in sorted(folder.glob("*/paths.toml")):
                guest_manifest = load_toml(guest_path)
                placement = guest_manifest["placement"]
                guest_id = placement[id_key]
                if guest_id in seen_guests:
                    raise ValueError(f"Duplicate guest ID: {guest_id}")
                if placement["node"] != node:
                    raise ValueError(f"Folder/placement mismatch: {guest_path}")
                seen_guests.add(guest_id)
                source = guest_manifest.get("module", {}).get("source_module")
                source_path = (guest_path.parent / source).resolve() if source else None
                if source_path is not None and not source_path.is_relative_to(root.resolve()) and source_path not in external_roots:
                    raise ValueError(f"Undeclared external source: {source_path}")
                if source_path is not None and not source_path.is_dir():
                    raise ValueError(f"Missing source: {source_path}")
                guests.append({
                    "vmid": guest_id,
                    "type": guest_type,
                    "asset_id": asset_id,
                    **placement,
                    "manifest": str(guest_path.relative_to(root)),
                    "source": str(guest_path.parent.relative_to(root) / source) if source else None,
                })
    return {"nodes": nodes, "guests": sorted(guests, key=lambda guest: guest["vmid"])}


def query(host: str, endpoint: str) -> object:
    if not host or host.startswith("-") or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-@" for character in host):
        raise ValueError("Invalid SSH host")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o",
         "StrictHostKeyChecking=yes", host,
         f"pvesh get {endpoint} --output-format json"],
        check=True, capture_output=True, text=True, timeout=45,
    )
    return json.loads(result.stdout)


def observe(host: str) -> dict:
    status = query(host, "/cluster/status")
    resources = query(host, "/cluster/resources")
    nodes = {}
    for item in status:
        if item.get("type") != "node":
            continue
        node_name = item["name"]
        if not all(character.isalnum() or character == "-" for character in node_name):
            raise ValueError("Invalid node name from API")
        details = query(host, f"/nodes/{node_name}/status")
        nodes[node_name] = {
            "ip": item["ip"], "online": item["online"],
            "cpu": details["cpuinfo"]["model"],
            "logical_cpus": details["cpuinfo"]["cpus"],
            "memory": details["memory"], "swap": details["swap"],
            "pveversion": details["pveversion"],
        }
    allowed = ("id", "vmid", "type", "name", "node", "status", "maxmem", "mem", "maxcpu", "storage", "maxdisk", "disk", "shared", "content", "hastate")
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "transport": f"ssh:{host}; pvesh GET only",
        "cluster": status,
        "nodes": nodes,
        "resources": [{key: item[key] for key in allowed if key in item} for item in resources],
        "ha": query(host, "/cluster/ha/resources"),
        "replication": query(host, "/cluster/replication"),
        "backup_jobs": query(host, "/cluster/backup"),
    }


def compare(declared: dict, observed: dict) -> dict:
    expected = {guest["vmid"]: guest for guest in declared["guests"]}
    actual = {item["vmid"]: item for item in observed["resources"] if item["type"] in ("qemu", "lxc")}
    drift = []
    for guest_id in sorted(expected.keys() | actual.keys()):
        planned = expected.get(guest_id)
        live = actual.get(guest_id)
        if planned is None or live is None:
            drift.append({"vmid": guest_id, "issue": "undeclared" if planned is None else "missing_live"})
        elif (planned["node"], planned["type"]) != (live["node"], live["type"]):
            drift.append({"vmid": guest_id, "issue": "placement", "declared": planned["node"], "observed": live["node"]})
    expected_nodes = {node["node"]: node for node in declared["nodes"]}
    for node_name in sorted(expected_nodes.keys() | observed["nodes"].keys()):
        planned = expected_nodes.get(node_name)
        live = observed["nodes"].get(node_name)
        if planned is None or live is None:
            drift.append({"node": node_name, "issue": "undeclared" if planned is None else "missing_live"})
        elif planned["management_ip"] != live["ip"]:
            drift.append({"node": node_name, "issue": "management_ip"})
    covered = set()
    for job in observed["backup_jobs"]:
        if not job.get("enabled", 1):
            continue
        candidates = {int(value) for value in str(job.get("vmid", "")).split(",") if value.strip()}
        excluded = {int(value) for value in str(job.get("exclude", "")).split(",") if value.strip()}
        for guest_id, guest in actual.items():
            if job.get("node") and job["node"] != guest["node"]:
                continue
            if guest_id not in excluded and (job.get("all") or guest_id in candidates):
                covered.add(guest_id)
    return {"drift": drift, "not_in_enabled_backup_jobs": sorted(actual.keys() - covered)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", metavar="SSH_HOST")
    parser.add_argument("--observed", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.live and args.observed:
        parser.error("Use either --live or --observed")
    root = Path(__file__).resolve().parent.parent
    try:
        declared = declared_inventory(root)
        report = {"schema": 1, "declared": declared}
        if args.live or args.observed:
            observed = observe(args.live) if args.live else json.loads(args.observed.read_text())
            observed = observed.get("observed", observed)
            report.update(observed=observed, checks=compare(declared, observed))
        rendered = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 1 if report.get("checks", {}).get("drift") else 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(2, f"Audit failed; no report written: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())