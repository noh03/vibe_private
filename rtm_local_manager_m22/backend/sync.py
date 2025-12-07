
"""
sync.py - Tree synchronization logic between JIRA RTM and local SQLite DB.

Currently implements:
- map_rtm_type_to_local
- sync_tree(project, client, conn)

This is the "first milestone" for pulling RTM tree structure into local DB.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .db import upsert_folder, upsert_issue_from_tree, Project
from .jira_api import JiraRTMClient


def map_rtm_type_to_local(node_type: str) -> str:
    mapping = {
        "REQUIREMENT": "REQUIREMENT",
        "TEST_CASE": "TEST_CASE",
        "TEST_PLAN": "TEST_PLAN",
        "TEST_EXECUTION": "TEST_EXECUTION",
        "DEFECT": "DEFECT",
        # some RTM versions may return slightly different labels; map them here if needed
    }
    return mapping.get(node_type.upper(), "UNKNOWN")


def sync_tree(project: Project, client: JiraRTMClient, conn) -> None:
    """
    Download full RTM tree for the given project and store it in local DB.

    NOTE:
    - This function only ensures that folder + minimal issue records exist.
    - Detailed issue fields (status, description, steps, etc.) will be filled in
      later by separate detail sync functions.
    """
    tree = client.get_tree()

    def process_node(node: Dict[str, Any], parent_folder_id: Optional[str] = None, order: int = 0) -> None:
        node_type = node.get("type")
        node_id = node.get("id")
        name = node.get("name") or node.get("summary") or node.get("key") or ""

        if node_type == "FOLDER":
            upsert_folder(
                conn=conn,
                project_id=project.id,
                folder_id=node_id,
                name=name,
                node_type="FOLDER",
                parent_id=parent_folder_id,
                sort_order=order,
            )
            for idx, child in enumerate(node.get("children", [])):
                process_node(child, parent_folder_id=node_id, order=idx)
        else:
            issue_type = map_rtm_type_to_local(node_type or "")
            jira_key = node.get("jiraKey") or node.get("key")
            jira_id = node.get("jiraId")

            upsert_issue_from_tree(
                conn=conn,
                project_id=project.id,
                jira_key=jira_key,
                jira_id=jira_id,
                issue_type=issue_type,
                summary=name,
                folder_id=parent_folder_id,
            )

    # RTM tree root is usually a list of root nodes
    if isinstance(tree, list):
        for idx, root in enumerate(tree):
            process_node(root, parent_folder_id=None, order=idx)
    elif isinstance(tree, dict):
        # some RTM versions may wrap it in an object
        roots = tree.get("roots") or tree.get("children") or []
        for idx, root in enumerate(roots):
            process_node(root, parent_folder_id=None, order=idx)
