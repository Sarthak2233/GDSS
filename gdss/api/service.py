"""Service layer for gdss API."""
import os
from typing import Any

from gdss.conflict.commutativity import commutativity_table
from gdss.conflict.probability import ConflictProbabilityEstimator
from gdss.conflict.tensor import ConflictTensor, TensorEngine
from gdss.core.ast_parser import SOURCE_EXTENSIONS, ASTParser
from gdss.core.trajectory import extract_trajectory_operators, is_single_attractor_trajectory
from gdss.core.transform_extractor import TransformExtractor
from gdss.drift.alerts import DriftAlerts
from gdss.drift.engine import DriftEngine
from gdss.drift.history import SnapshotHistory, default_history_path
from gdss.drift.types import DriftAlert, DriftSnapshot
from gdss.embeddings.service import find_similar_symbols, project_symbol_embeddings
from gdss.graph.graph_builder import build_code_graph_from_repo
from gdss.watcher.git_observer import GitObserver

_VELOCITY_EPS = 1e-6


def _wrap_ok(data: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": "ok",
        "data": data,
        "warnings": list(warnings) if warnings else [],
    }


def _wrap_err(code: str, what: str, why: str, fix: str) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "code": code,
            "details": {
                "what": what,
                "why": why,
                "fix": fix
            }
        }
    }


def _convergence_label(velocity: float) -> str:
    """Derive converging|diverging|stable from velocity sign."""
    if velocity < -_VELOCITY_EPS:
        return "converging"
    if velocity > _VELOCITY_EPS:
        return "diverging"
    return "stable"


def _serialize_affected(affected) -> list[dict[str, Any]]:
    return [
        {
            "id": a.symbol_id,
            "name": a.name,
            "distance": a.distance,
            "reason": a.reason,
        }
        for a in affected
    ]


def _serialize_drift_row(
    snap: DriftSnapshot,
    conflict: dict[str, Any] | None = None,
    history: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "branch": snap.branch,
        "magnitude": snap.magnitude.magnitude,
        "tip_distance": snap.magnitude.tip_distance,
        "trajectory_integral": snap.magnitude.trajectory_integral,
        "velocity": snap.velocity,
        "convergence_score": snap.convergence,
        "convergence_label": _convergence_label(snap.velocity),
        "affected": _serialize_affected(snap.affected),
        "history": [
            {"timestamp": t, "magnitude": m} for t, m in (history or [])
        ],
    }
    if conflict is not None:
        row["conflict_probability"] = conflict
    return row


def _serialize_alert(alert: DriftAlert) -> dict[str, Any]:
    return {
        "branch": alert.branch,
        "severity": alert.severity,
        "message": alert.message,
        "magnitude": alert.magnitude,
        "affected": _serialize_affected(alert.affected),
    }


def _conflict_for_snapshot(
    observer: GitObserver,
    parser: ASTParser,
    extractor: TransformExtractor,
    snap: DriftSnapshot,
    estimator: ConflictProbabilityEstimator,
) -> dict[str, Any]:
    branch_ops = extract_trajectory_operators(
        observer, parser, extractor, ref_branch=snap.reference_branch, head=snap.branch
    )
    ref_ops = extract_trajectory_operators(
        observer, parser, extractor, ref_branch=snap.branch, head=snap.reference_branch
    )
    shared = sorted({op.file for op in branch_ops} & {op.file for op in ref_ops})
    result = estimator.estimate(
        branch_ops, ref_ops, shared, snap.magnitude.magnitude
    )
    return {
        "score": result.score,
        "reasons": list(result.reasons),
        "heuristic": "flat",
    }


def _serialize_op(op):
    base = {
        "type": op.operator.value,
        "file": str(op.file)
    }
    if op.operator.value == "rename_function" or op.operator.value == "rename_class":
        base["name"] = f"{getattr(op, 'from_name', '')} -> {getattr(op, 'to_name', '')}"
        base["symbol_id"] = getattr(op, "symbol_id", "")
    else:
        base["name"] = getattr(op, "name", "")
        base["symbol_id"] = getattr(op, "symbol_id", "")  # dsa:ignore
        if hasattr(op, "changed_blocks"):
            base["changed_block_count"] = len(op.changed_blocks)
    return base


