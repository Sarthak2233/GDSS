"""Drift engine: combined tip proxy + trajectory integral I(B_i)."""

from __future__ import annotations

import time

import numpy as np

from gdss.core.ast_parser import SOURCE_EXTENSIONS, ASTParser
from gdss.core.trajectory import extract_trajectory_operators
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import CodeSymbol, OperatorType, SemanticOperator
from gdss.drift.history import SnapshotHistory, default_history_path
from gdss.drift.types import AffectedSymbol, DriftMagnitude, DriftSnapshot
from gdss.embeddings.branch_vector import (
    aggregate_branch_tip,
    embed_symbols,
    embedding_distance_to_attractor,
)
from gdss.embeddings.encoder import CodeEncoder, get_encoder
from gdss.embeddings.similarity import cosine_distance
from gdss.logger import get_logger
from gdss.watcher.git_observer import GitObserver

logger = get_logger("gdss.drift.engine")

_MODIFY_OPS = {
    OperatorType.MODIFY_FUNCTION,
    OperatorType.MODIFY_CLASS,
    OperatorType.MODIFY_VARIABLE,
    OperatorType.MODIFY_CONSTANT,
    OperatorType.RENAME_FUNCTION,
    OperatorType.RENAME_CLASS,
}

_COMMIT_SYMBOLS_CACHE: dict[str, list[CodeSymbol]] = {}
_TIP_VECTOR_CACHE: dict[tuple[str, str, str], np.ndarray] = {}


def clear_drift_cache() -> None:
    """Clear in-memory commit symbol and tip vector memoization."""
    _COMMIT_SYMBOLS_CACHE.clear()
    _TIP_VECTOR_CACHE.clear()


