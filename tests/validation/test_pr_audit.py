"""Tests for GDSS Layer 10: GitHub Actions PR Collision Radar (Phase D)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from gdss.validation.pr_audit import (
    STICKY_SIGNATURE,
    PRAuditContext,
    PRCollisionDetail,
    PRCollisionResult,
    fetch_concurrent_prs,
    load_radar_config,
    parse_github_env,
    post_or_update_sticky_comment,
    render_radar_markdown,
    run_pr_audit,
)


def test_parse_github_env_from_event_file(tmp_path: Path):
    event_payload = {
        "pull_request": {
            "number": 42,
            "base": {"ref": "main"},
            "head": {"ref": "feature-billing", "sha": "a1b2c3d4e5f67890"},
        }
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event_payload), encoding="utf-8")

    env = {
        "GITHUB_REPOSITORY": "octocat/hello-world",
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_TOKEN": "ghp_secret_token",
        "GITHUB_API_URL": "https://api.github.com",
    }
    with patch.dict("os.environ", env, clear=True):
        ctx = parse_github_env()
        assert ctx is not None
        assert ctx.repo_owner == "octocat"
        assert ctx.repo_name == "hello-world"
        assert ctx.pr_number == 42
        assert ctx.base_ref == "main"
        assert ctx.head_ref == "feature-billing"
        assert ctx.head_sha == "a1b2c3d4e5f67890"
        assert ctx.github_token == "ghp_secret_token"
        assert ctx.api_url == "https://api.github.com"


def test_parse_github_env_non_pr_returns_none(tmp_path: Path):
    event_payload = {"action": "push", "ref": "refs/heads/main"}
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event_payload), encoding="utf-8")

    env = {
        "GITHUB_REPOSITORY": "octocat/hello-world",
        "GITHUB_EVENT_PATH": str(event_file),
    }
    with patch.dict("os.environ", env, clear=True):
        ctx = parse_github_env()
        assert ctx is None


def test_fetch_concurrent_prs_filters_current_pr():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test",
    )

    mock_api_response = [
        {
            "number": 42,
            "title": "Add billing service",
            "user": {"login": "charlie"},
            "head": {"ref": "feature-billing", "sha": "sha42"},
            "base": {"ref": "main"},
        },
        {
            "number": 41,
            "title": "Refactor auth login",
            "user": {"login": "alice"},
            "head": {"ref": "feature-auth", "sha": "sha41"},
            "base": {"ref": "main"},
        },
        {
            "number": 39,
            "title": "Docs update",
            "user": {"login": "bob"},
            "head": {"ref": "docs-fix", "sha": "sha39"},
            "base": {"ref": "main"},
        },
    ]

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_api_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        concurrent = fetch_concurrent_prs(ctx)
        assert len(concurrent) == 2
        pr_numbers = [p["number"] for p in concurrent]
        assert 42 not in pr_numbers
        assert 41 in pr_numbers
        assert 39 in pr_numbers
        assert concurrent[0]["author"] == "alice"


def test_fetch_concurrent_prs_hierarchy_filtering():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=10,
        base_ref="main",
        head_ref="feature-core",
        head_sha="sha10",
        github_token="ghp_test",
    )

    mock_api_response = [
        {"number": 10, "head": {"ref": "feature-core"}, "base": {"ref": "main"}},
        {"number": 11, "head": {"ref": "feature/auth"}, "base": {"ref": "main"}},
        {"number": 12, "head": {"ref": "spike/proto"}, "base": {"ref": "main"}},
        {"number": 13, "head": {"ref": "hotfix/v1"}, "base": {"ref": "v1.0-release"}},
        {"number": 14, "head": {"ref": "bugfix/db"}, "base": {"ref": "main"}},
    ]

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_api_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        # Default: same_base_only=True excludes #13 (v1.0-release)
        res_default = fetch_concurrent_prs(ctx, same_base_only=True)
        nums = [p["number"] for p in res_default]
        assert nums == [11, 12, 14]

        # same_base_only=False includes #13
        res_all_bases = fetch_concurrent_prs(ctx, same_base_only=False)
        nums_all = [p["number"] for p in res_all_bases]
        assert nums_all == [11, 12, 13, 14]

        # Exclude pattern: excludes spike/*
        res_exclude = fetch_concurrent_prs(ctx, same_base_only=True, exclude=["spike/*"])
        nums_exc = [p["number"] for p in res_exclude]
        assert nums_exc == [11, 14]

        # Include pattern: only feature/*
        res_include = fetch_concurrent_prs(ctx, same_base_only=True, include=["feature/*"])
        nums_inc = [p["number"] for p in res_include]
        assert nums_inc == [11]


def test_load_radar_config_with_hierarchy(tmp_path):
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  fail_on_collision: true
  risk_threshold: 0.85
hierarchy:
  same_base_only: false
  include:
    - "feature/*"
    - "bugfix/*"
  exclude:
    - "spike/*"
  target_bases:
    - "main"
    - "develop"
""",
        encoding="utf-8",
    )

    cfg = load_radar_config(tmp_path)
    assert cfg["fail_on_collision"] is True
    assert cfg["risk_threshold"] == 0.85
    assert cfg["same_base_only"] is False
    assert cfg["include"] == ["feature/*", "bugfix/*"]
    assert cfg["exclude"] == ["spike/*"]
    assert cfg["target_bases"] == ["main", "develop"]


