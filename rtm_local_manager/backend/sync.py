
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


def sync_tree(project: Project, client: JiraRTMClient, conn, tree_types: Optional[list[str]] = None) -> None:
    """
    Download RTM tree for the given project and store it in local DB.

    NOTE:
    - 기본적으로 requirements / test-cases / test-plans / test-executions / defects
      5개 treeType 에 대해 순차적으로 트리를 조회하여 병합 저장한다.
    - 이 함수는 폴더 + 최소한의 이슈 레코드만 보장하며,
      상세 필드(status, description, steps 등)는 별도 동기화 단계에서 채운다.

    :param tree_types: 사용할 RTM treeType 목록.
                       None 이면 ["requirements", "test-cases", "test-plans",
                                 "test-executions", "defects"] 를 기본값으로 사용한다.
    """
    if tree_types is None:
        tree_types = ["requirements", "test-cases", "test-plans", "test-executions", "defects"]

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

    for tt in tree_types:
        tree = client.get_tree(tree_type=tt)

        # RTM tree root is usually a list of root nodes
        if isinstance(tree, list):
            for idx, root in enumerate(tree):
                process_node(root, parent_folder_id=None, order=idx)
        elif isinstance(tree, dict):
            # some RTM versions may wrap it in an object
            roots = tree.get("roots") or tree.get("children") or []
            for idx, root in enumerate(roots):
                process_node(root, parent_folder_id=None, order=idx)
