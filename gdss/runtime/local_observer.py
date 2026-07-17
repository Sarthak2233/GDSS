import time

from git import Repo

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.runtime.event_bus import EventBus
from gdss.watcher.git_observer import GitObserver


class LocalObserver:
    def __init__(self, repo_path: str, event_bus: EventBus):
        self.repo_path = repo_path
        self.bus = event_bus
        self.repo = Repo(repo_path)
        self.git_obs = GitObserver(repo_path)
        self.parser = ASTParser()
        self.extractor = TransformExtractor()

        self.last_head_hexsha = self.repo.head.commit.hexsha if not self.repo.head.is_detached or self.repo.heads else None

    def scan_once(self):
        """Manual trigger for TDD/Check, in production called by daemon loop."""
        try:
            current_hexsha = self.repo.head.commit.hexsha
            if current_hexsha != self.last_head_hexsha:
                event_type = "commit" if not self.repo.head.is_detached else "checkout"
                payload = {
                    "event": event_type,
                    "branch": self.repo.active_branch.name if not self.repo.head.is_detached else "DETACHED",
                    "hexsha": current_hexsha,
                    "timestamp": time.time(),
                    "semantic_operators": []
                }

                # Perform semantic extraction if it's a new commit
                if self.last_head_hexsha and event_type == "commit":
                    diffs = self.git_obs.get_file_diffs_between_commits(self.last_head_hexsha, current_hexsha)
                    all_ops = []

                    # 1. File-level operators
                    repo_ops = self.extractor.extract_repo_operators(
                        diffs["modified"] + diffs["deleted"], # Old files (approx)
                        diffs["modified"] + diffs["added"],   # New files (approx)
                        current_hexsha
                    )
                    all_ops.extend(repo_ops)

                    # 2. Inside-file operators
                    for f in diffs["modified"]:
                        if f.endswith((".py", ".js")):
                            old_content = self.git_obs.get_file_content_at_commit(self.last_head_hexsha, f)
                            new_content = self.git_obs.get_file_content_at_commit(current_hexsha, f)
                            if old_content and new_content:
                                old_syms = self.parser.parse_file(f, old_content)
                                new_syms = self.parser.parse_file(f, new_content)
                                all_ops.extend(self.extractor.extract_operators(f, old_syms, new_syms, current_hexsha))

                    payload["semantic_operators"] = [op.to_dict() for op in all_ops]

                self.bus.emit("local", payload)
                self.last_head_hexsha = current_hexsha
        except Exception:
            # Handle empty repos or other git issues
            pass
