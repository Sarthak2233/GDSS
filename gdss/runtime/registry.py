import json
import yaml
from typing import Dict, Any, List, Optional
from gdss.storage.db import RuntimeDB

class RepositoryRegistry:
    def __init__(self, db: RuntimeDB):
        self.db = db

    def update_branch_state(self, repo_id: int, name: str, remote_name: Optional[str] = None, is_local: bool = True):
        # First check if branch exists to avoid duplication
        branches = self.db.get_branches(repo_id)
        exists = any(b['name'] == name for b in branches)
        if not exists:
            self.db.register_branch(repo_id, name, remote_name, is_local)
        else:
            # Update existing branch logic could go here
            pass

    def get_branches(self, repo_id: int) -> List[Dict[ Any, Any]]:
        return self.db.get_branches(repo_id)

    def set_hierarchy_config(self, repo_id: int, config: Dict[str, Any]):
        from gdss.runtime.hierarchy import HierarchyManager
        hm = HierarchyManager(self.db)
        hm.set_config(repo_id, config)

    def get_hierarchy(self, repo_id: int) -> Dict[str, Any]:
        from gdss.runtime.hierarchy import HierarchyManager
        hm = HierarchyManager(self.db)
        return hm.get_config(repo_id)
