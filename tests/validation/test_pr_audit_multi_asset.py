"""Tests for PR Collision Radar multi-asset domain classification and lockfile synchronization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from gdss.validation.pr_audit import (
    PRAuditContext,
    PRCollisionDetail,
    PRCollisionResult,
    _get_topology_badge,
    render_radar_markdown,
)
from gdss.validation.test_runner import synchronize_sandbox_lockfiles


def test_get_topology_badge_multi_asset():
    assert "🗄️ Split-Head Hazard" in _get_topology_badge("split_head")
    assert "📦 Manifest Divergence" in _get_topology_badge("manifest_divergence")
    assert "🔀 Union" in _get_topology_badge("union")
    assert "⚙️ Lexical Overlap" in _get_topology_badge("lexical_overlap")


def test_render_radar_markdown_migration_split_head():
    ctx = PRAuditContext(
        repo_owner="test-org",
        repo_name="test-repo",
        pr_number=101,
        base_ref="main",
        head_ref="feat/add-payments",
        head_sha="sha101",
    )
    col = PRCollisionDetail(
        colliding_pr=102,
        author="alice",
        branch="feat/add-users",
        target_file="alembic/versions/0023_payments.py",
        overlapping_symbol="migration_parent::0022_initial",
        risk=1.0,
        description="Database Migration Split-Head: concurrent migrations branching off identical parent revision '0022_initial'.",
        merge_order_recommendation="Split-Head Hazard: Rebase PR #101 onto PR #102 and update child down_revision.",
        topology_kind="split_head",
    )
    res = PRCollisionResult(
        current_pr=101,
        has_collisions=True,
        max_risk=1.0,
        collisions=[col],
        audited_prs_count=1,
    )

    markdown = render_radar_markdown(ctx, res)
    assert "🗄️ Split-Head Hazard" in markdown
    assert "🚨" in markdown
    assert "1.00 (Critical)" in markdown
    assert "alembic/versions/0023_payments.py" in markdown
    assert "migration_parent::0022_initial" in markdown
    assert "Rebase PR #101 onto PR #102" in markdown


def test_render_radar_markdown_manifest_divergence():
    ctx = PRAuditContext(
        repo_owner="test-org",
        repo_name="test-repo",
        pr_number=201,
        base_ref="main",
        head_ref="feat/upgrade-deps",
        head_sha="sha201",
    )
    col = PRCollisionDetail(
        colliding_pr=202,
        author="bob",
        branch="feat/add-graphql",
        target_file="package.json",
        overlapping_symbol="manifest::package.json::dependencies.graphql",
        risk=0.7,
        description="Package Manifest Divergence: concurrent dependency changes in 'package.json'.",
        merge_order_recommendation="Merge PR #202 first, then rebase PR #201 and regenerate lockfile.",
        topology_kind="manifest_divergence",
    )
    res = PRCollisionResult(
        current_pr=201,
        has_collisions=True,
        max_risk=0.7,
        collisions=[col],
        audited_prs_count=1,
    )

    markdown = render_radar_markdown(ctx, res)
    assert "📦 Manifest Divergence" in markdown
    assert "package.json" in markdown
    assert "manifest::package.json::dependencies.graphql" in markdown
    assert "regenerate lockfile" in markdown


def test_synchronize_sandbox_lockfiles_no_manifests(tmp_path: Path):
    result = synchronize_sandbox_lockfiles(tmp_path, ["src/utils.py"])
    assert result is False


def test_synchronize_sandbox_lockfiles_npm(tmp_path: Path):
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{"name": "test"}', encoding="utf-8")
    lock_file = tmp_path / "package-lock.json"
    lock_file.write_text('{"lockfileVersion": 3}', encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = synchronize_sandbox_lockfiles(tmp_path, ["package.json"])
        assert res is True
        assert mock_run.called
        cmd_called = mock_run.call_args[0][0]
        assert "npm install --package-lock-only" in cmd_called


def test_synchronize_sandbox_lockfiles_pnpm(tmp_path: Path):
    pkg_file = tmp_path / "package.json"
    pkg_file.write_text('{"name": "test"}', encoding="utf-8")
    lock_file = tmp_path / "pnpm-lock.yaml"
    lock_file.write_text("lockfileVersion: '6.0'", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = synchronize_sandbox_lockfiles(tmp_path, ["package.json"])
        assert res is True
        assert mock_run.called
        cmd_called = mock_run.call_args[0][0]
        assert "pnpm install --lockfile-only" in cmd_called


def test_synchronize_sandbox_lockfiles_cargo(tmp_path: Path):
    cargo_toml = tmp_path / "Cargo.toml"
    cargo_toml.write_text('[package]\nname = "test"', encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = synchronize_sandbox_lockfiles(tmp_path, ["Cargo.toml"])
        assert res is True
        assert mock_run.called
        cmd_called = mock_run.call_args[0][0]
        assert "cargo generate-lockfile" in cmd_called
