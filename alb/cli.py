"""Typer CLI for Agent Learning Bench.

After `uv sync` and with the venv active:

    alb run tally --system icl
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from alb.bench import (
    ROOT,
    SYSTEMS_TOML,
    extra_args,
    prepare_task,
    print_systems,
    run_task,
    task_names,
    upload_job,
)
from alb.report import render_markdown, write_report

app = typer.Typer(
    help="Prepare, smoke, run, upload, and report Agent Learning Bench jobs.",
    no_args_is_help=True,
)

_EXTRA = {"allow_extra_args": True, "ignore_unknown_options": True}


@app.command()
def systems() -> None:
    """List systems and Harbor run recipes from systems.toml."""
    print_systems()


@app.command("tasks")
def list_tasks() -> None:
    """List runnable Harbor tasks."""
    for name in task_names():
        print(name)


@app.command()
def prepare(
    task: Annotated[str, typer.Argument(help="Task directory name under tasks/")],
    n: Annotated[Optional[int], typer.Option("--n", help="First N steps; default is all")] = None,
    force: Annotated[bool, typer.Option("--force", help="Download even if data/ exists")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Download the dataset and generate Harbor steps."""
    prepare_task(task, n, force=force, dry_run=dry_run)


@app.command(context_settings=_EXTRA)
def run(
    ctx: typer.Context,
    task: Annotated[str, typer.Argument(help="Task directory name under tasks/")],
    system: Annotated[
        str,
        typer.Option("--system", help=f"Learning system from {SYSTEMS_TOML.name}"),
    ] = "baseline",
    model: Annotated[Optional[str], typer.Option("--model")] = None,
    job_name: Annotated[Optional[str], typer.Option("--job-name")] = None,
    jobs_dir: Annotated[Optional[Path], typer.Option("--jobs-dir")] = None,
    n: Annotated[Optional[int], typer.Option("--n", help="First N steps")] = None,
    agent_timeout_multiplier: Annotated[
        Optional[float],
        typer.Option("--agent-timeout-multiplier"),
    ] = None,
    n_concurrent: Annotated[Optional[int], typer.Option("--n-concurrent")] = None,
    upload: Annotated[bool, typer.Option("--upload", help="Upload to Harbor Hub after the job")] = False,
    public: Annotated[bool, typer.Option("--public", help="Make the Hub upload public")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Run a system on a task. Extra Harbor flags go after --."""
    run_task(
        task,
        system,
        model=model,
        job_name=job_name,
        jobs_dir=jobs_dir,
        n=n,
        timeout=agent_timeout_multiplier,
        n_concurrent=n_concurrent,
        upload=upload,
        public=public,
        dry_run=dry_run,
        extra=extra_args(list(ctx.args)),
    )


@app.command(context_settings=_EXTRA)
def smoke(
    ctx: typer.Context,
    task: Annotated[str, typer.Argument(help="Task directory name under tasks/")],
    system: Annotated[
        str,
        typer.Option("--system", help=f"Learning system from {SYSTEMS_TOML.name}"),
    ] = "baseline",
    model: Annotated[Optional[str], typer.Option("--model")] = None,
    job_name: Annotated[Optional[str], typer.Option("--job-name")] = None,
    jobs_dir: Annotated[Optional[Path], typer.Option("--jobs-dir")] = None,
    n: Annotated[Optional[int], typer.Option("--n", help="First N steps (default 10)")] = None,
    agent_timeout_multiplier: Annotated[
        Optional[float],
        typer.Option("--agent-timeout-multiplier"),
    ] = None,
    n_concurrent: Annotated[Optional[int], typer.Option("--n-concurrent")] = None,
    upload: Annotated[bool, typer.Option("--upload", help="Upload to Harbor Hub after the job")] = False,
    public: Annotated[bool, typer.Option("--public", help="Make the Hub upload public")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Run the first 10 steps (or --n). Extra Harbor flags go after --."""
    run_task(
        task,
        system,
        model=model,
        job_name=job_name,
        jobs_dir=jobs_dir,
        n=n,
        timeout=agent_timeout_multiplier,
        n_concurrent=n_concurrent,
        upload=upload,
        public=public,
        dry_run=dry_run,
        extra=extra_args(list(ctx.args)),
        smoke=True,
    )


@app.command()
def upload(
    job: Annotated[
        Optional[str],
        typer.Argument(help="Job name or directory; default is the newest job"),
    ] = None,
    jobs_dir: Annotated[Optional[Path], typer.Option("--jobs-dir")] = None,
    public: Annotated[bool, typer.Option("--public")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Upload a job directory to Harbor Hub."""
    upload_job(job, jobs_dir=jobs_dir, public=public, dry_run=dry_run)


@app.command()
def report(
    task: Annotated[Optional[str], typer.Option("--task")] = None,
    job: Annotated[Optional[str], typer.Option("--job")] = None,
    jobs_dir: Annotated[Path, typer.Option("--jobs-dir")] = ROOT / "jobs",
    out_dir: Annotated[Path, typer.Option("--out-dir")] = ROOT / "reports",
) -> None:
    """Write markdown, JSON, HTML, and SVG charts."""
    rows, written = write_report(jobs_dir, out_dir, task, job)
    print(render_markdown(rows))
    for path in written.values():
        print(f"Wrote {path}")
