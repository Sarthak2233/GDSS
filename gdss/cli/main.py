#!/usr/bin/env python3
import os
import sys
from typing import Annotated
from unittest.mock import patch

import typer

from gdss.cli.start import GDSSShell, console
from gdss.graph.graph_builder import build_code_graph_from_repo
from gdss.graph.graph_export import UnsupportedGraphFormatError, export_graph
from gdss.logger import configure_logging, get_logger

logger = get_logger("gdss.cli")

app = typer.Typer(help="GDSS: Gate Distributive Semantic Synopsis", no_args_is_help=False)
graph_app = typer.Typer(help="Dependency graph operations")
model_app = typer.Typer(help="Manage local Ollama model lifecycle")
app.add_typer(graph_app, name="graph")
app.add_typer(model_app, name="model")


def run_shell(repo_path: str, command: str | None = None):
    status_code = 0
    try:
        if not os.path.exists(repo_path):
            console.print(f"[bold red]✗ Error:[/] Path '{repo_path}' does not exist!")
            status_code = 1
        else:
            # Patcher for non-interactive mode
            patcher = patch("rich.prompt.Prompt.ask", return_value="default")
            if command:
                patcher.start()

            shell = GDSSShell(repo_path)

            if command:
                shell.onecmd(command)
                shell.do_quit(None)
                patcher.stop()
            else:
                shell.cmdloop()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⏹ Shell interrupted[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]✗ Fatal error:[/] {e}")
        status_code = 1

    if status_code != 0:
        sys.exit(status_code)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose informational logging"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug diagnostic logging"),
    log_file: str | None = typer.Option(None, "--log-file", help="Path to write log output"),
):
    level = "DEBUG" if debug else ("INFO" if verbose else None)
    configure_logging(level=level, log_file=log_file)
    if ctx.invoked_subcommand is None:
        run_shell(repo)


