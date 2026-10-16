import time
from threading import Thread

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.drift.engine import DriftEngine
from gdss.drift.history import SnapshotHistory, default_history_path
from gdss.drift.monitor import DriftMonitor
from gdss.runtime.context_engine import ContextEngine
from gdss.runtime.event_bus import EventBus
from gdss.runtime.local_observer import LocalObserver
from gdss.runtime.remote_monitor import RemoteMonitor
from gdss.watcher.git_observer import GitObserver


class GDSSDaemon:
    def __init__(self, repo_path: str, registry_manager, db, drift_every: int = 3):
        self.repo_path = repo_path
        self.bus = EventBus()
        self.local_observer = LocalObserver(repo_path, self.bus)
        self.remote_monitor = RemoteMonitor(repo_path, self.bus)

        # Register this repo in DB
        self.repo_id = db.register_repository("auto", repo_path)
        self.context_engine = ContextEngine(self.repo_id, registry_manager, self.bus)

        observer = GitObserver(repo_path)
        parser = ASTParser()
        extractor = TransformExtractor()
        engine = DriftEngine(
            observer=observer,
            parser=parser,
            extractor=extractor,
            history=SnapshotHistory(default_history_path(repo_path)),
        )
        self.drift_monitor = DriftMonitor(
            observer=observer,
            parser=parser,
            extractor=extractor,
            bus=self.bus,
            engine=engine,
        )
        self.drift_every = max(1, drift_every)
        self._loop_count = 0

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
            self._loop_count += 1
            if self._loop_count % self.drift_every == 0:
                try:
                    ref = self.context_engine.get_reference_branch()
                    self.drift_monitor.scan_once(ref)
                except Exception:
                    pass
            time.sleep(5)  # Poll every 5 seconds

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()
