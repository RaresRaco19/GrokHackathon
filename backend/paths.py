"""Resolve kit and state paths. Colleague may move this package; kit stays at repo root."""
from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("CLAIMDESK_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def var_dir() -> Path:
    env = os.environ.get("CLAIMDESK_VAR")
    if env:
        return Path(env)
    path = repo_root() / "var"
    path.mkdir(parents=True, exist_ok=True)
    return path