def _get_uncommitted_ops(observer, parser, extractor, repo_path):
    changes = observer.get_working_tree_changes()
    ops = []

    for f in changes.get("modified", []):
        if not f.endswith(SOURCE_EXTENSIONS):
            continue
        head_content = observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
        if head_content is None:
            continue
        try:
            with open(os.path.join(repo_path, f), encoding="utf-8", errors="ignore") as current_f:
                current_content = current_f.read()  # dsa:ignore
        except OSError:
            continue
        old_syms = parser.parse_file(f, head_content)  # dsa:ignore
        new_syms = parser.parse_file(f, current_content)  # dsa:ignore
        ops.extend(extractor.extract_operators(f, old_syms, new_syms))

    for f in changes.get("added", []):
        if not f.endswith(SOURCE_EXTENSIONS):
            continue
        try:
            with open(os.path.join(repo_path, f), encoding="utf-8", errors="ignore") as current_f:
                current_content = current_f.read()  # dsa:ignore
        except OSError:
            continue
        new_syms = parser.parse_file(f, current_content)  # dsa:ignore
        ops.extend(extractor.extract_operators(f, [], new_syms))

    for f in changes.get("deleted", []):
        if not f.endswith(SOURCE_EXTENSIONS):
            continue
        head_content = observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
        if not head_content:
            continue
        old_syms = parser.parse_file(f, head_content)  # dsa:ignore
        ops.extend(extractor.extract_operators(f, old_syms, []))

    return ops


def get_status(repo_path: str, ref: str | None = None) -> dict[str, Any]:
    observer = GitObserver(repo_path)
    if not ref:
        ref = "main"

    if not observer.is_valid() or not observer.repo:
        return _wrap_err("INVALID_REPO", "Not a valid git repo", "Path does not contain a git database", "Check path")

    try:
        remote = observer.get_remote_sync_status(ref)
        if remote["label"] == "N/A" and ref != "main" and ref not in observer.repo.heads:
             # branch might not exist locally or remotely
             raise ValueError("Branch not found")
    except Exception:
        return _wrap_err("INVALID_REF", f"Branch '{ref}' missing", "Branch does not exist", f"Check {ref}")

    parser = ASTParser()
    extractor = TransformExtractor()

    try:
         traj_ops = extract_trajectory_operators(observer, parser, extractor, ref_branch=ref, head="HEAD")
    except Exception:
         return _wrap_err("INVALID_REF", f"Invalid trajectory for {ref}", "Branch not found", "Check ref")

    wt_ops = _get_uncommitted_ops(observer, parser, extractor, repo_path)

    return _wrap_ok({
        "active_branch": observer.get_active_branch() or "DETACHED",
        "reference": ref,
        "remote_sync": remote,
        "committed_operators": [_serialize_op(o) for o in traj_ops],  # dsa:ignore
        "uncommitted_operators": [_serialize_op(o) for o in wt_ops]  # dsa:ignore
    })


def get_graph(repo_path: str, ref: str | None = None) -> dict[str, Any]:
    try:
        g = build_code_graph_from_repo(repo_path)
    except Exception:
        return _wrap_ok({"summary": {"total_nodes": 0, "total_edges": 0}, "nodes": [], "edges": []})

    nodes = []
    edges = []

    for n, data in g.g.nodes(data=True):
        nodes.append({
            "id": n,
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "location": data.get("chart_location", "")
        })
    for u, v, data in g.g.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relationship": data.get("relationship", "imports")
        })

    return _wrap_ok({
        "summary": g.get_summary(),
        "nodes": nodes,
        "edges": edges
    })


def get_symbols(repo_path: str, ref: str | None = None) -> dict[str, Any]:
    try:
        g = build_code_graph_from_repo(repo_path)
    except Exception:
        return _wrap_ok({"symbols": []})

    symbols = []
    for n, data in g.g.nodes(data=True):
        symbols.append({
            "id": n,
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "location": data.get("chart_location", "")
        })
    return _wrap_ok({"symbols": symbols})


def get_drift(repo_path: str, ref: str | None = None, branch: str | None = None) -> dict[str, Any]:
    if not ref:
        ref = "main"

    observer = GitObserver(repo_path)
    if not observer.is_valid():
        return _wrap_err("INVALID_REPO", "repo invalid", "repo invalid", "fix")

    parser = ASTParser()
    extractor = TransformExtractor()
    engine = DriftEngine(
        observer=observer,
        parser=parser,
        extractor=extractor,
        history=SnapshotHistory(default_history_path(repo_path))
    )
    conflict_est = ConflictProbabilityEstimator()

    try:
        targets = [branch] if branch else [
            b for b in observer.list_local_branches() if b != ref
        ]
        res = []
        for b in targets:
            snap = engine.snapshot(b, ref)
            conflict = _conflict_for_snapshot(
                observer, parser, extractor, snap, conflict_est
            )
            history_pts = engine.history.recent(b, n=10) if engine.history else None
            res.append(_serialize_drift_row(snap, conflict, history=history_pts))
        return _wrap_ok({"reference": ref, "drift": res})
    except Exception:
        return _wrap_err("INVALID_REF", "ref invalid", "ref invalid", "fix")