def test_render_radar_markdown_no_collisions():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test",
    )
    result = PRCollisionResult(
        current_pr=42,
        has_collisions=False,
        max_risk=0.0,
        collisions=[],
        audited_prs_count=3,
    )
    md = render_radar_markdown(ctx, result)
    assert STICKY_SIGNATURE in md
    assert "🛰️ GDSS PR Collision Radar" in md
    assert "✅ **All Clear**" in md
    assert "Audited 3 open pull request(s)" in md


def test_render_radar_markdown_with_collisions():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test",
    )
    col = PRCollisionDetail(
        colliding_pr=41,
        author="alice",
        branch="feature-auth",
        target_file="services/auth.py",
        overlapping_symbol="login() signature",
        risk=0.85,
        description="PR #42 calls `services/auth.py::login(user)` while PR #41 adds `timeout=30`.",
        merge_order_recommendation="Merge PR #41 first, then adapt PR #42.",
        suggestion_code="def login(user: str, timeout: int = 30) -> bool:",
    )
    result = PRCollisionResult(
        current_pr=42,
        has_collisions=True,
        max_risk=0.85,
        collisions=[col],
        audited_prs_count=2,
    )
    md = render_radar_markdown(ctx, result)
    assert STICKY_SIGNATURE in md
    assert "services/auth.py" in md
    assert "#41 by @alice" in md
    assert "0.85 (Critical)" in md
    assert "def login(user: str, timeout: int = 30) -> bool:" in md
    assert "Commit suggestion" in md
    assert "Merge PR #41 first" in md


def test_post_or_update_sticky_comment_creates_when_no_signature():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test",
    )
    existing_comments = [
        {"id": 101, "body": "Looks great to me!"},
        {"id": 102, "body": "Please add tests."},
    ]

    mock_get = MagicMock()
    mock_get.read.return_value = json.dumps(existing_comments).encode("utf-8")
    mock_get.__enter__.return_value = mock_get

    mock_post = MagicMock()
    mock_post.read.return_value = json.dumps({"id": 201, "body": "radar"}).encode("utf-8")
    mock_post.__enter__.return_value = mock_post

    with patch("urllib.request.urlopen", side_effect=[mock_get, mock_post]) as mock_url:
        res = post_or_update_sticky_comment(ctx, f"{STICKY_SIGNATURE}\n# Report")
        assert res["action"] == "created"
        assert res["comment_id"] == 201

        # Check POST url was called
        calls = mock_url.call_args_list
        assert len(calls) == 2
        req_post = calls[1][0][0]
        assert req_post.get_method() == "POST"
        assert "issues/42/comments" in req_post.full_url


