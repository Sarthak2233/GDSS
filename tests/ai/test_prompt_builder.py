from gdss.ai.patch_combinations import enumerate_combinations
from gdss.ai.prompt_builder import build_conflict_prompt, build_prompt
from gdss.ai.types import (
    ConflictTopology,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)


def _suggestion() -> Suggestion:
    topology = ConflictTopology(
        "disjoint", "a.py::run", "rename_function", "delete_function", "interfere", "same symbol"
    )
    return Suggestion(
        "conflict",
        "a.py",
        2,
        5,
        "a.py::run",
        "rename_function",
        "review",
        "conflict",
        ("operators interfere",),
        0.8,
        topology=topology,
        patch_combinations=enumerate_combinations(topology),
        anchor=SuggestionAnchor("a.py", 2, 5, 1, 1, "feature/a", "content-digest", "symbol-digest"),
        context=SuggestionContext("main", "feature/a", 0.8, 1.1, "feature-op", "main-op"),
    )


def test_prompts_include_topology_and_do_not_apply_instruction():
    suggestion = _suggestion()
    prompt = build_prompt([suggestion], "repo", "main")
    conflict_prompt = build_conflict_prompt(suggestion, "def run():\n    pass\n", "repo", "main")
    assert "DO NOT apply" in prompt
    assert "disjoint" in prompt
    assert "keep i" in prompt
    assert "DO NOT apply" in conflict_prompt
    assert "def run" in conflict_prompt
    assert "feature/a" in conflict_prompt
    assert "Pairwise omega: 0.80" in conflict_prompt
    assert "Merge risk: 1.10" in conflict_prompt
    assert "same symbol" in conflict_prompt
    assert "UNTRUSTED SOURCE CONTENT" in conflict_prompt


def test_conflict_prompt_injects_developer_intent_and_commits():
    suggestion = _suggestion()
    branch_commits = {
        "feature/a": [{"sha": "1a2b3c4d", "summary": "Add feature A", "author": "alice"}],
        "feature/b": [{"sha": "5e6f7a8b", "summary": "Refactor B", "author": "bob"}],
    }
    branch_intents = {
        "feature/a": {
            "title": "PR #1: Feature A",
            "description": "Adds user login",
            "author": "alice",
        },
        "feature/b": {
            "title": "PR #2: Refactor B",
            "description": "Migrates to v2",
            "author": "bob",
        },
    }

    prompt = build_conflict_prompt(
        suggestion,
        "def run():\n    pass\n",
        "repo",
        "main",
        branch_commits=branch_commits,
        branch_intents=branch_intents,
        other_branch="feature/b",
    )

    assert "--- DEVELOPER INTENT & COMMIT HISTORY ---" in prompt
    assert "Branch A: feature/a" in prompt
    assert "Intent: PR #1: Feature A" in prompt
    assert "Description: Adds user login" in prompt
    assert "1a2b3c4d: Add feature A (alice)" in prompt

    assert "Branch B: feature/b" in prompt
    assert "Intent: PR #2: Refactor B" in prompt
    assert "Description: Migrates to v2" in prompt
    assert "5e6f7a8b: Refactor B (bob)" in prompt


def test_build_refinement_prompt():
    from gdss.ai.prompt_builder import build_refinement_prompt

    suggestion = _suggestion()
    prompt = build_refinement_prompt(
        suggestion,
        strategy_label="keep i",
        previous_patch="def run():\n    return syntax_error(\n",
        validation_error="SyntaxError: unexpected EOF while parsing at line 2",
        repo="repo",
        ref="main",
    )

    assert "VALIDATION FAILURE TRACE" in prompt
    assert "SyntaxError: unexpected EOF while parsing at line 2" in prompt
    assert "PREVIOUS ATTEMPTED PATCH" in prompt
    assert "def run():\n    return syntax_error(" in prompt
    assert "Fix the syntax, type, or test errors reported above" in prompt
    assert "strategy `keep i`" in prompt


def test_conflict_prompt_with_3way_semantic_context():
    from gdss.ai.context_builder import SemanticCollisionContext

    suggestion = _suggestion()
    collision_ctx = SemanticCollisionContext(
        file_path="a.py",
        symbol_name="run",
        language="python",
        base_branch="main",
        base_code="def run():\n    return 1\n",
        base_line_range=(2, 4),
        branch_a_name="feature/a",
        branch_a_code="def run(mode='fast'):\n    return 1\n",
        branch_a_line_range=(2, 5),
        branch_b_name="feature/b",
        branch_b_code="def run(verbose=True):\n    return 1\n",
        branch_b_line_range=(2, 5),
        impacted_callers=("main.py: caller_one", "worker.py: caller_two"),
    )

    prompt = build_conflict_prompt(
        suggestion,
        repo="my-org/my-repo",
        ref="main",
        collision_context=collision_ctx,
    )

    assert "Principal Software Integration Engineer" in prompt
    assert "BASE CANONICAL DEFINITION (main: lines 2-4)" in prompt
    assert "def run():\n    return 1" in prompt
    assert "INCOMING BRANCH A (feature/a: lines (2, 5))" in prompt
    assert "mode='fast'" in prompt
    assert "CONCURRENT BRANCH B (feature/b: lines (2, 5))" in prompt
    assert "verbose=True" in prompt
    assert "IMPACTED CALLERS & BLAST RADIUS" in prompt
    assert "main.py: caller_one" in prompt
    assert "worker.py: caller_two" in prompt


def test_conflict_prompt_topology_directives():
    from gdss.ai.types import ConflictTopology

    suggestion = _suggestion()
    # Test signature divergence
    top_sig = ConflictTopology(
        "union",
        "a.py::run",
        "modify_function",
        "modify_function",
        "interfere",
        "signature divergence",
    )
    sug_sig = Suggestion(
        suggestion.kind,
        suggestion.file_path,
        suggestion.line_start,
        suggestion.line_end,
        suggestion.symbol_id,
        suggestion.operator,
        suggestion.action,
        rationale="signature_divergence",
        reason=suggestion.reason,
        confidence=0.9,
        topology=top_sig,
        anchor=suggestion.anchor,
        context=suggestion.context,
    )

    prompt = build_conflict_prompt(sug_sig, "code", "repo", "main")
    assert "OPERATIONAL RECONCILIATION DIRECTIVE" in prompt
    assert "backward-compatible union" in prompt or "parameters" in prompt


def test_conflict_prompt_output_format_modes():
    suggestion = _suggestion()

    prompt_diff = build_conflict_prompt(
        suggestion,
        "code",
        "repo",
        "main",
        output_format="unified_diff",
    )
    assert "--- a/a.py" in prompt_diff
    assert "+++ b/a.py" in prompt_diff
    assert "DO NOT apply or run anything" in prompt_diff

    prompt_block = build_conflict_prompt(
        suggestion,
        "code",
        "repo",
        "main",
        output_format="replacement_block",
    )
    assert "Output ONLY the replacement code block enclosed in markdown code fences" in prompt_block
    assert "```python" in prompt_block


def test_build_tool_aware_prompt():
    from gdss.ai.prompt_builder import build_tool_aware_prompt

    suggestion = _suggestion()
    prompt = build_tool_aware_prompt(suggestion, "code", "repo", "main")
    assert "AVAILABLE DETERMINISTIC GDSS TOOLS" in prompt
    assert "gdss_find_collisions" in prompt
    assert "gdss_inspect_symbol_impact" in prompt
    assert "gdss_validate_patch" in prompt
    assert "gdss_sandbox_validate_patch" in prompt