def get_alerts(repo_path: str, ref: str | None = None) -> dict[str, Any]:
    if not ref:
        ref = "main"
    observer = GitObserver(repo_path)
    if not observer.is_valid():
        return _wrap_err("INVALID_REPO", "repo invalid", "repo invalid", "fix")

    parser = ASTParser()
    extractor = TransformExtractor()
    engine = DriftEngine(
        observer=observer,
        parser=parser,
        extractor=extractor,
        history=SnapshotHistory(default_history_path(repo_path))
    )
    alerts = DriftAlerts()

    res = []
    try:
        for b in observer.list_local_branches():
            if b == ref:
                continue
            snap = engine.snapshot(b, ref)
            alert = alerts.evaluate(snap)
            if alert:
                res.append(_serialize_alert(alert))
        return _wrap_ok(res)
    except Exception:
        return _wrap_err("INVALID_REF", "ref error", "ref error", "fix")


def get_log(repo_path: str, n: int = 20) -> dict[str, Any]:
    observer = GitObserver(repo_path)
    if not observer.is_valid() or not observer.repo:
        return _wrap_err("INVALID_REPO", "repo invalid", "repo invalid", "fix")

    n = min(n, 100) # conservative maximum
    try:
        commits = list(observer.repo.iter_commits("HEAD", max_count=n))
    except Exception:
        return _wrap_ok([])

    parser = ASTParser()
    extractor = TransformExtractor()

    res = []
    for commit in commits:
        sha = commit.hexsha
        parent = observer.get_parent_sha(sha)
        ops = []
        if parent:
            changes = observer.get_file_diffs_between_commits(parent, sha)
            for f in changes["modified"]:
                if f.endswith(SOURCE_EXTENSIONS):
                    oldc = observer.get_file_content_at_commit(parent, f)  # dsa:ignore
                    newc = observer.get_file_content_at_commit(sha, f)  # dsa:ignore
                    if oldc and newc:
                        ops.extend(extractor.extract_operators(f, parser.parse_file(f, oldc), parser.parse_file(f, newc), sha))  # dsa:ignore
            for f in changes["added"]:
                if f.endswith(SOURCE_EXTENSIONS):
                    newc = observer.get_file_content_at_commit(sha, f)  # dsa:ignore
                    if newc:
                        ops.extend(extractor.extract_operators(f, [], parser.parse_file(f, newc), sha))  # dsa:ignore
            for f in changes["deleted"]:
                if f.endswith(SOURCE_EXTENSIONS):
                    oldc = observer.get_file_content_at_commit(parent, f)  # dsa:ignore
                    if oldc:
                        ops.extend(extractor.extract_operators(f, parser.parse_file(f, oldc), [], sha))  # dsa:ignore

        res.append({
            "sha": sha,
            "timestamp": str(commit.authored_datetime),
            "operators": [_serialize_op(o) for o in ops]  # dsa:ignore
        })

    return _wrap_ok(res)


def get_similar(repo_path: str, symbol: str, k: int = 5) -> dict[str, Any]:
    try:
        res = find_similar_symbols(repo_path, symbol, min(k, 50))
        hits = []
        for sid, score, sym in res:
            hits.append({
                "id": sid,
                "score": score,
                "name": sym.name if sym else sid,
                "location": (sym.chart_location or "") if sym else ""
            })
        return _wrap_ok({
            "assistive": True,
            "hits": hits
        })
    except Exception as e:
        return _wrap_err("INDEX_ERROR", "search failed", str(e), "reindex via gdss reindex")


def get_embeddings_projection(
    repo_path: str,
    dims: int = 2,
    limit: int = 500,
) -> dict[str, Any]:
    """Assistive PCA projection of symbol embeddings for the embedding-space UI."""
    try:
        data = project_symbol_embeddings(repo_path, dims=dims, limit=limit)
        return _wrap_ok(data)
    except Exception as e:
        return _wrap_err(
            "INDEX_ERROR",
            "embedding projection failed",
            str(e),
            "reindex via gdss reindex",
        )


def _serialize_commutativity() -> list[dict[str, str]]:
    """Compact OperatorType×OperatorType table for the tensor UI."""
    return [
        {"a": a.value, "b": b.value, "class": cls.value}
        for (a, b), cls in commutativity_table().items()
    ]


def _serialize_tensor(tensor: ConflictTensor) -> dict[str, Any]:
    entries = [
        {
            "i": entry.i,
            "j": entry.j,
            "omega": entry.omega,
            "reasons": list(entry.reasons),
        }
        for entry in tensor.entries.values()
    ]
    return {
        "branches": list(tensor.branches),
        "entries": entries,
        "merge_risk": tensor.merge_risk,
    }


