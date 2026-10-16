from pathlib import Path

import git

from gdss.ai.anchors import resolve_anchor
from gdss.core.ast_parser import ASTParser
from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.watcher.git_observer import GitObserver


def test_resolve_anchor_uses_the_committed_target_branch_symbol(tmp_path):
    source = "    def process_payment(amount):\n        return amount\n"
    repository = git.Repo.init(tmp_path)
    with repository.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    Path(tmp_path, "payments.py").write_text(source, encoding="utf-8")
    repository.index.add(["payments.py"])
    repository.index.commit("add payment processing")

    symbol = ASTParser().parse_file("payments.py", content=source)[0]
    operator = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="payments.py",
        name="process_payment",
        symbol_id=symbol.symbol_id,
    )

    anchor = resolve_anchor(
        GitObserver(str(tmp_path)),
        ASTParser(),
        operator,
        repository.active_branch.name,
    )

    assert anchor is not None
    assert anchor.file_path == "payments.py"
    assert anchor.line_start == 1
    assert anchor.column_start == 5
    assert anchor.target_branch == repository.active_branch.name
    assert anchor.content_digest
    assert anchor.symbol_digest
