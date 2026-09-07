#!/usr/bin/env bash
# =============================================================================
# log-collector.sh — Unified Log Collection from All Container Types
#
# Collects and centralizes logs from:
# - LXC containers (pct + journalctl)
# - Docker containers (docker compose logs)
# - SSH remotes (ssh + journalctl)
# - Local services (journalctl)
#
# Stores in: <workspace>/tools/logs/modules/<module>/*.log
# Usage:
#   log-collector.sh <module|all> [lines]
# =============================================================================

set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_SCRIPT_DIR}/paths.sh"
TOOLS_ROOT="${TOOLS_ROOT:-$(bh_path tools)}"
MODULES_JSON="$TOOLS_ROOT/config/modules.json"
LOGS_DIR="$TOOLS_ROOT/logs/modules"
LOCK_FILE="$LOGS_DIR/.lock"
DEFAULT_LINES=120
MAX_SERVICES=25
CMD_TIMEOUT=30

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error()   { echo -e "${RED}[ERR]${NC}  $*"; }

acquire_lock() {
  mkdir -p "$LOGS_DIR"
  if mkdir "$LOCK_FILE" 2>/dev/null; then
    trap 'rmdir "$LOCK_FILE" 2>/dev/null || true' EXIT
    return 0
  fi
  log_warn "Collector lock already active; continuing without exclusive lock"
}

safe_write() {
  local out_file="$1"
  shift
  if timeout "${CMD_TIMEOUT}s" "$@" > "$out_file" 2>/dev/null; then
    return 0
  fi
  return 1
}

collect_lxc_logs() {
  local module="$1"
  local lines="$2"
  local ct_id
  ct_id=$(jq -r ".modules.\"$module\".container.id // \"\"" "$MODULES_JSON")
  local module_dir="$LOGS_DIR/$module"

  if [ -z "$ct_id" ]; then
    log_warn "$module: LXC ID not configured"
    return 1
  fi

  mkdir -p "$module_dir"

  # Syslog in one exec call
  safe_write "$module_dir/_syslog.log" pct exec "$ct_id" -- \
    bash -c "tail -n $lines /var/log/syslog 2>/dev/null || true" || true

  # Collect all active service journals in a single exec call to avoid the
  # ~3.5s per-invocation overhead of pct exec (30 services × 3.5s = ~105s).
  # The embedded bash loop runs entirely inside the container and streams
  # all service logs into one combined file on the local host.
  # The combined journal collection can take several seconds inside a busy
  # container; use a longer timeout than individual calls.
  local lxc_timeout=$(( CMD_TIMEOUT * 2 ))
  local combined_log="$module_dir/_all_services.log"
  if timeout "${lxc_timeout}s" pct exec "$ct_id" -- bash -c "
    services=\$(systemctl list-units --type=service --no-pager --no-legend 2>/dev/null \
      | awk '{print \$1}' | head -n $MAX_SERVICES)
    for svc in \$services; do
      echo '### SERVICE: '\"\$svc\"
      journalctl -u \"\$svc\" -n $lines --no-pager 2>/dev/null
      echo
    done
  " > "$combined_log" 2>/dev/null; then
    local count
    count=$(grep -c '^### SERVICE:' "$combined_log" 2>/dev/null || echo 0)
    log_success "$module: collected $count service logs in one pass (LXC $ct_id)"
  else
    log_warn "$module: LXC log collection timed out or failed (LXC $ct_id)"
    return 1
  fi

  return 0
}

collect_docker_logs() {
  local module="$1"
  local lines="$2"
  local module_path
  module_path=$(jq -r ".modules.\"$module\".path // \"\"" "$MODULES_JSON")
  local module_dir="$LOGS_DIR/$module"
  local collected=0

  if [ ! -d "$module_path" ]; then
    log_warn "$module: module path missing ($module_path)"
    return 1
  fi

  mkdir -p "$module_dir"

  local services
  services=$(cd "$module_path" && timeout "${CMD_TIMEOUT}s" docker compose ps --services 2>/dev/null | head -n "$MAX_SERVICES" || true)

  if [ -z "$services" ]; then
    log_warn "$module: no docker services detected"
    return 1
  fi

  while IFS= read -r service; do
    [ -z "$service" ] && continue
    if (cd "$module_path" && timeout "${CMD_TIMEOUT}s" docker compose logs --no-color --tail "$lines" "$service" > "$module_dir/${service}.log" 2>/dev/null); then
      collected=$((collected + 1))
    fi
  done <<< "$services"

  log_success "$module: collected $collected service logs (Docker)"
  return 0
}

