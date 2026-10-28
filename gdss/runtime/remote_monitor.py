import subprocess
import time

from gdss.runtime.event_bus import EventBus


class RemoteMonitor:
    def __init__(self, repo_path: str, event_bus: EventBus):
        self.repo_path = repo_path
        self.bus = event_bus
        self.last_remote_state: dict[str, str] = {}

    def scan_remote(self):
        """Runs git ls-remote to check for remote drift."""
        try:
            result = subprocess.run(
                ["git", "ls-remote", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_state = {}
            for line in result.stdout.splitlines():
                if not line:
                    continue
                sha, ref = line.split()
                current_state[ref] = sha

            now = time.time()
            # Compare with last state
            for ref, sha in current_state.items():
                if ref in self.last_remote_state and self.last_remote_state[ref] != sha:
                    self.bus.emit(
                        "remote",
                        {
                            "event": "branch_update",
                            "ref": ref,
                            "old_sha": self.last_remote_state[ref],
                            "new_sha": sha,
                            "timestamp": now,
                        },
                    )
                elif ref not in self.last_remote_state:
                    self.bus.emit(
                        "remote",
                        {"event": "branch_created", "ref": ref, "sha": sha, "timestamp": now},
                    )

            self.last_remote_state = current_state
        except Exception:
            # Silently fail if no remote or network issues
            pass
