#!/usr/bin/env python3
"""Shim: use `alb` after `uv sync` (see pyproject.toml)."""

from alb.cli import app

if __name__ == "__main__":
    app()
