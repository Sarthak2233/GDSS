#!/usr/bin/env python3
import sys
import os
import typer
from gdss.cli.start import GDSSShell, console
from unittest.mock import patch

app = typer.Typer(help="GDSS: Geometric Distributed Software Synchronizer", no_args_is_help=False)

def run_shell(repo_path: str, command: str = None):
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
def status(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path"), ref: str = typer.Option("main", "--ref", help="Reference branch")):
    """Show distributed status and semantic drift."""
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
def watch(repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Real-time monitoring of the distributed event bus."""
    run_shell(repo, "watch")
    
@app.command()
def diff(target: str = typer.Argument("main"), repo: str = typer.Option(os.getcwd(), "--repo", help="Repository path")):
    """Perform semantic diff between branches."""
    run_shell(repo, f"diff {target}")

if __name__ == "__main__":
    app()
