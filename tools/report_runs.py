#!/usr/bin/env python3
"""Shim: prefer `alb report <run>`."""

from __future__ import annotations

import argparse
from pathlib import Path

from alb.bench import ROOT, resolve_job_dir
from alb.report import render_markdown, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Task run: job name or job directory")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    given = Path(args.run)
    job_dir = given if given.is_dir() else resolve_job_dir(args.jobs_dir, args.run)
    rows, written = write_report(job_dir, args.out_dir)
    print(render_markdown(rows))
    for path in written.values():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