collect_ssh_logs() {
  local module="$1"
  local lines="$2"
  local host
  host=$(jq -r ".modules.\"$module\".container.hosts[0] // \"\"" "$MODULES_JSON")
  local module_dir="$LOGS_DIR/$module"
  local collected=0

  if [ -z "$host" ]; then
    log_warn "$module: SSH host not configured"
    return 1
  fi

  mkdir -p "$module_dir"
  timeout "${CMD_TIMEOUT}s" ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$host" \
    "tail -n $lines /var/log/syslog" > "$module_dir/_syslog.log" 2>/dev/null || true

  local services
  services=$(timeout "${CMD_TIMEOUT}s" ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$host" \
    "systemctl list-units --type=service --no-pager --no-legend 2>/dev/null | awk '{print \\\$1}' | head -n $MAX_SERVICES" 2>/dev/null || true)

  while IFS= read -r service; do
    [ -z "$service" ] && continue
    if timeout "${CMD_TIMEOUT}s" ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$host" \
      "journalctl -u $service -n $lines --no-pager" > "$module_dir/${service}.log" 2>/dev/null; then
      collected=$((collected + 1))
    fi
  done <<< "$services"

  log_success "$module: collected $collected service logs (SSH $host)"
  return 0
}

collect_local_logs() {
  local module="$1"
  local lines="$2"
  local module_dir="$LOGS_DIR/$module"
  local collected=0

  mkdir -p "$module_dir"
  tail -n "$lines" /var/log/syslog > "$module_dir/_syslog.log" 2>/dev/null || true

  local services
  services=$(systemctl list-units --type=service --no-pager --no-legend 2>/dev/null \
    | awk '{print $1}' | head -n "$MAX_SERVICES" || true)

  while IFS= read -r service; do
    [ -z "$service" ] && continue
    if journalctl -u "$service" -n "$lines" --no-pager > "$module_dir/${service}.log" 2>/dev/null; then
      collected=$((collected + 1))
    fi
  done <<< "$services"

  log_success "$module: collected $collected service logs (local)"
  return 0
}

collect_one() {
  local module="$1"
  local lines="$2"

  if ! jq -e ".modules.\"$module\"" "$MODULES_JSON" >/dev/null 2>&1; then
    log_warn "$module: not found in registry"
    return 1
  fi

  local container_type
  container_type=$(jq -r ".modules.\"$module\".container.type // \"local\"" "$MODULES_JSON")

  case "$container_type" in
    lxc)    collect_lxc_logs "$module" "$lines" ;;
    docker) collect_docker_logs "$module" "$lines" ;;
    ssh)    collect_ssh_logs "$module" "$lines" ;;
    local)  collect_local_logs "$module" "$lines" ;;
    *)
      log_warn "$module: unknown container type '$container_type'"
      return 1
      ;;
  esac
}

main() {
  local target="${1:-all}"
  local lines="${2:-$DEFAULT_LINES}"

  if ! [[ "$lines" =~ ^[0-9]+$ ]]; then
    log_error "Lines must be numeric (got: $lines)"
    return 1
  fi

  if [ ! -f "$MODULES_JSON" ]; then
    log_error "Modules registry missing: $MODULES_JSON"
    return 1
  fi

  acquire_lock

  local ok=0
  local fail=0

  if [ "$target" = "all" ]; then
    while IFS= read -r module; do
      [ -z "$module" ] && continue
      log_info "Collecting logs for $module"
      if collect_one "$module" "$lines"; then
        ok=$((ok + 1))
      else
        fail=$((fail + 1))
      fi
    done < <(jq -r '.modules | keys[]' "$MODULES_JSON")
  else
    log_info "Collecting logs for $target"
    if collect_one "$target" "$lines"; then
      ok=1
    else
      fail=1
    fi
  fi

  log_info "Summary: success=$ok failed=$fail"
  [ "$fail" -eq 0 ]
}

main "$@"
