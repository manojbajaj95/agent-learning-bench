#!/usr/bin/env python3
"""Backfill Harbor viewer trajectories from a finished Pi job, trial, or pi.txt."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from affinity_agent.convert import export_trajectory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--pi-version", default="unknown")
    args = parser.parse_args()
    if args.path.is_file() and args.path.name == "pi.txt":
        sources = [args.path]
    elif args.path.is_dir():
        sources = sorted(args.path.rglob("agent/pi.txt"))
    else:
        parser.error("provide a job/trial directory or a pi.txt event log")
    if not sources:
        parser.error("no agent/pi.txt logs found")
    failed = 0
    for source in sources:
        existed = source.with_name("trajectory.json").exists()
        try:
            target = export_trajectory(source, version=args.pi_version)
            print(f"{'Kept existing' if existed else 'Exported'}: {target}")
        except (ValueError, OSError, KeyError, TypeError) as exc:
            failed += 1
            print(f"Failed: {source}: {exc}", file=sys.stderr)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
