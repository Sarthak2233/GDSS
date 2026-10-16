from gdss.ai.patch_combinations import enumerate_combinations
from gdss.ai.prompt_builder import build_conflict_prompt, build_prompt
from gdss.ai.types import (
    ConflictTopology,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)


def _suggestion() -> Suggestion:
    topology = ConflictTopology("disjoint", "a.py::run", "rename_function", "delete_function", "interfere", "same symbol")
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
        anchor=SuggestionAnchor(
            "a.py", 2, 5, 1, 1, "feature/a", "content-digest", "symbol-digest"
        ),
        context=SuggestionContext(
            "main", "feature/a", 0.8, 1.1, "feature-op", "main-op"
        ),
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
        "feature/a": {"title": "PR #1: Feature A", "description": "Adds user login", "author": "alice"},
        "feature/b": {"title": "PR #2: Refactor B", "description": "Migrates to v2", "author": "bob"},
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

