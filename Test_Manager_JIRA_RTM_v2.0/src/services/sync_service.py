from datetime import datetime
from typing import Any, Dict, Optional

from api.jira_client import JiraClient
from database.repository import issue_repository


class SyncService:
    """
    JIRA RTM <-> 로컬 DB 동기화 서비스 (v2.0 기본 골격).

    현재는 Tree 구조를 기준으로 Requirement/Test Case 등 이슈를
    단순 upsert 하는 수준이며, 상세 필드 매핑은 점진적으로 확장할 수 있습니다.
    """

    def __init__(self, jira_client: JiraClient) -> None:
        self.jira_client = jira_client

    def sync_tree(self, project_id: int = 41500) -> None:
        """RTM Tree 전체를 가져와 로컬 DB에 반영."""
        tree_data = self.jira_client.get_tree(project_id)

        # 트리 루트 구조는 Deviniti RTM 스펙에 따라 달라질 수 있으므로
        # 리스트 / dict(roots 포함) 모두 처리
        if isinstance(tree_data, list):
            for node in tree_data:
                self._sync_node(node, parent_key=None)
        elif isinstance(tree_data, dict):
            roots = tree_data.get("roots") or tree_data.get("children") or [tree_data]
            for node in roots:
                self._sync_node(node, parent_key=None)

    # 내부 유틸

    def _map_issue_type(self, raw_type: Optional[str]) -> str:
        """
        RTM 트리 노드의 type/issueType 값을 우리 로컬 issue_type으로 매핑.
        실제 값은 Deviniti 문서를 참고해 보완할 수 있음.
        """
        if not raw_type:
            return "Requirement"

        t = raw_type.lower()
        if "requirement" in t:
            return "Requirement"
        if "test case" in t or "test_case" in t:
            return "Test Case"
        if "test plan" in t or "test_plan" in t:
            return "Test Plan"
        if "test execution" in t or "test_execution" in t:
            return "Test Execution"
        if "defect" in t or "bug" in t:
            return "Defect"
        return "Requirement"

    def _sync_node(self, node: Dict[str, Any], parent_key: Optional[str]) -> None:
        """
        단일 트리 노드를 로컬 DB에 반영하고, children 재귀 처리.
        """
        name = node.get("name") or node.get("summary") or ""
        issue_key = node.get("issueKey") or node.get("key")
        status = node.get("status")
        raw_type = node.get("issueType") or node.get("type")
        issue_type = self._map_issue_type(raw_type)

        # 폴더/루트 노드 등 issueKey가 없는 노드는 DB에 이슈로 저장하지 않고 트리에서만 사용
        if issue_key:
            data = {
                "issue_key": issue_key,
                "summary": name,
                "issue_type": issue_type,
                "status": status,
                "parent_key": parent_key,
                # 동기화 메타
                "sync_status": "clean",
                "last_synced_at": datetime.utcnow(),
            }
            issue_repository.upsert_issue_from_jira(issue_type, issue_key, data)

        # 자식 노드 처리
        children = node.get("children") or []
        # 일부 스펙에서는 'nodes' 나 'items' 등 다른 키를 쓸 수도 있어 확장 여지 남김
        if isinstance(children, list):
            for child in children:
                self._sync_node(child, parent_key=issue_key or parent_key)

    # ---------- 로컬 -> JIRA 푸시 ----------

    def push_dirty_issues(self, project_id: int = 41500) -> int:
        """
        로컬에서 dirty 상태인 이슈들을 JIRA로 반영.

        - NEW-로 시작하는 key: 새 이슈로 생성
        - 그 외: 기존 JIRA 이슈 업데이트 (summary/description 정도만)
        """
        dirty_items = issue_repository.get_dirty_issues()
        pushed = 0

        for item in dirty_items:
            issue_type = item.get("issue_type", "Requirement")
            issue_key = item.get("issue_key")
            summary = item.get("summary", "")
            description = item.get("description", "") or ""

            try:
                if issue_key and str(issue_key).startswith("NEW-"):
                    # 신규 생성
                    created = self.jira_client.create_issue(
                        project_id=str(project_id),
                        issue_type_name=issue_type,
                        summary=summary,
                        description=description,
                    )
                    new_key = created.get("key")
                    if new_key:
                        # 로컬 issue_key를 실제 JIRA key로 교체
                        issue_repository.update_issue_key(issue_type, issue_key, new_key)
                        issue_repository.mark_issue_clean(issue_type, new_key)
                elif issue_key:
                    # 기존 이슈 업데이트
                    self.jira_client.update_issue(
                        issue_key=issue_key,
                        fields={
                            "summary": summary,
                            "description": description,
                        },
                    )
                    issue_repository.mark_issue_clean(issue_type, issue_key)

                pushed += 1
            except Exception:
                # 개별 이슈 푸시에 실패해도 전체 루프는 계속 진행
                continue

        return pushed


