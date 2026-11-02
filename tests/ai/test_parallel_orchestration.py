"""Unit tests for parallel conflict drafting and local sub-loop refinement."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from gdss.ai.orchestration import (
    ConvergenceState,
    draft_step,
)
from gdss.ai.types import (
    ConflictTopology,
    PatchCombination,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)


def _make_dummy_suggestion(file_path: str, sug_id: str) -> Suggestion:
    anchor = SuggestionAnchor(
        file_path=file_path,
        line_start=1,
        line_end=5,
    )
    topology = ConflictTopology(
        kind="intersection",
        symbol_id=f"{file_path}::func",
        operator_i="modify_function",
        operator_j="modify_function",
        commutativity="interfere",
        justification="Overlapping modify",
    )
    combo = PatchCombination(
        label="reconcile",
        strategy="compose",
        patch_text="",
        validated=False,
        validation_status="draft",
    )
    return Suggestion(
        kind="modify_function",
        file_path=file_path,
        line_start=1,
        line_end=5,
        symbol_id=f"{file_path}::func",
        operator="modify_function",
        action="reconcile",
        rationale="Overlapping modify",
        reason=("Same file",),
        confidence=0.9,
        rank=1,
        topology=topology,
        patch_combinations=(combo,),
        anchor=anchor,
        suggestion_id=sug_id,
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature-a",
            omega=0.8,
            merge_risk=0.5,
            operator_i_id="op1",
            operator_j_id="op2",
            other_branch="feature-b",
        ),
    )


class SlowMockProvider:
    """Mock provider with simulated latency to verify parallelism."""

    def __init__(self, delay: float = 0.15) -> None:
        self.delay = delay
        self.model = "mock-parallel"
        self.call_count = 0

    def complete(self, prompt: str, **kwargs) -> str:
        self.call_count += 1
        time.sleep(self.delay)
        return (
            "--- a/file\n+++ b/file\n@@ -1,3 +1,3 @@\n def func():\n-    pass\n+    return 42\n"
        )


def test_parallel_draft_speedup(tmp_path: Path):
    # 3 suggestions on 3 disjoint files
    s1 = _make_dummy_suggestion("services/a.py", "sug_1")
    s2 = _make_dummy_suggestion("services/b.py", "sug_2")
    s3 = _make_dummy_suggestion("services/c.py", "sug_3")

    mock_prov = SlowMockProvider(delay=0.15)

    state = ConvergenceState(
        repo_path=str(tmp_path),
        llm=True,
        validate=False,
        provider=mock_prov,
        suggestions=[s1, s2, s3],
        concurrency_limit=3,
        condensation_mode="lossless",
    )

    t0 = time.perf_counter()
    res_state = draft_step(state)
    elapsed = time.perf_counter() - t0

    assert res_state.checkpoint == "drafted"
    assert len(res_state.suggestions) == 3
    # 3 calls with 0.15s each running in parallel should take ~0.15 - 0.30s, NOT 0.45s+
    assert elapsed < 0.38, f"Expected parallel speedup (<0.38s), but took {elapsed:.3f}s"


def test_local_sub_loop_self_correction(tmp_path: Path):
    from gdss.ai.suggester import _draft_combinations

    # Provider that fails on first call (returns syntax broken), then returns clean diff on retry
    class SelfCorrectingProvider:
        def __init__(self):
            self.model = "test-model"
            self.attempts = 0

        def complete(self, prompt: str, **kwargs) -> str:
            self.attempts += 1
            if self.attempts == 1:
                return "BROKEN SYNTAX NOT A DIFF"
            return (
                "--- a/file.py\n+++ b/file.py\n@@ -1,2 +1,2 @@\n-def func(): pass\n+def func(): return 10\n"
            )

    prov = SelfCorrectingProvider()
    mock_ctx = MagicMock()
    mock_ctx.repo_path = str(tmp_path)
    mock_ctx.reference_branch = "main"
    mock_ctx.branch_commits = {}
    mock_ctx.branch_intents = {}
    mock_ctx.branch_operators = {}
    mock_ctx.observer.get_file_content_at_commit.return_value = "def func(): pass\n"

    sug = _make_dummy_suggestion("file.py", "sug_local_1")
    drafted = _draft_combinations(mock_ctx, sug, prov, max_local_refinements=2)

    assert prov.attempts >= 2
    assert drafted.patch_combinations[0].validated is True
    assert "return 10" in (drafted.patch_combinations[0].patch_text or "")
