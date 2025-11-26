import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class JiraSettings:
    url: str
    token: str


class JiraClient:
    """
    RTM v2.0용 JIRA/RTM REST API 클라이언트 (기본 골격).
    실제 엔드포인트는 Deviniti 문서의 V1 API 스펙에 맞춰 확장 예정.
    """

    def __init__(self, settings: JiraSettings) -> None:
        self._settings = settings

    @property
    def base_url(self) -> str:
        return self._settings.url.rstrip("/")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.request(
            method,
            url,
            headers=self.headers,
            params=params,
            data=json.dumps(data) if data is not None else None,
            timeout=30,
        )
        resp.raise_for_status()
        if not resp.text:
            return {}
        return resp.json()

    # ---- RTM Tree ----
    def get_tree(self, project_id: int) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/tree/{project_id}"
        return self._request("GET", path)

    # ---- 기본 JIRA 이슈 CRUD (표준 /rest/api/2/issue 사용) ----

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """표준 JIRA 이슈 조회"""
        path = f"/rest/api/2/issue/{issue_key}"
        return self._request("GET", path)

    def create_issue(
        self,
        project_id: str,
        issue_type_name: str,
        summary: str,
        description: str = "",
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        표준 JIRA 이슈 생성.
        RTM Requirement/Test Case 등도 JIRA 이슈 타입으로 생성되는 경우 이 메서드를 재사용 가능.
        """
        fields: Dict[str, Any] = {
            "project": {"id": project_id},
            "issuetype": {"name": issue_type_name},
            "summary": summary,
            "description": description,
        }
        if extra_fields:
            fields.update(extra_fields)

        path = "/rest/api/2/issue"
        return self._request("POST", path, data={"fields": fields})

    def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        표준 JIRA 이슈 업데이트.
        fields 딕셔너리에는 변경하고자 하는 필드만 포함.
        """
        path = f"/rest/api/2/issue/{issue_key}"
        return self._request("PUT", path, data={"fields": fields})

    # ---- RTM 전용 리소스 (Deviniti REST V1 스펙 기반 골격) ----
    # 실제 필드 구조는 참조 문서 스펙에 맞게 extra_data를 구성해 넘기면 됨.

    # Requirements
    def list_requirements(self, project_id: int, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/requirements"
        query = {"projectId": project_id}
        if params:
            query.update(params)
        return self._request("GET", path, params=query)

    def create_requirement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/requirements"
        return self._request("POST", path, data=data)

    def update_requirement(self, requirement_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/requirements/{requirement_id}"
        return self._request("PUT", path, data=data)

    def delete_requirement(self, requirement_id: int) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/requirements/{requirement_id}"
        return self._request("DELETE", path)

    # Test Cases
    def list_test_cases(self, project_id: int, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/test-cases"
        query = {"projectId": project_id}
        if params:
            query.update(params)
        return self._request("GET", path, params=query)

    def create_test_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/test-cases"
        return self._request("POST", path, data=data)

    def update_test_case(self, test_case_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-cases/{test_case_id}"
        return self._request("PUT", path, data=data)

    def delete_test_case(self, test_case_id: int) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-cases/{test_case_id}"
        return self._request("DELETE", path)

    # Test Plans
    def list_test_plans(self, project_id: int, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/test-plans"
        query = {"projectId": project_id}
        if params:
            query.update(params)
        return self._request("GET", path, params=query)

    def create_test_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/test-plans"
        return self._request("POST", path, data=data)

    def update_test_plan(self, test_plan_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-plans/{test_plan_id}"
        return self._request("PUT", path, data=data)

    def delete_test_plan(self, test_plan_id: int) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-plans/{test_plan_id}"
        return self._request("DELETE", path)

    # Test Executions
    def list_test_executions(self, project_id: int, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/test-executions"
        query = {"projectId": project_id}
        if params:
            query.update(params)
        return self._request("GET", path, params=query)

    def create_test_execution(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/test-executions"
        return self._request("POST", path, data=data)

    def update_test_execution(self, test_execution_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-executions/{test_execution_id}"
        return self._request("PUT", path, data=data)

    def delete_test_execution(self, test_execution_id: int) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-executions/{test_execution_id}"
        return self._request("DELETE", path)

    # Test Case Executions
    def list_test_case_executions(
        self, test_execution_id: int, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-executions/{test_execution_id}/test-case-executions"
        return self._request("GET", path, params=params)

    def update_test_case_execution(
        self, test_case_execution_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/test-case-executions/{test_case_execution_id}"
        return self._request("PUT", path, data=data)

    # Defects
    def list_defects(self, project_id: int, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/defects"
        query = {"projectId": project_id}
        if params:
            query.update(params)
        return self._request("GET", path, params=query)

    def create_defect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path = "/rest/rtm/1.0/api/defects"
        return self._request("POST", path, data=data)

    def update_defect(self, defect_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/defects/{defect_id}"
        return self._request("PUT", path, data=data)

    def delete_defect(self, defect_id: int) -> Dict[str, Any]:
        path = f"/rest/rtm/1.0/api/defects/{defect_id}"
        return self._request("DELETE", path)


