#!/usr/bin/env python3
import os
import sys
from unittest.mock import patch

import typer

from gdss.cli.start import GDSSShell, console
from gdss.graph.graph_builder import build_code_graph_from_repo
from gdss.graph.graph_export import UnsupportedGraphFormatError, export_graph

app = typer.Typer(help="GDSS: Geometric Distributed Software Synchronizer", no_args_is_help=False)
graph_app = typer.Typer(help="Dependency graph operations")
app.add_typer(graph_app, name="graph")

def run_shell(repo_path: str, command: str | None = None):
    status_code = 0
    try:
        if not os.path.exists(repo_path):
            console.print(f"[bold red]✗ Error:[/] Path '{repo_path}' does not exist!")
            status_code = 1
        else:
            # Patcher for non-interactive mode
            patcher = patch('rich.prompt.Prompt.ask', return_value='default')
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
def main_callback(ctx: typer.Context, repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    if ctx.invoked_subcommand is None:
        run_shell(repo)

@app.command()
def start(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Start interactive shell (alias)"""
    run_shell(repo)

@app.command()
def status(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"), ref: str = typer.Option("main", "--ref", help="Reference attractor branch")):
    """Show attractor/remote state, trajectory operators, and uncommitted semantic delta."""
    run_shell(repo, f"status {ref}")

@app.command()
def log(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"), n: int = typer.Option(5, "-n", help="Number of commits")):
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
):
    """Show per-branch drift magnitude (tip proxy + trajectory integral)."""
    run_shell(repo, f"drift {ref}")

@app.command()
def alerts(
    repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"),
    ref: str = typer.Option("main", "--ref", help="Reference attractor branch"),
):
    """Show drift alerts for diverging branch trajectories."""
    run_shell(repo, f"alerts {ref}")

@app.command()
def watch(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Real-time monitoring of the distributed event bus."""
    run_shell(repo, "watch")

@app.command()
def diff(target: str = typer.Argument("main"), repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Semantic diff from merge-base(target) through the working tree."""
    run_shell(repo, f"diff {target}")

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
