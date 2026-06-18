import os
import shutil
import tempfile
import pytest
import git
from gdss.watcher.git_observer import GitObserver

@pytest.fixture
def temp_git_repo():
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Init git repo
    repo = git.Repo.init(temp_dir)
    
    # Configure mock user for git commits
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test User")
        cw.set_value("user", "email", "test@example.com")
        
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_git_observer_features(temp_git_repo):
    repo_path = temp_git_repo
    repo = git.Repo(repo_path)
    
    # 1. Create initial file and commit to main
    file_a_path = os.path.join(repo_path, "calc.py")
    with open(file_a_path, "w") as f:
        f.write("def add(a, b):\n    return a + b\n")
        
    repo.index.add(["calc.py"])
    initial_commit = repo.index.commit("Initial commit")
    
    # 2. Check GitObserver initialization
    observer = GitObserver(repo_path)
    assert observer.is_valid() is True
    assert observer.get_active_branch() in ("master", "main")
    
    # 3. Create active branch
    feature_branch = repo.create_head("feature-div")
    repo.head.reference = feature_branch
    assert observer.get_active_branch() == "feature-div"
    
    # 4. Modify file and commit on feature-div
    with open(file_a_path, "w") as f:
        f.write("def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n")
    repo.index.add(["calc.py"])
    feature_commit = repo.index.commit("Add sub function")
    
    # 5. Verify base resolution and diffs
    merge_base = observer.get_merge_base("feature-div", ref_branch=initial_commit.hexsha)
    assert merge_base == initial_commit.hexsha
    
    diffs = observer.get_file_diffs_between_commits(initial_commit.hexsha, feature_commit.hexsha)
    assert "calc.py" in diffs["modified"]
    
    # 6. Verify working tree unstaged/staged modifications detection
    file_b_path = os.path.join(repo_path, "utils.py")
    with open(file_b_path, "w") as f:
        f.write("def log(msg):\n    print(msg)\n")
        
    working_changes = observer.get_working_tree_changes()
    assert "utils.py" in working_changes["added"]
    
    # Check historical content retrieval
    old_content = observer.get_file_content_at_commit(initial_commit.hexsha, "calc.py")
    assert "def sub" not in old_content
    assert "def add" in old_content