def test_post_or_update_sticky_comment_patches_when_signature_exists():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test",
    )
    existing_comments = [
        {"id": 101, "body": "Looks great to me!"},
        {"id": 102, "body": f"{STICKY_SIGNATURE}\nOld Radar Report"},
    ]

    mock_get = MagicMock()
    mock_get.read.return_value = json.dumps(existing_comments).encode("utf-8")
    mock_get.__enter__.return_value = mock_get

    mock_patch = MagicMock()
    mock_patch.read.return_value = json.dumps({"id": 102, "body": "updated"}).encode("utf-8")
    mock_patch.__enter__.return_value = mock_patch

    with patch("urllib.request.urlopen", side_effect=[mock_get, mock_patch]) as mock_url:
        res = post_or_update_sticky_comment(ctx, f"{STICKY_SIGNATURE}\nNew Radar Report")
        assert res["action"] == "updated"
        assert res["comment_id"] == 102

        calls = mock_url.call_args_list
        assert len(calls) == 2
        req_patch = calls[1][0][0]
        assert req_patch.get_method() == "PATCH"
        assert "issues/comments/102" in req_patch.full_url


def test_load_radar_config_defaults(tmp_path: Path):
    cfg = load_radar_config(str(tmp_path))
    assert cfg["fail_on_collision"] is False
    assert cfg["risk_threshold"] == 0.8
    assert cfg["model"] == "gpt-4o-mini"
    assert cfg["provider"] == "github"
    assert cfg["base_url"] is None


def test_load_radar_config_from_file(tmp_path: Path):
    gdss_yml = tmp_path / ".gdss.yml"
    gdss_yml.write_text(
        """
radar:
  fail_on_collision: true
  risk_threshold: 0.65
  model: "gpt-4o"
  provider: "openai"
  base_url: "https://api.deepseek.com/v1"
""",
        encoding="utf-8",
    )
    cfg = load_radar_config(str(tmp_path))
    assert cfg["fail_on_collision"] is True
    assert cfg["risk_threshold"] == 0.65
    assert cfg["model"] == "gpt-4o"
    assert cfg["provider"] == "openai"
    assert cfg["base_url"] == "https://api.deepseek.com/v1"


def test_run_pr_audit_dry_run_no_collisions(tmp_path: Path):
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token=None,
    )
    out_file = tmp_path / "radar_output.md"

    # In dry-run mode without token, it doesn't attempt network calls
    exit_code = run_pr_audit(
        repo_path=str(tmp_path),
        context=ctx,
        dry_run=True,
        output_file=str(out_file),
    )
    assert exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert STICKY_SIGNATURE in content
    assert "🛰️ GDSS PR Collision Radar" in content


def test_run_pr_audit_threshold_exit_code(tmp_path: Path):
    gdss_yml = tmp_path / ".gdss.yml"
    gdss_yml.write_text(
        """
radar:
  fail_on_collision: true
  risk_threshold: 0.5
""",
        encoding="utf-8",
    )
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="fake_token",
    )

    concurrent_prs = [
        {
            "number": 41,
            "title": "Auth changes",
            "author": "alice",
            "head_ref": "feature-auth",
            "head_sha": "sha41",
            "base_ref": "main",
        }
    ]

    mock_collision = PRCollisionResult(
        current_pr=42,
        has_collisions=True,
        max_risk=0.85,
        collisions=[
            PRCollisionDetail(
                colliding_pr=41,
                author="alice",
                branch="feature-auth",
                target_file="auth.py",
                overlapping_symbol="login",
                risk=0.85,
                description="Collision",
                merge_order_recommendation="Merge #41 first",
            )
        ],
        audited_prs_count=1,
    )

    with patch("gdss.validation.pr_audit.fetch_concurrent_prs", return_value=concurrent_prs):
        with patch("gdss.validation.pr_audit.audit_pr_collisions", return_value=mock_collision):
            with patch("gdss.validation.pr_audit.post_or_update_sticky_comment"):
                exit_code = run_pr_audit(
                    repo_path=str(tmp_path),
                    context=ctx,
                    dry_run=False,
                )
                assert exit_code == 1  # Blocked because fail_on_collision=True and 0.85 >= 0.5


