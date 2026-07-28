"""Service layer for gdss API."""
import os
from typing import Dict, Any, List

from gdss.watcher.git_observer import GitObserver
from gdss.core.ast_parser import ASTParser, SOURCE_EXTENSIONS
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.trajectory import extract_trajectory_operators
from gdss.graph.graph_builder import build_code_graph_from_repo
from gdss.drift.engine import DriftEngine
from gdss.drift.history import SnapshotHistory, default_history_path
from gdss.drift.alerts import DriftAlerts
from gdss.embeddings.service import find_similar_symbols


def _wrap_ok(data: Any) -> Dict[str, Any]:
    return {
        "status": "ok",
        "data": data,
        "warnings": []
    }

def _wrap_err(code: str, what: str, why: str, fix: str) -> Dict[str, Any]:
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
        if not f.endswith(SOURCE_EXTENSIONS): continue
        head_content = observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
        if head_content is None: continue
        try:
            with open(os.path.join(repo_path, f), encoding="utf-8", errors="ignore") as current_f:
                current_content = current_f.read()  # dsa:ignore
        except OSError:
            continue
        old_syms = parser.parse_file(f, head_content)  # dsa:ignore
        new_syms = parser.parse_file(f, current_content)  # dsa:ignore
        ops.extend(extractor.extract_operators(f, old_syms, new_syms))

    for f in changes.get("added", []):
        if not f.endswith(SOURCE_EXTENSIONS): continue
        try:
            with open(os.path.join(repo_path, f), encoding="utf-8", errors="ignore") as current_f:
                current_content = current_f.read()  # dsa:ignore
        except OSError:
            continue
        new_syms = parser.parse_file(f, current_content)  # dsa:ignore
        ops.extend(extractor.extract_operators(f, [], new_syms))

    for f in changes.get("deleted", []):
        if not f.endswith(SOURCE_EXTENSIONS): continue
        head_content = observer.get_file_content_at_commit("HEAD", f)  # dsa:ignore
        if not head_content: continue
        old_syms = parser.parse_file(f, head_content)  # dsa:ignore
        ops.extend(extractor.extract_operators(f, old_syms, []))
        
    return ops

def get_status(repo_path: str, ref: str | None = None) -> Dict[str, Any]:
    observer = GitObserver(repo_path)
    if not ref:
        ref = "main"
        
    if not observer.is_valid():
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

def get_graph(repo_path: str, ref: str | None = None) -> Dict[str, Any]:
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
            "relationship": data.get("relationship", "")
        })
        
    return _wrap_ok({
        "summary": g.get_summary(),
        "nodes": nodes,
        "edges": edges
    })

def get_drift(repo_path: str, ref: str | None = None, branch: str | None = None) -> Dict[str, Any]:
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
    
    try:
        if branch:
            snap = engine.snapshot(branch, ref)
            res = [{
                "branch": branch,
                "magnitude": snap.magnitude.magnitude,
                "velocity": snap.velocity,
                "convergence": snap.convergence,
                "affected": [{"id": a.symbol_id, "name": a.name} for a in snap.affected]
            }]
        else:
            res = []
            for b in observer.list_local_branches():
                if b == ref: continue
                snap = engine.snapshot(b, ref)
                res.append({
                    "branch": b,
                    "magnitude": snap.magnitude.magnitude,
                    "velocity": snap.velocity,
                    "convergence": snap.convergence,
                    "affected": [{"id": a.symbol_id, "name": a.name} for a in snap.affected]
                })
        return _wrap_ok({"reference": ref, "drift": res})
    except Exception:
        return _wrap_err("INVALID_REF", "ref invalid", "ref invalid", "fix")

def get_alerts(repo_path: str, ref: str | None = None) -> Dict[str, Any]:
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
            if b == ref: continue
            snap = engine.snapshot(b, ref)
            alert = alerts.evaluate(snap)
            if alert:
                res.append({
                    "branch": b,
                    "severity": alert,
                    "message": f"Alert severity {alert}",  # Omit source string
                    "magnitude": snap.magnitude.magnitude,
                    "affected": [{"id": a.symbol_id, "name": a.name} for a in snap.affected]
                })
        return _wrap_ok(res)
    except Exception:
        return _wrap_err("INVALID_REF", "ref error", "ref error", "fix")

def get_log(repo_path: str, n: int = 20) -> Dict[str, Any]:
    observer = GitObserver(repo_path)
    if not observer.is_valid():
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

def get_similar(repo_path: str, symbol: str, k: int = 5) -> Dict[str, Any]:
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
