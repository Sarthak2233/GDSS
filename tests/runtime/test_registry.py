import pytest
import os
from gdss.runtime.registry import RepositoryRegistry
from gdss.storage.db import RuntimeDB

@pytest.fixture
def db(tmp_path):
    db_path = os.path.join(tmp_path, "runtime.db")
    return RuntimeDB(db_path)

@pytest.fixture
def registry(db):
    return RepositoryRegistry(db)

def test_registry_local_remote_sync(registry):
    # Registering a repository
    repo_path = "/fake/repo"
    repo_id = registry.db.register_repository("my-repo", repo_path)
    
    # Adding local and remote branches
    registry.update_branch_state(repo_id, "main", "origin/main", is_local=True)
    registry.update_branch_state(repo_id, "feature-1", "origin/feature-1", is_local=True)
    registry.update_branch_state(repo_id, "feature-remote", "origin/feature-remote", is_local=False)
    
    branches = registry.get_branches(repo_id)
    assert len(branches) == 3
    
    local_branches = [b for b in branches if b['is_local']]
    assert len(local_branches) == 2

def test_hierarchy_resolution(registry):
    config = {
        "repository": {
            "name": "test-repo"
        },
        "hierarchy": {
            "production": "main",
            "staging": "staging",
            "development": "dev"
        },
        "feature_patterns": [
            "feature/*"
        ]
    }
    repo_id = registry.db.register_repository("test-repo", "/path")
    registry.set_hierarchy_config(repo_id, config)
    
    hierarchy = registry.get_hierarchy(repo_id)
    assert hierarchy['hierarchy']['production'] == "main"
    assert "feature/*" in hierarchy['feature_patterns']
