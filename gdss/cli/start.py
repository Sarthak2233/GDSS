#!/usr/bin/env python3
"""
GDSS: Geometric Distributed Software Synchronizer
Interactive Shell for Distributed Repository Awareness
"""

import cmd
import os
import sys
import time
from typing import Optional, List, Dict, Any, Set

# Rich Console imports - USED
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.columns import Columns
from rich.tree import Tree

# GDSS Core imports - USED
from gdss.core.ast_parser import ASTParser, SOURCE_EXTENSIONS
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import OperatorType, CodeSymbol, SymbolType, SemanticOperator

# GDSS Graph imports - USED
from gdss.graph.code_graph import CodeGraph
from gdss.graph.graph_builder import build_code_graph_from_repo

# GDSS Runtime imports - USED
from gdss.runtime.daemon import GDSSDaemon
from gdss.runtime.registry import RepositoryRegistry
from gdss.runtime.hierarchy import HierarchyManager
from gdss.storage.db import RuntimeDB

# GDSS Watcher imports - USED
from gdss.watcher.git_observer import GitObserver
from gdss.core.trajectory import extract_trajectory_operators, is_single_attractor_trajectory
from gdss.embeddings.encoder import get_encoder
from gdss.embeddings.service import find_similar_symbols, rebuild_vector_index
from gdss.embeddings.branch_vector import (
    aggregate_branch_tip,
    embed_symbols,
)
from gdss.embeddings.service import collect_repo_symbols

# Initialize Rich Console
console = Console()


class ColorTheme:
    """Dynamic Theme Registry for GDSS"""
    THEMES = {
        "default": {
            "primary": "cyan",
            "secondary": "magenta",
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "info": "blue",
            "accent": "bright_magenta"
        },
        "monokai": {
            "primary": "#e6db74",
            "secondary": "#f92672",
            "success": "#a6e22e",
            "error": "#f92672",
            "warning": "#fd971f",
            "info": "#66d9ef",
            "accent": "#ae81ff"
        },
        "nord": {
            "primary": "bright_blue",
            "secondary": "blue",
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "info": "bright_cyan",
            "accent": "cyan"
        },
        "matrix": {
            "primary": "green",
            "secondary": "bright_green",
            "success": "bright_green",
            "error": "red",
            "warning": "green",
            "info": "green",
            "accent": "bright_green"
        }
    }

    def __init__(self, theme_name: str = "default"):
        self.colors = self.THEMES.get(theme_name, self.THEMES["default"])

    def __getitem__(self, key):
        return self.colors.get(key, "white")


