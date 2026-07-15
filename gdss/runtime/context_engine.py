import json
import time
from gdss.runtime.event_bus import EventBus
from gdss.runtime.registry import RepositoryRegistry
from gdss.runtime.hierarchy import HierarchyManager

class ContextEngine:
    def __init__(self, repo_id: int, registry: RepositoryRegistry, bus: EventBus):
        self.repo_id = repo_id
        self.registry = registry
        self.hierarchy = HierarchyManager(registry.db)
        self.bus = bus
        self.bus.subscribe("all", self.on_any_event)

    def on_any_event(self, event_packet: dict):
        topic = event_packet['topic']
        data = event_packet['data']
        
        # Construct Awareness Packet
        packet = {
            "source": topic,
            "event": data.get("event"),
            "timestamp": data.get("timestamp", time.time()),
            "repo_id": self.repo_id,
            "reference_branch": self.get_reference_branch(),
            "remote_aware": topic == "remote",
            "semantic_operators": data.get("semantic_operators", [])
        }
        
        # Log to DB
        self.log_context(packet)

    def get_reference_branch(self) -> str:
        config = self.hierarchy.get_config(self.repo_id)
        if config.get("reference_branch"):
            return str(config["reference_branch"])
        chain = self.hierarchy.resolve_priority_chain(self.repo_id, "HEAD")
        return chain[-1] if chain else "main"

    def set_reference_branch(self, branch: str) -> None:
        config = self.hierarchy.get_config(self.repo_id)
        config = dict(config) if config else {}
        config["reference_branch"] = branch
        # Keep production attractor aligned with the configured reference.
        hierarchy = dict(config.get("hierarchy") or {})
        hierarchy["production"] = branch
        config["hierarchy"] = hierarchy
        self.hierarchy.set_config(self.repo_id, config)

    def log_context(self, packet: dict):
        with self.registry.db._get_connection() as conn:
            conn.execute(
                "INSERT INTO contexts (repo_id, packet) VALUES (?, ?)",
                (self.repo_id, json.dumps(packet))
            )

    def get_latest_context(self) -> dict:
        with self.registry.db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT packet FROM contexts WHERE repo_id = ? ORDER BY id DESC LIMIT 1",
                (self.repo_id,)
            )
            row = cursor.fetchone()
            return json.loads(row['packet']) if row else {}
