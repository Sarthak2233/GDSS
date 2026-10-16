import os

import git


class GitObserver:
    """
    Observer class to interact with Git history, branch structures,
    commits, and hook registrations using GitPython.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        self.repo: git.Repo | None
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
            self.repo_path = str(self.repo.working_tree_dir or self.repo_path)
        except git.InvalidGitRepositoryError:
            self.repo = None

    def is_valid(self) -> bool:
        return self.repo is not None

    def get_active_branch(self) -> str | None:
        if not self.repo:
            return None
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Head is detached
            return "DETACHED"

    def get_merge_base(self, branch_name: str, ref_branch: str = "main") -> str | None:
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

    def get_parent_sha(self, commit_sha: str) -> str | None:
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

    def get_file_content_at_commit(self, commit_sha: str, file_path: str) -> str | None:
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

    def get_file_diffs_between_commits(self, commit_sha_a: str, commit_sha_b: str) -> dict[str, list[str]]:
        """
        Calculates file list changes between commit A and commit B.
        Returns dictionary mapping:
        - "added": [filepath]
        - "deleted": [filepath]
        - "modified": [filepath]
        """
        changes: dict[str, list[str]] = {"added": [], "deleted": [], "modified": []}
        if not self.repo:
            return changes

        try:
            commit_a = self.repo.commit(commit_sha_a)
            commit_b = self.repo.commit(commit_sha_b)
            diffs = commit_a.diff(commit_b)

            for d in diffs:
                if d.new_file and d.b_path:
                    changes["added"].append(d.b_path)
                elif d.deleted_file and d.a_path:
                    changes["deleted"].append(d.a_path)
                elif d.b_path:
                    changes["modified"].append(d.b_path)
        except Exception:
            pass
        return changes

    def get_working_tree_changes(self) -> dict[str, list[str]]:
        """Retrieves unstaged and staged changes in working tree against HEAD."""
        changes: dict[str, list[str]] = {"added": [], "deleted": [], "modified": []}
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
                if d.new_file and d.b_path:
                    if d.b_path not in changes["added"]:
                        changes["added"].append(d.b_path)
                elif d.deleted_file and d.a_path:
                    changes["deleted"].append(d.a_path)
                elif d.b_path:
                    changes["modified"].append(d.b_path)

            for d in unstaged_diffs:
                if d.new_file and d.b_path:
                    if d.b_path not in changes["added"]:
                        changes["added"].append(d.b_path)
                elif d.deleted_file and d.a_path:
                    if d.a_path not in changes["deleted"]:
                        changes["deleted"].append(d.a_path)
                elif d.b_path:
                    if d.b_path not in changes["modified"]:
                        changes["modified"].append(d.b_path)
        except Exception:
            pass
        return changes


    def list_local_branches(self) -> list[str]:
        """Return local branch names."""
        if not self.repo:
            return []
        try:
            return [head.name for head in self.repo.heads]
        except Exception:
            return []

    def get_remote_sync_status(
        self, ref_branch: str, remote: str = "origin"
    ) -> dict[str, object]:
        """
        Compare HEAD to origin/<ref> (or configured remote).

        Returns ahead/behind counts. label is N/A when the remote ref is missing.
        Never infers semantic drift from remote event topic flags.
        """
        result: dict[str, object] = {
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

    def get_commits_between(
        self,
        base_ref: str,
        head_ref: str,
        max_count: int = 25,
    ) -> list[dict[str, str]]:
        """Return list of commits on head_ref added apart from base_ref.

        Equivalent to `git log base_ref..head_ref`.
        Returns dicts with:
          - sha: short 8-char commit SHA
          - summary: commit title / first line
          - author: author name
          - message: full commit message trimmed
        """
        if not self.repo:
            return []
        try:
            commits: list[dict[str, str]] = []
            rev_range = f"{base_ref}..{head_ref}"
            for c in self.repo.iter_commits(rev_range, max_count=max_count):
                commits.append(
                    {
                        "sha": c.hexsha[:8],
                        "summary": str(c.summary),
                        "author": str(c.author.name) if c.author else "unknown",
                        "message": str(c.message).strip(),
                    }
                )
            return commits
        except Exception:
            return []

