import json
import os
import shutil
import tempfile

import git
import pytest

from gdss.core.ast_parser import ASTParser
from gdss.core.trajectory import extract_trajectory_operators
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import OperatorType
from gdss.watcher.git_observer import GitObserver


@pytest.fixture
def multi_asset_repo():
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")

    # Base commit with package.json, an env file, and initial migration
    pkg_path = os.path.join(temp_dir, "package.json")
    with open(pkg_path, "w") as f:
        json.dump({"name": "app", "dependencies": {"express": "^4.18.2"}}, f)

    env_path = os.path.join(temp_dir, ".env")
    with open(env_path, "w") as f:
        f.write("PORT=3000\nDEBUG=false\n")

    os.makedirs(os.path.join(temp_dir, "alembic", "versions"), exist_ok=True)
    mig_path = os.path.join(temp_dir, "alembic", "versions", "0001_init.py")
    with open(mig_path, "w") as f:
        f.write("revision = '0001'\ndown_revision = None\n")

    repo.index.add(["package.json", ".env", "alembic/versions/0001_init.py"])
    repo.index.commit("base commit")
    base_name = repo.active_branch.name

    # Create feature branch
    feature = repo.create_head("feature-work")
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)

    # 1. Update package.json (add axios)
    with open(pkg_path, "w") as f:
        json.dump(
            {"name": "app", "dependencies": {"express": "^4.18.2", "axios": "^1.6.0"}},
            f,
        )

    # 2. Add new migration pointing to 0001
    mig2_path = os.path.join(temp_dir, "alembic", "versions", "0002_add_roles.py")
    with open(mig2_path, "w") as f:
        f.write("revision = '0002'\ndown_revision = '0001'\n")

    # 3. Add schema.sql
    sql_path = os.path.join(temp_dir, "schema.sql")
    with open(sql_path, "w") as f:
        f.write("CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50));\n")

    # 4. Modify .env
    with open(env_path, "w") as f:
        f.write("PORT=8080\nDEBUG=true\n")

    repo.index.add(
        [
            "package.json",
            "alembic/versions/0002_add_roles.py",
            "schema.sql",
            ".env",
        ]
    )
    repo.index.commit("multi asset modifications")

    yield temp_dir, base_name
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_trajectory_multi_asset_ingestion(multi_asset_repo):
    temp_dir, base_name = multi_asset_repo
    observer = GitObserver(temp_dir)
    ops = extract_trajectory_operators(
        observer,
        ASTParser(),
        TransformExtractor(),
        ref_branch=base_name,
        head="HEAD",
    )

    op_types = {op.operator for op in ops}

    # Manifest dependency captured
    assert OperatorType.ADD_DEPENDENCY in op_types
    add_dep = next(op for op in ops if op.operator == OperatorType.ADD_DEPENDENCY)
    assert add_dep.name == "axios"

    # Migration step captured
    assert OperatorType.MIGRATION_STEP in op_types
    mig_op = next(op for op in ops if op.operator == OperatorType.MIGRATION_STEP)
    assert mig_op.name == "migration_parent::0001"

    # SQL DDL table and column captured
    assert OperatorType.SCHEMA_ADD_TABLE in op_types
    assert OperatorType.SCHEMA_ADD_COLUMN in op_types

    # Lexical chunk edit for .env captured
    assert OperatorType.LEXICAL_CHUNK_EDIT in op_types
    lex_op = next(op for op in ops if op.operator == OperatorType.LEXICAL_CHUNK_EDIT)
    assert lex_op.file == ".env"
