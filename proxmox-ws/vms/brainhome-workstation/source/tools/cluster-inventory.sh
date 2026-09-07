#!/bin/bash
# =============================================================================
# cluster-inventory.sh — BrainHome Cluster Inventory
# Gibt alle VMs/CTs mit Node, IP, Tags und Status aus.
#
# Requires: pvesh (Proxmox), python3
# Run from: any Proxmox node or proxmox-master
#
# Usage:
#   cluster-inventory.sh              # Tabelle (alle)
#   cluster-inventory.sh --json       # JSON output
#   cluster-inventory.sh --tag <tag>  # Filter by tag
#   cluster-inventory.sh --missing    # Nur Hosts ohne Tags
# =============================================================================

set -euo pipefail

MODE="table"
FILTER_TAG=""
FILTER_MISSING=false

for arg in "$@"; do
  case "$arg" in
    --json)    MODE="json" ;;
    --missing) FILTER_MISSING=true ;;
    --tag)     shift; FILTER_TAG="$1" ;;
    --tag=*)   FILTER_TAG="${arg#--tag=}" ;;
  esac
done

# Collect cluster resources via pvesh
RAW_JSON=$(pvesh get /cluster/resources --output-format json 2>/dev/null)

python3 - <<PY
import json, os, subprocess, sys

raw = """$RAW_JSON"""
try:
    items = json.loads(raw)
except Exception as e:
    print(f"ERROR: cannot parse pvesh output: {e}", file=sys.stderr)
    sys.exit(1)

mode = "${MODE}"
filter_tag = "${FILTER_TAG}"
filter_missing = "${FILTER_MISSING}" == "true"

nodes = {}
for item in items:
    if item.get("type") == "node":
        nodes[item.get("node", "")] = item.get("ip", "")

vms = [x for x in items if x.get("type") in ("lxc", "qemu")]
vms.sort(key=lambda x: x.get("vmid", 0))

def get_ip(item):
    # Try to resolve IP from ipconfig0 via pvesh (synchronous, best-effort)
    vmid = item.get("vmid")
    vtype = item.get("type")
    node = item.get("node", "")
    try:
        if vtype == "lxc":
            out = subprocess.check_output(
                ["ssh", node, f"LC_ALL=C pct exec {vmid} -- ip -4 addr show eth0 2>/dev/null | grep 'inet '"],
                timeout=3, stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                if "inet " in line:
                    return line.strip().split()[1].split("/")[0]
        elif vtype == "qemu":
            out = subprocess.check_output(
                ["ssh", node, f"LC_ALL=C qm guest cmd {vmid} network-get-interfaces 2>/dev/null"],
                timeout=3, stderr=subprocess.DEVNULL
            ).decode()
            data = json.loads(out)
            for iface in data:
                for addr in iface.get("ip-addresses", []):
                    ip = addr.get("ip-address", "")
                    if addr.get("ip-address-type") == "ipv4" and not ip.startswith("127."):
                        return ip
    except Exception:
        pass
    return ""

results = []
for item in vms:
    vmid = item.get("vmid", 0)
    name = item.get("name", "?")
    ntype = "CT" if item.get("type") == "lxc" else "VM"
    node = item.get("node", "?")
    status = item.get("status", "?")
    tags_raw = item.get("tags", "") or ""
    tags = sorted([t.strip() for t in tags_raw.split(";") if t.strip()])

    if filter_tag and filter_tag not in tags:
        continue
    if filter_missing and tags:
        continue

    results.append({
        "id": f"{ntype}{vmid}",
        "vmid": vmid,
        "type": ntype,
        "name": name,
        "node": node,
        "status": status,
        "tags": tags,
    })

if mode == "json":
    print(json.dumps(results, indent=2))
    sys.exit(0)

# Table mode
BOLD = "\033[1m"
NC = "\033[0m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
DIM = "\033[2m"
RED = "\033[0;31m"

header = f"{BOLD}{'ID':<8} {'NAME':<26} {'NODE':<22} {'STATUS':<10} TAGS{NC}"
print()
print(header)
print("─" * 90)
for r in results:
    status_col = f"{GREEN}{r['status']:<10}{NC}" if r["status"] == "running" else f"{DIM}{r['status']:<10}{NC}"
    tags_col = ";".join(r["tags"]) if r["tags"] else f"{RED}(none){NC}"
    print(f"{r['id']:<8} {r['name']:<26} {r['node']:<22} {status_col} {tags_col}")
print()
print(f"{DIM}{len(results)} entries{NC}")
print()
PY
