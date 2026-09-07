#!/usr/bin/env python3
"""
module-discovery.py — BrainHome Module Discovery System

Automatische Erkennung aller BrainHome Module via .git + .brainhome.yml Scanner.
Führt Discovery durch und generiert modules.json Registry.
"""

import os
import sys
import json
import subprocess
import tomllib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from paths import resolve_tools_root, resolve_workspace_root

# ─── Schema ───────────────────────────────────────────────────────────────────

MODULE_CONFIG_FILE = ".brainhome.yml"
_TOOLS_ROOT = resolve_tools_root()
_WORKSPACE_ROOT = resolve_workspace_root()
MODULES_REGISTRY = str(_TOOLS_ROOT / "config" / "modules.json")
CACHE_TTL_SECONDS = 300  # 5 min cache


@dataclass
class Module:
    """Discovered module."""
    name: str
    path: str
    module_type: str  # full-stack, backend, frontend, container, script
    category: str  # infrastructure, development, monitoring, security, automation, data
    languages: list = None
    container: dict = None  # {"type": "lxc", "id": "112", "host": "proxmox-dev", ...}
    dev_services: list = None  # [{"name": "backend-dev", "port": 8080, ...}]
    dependencies: list = None  # ["keycloak", "grafana"]
    is_git: bool = True
    git_remote: str = ""
    git_branch: str = ""
    discovered_at: str = ""

    def to_dict(self):
        return asdict(self)


# ─── Discovery ────────────────────────────────────────────────────────────────

