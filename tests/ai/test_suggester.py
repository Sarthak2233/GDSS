from pathlib import Path
from unittest.mock import Mock

import git

from gdss.ai.suggester import suggest


def _create_divergent_repository(tmp_path):
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

    for branch_name, replacement in (
        ("feature-a", "return amount * 2"),
        ("feature-b", "return amount + 3"),
    ):
        branch = repository.create_head(branch_name, base)
        branch.checkout()
        Path(tmp_path, "payments.py").write_text(
            f"def process_payment(amount):\n    {replacement}\n", encoding="utf-8"
        )
        repository.index.add(["payments.py"])
        repository.index.commit(branch_name)

    return repository, reference


def test_suggest_returns_ranked_anchored_deterministic_conflicts(tmp_path):
    _repository, reference = _create_divergent_repository(tmp_path)

    suggestions = suggest(str(tmp_path), reference)

    assert [item.rank for item in suggestions] == list(range(1, len(suggestions) + 1))
    assert suggestions
    suggestion = suggestions[0]
    assert suggestion.anchor is not None
    assert suggestion.anchor.file_path == "payments.py"
    assert suggestion.topology is not None
    assert suggestion.patch_combinations
    assert all(item.patch_text is None for item in suggestion.patch_combinations)


def test_suggest_attaches_only_validation_gated_local_drafts(tmp_path):
    repository, reference = _create_divergent_repository(tmp_path)
    draft = """--- a/payments.py
+++ b/payments.py
@@ -2,1 +2,1 @@
-    return amount * 2
+    return amount * 4
"""

    mock_provider = Mock()
    mock_provider.complete.return_value = draft

    suggestions = suggest(
        str(tmp_path), reference, llm=True, provider=mock_provider
    )

    assert suggestions
    assert all(item.validated for item in suggestions[0].patch_combinations)
    assert all(item.patch_text == draft for item in suggestions[0].patch_combinations)
    assert repository.is_dirty(untracked_files=True) is False
