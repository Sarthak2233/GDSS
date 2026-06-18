import json
import yaml
import os
from typing import Dict, Any, List, Optional
from gdss.storage.db import RuntimeDB

class HierarchyManager:
    """
    Layer 3: Distributed Hierarchy Manager.
    Resolves branch priorities and development trajectories.
    """
    def __init__(self, db: RuntimeDB):
        self.db = db

    def set_config(self, repo_id: int, config: Dict[str, Any]):
        with self.db._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hierarchies (repo_id, config_payload) VALUES (?, ?)",
                (repo_id, json.dumps(config))
            )

    def get_config(self, repo_id: int) -> Dict[str, Any]:
        with self.db._get_connection() as conn:
            cursor = conn.execute("SELECT config_payload FROM hierarchies WHERE repo_id = ?", (repo_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row['config_payload'])
            return {}

    def resolve_priority_chain(self, repo_id: int, current_branch: str) -> List[str]:
        config = self.get_config(repo_id)
        if not config:
            return ["main"] # Default trajectory
            
        hierarchy = config.get("hierarchy", {})
        chain = []
        # Trajectory: dev -> staging -> main
        if 'development' in hierarchy:
            chain.append(hierarchy['development'])
        if 'staging' in hierarchy:
            chain.append(hierarchy['staging'])
        if 'production' in hierarchy:
            chain.append(hierarchy['production'])
            
        return chain if chain else ["main"]
