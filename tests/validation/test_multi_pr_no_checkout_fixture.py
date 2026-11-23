"""Real-Git integration fixture for read-only multi-PR collision analysis."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import git

from gdss.conflict.merge_order import plan_merge_order
from gdss.core.config import load_gdss_config
from gdss.drift.context import build_pr_analysis_context
from gdss.validation.pr_audit import (
    CallSiteEvidence,
    PRAuditContext,
    _classify_call_compatibility,
    audit_pr_collisions,
    run_pr_audit,
)


def _commit_all(repo: git.Repo, message: str) -> str:
    repo.git.add(A=True)
    repo.index.commit(message)
    return repo.head.commit.hexsha


def _snapshot_repository(repo: git.Repo) -> tuple[str, str, str, str, str]:
    head = repo.head.commit.hexsha
    branch = repo.active_branch.name
    index_status = repo.git.diff("--cached", "--stat")
    working_status = repo.git.diff("--stat")
    status_porcelain = repo.git.status("--porcelain")
    file_contents = {
        path: (Path(repo.working_tree_dir) / path).read_text(encoding="utf-8")
        if (Path(repo.working_tree_dir) / path).exists()
        else None
        for path in ("services/payment.py", "services/checkout.py", "README.md")
    }
    worktree_files = sorted(
        path
        for path in ("services/payment.py", "services/checkout.py", "README.md")
        if (Path(repo.working_tree_dir) / path).exists()
    )
    return (
        head,
        branch,
        f"{index_status}\n{status_porcelain}",
        f"{working_status}\n{repr(file_contents)}",
        "|".join(worktree_files),
    )


def test_multi_pr_analysis_preserves_git_state_and_detects_contract_collision(tmp_path: Path):
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "GDSS Fixture").release()
    repo.config_writer().set_value("user", "email", "gdss@example.test").release()

    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "payment.py").write_text(
        "def process_payment(user, card):\n"
        "    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "services" / "checkout.py").write_text(
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    return process_payment(user, card)\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")
    base_sha = _commit_all(repo, "base")
    repo.git.branch("-M", "main")
    repo.git.checkout("-b", "contract-change")
    (tmp_path / "services" / "payment.py").write_text(
        "def process_payment(user):\n"
        "    return True\n",
        encoding="utf-8",
    )
    contract_sha = _commit_all(repo, "change payment contract")

    repo.git.checkout("-B", "stale-caller", base_sha)
    (tmp_path / "services" / "checkout.py").write_text(
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    print('checkout telemetry')\n"
        "    return process_payment(user, card)\n",
        encoding="utf-8",
    )
    stale_sha = _commit_all(repo, "update checkout independently")

    repo.git.checkout("-B", "independent", base_sha)
    (tmp_path / "README.md").write_text("# Fixture\n\nIndependent documentation update.\n", encoding="utf-8")
    independent_sha = _commit_all(repo, "independent docs")

    repo.git.checkout("main")
    repo.git.reset("--hard", base_sha)
    repo.git.branch("-D", "contract-change", "stale-caller", "independent")
    repo.git.branch("contract-change", contract_sha)
    repo.git.branch("stale-caller", stale_sha)
    repo.git.branch("independent", independent_sha)

    before = _snapshot_repository(repo)

    # Use actual commits and Git objects: no branch checkout is performed here.
    analysis = build_pr_analysis_context(
        repo_path=str(tmp_path),
        reference_branch="main",
        current_pr_branch=contract_sha,
        concurrent_branches=[stale_sha, independent_sha],
    )

    after = _snapshot_repository(repo)
    assert after == before

    contract_ops = analysis.branch_operators[contract_sha]
    stale_ops = analysis.branch_operators[stale_sha]
    independent_ops = analysis.branch_operators[independent_sha]

    assert any(op.name == "process_payment" for op in contract_ops)
    assert not any(
        op.details.get("callsite_contact") and op.name == "process_payment"
        for op in stale_ops
    )
    assert not any(op.name == "process_payment" for op in independent_ops)

    pair = tuple(sorted((contract_sha, stale_sha)))
    result_entry = analysis.tensor.entries.get((pair[0], pair[1]))
    assert result_entry is not None
    assert result_entry.omega > 0.1

    ctx = PRAuditContext(
        repo_owner="fixture",
        repo_name="fixture",
        pr_number=101,
        base_ref="main",
        head_ref="contract-change",
        head_sha=contract_sha,
    )
    result = audit_pr_collisions(
        tmp_path,
        ctx,
        [
            {
                "number": 102,
                "author": "stale",
                "head_ref": "stale-caller",
                "head_sha": stale_sha,
                "base_ref": "main",
            },
            {
                "number": 103,
                "author": "independent",
                "head_ref": "independent",
                "head_sha": independent_sha,
                "base_ref": "main",
            },
        ],
        config={"provider": "none", "risk_threshold": 0.1, "fail_on_collision": False},
    )

    assert result.has_collisions
    stale_collision = next(c for c in result.collisions if c.colliding_pr == 102)
    assert stale_collision.overlapping_symbol == "process_payment"
    assert stale_collision.risk > 0.1
    assert stale_collision.merge_order_recommendation
    assert all(c.colliding_pr != 103 for c in result.collisions)

    independent_pair = tuple(sorted((contract_sha, independent_sha)))
    assert analysis.tensor.entries.get((independent_pair[0], independent_pair[1])) is None

    costs = {
        (contract_sha, stale_sha): stale_collision.risk,
    }
    first_plan = plan_merge_order([contract_sha, stale_sha, independent_sha], costs)
    second_plan = plan_merge_order([contract_sha, stale_sha, independent_sha], costs)
    assert first_plan.order == second_plan.order
    assert first_plan.heuristic == "greedy_nearest_neighbor"
    assert first_plan.steps


def test_repository_gdss_config_uses_supported_loader_fields():
    repo_root = Path(__file__).resolve().parents[2]
    cfg = load_gdss_config(repo_root)

    assert cfg.version == 1
    assert cfg.radar.context_window == 128000
    assert cfg.radar.risk_threshold == 0.1
    assert cfg.radar.fail_on_collision is False
    assert cfg.hierarchy.reference_branch == "main"
    assert cfg.hierarchy.same_base_only is True
    assert cfg.ast.exclude_patterns
    assert cfg.validation.timeout_seconds == 60
    assert cfg.validation.test_command == "pytest {test_file}"
    assert cfg.validation.typecheck_command == "mypy {file}"


def _make_call_compatibility_fixture(
    tmp_path: Path,
    caller_source: str,
    contract_source: str = (
        "def process_payment(user):\n"
        "    return True\n"
    ),
    caller_contract_source: str | None = None,
):
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "GDSS Fixture").release()
    repo.config_writer().set_value("user", "email", "gdss@example.test").release()

    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "payment.py").write_text(
        "def process_payment(user, card):\n"
        "    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "services" / "checkout.py").write_text(
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    return process_payment(user, card)\n",
        encoding="utf-8",
    )
    base_sha = _commit_all(repo, "base")
    repo.git.branch("-M", "main")

    repo.git.checkout("-b", "contract-change")
    (tmp_path / "services" / "payment.py").write_text(
        contract_source,
        encoding="utf-8",
    )
    contract_sha = _commit_all(repo, "change payment contract")

    repo.git.checkout("-B", "caller-change", base_sha)
    (tmp_path / "services" / "checkout.py").write_text(
        caller_source,
        encoding="utf-8",
    )
    if caller_contract_source is not None:
        (tmp_path / "services" / "payment.py").write_text(
            caller_contract_source,
            encoding="utf-8",
        )
    caller_sha = _commit_all(repo, "change caller")

    repo.git.checkout("main")
    repo.git.reset("--hard", base_sha)
    return repo, contract_sha, caller_sha


def _audit_caller_fixture(
    tmp_path: Path,
    caller_source: str,
    pr_number: int,
    contract_source: str = (
        "def process_payment(user):\n"
        "    return True\n"
    ),
):
    repo, contract_sha, caller_sha = _make_call_compatibility_fixture(
        tmp_path,
        caller_source,
        contract_source,
    )
    before = _snapshot_repository(repo)
    result = audit_pr_collisions(
        tmp_path,
        PRAuditContext(
            repo_owner="fixture",
            repo_name="fixture",
            pr_number=101,
            base_ref="main",
            head_ref="contract-change",
            head_sha=contract_sha,
        ),
        [
            {
                "number": pr_number,
                "author": "caller",
                "head_ref": "caller-change",
                "head_sha": caller_sha,
                "base_ref": "main",
            }
        ],
        config={"provider": "none", "risk_threshold": 0.1, "fail_on_collision": False},
    )
    assert _snapshot_repository(repo) == before
    return repo, contract_sha, caller_sha, result


def test_old_two_argument_caller_is_true_stale_collision(tmp_path: Path):
    _repo, _contract_sha, _caller_sha, result = _audit_caller_fixture(
        tmp_path,
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    print('stale caller edit')\n"
        "    return process_payment(user, card)\n",
        102,
    )

    collision = next(c for c in result.collisions if c.colliding_pr == 102)
    assert collision.risk >= 0.85
    assert "old contract" in collision.description
    assert "services/payment.py" in collision.description
    assert "services/checkout.py" in collision.description
    assert collision.target_file == "services/payment.py"
    assert "update the caller" in collision.merge_order_recommendation.lower()
    assert "before or together" in collision.merge_order_recommendation.lower()


def test_updated_one_argument_caller_is_adapted_not_stale(tmp_path: Path):
    _repo, _contract_sha, _caller_sha, result = _audit_caller_fixture(
        tmp_path,
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    return process_payment(user)\n",
        102,
    )

    collisions = [c for c in result.collisions if c.colliding_pr == 102]
    assert collisions
    collision = collisions[0]
    assert "stale" not in collision.description.lower()
    assert "already uses" in collision.description.lower()
    assert "services/payment.py" in collision.description
    assert "services/checkout.py" in collision.description
    assert "already-adapted" in collision.merge_order_recommendation.lower()
    assert "contract update in pr #101 first" in (
        collision.merge_order_recommendation.lower()
    )
    assert "then merge the already-adapted caller pr #102" in (
        collision.merge_order_recommendation.lower()
    )


def test_call_accepted_by_both_contracts_is_common_not_stale(tmp_path: Path):
    _repo, _contract_sha, _caller_sha, result = _audit_caller_fixture(
        tmp_path,
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    print('unchanged call, independent edit')\n"
        "    return process_payment(user, card)\n",
        102,
        contract_source=(
            "def process_payment(user, card, timeout=30):\n"
            "    return True\n"
        ),
    )

    assert not result.has_collisions
    assert not result.collisions
    assert result.max_risk <= 0.1


def test_common_call_does_not_block_fail_on_collision(tmp_path: Path):
    repo, contract_sha, caller_sha = _make_call_compatibility_fixture(
        tmp_path,
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    print('independent caller edit')\n"
        "    return process_payment(user, card)\n",
        contract_source=(
            "def process_payment(user, card, timeout=30):\n"
            "    return True\n"
        ),
    )
    (tmp_path / ".gdss.yml").write_text(
        "radar:\n"
        "  provider: none\n"
        "  risk_threshold: 0.1\n"
        "  fail_on_collision: true\n",
        encoding="utf-8",
    )
    context = PRAuditContext(
        repo_owner="fixture",
        repo_name="fixture",
        pr_number=101,
        base_ref="main",
        head_ref="contract-change",
        head_sha=contract_sha,
        github_token="fixture-token",
    )
    caller_pr = {
        "number": 102,
        "author": "caller",
        "head_ref": "caller-change",
        "head_sha": caller_sha,
        "base_ref": "main",
    }

    with patch(
        "gdss.validation.pr_audit.fetch_concurrent_prs",
        return_value=[caller_pr],
    ), patch("gdss.validation.pr_audit.post_or_update_sticky_comment"):
        exit_code = run_pr_audit(
            repo_path=str(tmp_path),
            context=context,
        )

    assert exit_code == 0


def test_common_call_does_not_hide_independent_same_symbol_conflict(
    tmp_path: Path,
):
    _repo, contract_sha, caller_sha = _make_call_compatibility_fixture(
        tmp_path,
        "from services.payment import process_payment\n\n"
        "def checkout(user, card):\n"
        "    print('caller and contract conflict')\n"
        "    return process_payment(user, card)\n",
        contract_source=(
            "def process_payment(user, card, timeout=30):\n"
            "    return True\n"
        ),
        caller_contract_source=(
            "def process_payment(user, card):\n"
            "    print('independent implementation change')\n"
            "    return True\n"
        ),
    )
    result = audit_pr_collisions(
        tmp_path,
        PRAuditContext(
            repo_owner="fixture",
            repo_name="fixture",
            pr_number=101,
            base_ref="main",
            head_ref="contract-change",
            head_sha=contract_sha,
        ),
        [
            {
                "number": 102,
                "author": "caller",
                "head_ref": "caller-change",
                "head_sha": caller_sha,
                "base_ref": "main",
            }
        ],
        config={"provider": "none", "risk_threshold": 0.1, "fail_on_collision": False},
    )

    assert result.has_collisions
    assert result.max_risk > 0.1
    assert result.collisions
    collision = next(c for c in result.collisions if c.colliding_pr == 102)
    assert collision.target_file == "services/payment.py"
    assert "both contract signatures" not in collision.description.lower()
    assert "without breaking it" not in collision.merge_order_recommendation.lower()


def test_unrelated_changed_file_with_no_call_is_not_a_collision(tmp_path: Path):
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "GDSS Fixture").release()
    repo.config_writer().set_value("user", "email", "gdss@example.test").release()

    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "payment.py").write_text(
        "def process_payment(user, card):\n"
        "    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Base\n", encoding="utf-8")
    base_sha = _commit_all(repo, "base")
    repo.git.branch("-M", "main")

    repo.git.checkout("-b", "contract-change")
    (tmp_path / "services" / "payment.py").write_text(
        "def process_payment(user):\n"
        "    return True\n",
        encoding="utf-8",
    )
    contract_sha = _commit_all(repo, "change contract")

    repo.git.checkout("-B", "unrelated-change", base_sha)
    (tmp_path / "README.md").write_text("# Base\n\nUnrelated docs.\n", encoding="utf-8")
    unrelated_sha = _commit_all(repo, "change docs")

    repo.git.checkout("main")
    repo.git.reset("--hard", base_sha)

    before = _snapshot_repository(repo)
    result = audit_pr_collisions(
        tmp_path,
        PRAuditContext(
            repo_owner="fixture",
            repo_name="fixture",
            pr_number=101,
            base_ref="main",
            head_ref="contract-change",
            head_sha=contract_sha,
        ),
        [
            {
                "number": 103,
                "author": "docs",
                "head_ref": "unrelated-change",
                "head_sha": unrelated_sha,
                "base_ref": "main",
            }
        ],
        config={"provider": "none", "risk_threshold": 0.1, "fail_on_collision": False},
    )

    assert _snapshot_repository(repo) == before
    assert all(c.colliding_pr != 103 for c in result.collisions)


def test_uncertain_call_shape_is_not_classified_as_stale():
    evidence = CallSiteEvidence(
        target="process_payment",
        file_path="services/checkout.py",
        structure="process_payment(customer, card, 'summary')",
        arguments=("customer", "card", "'summary'"),
    )

    assert (
        _classify_call_compatibility(
            evidence,
            "(user, card)",
            "(user)",
        )
        == "uncertain"
    )


def _compatibility_evidence(*arguments: str) -> CallSiteEvidence:
    return CallSiteEvidence(
        target="process_payment",
        file_path="services/checkout.py",
        structure=f"process_payment({', '.join(arguments)})",
        arguments=arguments,
    )


def test_two_argument_call_is_old_only_after_required_parameter_removal():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card"),
            "(user, card)",
            "(user)",
        )
        == "old_only"
    )


def test_one_argument_call_is_new_only_after_required_parameter_removal():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user"),
            "(user, card)",
            "(user)",
        )
        == "new_only"
    )


def test_call_with_two_arguments_is_compatible_with_optional_new_parameter():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card"),
            "(user, card)",
            "(user, card, timeout=30)",
        )
        == "both"
    )


def test_keyword_rename_uses_accepted_keyword_names():
    old_call = _compatibility_evidence("user=user", "card=card")
    new_call = _compatibility_evidence("user=user", "payment_card=card")

    assert (
        _classify_call_compatibility(
            old_call,
            "(user, card)",
            "(user, payment_card)",
        )
        == "old_only"
    )
    assert (
        _classify_call_compatibility(
            new_call,
            "(user, card)",
            "(user, payment_card)",
        )
        == "new_only"
    )


def test_default_parameters_affect_required_argument_compatibility():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user"),
            "(user, card='default')",
            "(user)",
        )
        == "both"
    )
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card"),
            "(user, card='default')",
            "(user)",
        )
        == "old_only"
    )


def test_variadic_parameters_accept_extra_arguments_and_keywords():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card", "timeout"),
            "(user, *args)",
            "(user, *args)",
        )
        == "both"
    )
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card=card", "timeout=30"),
            "(user, **kwargs)",
            "(user, **kwargs)",
        )
        == "both"
    )


def test_starred_call_arguments_are_uncertain():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("*values"),
            "(user, card)",
            "(user)",
        )
        == "uncertain"
    )


def test_keyword_only_parameters_require_keywords():
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card=card"),
            "(user, *, card)",
            "(user, *, card, timeout=30)",
        )
        == "both"
    )
    assert (
        _classify_call_compatibility(
            _compatibility_evidence("user", "card"),
            "(user, *, card)",
            "(user, *, card)",
        )
        == "uncertain"
    )
