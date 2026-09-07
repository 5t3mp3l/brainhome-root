"""Shared dynamic path resolution for BrainHome Python tooling."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_tools_root() -> Path:
    """Return TOOLS_ROOT or infer it from this library's location."""
    configured_root = os.environ.get("TOOLS_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def resolve_workspace_root() -> Path:
    """Return BRAINHOME_ROOT or the parent of the resolved tools directory."""
    configured_root = os.environ.get("BRAINHOME_ROOT")
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return resolve_tools_root().parent