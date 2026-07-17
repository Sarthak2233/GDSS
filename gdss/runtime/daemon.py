import time
from threading import Thread

from gdss.runtime.context_engine import ContextEngine
from gdss.runtime.event_bus import EventBus
from gdss.runtime.local_observer import LocalObserver
from gdss.runtime.remote_monitor import RemoteMonitor


class GDSSDaemon:
    def __init__(self, repo_path: str, registry_manager, db):
        self.repo_path = repo_path
        self.bus = EventBus()
        self.local_observer = LocalObserver(repo_path, self.bus)
        self.remote_monitor = RemoteMonitor(repo_path, self.bus)

        # Register this repo in DB
        self.repo_id = db.register_repository("auto", repo_path)
        self.context_engine = ContextEngine(self.repo_id, registry_manager, self.bus)

        self.running = False
        self._thread: Thread | None = None

    def start(self):
        self.running = True
        self._thread = Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self.running:
            self.local_observer.scan_once()
            self.remote_monitor.scan_remote()
            time.sleep(5) # Poll every 5 seconds

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()