class GDSSShell(cmd.Cmd):
    """
    GDSS Interactive Shell: Convergence of Phase 0 Runtime and Rich Visuals
    """
    
    def __init__(self, repo_path: str, theme: Optional[str] = None):
        super().__init__()
        self.repo_path = os.path.abspath(repo_path)
        self.observer = GitObserver(self.repo_path)
        
        # 0. Initialize core engines
        self.parser = ASTParser()
        self.graph = CodeGraph()
        self.extractor = TransformExtractor()
        
        # 1. Visual Theme Selection
        if theme:
            self.theme = ColorTheme(theme)
        else:
            self._select_theme()
        
        # 2. Engine Bootstrap (Phase 0 Wiring)
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(
                f"[bold {self.theme['primary']}]Waking Distributed Daemon...[/]", 
                total=None
            )
            
            self.db = RuntimeDB()
            self.registry = RepositoryRegistry(self.db)
            self.hierarchy = HierarchyManager(self.db)
            self.daemon = GDSSDaemon(self.repo_path, self.registry, self.db)
            self.daemon.start()
            
            progress.update(
                task, 
                description=f"[bold {self.theme['success']}]✓ GDSS Engine Ready!"
            )
        
        self.active_branch = (self.observer.get_active_branch() or "DETACHED") if self.observer.is_valid() else "unknown"
        self.prompt = self._get_colored_prompt()
        self._show_welcome_banner()

    def _select_theme(self):
        console.print(Panel(
            Align.center(
                f"[bold cyan]GDSS Geometric Interface[/]\n[dim]Choose your visualization trajectory[/]"
            ),
            border_style="cyan"
        ))
        choice = Prompt.ask(
            "Theme", 
            choices=["default", "monokai", "nord", "matrix"], 
            default="default"
        )
        self.theme = ColorTheme(choice)

    def _get_status_indicator(self) -> str:
        """Prompt indicator for local uncommitted semantic delta (not remote topic)."""
        is_valid = self.observer.is_valid()
        self.active_branch = (self.observer.get_active_branch() or "DETACHED") if is_valid else "unknown"

        if not is_valid:
            return f"[bold {self.theme['error']}]![/]"

        changes = self.observer.get_working_tree_changes()
        has_changes = any(changes.values())
        if not has_changes:
            return f"[bold {self.theme['success']}]●[/]"

        # Δ means local working-tree semantic operators, never remote_aware.
        has_semantic_delta = False
        candidate_files = (
            changes.get("modified", []) + changes.get("added", []) + changes.get("deleted", [])
        )
        for f in candidate_files:
            if not f.endswith(SOURCE_EXTENSIONS):
                continue
            try:
                head_content = self.observer.get_file_content_at_commit("HEAD", f) or ""  # dsa:ignore
                current_path = os.path.join(self.repo_path, f)
                current_content = ""
                if os.path.exists(current_path):
                    with open(current_path, "r", encoding="utf-8", errors="ignore") as current_f:
                        current_content = current_f.read()  # dsa:ignore
                old_syms = self.parser.parse_file(f, head_content) if head_content else []  # dsa:ignore
                new_syms = self.parser.parse_file(f, current_content) if current_content else []  # dsa:ignore
                ops = self.extractor.extract_operators(f, old_syms, new_syms)
                if ops:
                    has_semantic_delta = True
                    break
            except Exception:
                pass

        if has_semantic_delta:
            return f"[bold {self.theme['error']}]Δ[/]"
        return f"[bold {self.theme['warning']}]✱[/]"

    def _resolve_reference_branch(self, arg: str = "") -> str:
        """Resolve reference attractor from CLI arg, then persisted config, then default."""
        parts = arg.split() if arg else []
        if parts:
            return parts[0]
        if hasattr(self, "daemon") and self.daemon:
            return self.daemon.context_engine.get_reference_branch()
        return "main"

    def _extract_uncommitted_operators(self) -> List[SemanticOperator]:
        working_changes = self.observer.get_working_tree_changes()
        operators: List[SemanticOperator] = []
        for f in working_changes.get("modified", []):
            if not f.endswith(SOURCE_EXTENSIONS):
                continue
            head_content = self.observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
            try:
                with open(os.path.join(self.repo_path, f), "r", encoding="utf-8", errors="ignore") as current_f:
                    current_content = current_f.read()  # dsa:ignore
            except OSError:
                continue
            if head_content is None:
                continue
            old_syms = self.parser.parse_file(f, head_content)  # dsa:ignore
            new_syms = self.parser.parse_file(f, current_content)  # dsa:ignore
            operators.extend(self.extractor.extract_operators(f, old_syms, new_syms))
        for f in working_changes.get("added", []):
            if not f.endswith(SOURCE_EXTENSIONS):
                continue
            try:
                with open(os.path.join(self.repo_path, f), "r", encoding="utf-8", errors="ignore") as current_f:
                    current_content = current_f.read()  # dsa:ignore
            except OSError:
                continue
            new_syms = self.parser.parse_file(f, current_content)  # dsa:ignore
            operators.extend(self.extractor.extract_operators(f, [], new_syms))
        for f in working_changes.get("deleted", []):
            if not f.endswith(SOURCE_EXTENSIONS):
                continue
            head_content = self.observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
            if not head_content:
                continue
            old_syms = self.parser.parse_file(f, head_content)  # dsa:ignore
            operators.extend(self.extractor.extract_operators(f, old_syms, []))
        return operators

    def _print_operator_table(self, title: str, operators: List[SemanticOperator], border_key: str) -> None:
        console.print(f"\n[bold {self.theme[border_key]}]{title}[/]")
        if not operators:
            console.print("[dim]  (none)[/]")
            return
        table = Table(box=box.MINIMAL, border_style=self.theme[border_key])
        table.add_column("Operator", style="dim")
        table.add_column("Symbol")
        table.add_column("File")
        for op in operators:
            table.add_row(
                f"{op.get_icon()} {op.get_display_name()}",
                op.name or f"{op.from_name} -> {op.to_name}",
                op.file,
            )
        console.print(table)
    def _get_colored_prompt(self) -> str:
        status = self._get_status_indicator()
        branch_part = f"([bold {self.theme['secondary']}]{self.active_branch}[/])" if self.active_branch else ""
        return f"[bold {self.theme['primary']}]gdss[/]{branch_part} {status} [bold {self.theme['accent']}]▶[/] "

    def cmdloop(self, intro=None):
        """Override cmdloop to use rich console input for colored prompts."""
        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            console.print(self.intro)
        
        stop = None
        while not stop:
            try:
                # Update prompt dynamically
                self.prompt = self._get_colored_prompt()
                line = console.input(self.prompt)
            except EOFError:
                line = 'EOF'
            except KeyboardInterrupt:
                console.print()  # print a newline
                line = ''
                continue
            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        self.postloop()

    def _show_welcome_banner(self):
        title_style = f"bold {self.theme['secondary']}"
        banner = f"""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   ██████╗ ███████╗ ███████╗███████╗                               ║
║  ██╔════╝ ██╔═══██╗██╔════╝██╔════╝                               ║
║  ██║  ███╗██║   ██║███████╗███████╗                               ║
║  ██║   ██║██║   ██║╚════██║╚════██║                               ║
║  ╚██████╔╝███████  ███████║███████║                               ║
║   ╚═════╝ ╚══════╝ ╚══════╝╚══════╝                               ║
║                                                                    ║
║  [{title_style}]Geometric Distributed Software Synchronizer[/]     ║
║  [dim]Semantic Intelligence Layer Above Git[/]                    ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║  📁 Repo: [bold {self.theme['info']}]{self.repo_path}[/]          ║
║  🌿 Branch: [bold {self.theme['success']}]{self.active_branch}[/] ║
╚════════════════════════════════════════════════════════════════════╝
        """
        console.print(Panel(
            Align.center(banner), 
            border_style=self.theme['primary'], 
            padding=(0, 1)
        ))
        
        tips = Columns([
            f"[{self.theme['info']}]❓[/] [bold]help[/] for commands",
            f"[{self.theme['success']}]📈[/] [bold]status[/] for trajectory",
            f"[{self.theme['warning']}]🕸[/] [bold]analyze[/] for graph",
            f"[{self.theme['error']}]🚪[/] [bold]quit[/] to exit"
        ], equal=True)
        console.print(tips)

    def do_status(self, arg):
        """Show branch/attractor/remote state, trajectory since ref, and uncommitted semantic delta.

        Usage: status [ref_branch]
        """
        console.print(f"\n[bold {self.theme['primary']}]━━━ DISTRIBUTED STATUS ━━━[/]")
        ref = self._resolve_reference_branch(arg)
        ctx = self.daemon.context_engine.get_latest_context() if self.daemon else {}

        table = Table(box=box.ROUNDED, border_style=self.theme["info"])
        table.add_column("Vector", style=f"bold {self.theme['secondary']}")
        table.add_column("State")

        table.add_row("Local Branch", f"[bold {self.theme['success']}]{self.active_branch}[/]")
        table.add_row("Attractor (ref)", f"[bold]{ref}[/]")

        remote = self.observer.get_remote_sync_status(ref)
        remote_style = self.theme["success"] if remote["label"] == "ALIGNED" else self.theme["info"]
        if remote["label"] == "N/A":
            remote_style = "dim"
        table.add_row(
            "Remote",
            f"[{remote_style}]{remote['label']}[/] [dim]({remote['remote_ref']})[/]",
        )
        if ctx:
            table.add_row("Last Context Event", str(ctx.get("event") or ctx.get("source") or "—"))

        console.print(table)

        single, only_branch = is_single_attractor_trajectory(self.observer, ref)
        if single:
            console.print(
                f"\n[dim]Single trajectory on attractor '{only_branch}'. "
                "Multi-branch conflict tensor Ω_ij is N/A.[/]"
            )

        traj_ops = extract_trajectory_operators(
            self.observer, self.parser, self.extractor, ref_branch=ref, head="HEAD"
        )
        self._print_operator_table("Trajectory since reference (committed)", traj_ops, "info")

        wt_ops = self._extract_uncommitted_operators()
        self._print_operator_table("Uncommitted semantic delta (working tree)", wt_ops, "warning")

        # Assistive embedding tip (not continuous I(B_i) / Phase 3 drift)
        try:
            enc = get_encoder()
            symbols = collect_repo_symbols(self.repo_path, self.parser)
            if symbols:
                emb = embed_symbols(symbols, enc)
                tip = aggregate_branch_tip(
                    emb.values(), branch=self.active_branch, reference_branch=ref
                )
                console.print(
                    f"\n[dim]Embedding tip (assistive): {tip.symbol_count} symbols, "
                    f"backend={enc.name}, dim={tip.dim}. Not drift energy I(B_i).[/]"
                )
        except Exception:
            pass

    def do_reindex(self, _):
        """Rebuild local FAISS/numpy vector index under .gdss/vectors/."""
        console.print(f"\n[bold {self.theme['primary']}]━━━ REBUILD EMBEDDING INDEX ━━━[/]")
        try:
            store, n = rebuild_vector_index(self.repo_path)
            console.print(
                f"[bold {self.theme['success']}]✓ Indexed {n} symbols "
                f"(backend={store.backend}, dim={store.dim}) → .gdss/vectors/[/]"
            )
        except Exception as exc:
            console.print(f"[bold {self.theme['error']}]✗ {exc}[/]")

    def do_similar(self, arg):
        """Find semantically similar symbols via FAISS/numpy index.

        Usage: similar <symbol_name> [k]
        """
        parts = arg.split()
        if not parts:
            console.print(f"[bold {self.theme['error']}]Usage: similar <symbol_name> [k][/]")
            return
        name = parts[0]
        k = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
        console.print(f"\n[bold {self.theme['primary']}]━━━ SIMILAR TO {name} (assistive) ━━━[/]")
        try:
            hits = find_similar_symbols(self.repo_path, name, k=k)
        except Exception as exc:
            console.print(f"[bold {self.theme['error']}]✗ {exc}[/]")
            return
        if not hits:
            console.print(f"[dim]No symbol named '{name}' found (or index empty).[/]")
            return
        table = Table(box=box.MINIMAL, border_style=self.theme["info"])
        table.add_column("Score")
        table.add_column("Symbol")
        table.add_column("Location")
        for sid, score, sym in hits:
            label = sym.name if sym else sid
            loc = (sym.chart_location or "") if sym else ""
            table.add_row(f"{score:.3f}", label, loc)
        console.print(table)
        console.print("[dim]Probabilistic neighbors — not a merge oracle.[/]")

    def do_log(self, arg):
        """Show semantic commit log. Usage: log [count] [--type=operator_type]"""
        args = arg.split()
        count = 5
        filter_type: Optional[OperatorType] = None
        
        for a in args:
            if a.startswith("--type="):
                val = a.split("=")[1]
                try:
                    filter_type = OperatorType(val)
                except ValueError:
                    console.print(f"[bold {self.theme['error']}]✗ Invalid operator type: {val}[/]")
                    return
            elif a.isdigit():
                count = int(a)

        console.print(f"\n[bold {self.theme['primary']}]━━━ 📜 SEMANTIC LOG (Last {count}) ━━━[/]")
        
        commits = list(self.observer.repo.iter_commits("HEAD", max_count=count))
        
        for commit in commits:
            msg = str(commit.summary)
            sha = commit.hexsha
            parent_sha = self.observer.get_parent_sha(sha)
            
            # Semantic extraction
            all_ops: List[SemanticOperator] = []
            if parent_sha:
                changes = self.observer.get_file_diffs_between_commits(parent_sha, sha)
                for f in changes["modified"]:
                    if f.endswith(SOURCE_EXTENSIONS):
                        old_content = self.observer.get_file_content_at_commit(parent_sha, f)
                        new_content = self.observer.get_file_content_at_commit(sha, f)
                        if old_content and new_content:
                            ops = self.extractor.extract_operators(f, self.parser.parse_file(f, old_content), self.parser.parse_file(f, new_content), sha)
                            all_ops.extend(ops)
            
            # Filter by type
            if filter_type:
                all_ops = [op for op in all_ops if op.operator == filter_type]
                if not all_ops:
                    continue

            color = self.theme['success']
            if "fix" in msg.lower(): color = self.theme['error']
            elif "feat" in msg.lower(): color = self.theme['info']
            
            console.print(f"\n[bold {color}]● {sha[:8]}[/] [bold]{msg}[/]")
            
            num_ops = len(all_ops)
            for op in all_ops[:8]:
                icon = op.get_icon()
                op_color = op.get_color()
                name = op.name or f"{op.from_name} -> {op.to_name}"
                console.print(f"  [{op_color}]{icon}[/] [dim]{op.get_display_name()}:[/] [bold]{name}[/]")
            
            if num_ops > 8:
                console.print(f"  [dim]... and {num_ops - 8} more transformations[/]")

    def do_analyze(self, _):
        """Deep semantic analysis and dependency mapping."""
        console.print(f"\n[bold {self.theme['primary']}]━━━ SEMANTIC ANALYSIS ━━━[/]")

        def on_progress(done, total, skipped):
            console.print(f"[dim]  parsed {done}/{total} files...[/]")

        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Building dependency graph...", total=None)
            self.graph = build_code_graph_from_repo(
                self.repo_path, progress_callback=on_progress, batch_size=500
            )
            progress.update(task, description="[green]Analysis complete!")
        summary = self.graph.get_summary()
        console.print(f"Nodes: [bold]{summary['total_nodes']}[/] | Edges: [bold]{summary['total_edges']}[/]")

        skipped = getattr(self.graph, "skipped_unsupported", {}) or {}
        if skipped:
            parts = [f"{count} {ext}" for ext, count in sorted(skipped.items())]
            console.print(f"[dim]Skipped unsupported: {', '.join(parts)}[/]")

        for stype in SymbolType:
            count = sum(1 for _, data in self.graph.g.nodes(data=True) if data.get("type") == stype.value)
            if count > 0:
                console.print(f"  • {stype.value.capitalize()}: {count}")

    def do_watch(self, _):
        """Real-time monitoring of the distributed event bus."""
        console.print(f"\n[bold {self.theme['primary']}]━━━ 👁️ LIVE MONITOR ━━━[/]")
        try:
            with Live(console=console, screen=True) as live:
                while True:
                    ctx = self.daemon.context_engine.get_latest_context()
                    layout = Layout()
                    layout.split(
                        Layout(
                            Panel(
                                f"[bold cyan]GDSS Live Monitor[/] | Branch: [green]{self.active_branch}[/]",
                                border_style="cyan"
                            ), 
                            size=3
                        ),
                        Layout(
                            Panel(
                                f"Last Event: [yellow]{ctx.get('event', 'Watching...')}[/]\n"
                                f"Remote Peer State: [magenta]{'ACTIVE' if ctx.get('remote_aware') else 'IDLE'}[/] "
                                f"[dim](event bus; not semantic drift)[/]",
                                border_style="green"
                            )
                        ),
                        Layout(
                            Text("Press Ctrl+C to stop", justify="center", style="dim"), 
                            size=1
                        )
                    )
                    live.update(layout)
                    time.sleep(1)
        except KeyboardInterrupt:
            pass

    def do_diff(self, arg):
        """Semantic diff: merge-base(ref) through working tree (committed + uncommitted).

        Usage: diff [ref_branch]
        """
        target = arg.strip() or self._resolve_reference_branch("")
        console.print(
            f"\n[bold {self.theme['primary']}]━━━ SEMANTIC DIFF "
            f"(merge-base with {target} → working tree) ━━━[/]"
        )
        
        base_sha = self.observer.get_merge_base(self.active_branch, target)
        if not base_sha:
            console.print(f"[bold {self.theme['error']}]✗ No common ancestor found with {target}[/]")
            return
            
        # Get diff between base_sha and working directory (including staged/unstaged changes)
        diffs = {"added": [], "deleted": [], "modified": []}
        try:
            commit_base = self.observer.repo.commit(base_sha)
            diffs_to_wt = commit_base.diff(None)
            
            # Untracked files
            untracked = self.observer.repo.untracked_files
            diffs["added"].extend(untracked)
            
            for d in diffs_to_wt:
                if d.new_file:
                    if d.b_path not in diffs["added"]:
                        diffs["added"].append(d.b_path)
                elif d.deleted_file:
                    diffs["deleted"].append(d.a_path)
                elif d.renamed_file:
                    # Rename: store new path and old path for symbol extraction comparison
                    diffs["modified"].append((d.b_path, d.a_path))
                else:
                    diffs["modified"].append((d.b_path, d.b_path))
        except Exception:
            # Fallback using path strings
            fallback_diffs = self.observer.get_file_diffs_between_commits(base_sha, "HEAD")
            diffs["added"] = fallback_diffs["added"]
            diffs["deleted"] = fallback_diffs["deleted"]
            diffs["modified"] = [(f, f) for f in fallback_diffs["modified"]]
        
        table = Table(box=box.MINIMAL, border_style=self.theme['info'])
        table.add_column("State", style=f"bold {self.theme['secondary']}")
        table.add_column("File / Transformation")
        
        for f, old_f in diffs["modified"]: 
            table.add_row("MODIFIED", f)
            if f.endswith(SOURCE_EXTENSIONS):
                old_content = self.observer.get_file_content_at_commit(base_sha, old_f)
                try:
                    with open(os.path.join(self.repo_path, f), "r") as current_f:
                        new_content = current_f.read()  # dsa:ignore
                except Exception:
                    new_content = self.observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
                
                if old_content and new_content:
                    old_syms: List[CodeSymbol] = self.parser.parse_file(old_f, old_content)
                    new_syms: List[CodeSymbol] = self.parser.parse_file(f, new_content)
                    ops: List[SemanticOperator] = self.extractor.extract_operators(f, old_syms, new_syms)
                    for op in ops:
                        icon = op.get_icon()
                        name = op.name or f"{op.from_name} -> {op.to_name}"
                        table.add_row("", f"  {icon} [dim]{op.get_display_name()}:[/] [bold]{name}[/]")

        for f in diffs["added"]: 
            table.add_row("ADDED", f"[{self.theme['success']}]{f}[/]")
        for f in diffs["deleted"]: 
            table.add_row("DELETED", f"[{self.theme['error']}]{f}[/]")
        
        console.print(table)

    def do_hierarchy(self, _):
        """Show the distributed priority chain."""
        console.print(f"\n[bold {self.theme['primary']}]━━━ ⛓️ PRIORITY CHAIN ━━━[/]")
        repo_id = self.daemon.repo_id
        chain = self.hierarchy.resolve_priority_chain(repo_id, self.active_branch)
        
        tree = Tree(f"[bold {self.theme['secondary']}]Repository Trajectory[/]")
        curr = tree
        for branch in chain:
            style = "bold green" if branch == self.active_branch else "dim"
            curr = curr.add(f"[{style}]{branch}[/]")
        
        console.print(tree)

    def do_impact(self, arg):
        """Analyze downstream impact of a specific symbol."""
        symbol = arg.strip()
        if not symbol:
            console.print(f"[bold {self.theme['error']}]✗ Please provide a symbol name (e.g. 'process_payment')[/]")
            return
            
        console.print(f"\n[bold {self.theme['primary']}]━━━ 🎯 IMPACT ANALYSIS: {symbol} ━━━[/]")
        
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True) as progress:
            progress.add_task("[cyan]Scanning graph...", total=None)
            
            # Rebuild graph if empty
            if self.graph.g.number_of_nodes() <= 1:
                self.graph = build_code_graph_from_repo(self.repo_path)
            
            # Find nodes that match the symbol name
            target_nodes = [
                node for node, data in self.graph.g.nodes(data=True)
                if data.get("name") == symbol
            ]
            
            if not target_nodes:
                console.print(f"[bold {self.theme['warning']}]⚠ Symbol not found in current graph.[/]")
                return
                
            all_impacted = set()
            for node in target_nodes:
                all_impacted.update(self.graph.get_downstream_impact(node))
            
            table = Table(box=box.MINIMAL, border_style=self.theme['info'])
            table.add_column("Impacted Level", style=f"bold {self.theme['secondary']}")
            table.add_column("Symbol / File")
            
            for impacted in sorted(list(all_impacted)):
                data = self.graph.g.nodes[impacted]
                table.add_row(data.get("type", "unknown").upper(), impacted)
                
            console.print(table)
            console.print(f"\nTotal impacted nodes: [bold {self.theme['warning']}]{len(all_impacted)}[/]")

    def do_config(self, arg):
        """View or update configuration (e.g. choice of reference branch)."""
        args = arg.split()
        if not args:
            ref = self.daemon.context_engine.get_reference_branch()
            console.print(
                f"[{self.theme['info']}]Current Reference Branch (attractor):[/] {ref}"
            )
            return

        if args[0] == "ref":
            ref = args[1] if len(args) > 1 else "main"
            self.daemon.context_engine.set_reference_branch(ref)
            console.print(
                f"[bold {self.theme['success']}]✓ Reference branch set to {ref}[/] "
                f"[dim](persisted)[/]"
            )
            return

        console.print(f"[bold {self.theme['error']}]Unknown config key. Try: config ref <branch>[/]")

    def do_clear(self, _):
        os.system('clear' if os.name != 'nt' else 'cls')
        self._show_welcome_banner()

    def do_quit(self, _):
        console.print(f"\n[bold {self.theme['primary']}]👋 Closing interface. Daemon remains silent.[/]")
        if self.daemon: 
            self.daemon.stop()
        return True

    def do_EOF(self, _): 
        return self.do_quit(None)


if __name__ == "__main__":
    if len(sys.argv) > 1: 
        GDSSShell(sys.argv[1]).cmdloop()
    else: 
        GDSSShell(os.getcwd()).cmdloop()