#!/usr/bin/env python3
"""
module-scaffold.py — Create .brainhome.yml for a module path.

Goal:
- Fast onboarding for new/existing repos.
- Minimal dependencies (stdlib only).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from paths import resolve_tools_root

TOOLS_ROOT = resolve_tools_root()
TEMPLATE_PATH = TOOLS_ROOT / "config" / ".brainhome.yml.template"
TEMPLATE_DIR = TOOLS_ROOT / "config" / "templates"

ALLOWED_TYPES = {"full-stack", "backend", "frontend", "container", "script"}
ALLOWED_CATEGORIES = {
    "infrastructure",
    "development",
    "monitoring",
    "security",
    "automation",
    "data",
}
ALLOWED_CONTAINER_TYPES = {"lxc", "ssh", "local", "docker", "kubernetes"}
ALLOWED_TEMPLATES = {"auto", "full-stack", "backend", "container", "script", "base"}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate .brainhome.yml for a module directory.",
    )
    parser.add_argument("--path", required=True, help="Module root directory path")
    parser.add_argument("--name", help="Module name (defaults to directory name)")
    parser.add_argument("--module-type", default="script", help="Module type")
    parser.add_argument("--category", default="infrastructure", help="Module category")
    parser.add_argument("--container-type", default="local", help="Container/runtime type")
    parser.add_argument(
        "--template",
        default="auto",
        help="Scaffold template: auto, full-stack, backend, container, script, base",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing .brainhome.yml")
    parser.add_argument("--discover", action="store_true", help="Run discovery after generating config")
    return parser.parse_args()


def fail(msg: str, code: int = 1) -> None:
    print(f"[ERR] {msg}", file=sys.stderr)
    raise SystemExit(code)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stderr)


def resolve_template_path(template_name: str, module_type: str) -> Path:
    if template_name == "base":
        return TEMPLATE_PATH

    if template_name == "auto":
        candidate = TEMPLATE_DIR / f"{module_type}.yml"
        if candidate.is_file():
            return candidate
        return TEMPLATE_PATH

    candidate = TEMPLATE_DIR / f"{template_name}.yml"
    if not candidate.is_file():
        fail(f"Template not found: {candidate}")
    return candidate


def load_template(template_path: Path) -> str:
    if not template_path.is_file():
        fail(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render(template: str, name: str, module_type: str, category: str, container_type: str) -> str:
    rendered = template

    rendered = rendered.replace("__MODULE_NAME__", name)
    rendered = rendered.replace("__MODULE_TYPE__", module_type)
    rendered = rendered.replace("__CATEGORY__", category)
    rendered = rendered.replace("__CONTAINER_TYPE__", container_type)

    rendered = rendered.replace('name: "example-module"', f'name: "{name}"', 1)
    rendered = rendered.replace('module_type: "full-stack"', f'module_type: "{module_type}"', 1)
    rendered = rendered.replace('category: "infrastructure"', f'category: "{category}"', 1)
    rendered = rendered.replace('type: "lxc"', f'type: "{container_type}"', 1)

    # Keep the file minimal for local/script/container by removing extra blank lines.
    while "\n\n\n" in rendered:
        rendered = rendered.replace("\n\n\n", "\n\n")
    return rendered


def run_discover() -> int:
    cmd = ["python3", str(TOOLS_ROOT / "lib" / "module-discovery.py"), "discover", "--no-cache"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        warn("Discovery failed after scaffold. You can run it manually:")
        warn(f"  {TOOLS_ROOT / 'bin' / 'brainhome-discover'} discover --no-cache")
        if result.stderr:
            warn(result.stderr.strip())
        return result.returncode

    info("Discovery refreshed.")
    return 0


def main() -> int:
    args = parse_args()

    target_dir = Path(args.path).expanduser().resolve()
    if not target_dir.is_dir():
        fail(f"Path is not a directory: {target_dir}")

    if not args.name:
        name = target_dir.name
    else:
        name = args.name

    if args.module_type not in ALLOWED_TYPES:
        fail(f"Invalid --module-type '{args.module_type}'. Allowed: {', '.join(sorted(ALLOWED_TYPES))}")

    if args.category not in ALLOWED_CATEGORIES:
        fail(f"Invalid --category '{args.category}'. Allowed: {', '.join(sorted(ALLOWED_CATEGORIES))}")

    if args.container_type not in ALLOWED_CONTAINER_TYPES:
        fail(
            f"Invalid --container-type '{args.container_type}'. Allowed: {', '.join(sorted(ALLOWED_CONTAINER_TYPES))}"
        )

    if args.template not in ALLOWED_TEMPLATES:
        fail(f"Invalid --template '{args.template}'. Allowed: {', '.join(sorted(ALLOWED_TEMPLATES))}")

    target_file = target_dir / ".brainhome.yml"
    if target_file.exists() and not args.force:
        fail(f"File exists: {target_file} (use --force to overwrite)")

    if not (target_dir / ".git").exists():
        warn(f"No .git directory found in {target_dir}. Discovery may skip this path.")

    template_path = resolve_template_path(args.template, args.module_type)
    template = load_template(template_path)
    rendered = render(template, name=name, module_type=args.module_type, category=args.category, container_type=args.container_type)
    target_file.write_text(rendered, encoding="utf-8")

    print(f"[OK] Created {target_file}")
    print(f"  name={name}")
    print(f"  module_type={args.module_type}")
    print(f"  category={args.category}")
    print(f"  container_type={args.container_type}")
    print(f"  template={template_path}")

    if args.discover:
        return run_discover()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
