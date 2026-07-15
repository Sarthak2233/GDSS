import os
import git
from typing import Dict, List, Tuple, Optional

class GitObserver:
    """
    Observer class to interact with Git history, branch structures,
    commits, and hook registrations using GitPython.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
            self.repo_path = self.repo.working_tree_dir
        except git.InvalidGitRepositoryError:
            self.repo = None

    def is_valid(self) -> bool:
        return self.repo is not None

    def get_active_branch(self) -> Optional[str]:
        if not self.repo:
            return None
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Head is detached
            return "DETACHED"

    def get_merge_base(self, branch_name: str, ref_branch: str = "main") -> Optional[str]:
        """Calculates the merge base commit hash between active branch and reference branch."""
        if not self.repo:
            return None
        try:
            branch_commit = self.repo.commit(branch_name)
            ref_commit = self.repo.commit(ref_branch)
            merge_bases = self.repo.merge_base(branch_commit, ref_commit)
            if merge_bases:
                return merge_bases[0].hexsha
        except Exception:
            pass
        return None

    def get_parent_sha(self, commit_sha: str) -> Optional[str]:
        """Retrieves the parent commit SHA for a given commit."""
        if not self.repo:
            return None
        try:
            commit = self.repo.commit(commit_sha)
            if commit.parents:
                return commit.parents[0].hexsha
        except Exception:
            pass
        return None

    def get_file_content_at_commit(self, commit_sha: str, file_path: str) -> Optional[str]:
        """Retrieves file text content at a specific historical commit."""
        if not self.repo:
            return None
        try:
            # Ensure path is relative to repository root
            rel_path = os.path.relpath(os.path.join(self.repo_path, file_path), self.repo.working_tree_dir)
            commit = self.repo.commit(commit_sha)
            blob = commit.tree / rel_path
            return blob.data_stream.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    def get_file_diffs_between_commits(self, commit_sha_a: str, commit_sha_b: str) -> Dict[str, List[str]]:
        """
        Calculates file list changes between commit A and commit B.
        Returns dictionary mapping:
        - "added": [filepath]
        - "deleted": [filepath]
        - "modified": [filepath]
        """
        changes = {"added": [], "deleted": [], "modified": []}
        if not self.repo:
            return changes
        
        try:
            commit_a = self.repo.commit(commit_sha_a)
            commit_b = self.repo.commit(commit_sha_b)
            diffs = commit_a.diff(commit_b)

            for d in diffs:
                if d.new_file:
                    changes["added"].append(d.b_path)
                elif d.deleted_file:
                    changes["deleted"].append(d.a_path)
                else:
                    changes["modified"].append(d.b_path)
        except Exception:
            pass
        return changes

    def get_working_tree_changes(self) -> Dict[str, List[str]]:
        """Retrieves unstaged and staged changes in working tree against HEAD."""
        changes = {"added": [], "deleted": [], "modified": []}
        if not self.repo:
            return changes
        try:
            # Check staged
            staged_diffs = self.repo.index.diff("HEAD")
            # Check unstaged
            unstaged_diffs = self.repo.index.diff(None)

            # Untracked files
            untracked = self.repo.untracked_files
            changes["added"].extend(untracked)

            for d in staged_diffs:
                if d.new_file:
                    if d.b_path not in changes["added"]:
                        changes["added"].append(d.b_path)
                elif d.deleted_file:
                    changes["deleted"].append(d.a_path)
                else:
                    changes["modified"].append(d.b_path)

            for d in unstaged_diffs:
                if d.new_file:
                    if d.b_path not in changes["added"]:
                        changes["added"].append(d.b_path)
                elif d.deleted_file:
                    if d.a_path not in changes["deleted"]:
                        changes["deleted"].append(d.a_path)
                else:
                    if d.b_path not in changes["modified"]:
                        changes["modified"].append(d.b_path)
        except Exception:
            pass
        return changes

    def install_git_hooks(self) -> bool:
        """Installs pre-push and post-commit hooks in .git/hooks directory."""
        if not self.repo:
            return False
        
        hooks_dir = os.path.join(self.repo_path, ".git", "hooks")
        if not os.path.exists(hooks_dir):
            return False

        # Post-commit hook
        post_commit_path = os.path.join(hooks_dir, "post-commit")
        try:
            with open(post_commit_path, "w") as f:
                f.write("#!/bin/sh\n\n# GDSS Trigger\ngdss status\n")
            os.chmod(post_commit_path, 0o755)
        except Exception:
            return False

        # Pre-push hook
        pre_push_path = os.path.join(hooks_dir, "pre-push")
        try:
            with open(pre_push_path, "w") as f:
                f.write("#!/bin/sh\n\n# GDSS Trigger\ngdss status\n")
            os.chmod(pre_push_path, 0o755)
        except Exception:
            return False

        return True

    def list_local_branches(self) -> List[str]:
        """Return local branch names."""
        if not self.repo:
            return []
        try:
            return [head.name for head in self.repo.heads]
        except Exception:
            return []

    def get_remote_sync_status(
        self, ref_branch: str, remote: str = "origin"
    ) -> Dict[str, object]:
        """
        Compare HEAD to origin/<ref> (or configured remote).

        Returns ahead/behind counts. label is N/A when the remote ref is missing.
        Never infers semantic drift from remote event topic flags.
        """
        result: Dict[str, object] = {
            "label": "N/A",
            "ahead": 0,
            "behind": 0,
            "remote_ref": f"{remote}/{ref_branch}",
        }
        if not self.repo:
            return result

        remote_ref = f"{remote}/{ref_branch}"
        try:
            # Resolve remote tip; missing remote => N/A
            self.repo.commit(remote_ref)
        except Exception:
            return result

        try:
            ahead = sum(1 for _ in self.repo.iter_commits(f"{remote_ref}..HEAD"))
            behind = sum(1 for _ in self.repo.iter_commits(f"HEAD..{remote_ref}"))
            result["ahead"] = ahead
            result["behind"] = behind
            if ahead == 0 and behind == 0:
                result["label"] = "ALIGNED"
            elif ahead > 0 and behind == 0:
                result["label"] = f"AHEAD {ahead}"
            elif behind > 0 and ahead == 0:
                result["label"] = f"BEHIND {behind}"
            else:
                result["label"] = f"DIVERGED +{ahead}/-{behind}"
        except Exception:
            return result
        return result