def discover_git_repos(root_search_paths=None):
    """
    Find all .git directories up to 2 levels deep.
    Returns list of repo paths.
    """
    if root_search_paths is None:
        root_search_paths = [str(_WORKSPACE_ROOT)]

    repos = []
    for root_path in root_search_paths:
        if not os.path.isdir(root_path):
            continue

        try:
            result = subprocess.run(
                ["find", root_path, "-maxdepth", "3", "-name", ".git", "-type", "d"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                for git_dir in result.stdout.strip().split('\n'):
                    if git_dir:
                        repo_path = os.path.dirname(git_dir)
                        repos.append(repo_path)
        except subprocess.TimeoutExpired:
            print(f"[WARN] find timeout in {root_path}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] Error scanning {root_path}: {e}", file=sys.stderr)

    return repos


def discover_external_repos() -> list[str]:
    """Return existing external checkout paths declared in the root manifest."""
    manifest_path = _WORKSPACE_ROOT / "paths.toml"
    if not manifest_path.is_file():
        return []

    try:
        with manifest_path.open("rb") as manifest_file:
            manifest = tomllib.load(manifest_file)
    except tomllib.TOMLDecodeError as exc:
        print(f"[WARN] Invalid path manifest {manifest_path}: {exc}", file=sys.stderr)
        return []

    external_modules = manifest.get("external_modules", {})
    if not isinstance(external_modules, dict):
        return []

    repos = []
    for name, config in external_modules.items():
        if not isinstance(config, dict):
            continue
        relative_path = config.get("relative_path")
        if not isinstance(relative_path, str):
            continue
        repo_path = (_WORKSPACE_ROOT / relative_path).resolve()
        if (repo_path / ".git").exists() and (repo_path / MODULE_CONFIG_FILE).is_file():
            repos.append(str(repo_path))
        else:
            print(f"[WARN] External module '{name}' is unavailable: {repo_path}", file=sys.stderr)
    return repos


def discover_manifest_modules() -> list[str]:
    """Return internal module paths declared by the root path manifest."""
    manifest_path = _WORKSPACE_ROOT / "paths.toml"
    if not manifest_path.is_file():
        return []

    try:
        with manifest_path.open("rb") as manifest_file:
            manifest = tomllib.load(manifest_file)
    except tomllib.TOMLDecodeError as exc:
        print(f"[WARN] Invalid path manifest {manifest_path}: {exc}", file=sys.stderr)
        return []

    modules = manifest.get("modules", {})
    if not isinstance(modules, dict):
        return []

    repos = []
    for name, relative_path in modules.items():
        if not isinstance(relative_path, str):
            continue
        repo_path = (_WORKSPACE_ROOT / relative_path).resolve()
        if (repo_path / MODULE_CONFIG_FILE).is_file():
            repos.append(str(repo_path))
        else:
            print(f"[WARN] Manifest module '{name}' has no {MODULE_CONFIG_FILE}: {repo_path}", file=sys.stderr)
    return repos


def parse_brainhome_yml(file_path):
    """
    Parse .brainhome.yml into dict.
    Returns None if not parseable.
    """
    # We use a simple YAML parser + fallback pattern matching
    # (tomllib is Python 3.11+, ruamel.yaml adds dependency)
    try:
        import yaml
        with open(file_path) as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: key=value + indentation parsing
        print(f"[WARN] PyYAML not available; using pattern matching for {file_path}", file=sys.stderr)
        return parse_brainhome_yml_simple(file_path)


def parse_brainhome_yml_simple(file_path):
    """
    Minimal YAML-like parser for .brainhome.yml (no full YAML support).
    Supports basic key: value and nested structures with indentation.
    """
    result = {}
    current_section = result
    stack = [(result, 0)]  # (dict, indent_level)

    try:
        with open(file_path) as f:
            for line in f:
                # Skip comments and empty lines
                stripped = line.rstrip()
                if not stripped or stripped.startswith('#'):
                    continue

                # Measure indentation
                indent = len(line) - len(line.lstrip())

                # Pop stack until we find the right level
                while len(stack) > 1 and indent <= stack[-1][1]:
                    stack.pop()

                current_dict, _ = stack[-1]

                # Parse key: value
                if ':' in stripped:
                    key, val = stripped.split(':', 1)
                    key = key.strip()
                    val = val.strip()

                    if val:
                        # Simple value
                        try:
                            if val.lower() in ('true', 'false'):
                                val = val.lower() == 'true'
                            else:
                                val = int(val)
                        except (ValueError, AttributeError):
                            pass  # Keep as string
                        current_dict[key] = val
                    else:
                        # Nested dict incoming
                        new_dict = {}
                        current_dict[key] = new_dict
                        stack.append((new_dict, indent))

        return result
    except Exception as e:
        print(f"[WARN] Error parsing {file_path}: {e}", file=sys.stderr)
        return {}


def get_git_info(repo_path):
    """
    Get git remote + branch from repo.
    """
    remote = ""
    branch = ""

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote = result.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except Exception:
        pass

    return remote, branch


def discover_all_modules(root_search_paths=None):
    """
    Main discovery: find all repos, check for .brainhome.yml, build Module objects.
    """
    repos = discover_git_repos(root_search_paths)
    if root_search_paths is None:
        repos.extend(discover_manifest_modules())
        repos.extend(discover_external_repos())
    repos = list(dict.fromkeys(repos))
    modules = []

    for repo_path in repos:
        config_file = os.path.join(repo_path, MODULE_CONFIG_FILE)

        if not os.path.isfile(config_file):
            # No .brainhome.yml — skip
            continue

        try:
            config = parse_brainhome_yml(config_file)
            if not config:
                print(f"[WARN] Empty or invalid {config_file}", file=sys.stderr)
                continue

            name = config.get("name", os.path.basename(repo_path))
            module_type = config.get("module_type", "unknown")
            category = config.get("category", "misc")
            languages = config.get("languages", [])
            container = config.get("container", {})
            dev_services = config.get("dev_services", [])
            dependencies = config.get("dependencies", [])

            remote, branch = get_git_info(repo_path)

            module = Module(
                name=name,
                path=repo_path,
                module_type=module_type,
                category=category,
                languages=languages,
                container=container,
                dev_services=dev_services,
                dependencies=dependencies,
                is_git=(Path(repo_path) / ".git").exists(),
                git_remote=remote,
                git_branch=branch,
                discovered_at=datetime.now().isoformat(),
            )
            modules.append(module)
        except Exception as e:
            print(f"[WARN] Error loading {repo_path}: {e}", file=sys.stderr)
            continue

    return modules


# ─── Registry Management ──────────────────────────────────────────────────────

def load_registry():
    """Load modules.json if it exists and not stale."""
    if not os.path.isfile(MODULES_REGISTRY):
        return None

    try:
        stat = os.stat(MODULES_REGISTRY)
        age = datetime.now().timestamp() - stat.st_mtime

        if age > CACHE_TTL_SECONDS:
            return None  # Stale

        with open(MODULES_REGISTRY) as f:
            return json.load(f)
    except Exception:
        return None


def save_registry(modules):
    """Save modules list to modules.json."""
    registry = {
        "timestamp": datetime.now().isoformat(),
        "modules": {m.name: m.to_dict() for m in modules},
        "count": len(modules),
    }

    try:
        os.makedirs(os.path.dirname(MODULES_REGISTRY), exist_ok=True)
        with open(MODULES_REGISTRY, 'w') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        print(f"[OK] Registry saved: {MODULES_REGISTRY} ({len(modules)} modules)", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[ERR] Failed to save registry: {e}", file=sys.stderr)
        return False


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: module-discovery.py <command> [options]")
        print("Commands:")
        print("  discover [--no-cache]  Run discovery, output JSON")
        print("  list                   List modules (short)")
        print("  show <module_name>     Show module details")
        print("  validate               Check registry integrity")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "discover":
        use_cache = "--no-cache" not in sys.argv

        if use_cache:
            cached = load_registry()
            if cached:
                print(json.dumps(cached, indent=2, ensure_ascii=False))
                sys.exit(0)

        modules = discover_all_modules()
        save_registry(modules)

        output = {
            "timestamp": datetime.now().isoformat(),
            "modules": {m.name: m.to_dict() for m in modules},
            "count": len(modules),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    elif cmd == "list":
        registry = load_registry()
        if not registry:
            print("[INFO] Registry not cached; run 'discover' first", file=sys.stderr)
            registry = {"modules": {}}

        for name in sorted(registry.get("modules", {}).keys()):
            print(f"  • {name}")
        print(f"\nTotal: {len(registry.get('modules', {}))} modules")

    elif cmd == "show" and len(sys.argv) > 2:
        module_name = sys.argv[2]
        registry = load_registry()
        if not registry or module_name not in registry.get("modules", {}):
            print(f"[ERR] Module not found: {module_name}", file=sys.stderr)
            sys.exit(1)

        module = registry["modules"][module_name]
        print(json.dumps(module, indent=2, ensure_ascii=False))

    elif cmd == "validate":
        registry = load_registry()
        if not registry:
            print("[WARN] No registry to validate")
            sys.exit(1)

        modules = registry.get("modules", {})
        errors = 0

        for name, cfg in modules.items():
            if not cfg.get("path"):
                print(f"[ERR] {name}: missing path")
                errors += 1
            if not os.path.isdir(cfg.get("path", "")):
                print(f"[WARN] {name}: path does not exist: {cfg.get('path')}")
                errors += 1

        if errors == 0:
            print(f"[OK] Registry valid ({len(modules)} modules)")
        else:
            print(f"[ERR] Found {errors} issues")
            sys.exit(1)

    else:
        print(f"[ERR] Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
