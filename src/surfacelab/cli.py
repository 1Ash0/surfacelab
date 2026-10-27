"""CLI entry point for surfacelab.

Commands
--------
surfacelab run <cases>       replay a cassette run (no live calls)
surfacelab run --dry-run     estimate cost without any API calls
surfacelab run --record      live run; requires --max-usd and --provider/--model
surfacelab inspect <surface> print token ledger for a fixture surface
surfacelab probe <cmd...>    run the MCP handshake probe against a server
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@app.command()
def run(
    cases_path: Annotated[Path, typer.Argument(help="JSONL file of cases")],
    surface: Annotated[str, typer.Option(help="Fixture surface name (fixtures/surfaces/<name>.json)")] = "goodserver",
    provider: Annotated[str, typer.Option(help="Provider slug (openrouter|groq|gemini|nvidia|mistral)")] = "openrouter",
    model: Annotated[str, typer.Option(help="Model ID")] = "meta-llama/llama-3.1-8b-instruct:free",
    max_usd: Annotated[float, typer.Option(help="Budget cap in USD. 0 = offline-only (default)")] = 0.0,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Estimate cost and exit without calling the API")] = False,
    record: Annotated[bool, typer.Option("--record", help="Record live calls to cassette")] = False,
    variants: Annotated[int, typer.Option(help="Number of balanced permutation variants (1 = canonical only)")] = 1,
    workers: Annotated[int, typer.Option(help="Parallel trial workers (1 = sequential)")] = 1,
    out: Annotated[Path | None, typer.Option(help="Write JSON report to this path")] = None,
    html: Annotated[Path | None, typer.Option(help="Write HTML report to this path")] = None,
) -> None:
    """Run an experiment from a cases JSONL file."""
    from dotenv import load_dotenv

    load_dotenv()

    from .budget import estimate as budget_estimate
    from .cases import load_cases
    from .providers.cassette import CassetteStore
    from .providers.openai_compat import OpenAICompatProvider
    from .render import render as render_surface
    from .report import make_report
    from .runner import run_experiment
    from .surface import load_fixture_surface
    from .variants import balanced_permutations

    # ---- load inputs --------------------------------------------------------
    if not cases_path.exists():
        typer.echo(f"Cases file not found: {cases_path}", err=True)
        raise typer.Exit(1)

    cases = load_cases(cases_path)
    base_surface = load_fixture_surface(surface)

    if variants > 1:
        surface_variants = balanced_permutations(base_surface, variants)
    else:
        surface_variants = [base_surface]

    # ---- cost estimate (always shown) ---------------------------------------
    rendered = render_surface(base_surface)
    # Rough per-case token estimate: system + tools JSON + request
    tools_json = json.dumps(rendered)
    tokens_per_case = len(tools_json) // 4 + 256  # crude character → token approximation
    total_input_tokens = tokens_per_case * len(cases) * len(surface_variants)
    est = budget_estimate(model, total_input_tokens)

    typer.echo("Experiment plan:")
    typer.echo(f"  cases={len(cases)}  variants={len(surface_variants)}  trials={len(cases)*len(surface_variants)}")
    typer.echo(f"  {est}")

    if dry_run:
        typer.echo("(dry-run) No calls made.")
        raise typer.Exit(0)

    # ---- cassette store / live mode -----------------------------------------
    cassette_dir = Path("cassettes")
    cassette_dir.mkdir(exist_ok=True)
    cassette_store = CassetteStore(cassette_dir, mode="record" if record else "replay")

    provider_obj = OpenAICompatProvider(
        provider_slug=provider,
        model_id=model,
        cassette_store=cassette_store,
    )

    # ---- run ----------------------------------------------------------------
    total_trials = len(cases) * len(surface_variants)
    _done_count = 0
    _progress_lock = threading.Lock()

    from .cases import Case as _Case
    from .schema import Surface as _Surface

    base_harness = provider_obj.call

    def harness(case: _Case, surface: _Surface) -> str | None:
        nonlocal _done_count
        try:
            return base_harness(case, surface)
        finally:
            with _progress_lock:
                _done_count += 1
                n = _done_count
            typer.echo(f"\r  {n}/{total_trials} trials", nl=False, err=True)

    if workers > 1:
        typer.echo(f"  running {total_trials} trials with {workers} workers …", err=True)
    trials, errors = run_experiment(cases, surface_variants, harness, workers=workers)
    typer.echo("", err=True)  # newline after progress

    if errors:
        typer.echo(f"\n{len(errors)} trial(s) failed:", err=True)
        for e in errors:
            typer.echo(f"  case={e.case_id} variant={e.variant_index}: {e.message}", err=True)

    # ---- report -------------------------------------------------------------
    from .report import render_html, render_text

    report = make_report(trials)
    typer.echo("\n" + render_text(report))

    if out is not None:
        import dataclasses
        out.write_text(
            json.dumps(dataclasses.asdict(report), indent=2),
            encoding="utf-8",
        )
        typer.echo(f"JSON report -> {out}")

    if html is not None:
        html.write_text(render_html(report), encoding="utf-8")
        typer.echo(f"HTML report -> {html}")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@app.command()
def inspect(
    surface_name: Annotated[str, typer.Argument(help="Fixture surface name")],
    model: Annotated[str, typer.Option(help="Model to price against")] = "claude-sonnet-4-6",
) -> None:
    """Print a token-cost ledger for a fixture surface."""
    from .budget import estimate as budget_estimate
    from .render import render as render_surface
    from .surface import load_fixture_surface

    srf = load_fixture_surface(surface_name)
    rendered = render_surface(srf)
    tools_json = json.dumps(rendered)
    n_tools = len(srf.tools)
    chars = len(tools_json)
    approx_tokens = chars // 4

    typer.echo(f"Surface : {srf.server_name}")
    typer.echo(f"Tools   : {n_tools}")
    typer.echo(f"JSON len: {chars} chars (~{approx_tokens} tokens)")
    typer.echo("\nTool list:")
    for i, tool in enumerate(srf.tools, 1):
        typer.echo(f"  {i:2}. {tool.name:30s}  {len(tool.description)} chars")

    est = budget_estimate(model, approx_tokens)
    typer.echo(f"\nEstimated cost per call ({model}):")
    typer.echo(f"  {est}")


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------


@app.command()
def probe(
    command: Annotated[list[str], typer.Argument(help="Server command and args")],
    server_name: Annotated[str, typer.Option(help="Logical name for this server")] = "probe_target",
    timeout: Annotated[float, typer.Option(help="Handshake timeout in seconds")] = 10.0,
    snapshots_dir: Annotated[Path | None, typer.Option(help="Directory for snapshots (enables drift detection)")] = None,
) -> None:
    """Run the MCP handshake probe against a server command."""
    from .pulse import probe as run_probe
    from .snapshot import SnapshotStore

    snap_store = SnapshotStore(snapshots_dir) if snapshots_dir is not None else None
    result = run_probe(command, server_name, timeout=timeout, snapshot_store=snap_store)

    typer.echo(f"outcome    : {result.outcome.value}")
    typer.echo(f"server     : {result.server_name}")
    if result.error_message:
        typer.echo(f"error      : {result.error_message}")
    if result.surface is not None:
        n = len(result.surface.tools)
        typer.echo(f"tools      : {n}")
        for tool in result.surface.tools:
            typer.echo(f"  - {tool.name}")
    if result.instruction_like_flags:
        typer.echo("flags      :")
        for tool_name, pattern_id in result.instruction_like_flags:
            typer.echo(f"  [{pattern_id}] {tool_name}")
    if result.drift_events:
        typer.echo("drift      :")
        for ev in result.drift_events:
            typer.echo(f"  {ev.kind} {ev.tool_name!r}")

    raise typer.Exit(0 if result.outcome.value in ("ok", "no_tools") else 1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