def get_tensor(repo_path: str, ref: str | None = None) -> dict[str, Any]:
    """Flat pairwise Omega matrix (same composition as `gdss tensor` CLI)."""
    if not ref:
        ref = "main"

    observer = GitObserver(repo_path)
    if not observer.is_valid() or not observer.repo:
        return _wrap_err(
            "INVALID_REPO",
            "Not a valid git repo",
            "Path does not contain a git database",
            "Check path",
        )

    local_branches = observer.list_local_branches()
    if ref not in local_branches:
        return _wrap_err(
            "INVALID_REF",
            f"Branch '{ref}' missing",
            "Branch does not exist",
            f"Check {ref}",
        )

    commutativity = _serialize_commutativity()
    single, only_branch = is_single_attractor_trajectory(observer, ref)
    if single:
        msg = (
            f"Single attractor trajectory ({only_branch or ref}). "
            "No other local branches for Omega tensor."
        )
        return _wrap_ok(
            {
                "reference": ref,
                "form": "flat",
                "branches": [only_branch or ref],
                "entries": [],
                "merge_risk": 0.0,
                "commutativity": commutativity,
                "message": msg,
            },
            warnings=[msg],
        )

    branches = [b for b in local_branches if b != ref]
    if not branches:
        msg = "No other local branch trajectories found."
        return _wrap_ok(
            {
                "reference": ref,
                "form": "flat",
                "branches": [ref],
                "entries": [],
                "merge_risk": 0.0,
                "commutativity": commutativity,
                "message": msg,
            },
            warnings=[msg],
        )

    parser = ASTParser()
    extractor = TransformExtractor()
    drift_engine = DriftEngine(
        observer=observer,
        parser=parser,
        extractor=extractor,
        history=SnapshotHistory(default_history_path(repo_path)),
    )

    all_branches = branches
    branch_ops: dict[str, list] = {}
    drift_magnitudes: dict[str, float] = {}

    try:
        for branch in all_branches:
            snap = drift_engine.snapshot(branch, ref)  # dsa:ignore
            drift_magnitudes[branch] = snap.magnitude.magnitude
            branch_ops[branch] = extract_trajectory_operators(
                observer,
                parser,
                extractor,
                ref_branch=ref,
                head=branch,
            )
        tensor = TensorEngine().compute(branch_ops, drift_magnitudes)
    except Exception:
        return _wrap_err(
            "INVALID_REF",
            "tensor computation failed",
            "Could not compute Omega for the given ref",
            f"Check ref '{ref}' and local branches",
        )

    payload = _serialize_tensor(tensor)
    return _wrap_ok(
        {
            "reference": ref,
            "form": "flat",
            "branches": payload["branches"],
            "entries": payload["entries"],
            "merge_risk": payload["merge_risk"],
            "commutativity": commutativity,
        }
    )


def get_branches(repo_path: str) -> dict[str, Any]:
    observer = GitObserver(repo_path)
    if not observer.is_valid():
        return _wrap_err("INVALID_REPO", "repo invalid", "repo invalid", "fix")
    branches = observer.list_local_branches()
    active = observer.get_active_branch()
    return _wrap_ok({
        "branches": branches,
        "active_branch": active,
        "repo": repo_path,
    })


def get_drift_history(
    repo_path: str,
    branch: str,
    n: int = 20,
) -> dict[str, Any]:
    if not branch:
        return _wrap_err(
            "INVALID_BRANCH",
            "branch is required",
            "SnapshotHistory is keyed by branch name",
            "Pass ?branch=NAME",
        )
    observer = GitObserver(repo_path)
    if not observer.is_valid():
        return _wrap_err("INVALID_REPO", "repo invalid", "repo invalid", "fix")
    n = min(max(n, 1), 100)
    history = SnapshotHistory(default_history_path(repo_path))
    rows = history.recent(branch, n=n)
    return _wrap_ok({
        "branch": branch,
        "history": [{"timestamp": t, "magnitude": m} for t, m in rows],
    })


def get_model_status() -> dict[str, Any]:
    from gdss.ai.model_manager import ModelManager
    try:
        mgr = ModelManager()
        return _wrap_ok(mgr.status())
    except Exception as e:
        return _wrap_err("MODEL_ERROR", "model status failed", str(e), "Check ollama")


def get_suggestions(
    repo_path: str,
    ref: str | None = None,
    format: str = "metadata",
    llm: bool = False,
    combos: int = 3,
    max_candidates: int = 50,
) -> dict[str, Any]:
    from gdss.ai.suggester import suggest
    if not ref:
        ref = "main"
    try:
        suggestions = suggest(
            repo_path=repo_path,
            reference_branch=ref,
            llm=llm,
            combos=combos,
            max_candidates=max_candidates
        )
        if format == "prompt" or format == "source":
            res = [s.to_local_source() for s in suggestions]
        else:
            res = [s.to_metadata() for s in suggestions]
        return _wrap_ok(res)
    except Exception as e:
        return _wrap_err("SUGGESTION_ERROR", "suggestion failed", str(e), "Check input")