class DriftEngine:
    """Compute divergence magnitude between a branch and its attractor."""

    def __init__(
        self,
        observer: GitObserver,
        parser: ASTParser,
        extractor: TransformExtractor,
        encoder: CodeEncoder | None = None,
        alpha: float = 0.5,
        beta: float = 0.5,
        trajectory_ceiling: float = 2.0,
        history: SnapshotHistory | None = None,
        convergence_threshold: float = 1.0,
    ) -> None:
        self.observer = observer
        self.parser = parser
        self.extractor = extractor
        self.encoder = encoder or get_encoder()
        self.alpha = alpha
        self.beta = beta
        self.trajectory_ceiling = max(trajectory_ceiling, 1e-9)
        self.convergence_threshold = max(convergence_threshold, 1e-9)
        if history is not None:
            self.history = history
        else:
            repo = observer.repo_path if observer.is_valid() else "."
            self.history = SnapshotHistory(default_history_path(repo))

    def compute_magnitude(self, branch: str, reference_branch: str) -> DriftMagnitude:
        """Combined magnitude = alpha * d_tip + beta * normalized I_traj."""
        zero = DriftMagnitude(0.0, 0.0, 0.0, self.alpha, self.beta)
        if not self.observer.is_valid() or self.observer.repo is None:
            return zero

        try:
            branch_sha = self.observer.repo.commit(branch).hexsha
            ref_sha = self.observer.repo.commit(reference_branch).hexsha
        except Exception:
            return zero

        tip_distance = self._tip_distance(branch_sha, ref_sha, branch, reference_branch)
        raw_integral = self._trajectory_integral(branch, reference_branch, branch_sha)
        i_norm = min(raw_integral / self.trajectory_ceiling, 1.0)
        magnitude = self.alpha * tip_distance + self.beta * i_norm
        return DriftMagnitude(
            tip_distance=float(tip_distance),
            trajectory_integral=float(i_norm),
            magnitude=float(magnitude),
            alpha=self.alpha,
            beta=self.beta,
        )

    def snapshot(self, branch: str, reference_branch: str) -> DriftSnapshot:
        """Magnitude + affected symbols + velocity + convergence; records history."""
        magnitude = self.compute_magnitude(branch, reference_branch)
        affected = tuple(self.affected_symbols(branch, reference_branch))
        now = time.time()
        prior = self.history.recent(branch, n=1)
        velocity = 0.0
        if prior:
            t_old, mag_old = prior[-1]
            dt = now - t_old
            if dt > 1e-9:
                velocity = (magnitude.magnitude - mag_old) / dt
        convergence = self._convergence(magnitude.magnitude, velocity)
        snap = DriftSnapshot(
            branch=branch,
            reference_branch=reference_branch,
            timestamp=now,
            magnitude=magnitude,
            velocity=velocity,
            convergence=convergence,
            affected=affected,
        )
        self.history.record(snap)
        logger.info(
            "Drift snapshot: branch=%s ref=%s magnitude=%.3f velocity=%.3f convergence=%.3f affected_symbols=%d",
            branch,
            reference_branch,
            magnitude.magnitude,
            velocity,
            convergence,
            len(affected),
        )
        return snap

    def _convergence(self, magnitude: float, velocity: float) -> float:
        """s = clamp(1 - mag/threshold), adjusted by velocity sign."""
        base = 1.0 - (magnitude / self.convergence_threshold)
        base = max(0.0, min(1.0, base))
        if velocity > 0:
            base = max(0.0, base - min(0.25, velocity))
        elif velocity < 0:
            base = min(1.0, base + min(0.25, abs(velocity)))
        return float(base)

    def affected_symbols(self, branch: str, reference_branch: str) -> list[AffectedSymbol]:
        """Symbols modified on both trajectories, with per-symbol cosine distance."""
        branch_ops = extract_trajectory_operators(
            self.observer,
            self.parser,
            self.extractor,
            ref_branch=reference_branch,
            head=branch,
        )
        ref_ops = extract_trajectory_operators(
            self.observer,
            self.parser,
            self.extractor,
            ref_branch=branch,
            head=reference_branch,
        )
        branch_names = self._modified_name_map(branch_ops)
        ref_names = self._modified_name_map(ref_ops)
        shared = set(branch_names.keys()) & set(ref_names.keys())
        if not self.observer.repo:
            raise ValueError("Invalid repository")

        branch_emb = embed_symbols(
            self._symbols_at_commit(self.observer.repo.commit(branch).hexsha),
            self.encoder,
        )
        ref_emb = embed_symbols(
            self._symbols_at_commit(self.observer.repo.commit(reference_branch).hexsha),
            self.encoder,
        )

        # Match by name when symbol_id may differ across tips
        branch_by_name: dict[str, np.ndarray] = {}
        for sid, ev in branch_emb.items():
            # source_id may be path::name — take trailing name
            name = sid.split("::")[-1] if "::" in sid else sid
            branch_by_name[name] = ev.vector
        for sym_name in list(branch_names.keys()):
            if sym_name not in branch_by_name:
                for sid, ev in branch_emb.items():
                    if sym_name in sid or sid.endswith(sym_name):
                        branch_by_name[sym_name] = ev.vector
                        break

        ref_by_name: dict[str, np.ndarray] = {}
        for sid, ev in ref_emb.items():
            name = sid.split("::")[-1] if "::" in sid else sid
            ref_by_name[name] = ev.vector

        # Prefer intersection of modified names; if empty, use shared names present on both tips
        # from branch_ops that also appear in ref tip embeddings
        if not shared:
            shared = {n for n in branch_names if n in ref_by_name and n in branch_by_name}

        # For dual-modify fixture: both sides modify verify_token relative to merge base.
        # branch_ops has modifications on feature; ref_ops has modifications on attractor.
        # Intersection of modified target names should work.
        result: list[AffectedSymbol] = []
        for name in sorted(shared):
            bvec = branch_by_name.get(name)
            rvec = ref_by_name.get(name)
            if bvec is None or rvec is None:
                dist = 0.0
            else:
                dist = float(cosine_distance(bvec, rvec))
            sid = branch_names.get(name) or name
            result.append(
                AffectedSymbol(
                    symbol_id=sid,
                    name=name,
                    distance=dist,
                    reason="modified_in_both",
                )
            )
        return result

    def _tip_distance(
        self,
        branch_sha: str,
        ref_sha: str,
        branch: str,
        reference_branch: str,
    ) -> float:
        branch_syms = self._symbols_at_commit(branch_sha)
        ref_syms = self._symbols_at_commit(ref_sha)
        if not branch_syms and not ref_syms:
            return 0.0
        branch_emb = embed_symbols(branch_syms, self.encoder)
        ref_emb = embed_symbols(ref_syms, self.encoder)
        tip_b = aggregate_branch_tip(
            branch_emb.values(), branch=branch, reference_branch=reference_branch
        )
        tip_r = aggregate_branch_tip(
            ref_emb.values(), branch=reference_branch, reference_branch=reference_branch
        )
        if tip_b.dim == 0 or tip_r.dim == 0:
            return 0.0 if tip_b.dim == tip_r.dim else 1.0
        return embedding_distance_to_attractor(tip_b.vector, tip_r.vector)

    def _trajectory_integral(self, branch: str, reference_branch: str, branch_sha: str) -> float:
        """Discrete path length Σ ||phi(C_{c+1}) - phi(C_c)|| along merge_base..tip."""
        if self.observer.repo is None:
            return 0.0
        merge_base = self.observer.get_merge_base(branch, reference_branch)
        if not merge_base or merge_base == branch_sha:
            return 0.0

        try:
            # Oldest → newest along exclusive range merge_base..branch
            commits = list(
                self.observer.repo.iter_commits(f"{merge_base}..{branch_sha}", reverse=True)
            )
        except Exception:
            return 0.0

        if not commits:
            return 0.0

        # Include merge_base as the starting point
        shas = [merge_base] + [c.hexsha for c in commits]
        total = 0.0
        prev_vec: np.ndarray | None = None
        for sha in shas:
            tip = self._tip_vector_at(sha, label=branch)
            if tip is None or tip.size == 0:
                prev_vec = tip
                continue
            if prev_vec is not None and prev_vec.size == tip.size:
                total += float(np.linalg.norm(tip.astype(np.float64) - prev_vec.astype(np.float64)))
            prev_vec = tip
        return total

    def _tip_vector_at(self, commit_sha: str, label: str) -> np.ndarray | None:
        encoder_name = getattr(self.encoder, "name", "encoder")
        cache_key = (commit_sha, label, encoder_name)
        if cache_key in _TIP_VECTOR_CACHE:
            return _TIP_VECTOR_CACHE[cache_key]

        syms = self._symbols_at_commit(commit_sha)
        if not syms:
            vec = np.zeros(0, dtype=np.float32)
            _TIP_VECTOR_CACHE[cache_key] = vec
            return vec
        emb = embed_symbols(syms, self.encoder)
        tip = aggregate_branch_tip(emb.values(), branch=label)
        _TIP_VECTOR_CACHE[cache_key] = tip.vector
        return tip.vector

    def _symbols_at_commit(self, commit_sha: str) -> list[CodeSymbol]:
        if not commit_sha:
            return []
        if commit_sha in _COMMIT_SYMBOLS_CACHE:
            return _COMMIT_SYMBOLS_CACHE[commit_sha]

        if self.observer.repo is None:
            return []
        try:
            commit = self.observer.repo.commit(commit_sha)
        except Exception as exc:
            logger.debug("Failed to resolve commit %s: %s", commit_sha, exc)
            return []
        symbols: list[CodeSymbol] = []
        for blob in commit.tree.traverse():
            if getattr(blob, "type", None) != "blob":
                continue
            path = str(getattr(blob, "path", ""))
            if not path or not path.endswith(SOURCE_EXTENSIONS):
                continue
            content = self.observer.get_file_content_at_commit(commit_sha, path)  # dsa:ignore
            if content is None:
                continue
            try:
                file_syms = self.parser.parse_file(path, content)  # dsa:ignore
            except Exception as exc:
                logger.debug("Failed parsing %s at commit %s: %s", path, commit_sha, exc)
                continue
            for sym in file_syms:
                sym.ensure_identity(path)
                symbols.append(sym)
        _COMMIT_SYMBOLS_CACHE[commit_sha] = symbols
        return symbols

    @staticmethod
    def _modified_name_map(ops: list[SemanticOperator]) -> dict[str, str]:
        """Map symbol display name -> symbol_id for modify/rename operators."""
        out: dict[str, str] = {}
        for op in ops:
            if op.operator not in _MODIFY_OPS:
                continue
            name = op.get_target_name()
            if not name:
                continue
            sid = op.symbol_id or op.to_symbol_id or op.from_symbol_id or name
            out[name] = sid
        return out