def test_generate_pr_convergence_patch_success(tmp_path: Path):
    from gdss.core.transform_types import OperatorType, SemanticOperator
    from gdss.validation.pr_audit import generate_pr_convergence_patch

    cur_op = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="auth.py",
        name="login",
        details={"diff": "+def login(user): return True"},
    )
    oth_op = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="auth.py",
        name="login",
        details={"diff": "+def login(user, timeout=30): return True"},
    )

    valid_llm_code = "def login(user: str, timeout: int = 30) -> bool:\n    return True\n"
    with patch(
        "gdss.ai.openai_provider.OpenAICompatibleProvider.complete",
        return_value=f"```python\n{valid_llm_code}\n```",
    ):
        patch_code = generate_pr_convergence_patch(
            repo_path=tmp_path,
            target_file="auth.py",
            overlapping_symbol="login",
            current_ops=[cur_op],
            other_ops=[oth_op],
            token="ghp_test",
            model="gpt-4o-mini",
        )
        assert patch_code is not None
        assert "def login(user: str, timeout: int = 30) -> bool:" in patch_code


def test_generate_pr_convergence_patch_syntax_error_discarded(tmp_path: Path):
    from gdss.core.transform_types import OperatorType, SemanticOperator
    from gdss.validation.pr_audit import generate_pr_convergence_patch

    cur_op = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="auth.py",
        name="login",
        details={"diff": "+def login(user): return True"},
    )
    oth_op = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="auth.py",
        name="login",
        details={"diff": "+def login(user, timeout=30): return True"},
    )

    invalid_llm_code = "def login(user: str, timeout: int = \n    broken syntax {"
    with patch(
        "gdss.ai.openai_provider.OpenAICompatibleProvider.complete", return_value=invalid_llm_code
    ):
        patch_code = generate_pr_convergence_patch(
            repo_path=tmp_path,
            target_file="auth.py",
            overlapping_symbol="login",
            current_ops=[cur_op],
            other_ops=[oth_op],
            token="ghp_test",
        )
        assert patch_code is None


def test_audit_pr_collisions_generates_verified_suggestion_in_radar(tmp_path: Path):
    from gdss.core.transform_types import OperatorType, SemanticOperator
    from gdss.validation.pr_audit import (
        PRAuditContext,
        audit_pr_collisions,
        render_radar_markdown,
    )

    (tmp_path / ".git").mkdir()

    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test_token",
    )

    concurrent_prs = [
        {
            "number": 41,
            "title": "Auth updates",
            "author": "alice",
            "head_ref": "feature-auth",
            "head_sha": "sha41",
            "base_ref": "main",
        }
    ]

    cur_ops = [
        SemanticOperator(operator=OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")
    ]
    oth_ops = [
        SemanticOperator(operator=OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")
    ]

    mock_patch = "def login(user: str, timeout: int = 30) -> bool:\n    return True\n"

    with patch("git.Repo"):
        with patch("gdss.watcher.git_observer.GitObserver.is_valid", return_value=True):
            with patch(
                "gdss.core.trajectory.extract_trajectory_operators", side_effect=[cur_ops, oth_ops]
            ):
                with patch(
                    "gdss.validation.pr_audit.generate_pr_convergence_patch",
                    return_value=mock_patch,
                ):
                    result = audit_pr_collisions(
                        repo_path=str(tmp_path),
                        context=ctx,
                        concurrent_prs=concurrent_prs,
                    )
                    assert result.has_collisions is True
                    assert len(result.collisions) == 1
                    assert result.collisions[0].suggestion_code == mock_patch

                    md = render_radar_markdown(ctx, result)
                    assert "### 🛡️ Verified Convergence Suggestion" in md
                    assert "def login(user: str, timeout: int = 30) -> bool:" in md
                    assert "Commit suggestion" in md


def test_render_radar_markdown_displays_refinement_attempts():
    ctx = PRAuditContext(
        repo_owner="octocat",
        repo_name="hello-world",
        pr_number=42,
        base_ref="main",
        head_ref="feature-billing",
        head_sha="sha42",
        github_token="ghp_test",
    )
    result = PRCollisionResult(
        current_pr=42,
        has_collisions=True,
        max_risk=0.8,
        collisions=[
            PRCollisionDetail(
                colliding_pr=41,
                author="alice",
                branch="feature-auth",
                target_file="auth.py",
                overlapping_symbol="login",
                risk=0.8,
                description="Overlapping changes",
                merge_order_recommendation="Merge #41 first",
                suggestion_code="def login(): return True",
                refinement_attempts=2,
            )
        ],
        audited_prs_count=1,
    )
    md = render_radar_markdown(ctx, result)
    assert "refined in 2 self-correction attempt(s)" in md
    assert "def login(): return True" in md
