#!/bin/bash
# Shared workspace path resolver. Source from scripts instead of hardcoding paths.

if [[ -n "${BRAINHOME_PATHS_LOADED:-}" ]]; then
    return 0
fi
readonly BRAINHOME_PATHS_LOADED=1

_BH_PATHS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_BH_DISCOVERED_ROOT="$(cd "${_BH_PATHS_DIR}/../.." && pwd)"
readonly BRAINHOME_ROOT="${BRAINHOME_ROOT:-${_BH_DISCOVERED_ROOT}}"

bh_path() {
    local relative_path="${1:?relative path is required}"
    local normalized_path="${relative_path#./}"
    local leading_component="${normalized_path%%/*}"
    local remainder="${normalized_path#*/}"
    local module_path

    if [[ "$normalized_path" == */* ]]; then
        module_path="$(python3 - "$BRAINHOME_ROOT" "$leading_component" <<'PY'
import sys
import tomllib
from pathlib import Path

root = Path(sys.argv[1])
module_name = sys.argv[2]
with (root / "paths.toml").open("rb") as manifest_file:
    modules = tomllib.load(manifest_file).get("modules", {})

print(modules.get(module_name, ""))
PY
)" || return 1
        if [[ -n "$module_path" ]]; then
            printf '%s/%s\n' "$BRAINHOME_ROOT/$module_path" "$remainder"
            return 0
        fi
    fi

    printf '%s/%s\n' "$BRAINHOME_ROOT" "$normalized_path"
}

bh_module_dir() {
    local module_name="${1:?module name is required}"
    local module_path
    module_path="$(python3 - "$BRAINHOME_ROOT" "$module_name" <<'PY'
import sys
import tomllib
from pathlib import Path

root = Path(sys.argv[1])
module_name = sys.argv[2]
with (root / "paths.toml").open("rb") as manifest_file:
    modules = tomllib.load(manifest_file).get("modules", {})

print(modules.get(module_name, module_name))
PY
)" || return 1
    bh_path "$module_path"
}

bh_require_path() {
    local required_path="${1:?path is required}"
    [[ -e "$required_path" ]] || {
        echo "Required path does not exist: $required_path" >&2
        return 1
    }
}