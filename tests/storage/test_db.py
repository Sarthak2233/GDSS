import os
import sqlite3

import pytest

from gdss.storage.db import RuntimeDB


@pytest.fixture
def db_path(tmp_path):
    return os.path.join(tmp_path, "runtime.db")


@pytest.fixture
def db(db_path):
    return RuntimeDB(db_path)


def test_db_initialization(db, db_path):
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    expected_tables = {"repositories", "branches", "events", "contexts", "hierarchies"}
    assert expected_tables.issubset(tables)
    conn.close()


def test_repository_registry(db):
    repo_id = db.register_repository("test-repo", "/path/to/repo")
    assert repo_id is not None

    repos = db.get_repositories()
    assert len(repos) == 1
    assert repos[0]["name"] == "test-repo"


def test_branch_registration(db):
    repo_id = db.register_repository("test-repo", "/path/to/repo")
    db.register_branch(repo_id, "main", "origin/main", is_local=True)

    branches = db.get_branches(repo_id)
    assert len(branches) == 1
    assert branches[0]["name"] == "main"
    assert branches[0]["remote_name"] == "origin/main"
