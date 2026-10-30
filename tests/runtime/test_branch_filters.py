"""Tests for branch selection, filtering, and hierarchy resolution."""

from __future__ import annotations

import tempfile
from pathlib import Path

from gdss.runtime.hierarchy import (
    HierarchyManager,
    filter_branches,
    matches_any_pattern,
)
from gdss.storage.db import RuntimeDB


def test_matches_any_pattern():
    patterns = ["feature/*", "bugfix/*", "hotfix-v1"]
    assert matches_any_pattern("feature/login", patterns) is True
    assert matches_any_pattern("bugfix/123", patterns) is True
    assert matches_any_pattern("hotfix-v1", patterns) is True
    assert matches_any_pattern("spike/ml-experiment", patterns) is False
    assert matches_any_pattern("main", patterns) is False
    assert matches_any_pattern("feature/login", []) is False


def test_filter_branches_reference_exclusion():
    branches = ["main", "feature/a", "feature/b", "staging"]
    filtered = filter_branches(branches, reference_branch="main")
    assert filtered == ["feature/a", "feature/b", "staging"]


def test_filter_branches_include_patterns():
    branches = ["main", "feature/auth", "feature/ui", "spike/proto", "bugfix/12"]
    filtered = filter_branches(
        branches,
        include=["feature/*", "bugfix/*"],
        reference_branch="main",
    )
    assert filtered == ["feature/auth", "feature/ui", "bugfix/12"]


def test_filter_branches_exclude_patterns():
    branches = ["main", "feature/auth", "spike/proto", "wip-test", "bugfix/12"]
    filtered = filter_branches(
        branches,
        exclude=["spike/*", "wip-*"],
        reference_branch="main",
    )
    assert filtered == ["feature/auth", "bugfix/12"]


def test_filter_branches_include_and_exclude_combined():
    branches = ["feature/auth", "feature/spike-fast", "feature/ui", "release/v1"]
    filtered = filter_branches(
        branches,
        include=["feature/*"],
        exclude=["*spike*"],
        reference_branch="main",
    )
    assert filtered == ["feature/auth", "feature/ui"]


def test_filter_branches_deterministic_ordering():
    branches = ["z-feature", "a-feature", "m-feature"]
    filtered = filter_branches(branches, include=["*-feature"])
    assert filtered == ["z-feature", "a-feature", "m-feature"]


def test_hierarchy_manager_branch_filters():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "runtime.db")
        db = RuntimeDB(db_path)
        mgr = HierarchyManager(db)
        repo_id = 1

        # Initial state: empty filters
        inc, exc = mgr.get_branch_filters(repo_id)
        assert inc == []
        assert exc == []

        # Set include and exclude
        mgr.set_branch_filters(
            repo_id,
            include=["feature/*", "bugfix/*"],
            exclude=["spike/*"],
        )
        inc, exc = mgr.get_branch_filters(repo_id)
        assert inc == ["feature/*", "bugfix/*"]
        assert exc == ["spike/*"]

        # Update only exclude
        mgr.set_branch_filters(repo_id, exclude=["temp/*", "wip/*"])
        inc, exc = mgr.get_branch_filters(repo_id)
        assert inc == ["feature/*", "bugfix/*"]
        assert exc == ["temp/*", "wip/*"]


def test_hierarchy_manager_priority_chain_formats():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "runtime.db")
        db = RuntimeDB(db_path)
        mgr = HierarchyManager(db)
        repo_id = 42

        # Default trajectory
        assert mgr.resolve_priority_chain(repo_id) == ["main"]

        # Dict format
        mgr.set_config(
            repo_id,
            {"hierarchy": {"development": "dev", "staging": "stage", "production": "prod"}},
        )
        assert mgr.resolve_priority_chain(repo_id) == ["dev", "stage", "prod"]

        # List format in hierarchy key
        mgr.set_config(repo_id, {"hierarchy": ["develop", "staging", "main"]})
        assert mgr.resolve_priority_chain(repo_id) == ["develop", "staging", "main"]

        # priority_chain key
        mgr.set_config(repo_id, {"priority_chain": ["alpha", "beta", "stable"]})
        assert mgr.resolve_priority_chain(repo_id) == ["alpha", "beta", "stable"]


def test_build_analysis_context_branch_filtering(tmp_path):
    import git

    from gdss.drift.context import build_analysis_context

    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    Path(tmp_path, "calc.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    base = repo.index.commit("base")
    ref = repo.active_branch.name

    b_a = repo.create_head("feature-a", base)
    b_a.checkout()
    Path(tmp_path, "calc.py").write_text("def add(a, b): return a + b + 1\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    repo.index.commit("feat a")

    b_b = repo.create_head("feature-b", base)
    b_b.checkout()
    Path(tmp_path, "calc.py").write_text("def add(a, b): return a + b + 2\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    repo.index.commit("feat b")

    b_s = repo.create_head("spike-exp", base)
    b_s.checkout()
    Path(tmp_path, "calc.py").write_text("def add(a, b): return 0\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    repo.index.commit("spike")

    # Filter with explicit include: only feature-a
    ctx_inc = build_analysis_context(str(tmp_path), ref, branches=["feature-a"])
    assert ctx_inc.branches == ("feature-a",)

    # Filter with exclude: exclude spike-exp
    ctx_exc = build_analysis_context(str(tmp_path), ref, exclude_branches=["spike*"])
    assert ctx_exc.branches == ("feature-a", "feature-b")

    # Filter via .gdss.yml
    Path(tmp_path, ".gdss.yml").write_text(
        "hierarchy:\n  exclude:\n    - 'spike*'\n    - 'feature-b'\n",
        encoding="utf-8",
    )
    ctx_yml = build_analysis_context(str(tmp_path), ref)
    assert ctx_yml.branches == ("feature-a",)
