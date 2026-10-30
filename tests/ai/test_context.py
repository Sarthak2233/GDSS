from pathlib import Path

import git

from gdss.ai.context import build_analysis_context, iter_contact_pairs


def test_analysis_context_composes_two_divergent_branch_trajectories(tmp_path):
    repository = git.Repo.init(tmp_path)
    with repository.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    Path(tmp_path, "payments.py").write_text(
        "def process_payment(amount):\n    return amount\n", encoding="utf-8"
    )
    repository.index.add(["payments.py"])
    base = repository.index.commit("base")
    reference = repository.active_branch.name

    first = repository.create_head("feature-a", base)
    first.checkout()
    Path(tmp_path, "payments.py").write_text(
        "def process_payment(amount):\n    return amount * 2\n", encoding="utf-8"
    )
    repository.index.add(["payments.py"])
    repository.index.commit("feature a")

    second = repository.create_head("feature-b", base)
    second.checkout()
    Path(tmp_path, "payments.py").write_text(
        "def process_payment(amount):\n    return amount + 3\n", encoding="utf-8"
    )
    repository.index.add(["payments.py"])
    repository.index.commit("feature b")

    context = build_analysis_context(str(tmp_path), reference)

    assert context.branches == ("feature-a", "feature-b")
    assert set(context.branch_operators) == {"feature-a", "feature-b"}
    entry = context.tensor.entries[("feature-a", "feature-b")]
    assert entry.omega > 0.0
    assert list(iter_contact_pairs(context, entry))

    assert "feature-a" in context.branch_commits
    assert len(context.branch_commits["feature-a"]) == 1
    assert context.branch_commits["feature-a"][0]["summary"] == "feature a"
    assert "feature-b" in context.branch_commits
    assert len(context.branch_commits["feature-b"]) == 1
    assert context.branch_commits["feature-b"][0]["summary"] == "feature b"