@app.command()
def start(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Start interactive shell (alias)"""
    run_shell(repo)


@app.command()
def status(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    ref: str = typer.Option("main", "--ref", help="Reference attractor branch"),
):
    """Show attractor/remote state, trajectory operators, and uncommitted semantic delta."""
    run_shell(repo, f"status {ref}")


@app.command()
def log(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    n: int = typer.Option(5, "-n", help="Number of commits"),
):
    """Show semantic commit log."""
    run_shell(repo, f"log {n}")


@app.command()
def analyze(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Deep semantic analysis and dependency mapping."""
    run_shell(repo, "analyze")


@app.command()
def similar(
    symbol: str = typer.Argument(..., help="Symbol name to search neighbors for"),
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    k: int = typer.Option(5, "-k", help="Number of neighbors"),
):
    """Find assistive semantic neighbors (FAISS / bag embeddings)."""
    run_shell(repo, f"similar {symbol} {k}")


@app.command()
def reindex(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
):
    """Rebuild the local embedding vector index under .gdss/vectors/."""
    run_shell(repo, "reindex")


@app.command()
def drift(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    ref: str = typer.Option("main", "--ref", help="Reference attractor branch"),
    branches: Annotated[
        list[str] | None,
        typer.Option("--branches", "-b", help="Branch names or wildcard patterns to include"),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Branch names or wildcard patterns to exclude"),
    ] = None,
):
    """Show per-branch drift magnitude (tip proxy + trajectory integral)."""
    cmd = f"drift {ref}"
    if branches:
        cmd += f" --branches {','.join(branches)}"
    if exclude:
        cmd += f" --exclude {','.join(exclude)}"
    run_shell(repo, cmd)


@app.command()
def alerts(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    ref: str = typer.Option("main", "--ref", help="Reference attractor branch"),
):
    """Show drift alerts for diverging branch trajectories."""
    run_shell(repo, f"alerts {ref}")


@app.command()
def tensor(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    ref: str = typer.Option("main", "--ref", help="Reference attractor branch"),
    branches: Annotated[
        list[str] | None,
        typer.Option("--branches", "-b", help="Branch names or wildcard patterns to include"),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Branch names or wildcard patterns to exclude"),
    ] = None,
):
    """Show sparse conflict tensor Omega_ij and R_merge."""
    cmd = f"tensor {ref}"
    if branches:
        cmd += f" --branches {','.join(branches)}"
    if exclude:
        cmd += f" --exclude {','.join(exclude)}"
    run_shell(repo, cmd)


@app.command()
def serve(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    port: int = typer.Option(8787, "--port", help="Port to bind to"),
    allow_local_source: bool = typer.Option(
        False, "--allow-local-source", help="Allow source-bearing API requests"
    ),
):
    """Serve the local API (Local HTTP FastAPI service)."""
    from pathlib import Path

    import uvicorn

    from gdss.api.server import create_app

    if not os.path.exists(repo):
        console.print(f"[bold red]✗ Error:[/] Path '{repo}' does not exist!")
        raise typer.Exit(code=1)

    app_instance = create_app(Path(repo))
    app_instance.state.allow_local_source = allow_local_source
    console.print(f"[bold green]Starting GDSS Local API on http://127.0.0.1:{port}[/]")
    uvicorn.run(app_instance, host="127.0.0.1", port=port, log_level="info")


@app.command()
def mcp() -> None:
    """Start the Model Context Protocol (MCP) server over stdio for Cursor/Copilot."""
    from gdss.mcp.server import run_stdio_server

    try:
        run_stdio_server()
    except (KeyboardInterrupt, BrokenPipeError):
        pass


@app.command()
def watch(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Real-time monitoring of the distributed event bus."""
    run_shell(repo, "watch")


@app.command()
def diff(
    target: str = typer.Argument("main"),
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
):
    """Semantic diff from merge-base(target) through the working tree."""
    run_shell(repo, f"diff {target}")


@app.command()
def suggest(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    ref: str = typer.Option("main", "--ref", help="Reference attractor branch"),
    branches: Annotated[
        list[str] | None,
        typer.Option("--branches", "-b", help="Branch names or wildcard patterns to include"),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Branch names or wildcard patterns to exclude"),
    ] = None,
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    as_prompt: bool = typer.Option(False, "--as-prompt", help="Output LLM-ready prompt"),
    llm: bool = typer.Option(
        False, "--llm", help="Automatically request a patch from LLM (auto-detects vLLM or Ollama)"
    ),
    provider_name: str = typer.Option(
        "auto",
        "--provider",
        help="Provider to use: auto (default), vllm, ollama, openai/github, or openrouter",
    ),
    model: str = typer.Option(
        "qwen2.5-coder:7b",
        "--model",
        help="Model to use (for Ollama or OpenAI-compatible provider)",
    ),
    combos: int = typer.Option(3, "--combos", help="Number of resolution strategies to generate"),
    max_candidates: int = typer.Option(
        50, "--max-candidates", help="Limit number of suggestion anchors analyzed"
    ),
    validate: bool = typer.Option(
        False, "--validate", help="Validate candidate patches in ephemeral sandbox"
    ),
    sandbox_timeout: int = typer.Option(
        30, "--sandbox-timeout", help="Timeout in seconds for sandbox validation"
    ),
    context_window: int | None = typer.Option(
        None, "--context-window", help="Explicit LLM context window size override in tokens"
    ),
    max_refinements: int = typer.Option(
        2,
        "--max-refinements",
        help="Maximum agentic self-correction refinement attempts if validation fails",
    ),
):
    """Generate ranked semantic resolution suggestions (Phase 5)."""
    import json

    from gdss.ai.llm_patch import AnyProvider, LLMProvider
    from gdss.ai.ollama_provider import OllamaProvider
    from gdss.ai.openai_provider import OpenAICompatibleProvider
    from gdss.ai.suggester import suggest as get_suggestions
    from gdss.ai.vllm_provider import VLLMProvider

    try:
        if context_window is not None:
            os.environ["GDSS_CONTEXT_WINDOW"] = str(context_window)

        provider: AnyProvider | LLMProvider | None = None
        if llm or (provider_name != "auto" and provider_name != "off"):
            if provider_name == "vllm":
                provider = VLLMProvider()
            elif provider_name == "ollama":
                provider = OllamaProvider(model=model)
            elif provider_name == "openrouter":
                provider = OpenAICompatibleProvider(
                    base_url="https://openrouter.ai/api/v1",
                    model=model if model != "qwen2.5-coder:7b" else None,
                )
            elif provider_name in {"openai", "github", "github-models"}:
                provider = OpenAICompatibleProvider(
                    model=model if model != "qwen2.5-coder:7b" else None
                )
            else:  # auto
                from gdss.ai.suggester import _pick_provider

                provider = _pick_provider(llm=True, provider=None)
            if provider is None and llm:
                console.print(
                    "[bold red]✗ Error:[/] --llm requested but no provider is reachable (vLLM, Ollama, or GITHUB_TOKEN/OPENAI_API_KEY)."
                )
                raise typer.Exit(code=1)  # dsa:ignore

        orchestrated_state = None
        if validate or (llm and not as_prompt):
            from gdss.ai.orchestration import ConvergenceState, run_convergence_pipeline

            state = ConvergenceState(
                repo_path=repo,
                reference_branch=ref,
                branches=branches,
                exclude_branches=exclude,
                llm=llm,
                validate=validate,
                combos=combos,
                max_candidates=max_candidates,
                sandbox_timeout=float(sandbox_timeout),
                provider=provider,
                max_refinements=max_refinements,
            )
            orchestrated_state = run_convergence_pipeline(state)
            suggestions = orchestrated_state.suggestions
        else:
            suggestions = get_suggestions(
                repo_path=repo,
                reference_branch=ref,
                branches=branches,
                exclude_branches=exclude,
                llm=llm,
                provider=provider,
                combos=combos,
                max_candidates=max_candidates,
            )

        if as_prompt:
            from gdss.ai.context import build_analysis_context
            from gdss.ai.context_builder import extract_3way_symbol_context
            from gdss.ai.prompt_builder import build_conflict_prompt

            ctx = build_analysis_context(repo, ref, branches=branches, exclude_branches=exclude)
            for s in suggestions:
                other_br = getattr(s.context, "other_branch", "") if s.context else ""
                collision_ctx = extract_3way_symbol_context(ctx, s, other_branch=other_br)
                console.print(
                    build_conflict_prompt(
                        suggestion=s,
                        repo=repo,
                        ref=ref,
                        collision_context=collision_ctx,
                        branch_commits=ctx.branch_commits,
                        branch_intents=ctx.branch_intents,
                        other_branch=other_br,
                    )
                )
                console.print("\n--- Next Suggestion ---\n")
            return

        if json_output:
            out = [s.to_local_source() if llm else s.to_metadata() for s in suggestions]
            console.print(json.dumps(out, indent=2))
            return

        if not suggestions:
            console.print("No suggestions found.")
            return

        from gdss.ai.suggestion_store import save_suggestion

        for s in suggestions:
            try:
                save_suggestion(s, repo)
            except Exception as exc:
                logger.debug("Failed saving suggestion %s to cache: %s", s.suggestion_id, exc)
            console.print(
                f"\n[bold blue]Suggestion {s.rank}[/]: {s.kind} on [bold]{s.file_path}[/] (Confidence: {s.confidence:.2f}) [dim cyan](ID: {s.suggestion_id})[/]"
            )
            console.print(f"Rationale: {s.rationale}")
            console.print(f"Action: {s.action}")
            refinements = 0
            if orchestrated_state and orchestrated_state.refinement_history:
                refinements = sum(
                    1
                    for e in orchestrated_state.refinement_history
                    if e.get("suggestion_id") == s.suggestion_id
                )
            if refinements > 0:
                console.print(
                    f"  [cyan]ℹ Refined through {refinements} self-correction attempt(s)[/]"
                )
            for st in s.patch_combinations:
                status_badge = (
                    "[green]✓ Sandbox Validated[/]"
                    if st.validated
                    else (
                        "[red]✗ Failed Validation[/]"
                        if st.validation_status == "rejected"
                        else f"(Valid: {st.validated})"
                    )
                )
                console.print(f"  - Strategy: {st.label} {status_badge}")
                if st.validation_error:
                    console.print(f"    [dim red]Error: {st.validation_error}[/]")

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/] {e}")
        raise typer.Exit(code=1) from e


@app.command("apply")
def apply_cmd(
    suggestion_id: str = typer.Argument(..., help="Suggestion ID to apply (e.g., sug_abc123)"),
    strategy: str | None = typer.Option(
        None,
        "--strategy",
        "-s",
        help="Resolution strategy (keep_left, keep_right, compose, custom)",
    ),
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate application and display unified diff without modifying files",
    ),
    rollback: bool = typer.Option(
        False, "--rollback", help="Roll back a previously applied suggestion"
    ),
):
    """Safely apply or rollback an approved suggestion to the working tree."""
    from gdss.validation.guarded_apply import apply_suggestion, rollback_suggestion

    if rollback:
        rb_res = rollback_suggestion(suggestion_id, repo)
        if not rb_res.success:
            console.print(f"[bold red]✗ Rollback failed:[/]\n{rb_res.error}")
            raise typer.Exit(code=1)  # dsa:ignore
        console.print(
            f"[bold green]✓[/] Successfully restored [bold]{rb_res.target_file}[/] from rollback backup."
        )
        return

    apply_res = apply_suggestion(suggestion_id, repo, strategy_name=strategy, dry_run=dry_run)
    if not apply_res.success:
        console.print(f"[bold red]✗ Apply failed:[/]\n{apply_res.error}")
        raise typer.Exit(code=1)  # dsa:ignore

    mode_label = "[yellow](DRY RUN)[/]" if dry_run else "[bold green]✓ Successfully applied[/]"
    console.print(
        f"{mode_label} suggestion [bold cyan]{apply_res.suggestion_id}[/] (strategy: [bold]{apply_res.strategy}[/]) to [bold]{apply_res.target_file}[/]:\n"
    )
    if apply_res.diff:
        from rich.syntax import Syntax

        console.print(Syntax(apply_res.diff, "diff", theme="monokai", line_numbers=False))
    if not dry_run:
        console.print(
            "\n[dim]Note: Only your local working tree file was modified. Git index, commits, and branches are untouched.[/]"
        )
        console.print(
            f"[dim]To undo this change, run: [cyan]gdss apply --rollback {apply_res.suggestion_id}[/][/]"
        )


@app.command("audit-pr")
def audit_pr_cmd(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    pr_number: int | None = typer.Option(
        None, "--pr-number", help="PR number to audit (auto-detected from GITHUB_EVENT_PATH in CI)"
    ),
    token: str | None = typer.Option(
        None, "--token", help="GitHub token (defaults to GITHUB_TOKEN env var)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate audit and print radar markdown report without modifying GitHub",
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Write radar markdown report to file"
    ),
    branches: Annotated[
        list[str] | None,
        typer.Option("--branches", "-b", help="PR head branch names or patterns to audit against"),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="PR head branch names or patterns to exclude"),
    ] = None,
    same_base_only: bool | None = typer.Option(
        None,
        "--same-base-only/--no-same-base-only",
        help="Only audit PRs targeting the exact same base branch (default: true)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose informational logging"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug diagnostic logging"),
    log_file: str | None = typer.Option(None, "--log-file", help="Path to write log output"),
):
    """Audit concurrent pull requests for semantic collisions and post sticky radar reports."""
    if verbose or debug or log_file:
        level = "DEBUG" if debug else ("INFO" if verbose else None)
        configure_logging(level=level, log_file=log_file)

    from gdss.validation.pr_audit import run_pr_audit

    exit_code = run_pr_audit(
        repo_path=repo,
        pr_number=pr_number,
        token=token,
        dry_run=dry_run,
        output_file=output,
        console=console,
        branches=branches,
        exclude=exclude,
        same_base_only=same_base_only,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)  # dsa:ignore


@model_app.command("status")
def model_status():
    """Check if the local Ollama service is reachable."""
    from gdss.ai.model_manager import ModelManager, ModelManagerError

    try:
        mgr = ModelManager()
        stat = mgr.status()
        console.print(
            f"[bold green]✓[/] Ollama service is reachable (version {stat.get('version')})"
        )
    except ModelManagerError as e:
        console.print(f"[bold red]✗ Error:[/] {e}")
        raise typer.Exit(code=1) from e


@model_app.command("list")
def model_list():
    """List locally available models in the Ollama registry."""
    from gdss.ai.model_manager import ModelManager, ModelManagerError

    try:
        mgr = ModelManager()
        models = mgr.list_models()
        if not models:
            console.print("No models found.")
            return
        for m in models:
            console.print(f"- {m.get('name')}")
    except ModelManagerError as e:
        console.print(f"[bold red]✗ Error:[/] {e}")
        raise typer.Exit(code=1) from e


@model_app.command("install")
def model_install(model: str = typer.Argument(..., help="Model name to pull")):
    """Pull a model from the Ollama registry."""
    from gdss.ai.model_manager import ModelManager, ModelManagerError

    try:
        mgr = ModelManager()
        console.print(f"Pulling model '{model}'...")
        for progress in mgr.pull_model(model):
            if status := progress.get("status"):
                console.print(status)
        console.print(f"[bold green]✓[/] Model '{model}' installed successfully.")
    except ModelManagerError as e:
        console.print(f"[bold red]✗ Error:[/] {e}")
        raise typer.Exit(code=1) from e


@model_app.command("ensure")
def model_ensure(model: str = typer.Argument(..., help="Model name to ensure")):
    """Pull a model if it is not already available locally."""
    from gdss.ai.model_manager import ModelManager, ModelManagerError

    try:
        mgr = ModelManager()
        models = mgr.list_models()
        if any(m.get("name") == model or m.get("name") == f"{model}:latest" for m in models):
            console.print(f"[bold green]✓[/] Model '{model}' is already available.")
            return
        console.print(f"Model '{model}' not found. Pulling...")
        for progress in mgr.pull_model(model):
            if status := progress.get("status"):
                console.print(status)
        console.print(f"[bold green]✓[/] Model '{model}' installed successfully.")
    except ModelManagerError as e:
        console.print(f"[bold red]✗ Error:[/] {e}")
        raise typer.Exit(code=1) from e


@model_app.command("remove")
def model_remove(model: str = typer.Argument(..., help="Model name to remove")):
    """Remove a model from the local Ollama registry."""
    from gdss.ai.model_manager import ModelManager, ModelManagerError

    try:
        mgr = ModelManager()
        mgr.remove_model(model)
        console.print(f"[bold green]✓[/] Model '{model}' removed successfully.")
    except ModelManagerError as e:
        console.print(f"[bold red]✗ Error:[/] {e}")
        raise typer.Exit(code=1) from e


@graph_app.command("export")
def graph_export(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    output: str = typer.Option("gdss_graph.dot", "--output", "-o", help="Output file path"),
    fmt: str = typer.Option("dot", "--format", "-f", help="Export format: dot, json"),
):
    """Export the dependency graph to DOT or JSON."""
    error_message: str | None = None
    if not os.path.exists(repo):
        error_message = f"Path '{repo}' does not exist!"
    else:
        try:
            code_graph = build_code_graph_from_repo(repo)
            written = export_graph(code_graph, format=fmt, output_path=output)
            summary = code_graph.get_summary()
            console.print(
                f"[bold green]✓[/] Exported {summary['total_nodes']} nodes and "
                f"{summary['total_edges']} edges to [bold]{written}[/] ({fmt})"
            )
            return
        except UnsupportedGraphFormatError as exc:
            error_message = str(exc)
        except OSError as exc:
            error_message = f"Could not write output: {exc}"

    console.print(f"[bold red]✗ Error:[/] {error_message}")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
