"""
jira_api.py - REST client wrapper for JIRA RTM (Deviniti RTM for Jira Data Center).

역할:
- Personal Access Token 기반 인증 처리
- RTM 관련 주요 엔드포인트에 대한 thin wrapper 제공
  - Tree 구조
  - Requirement / Test Case / Test Plan / Test Execution / Defect (기본 CRUD)

※ 주의
- 실제 RTM REST API의 JSON 구조/필드명은 버전에 따라 다를 수 있다.
- 이 모듈은 "골격"을 제공하며, 현장 환경에 맞춰 엔드포인트 path와 payload mapping을
  조정해야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

from .logger import get_logger

import json
import requests
from requests.auth import HTTPBasicAuth


# 각 기능별 기본 엔드포인트 템플릿
DEFAULT_ENDPOINTS: Dict[str, str] = {
    # Tree
    # RTM REST API 기준:
    #   - V2: /api/v2/tree/{projectId}/{treeType}
    #   - V1: /api/tree/{projectId}/{treeType}
    # 여기서는 호환성을 위해 /api/tree/... 형태를 기본으로 사용하되,
    # Settings > REST API Endpoint Settings... 에서 자유롭게 변경 가능하다.
    #
    # 세미콜론(;) 으로 여러 버전의 엔드포인트를 나열하면,
    # 코드에서 순서대로 시도할 수 있도록 설계되어 있다.
    # 예: "/v1/tree/...; /v2/tree/..."
    "tree_get": "/rest/rtm/1.0/api/tree/{projectId}/{treeType};/rest/rtm/1.0/api/v2/tree/{projectId}/{treeType}",
    "tree_folder_create": "/rest/rtm/1.0/api/tree/{projectId}/folder",
    "tree_folder_update": "/rest/rtm/1.0/api/tree/{testKey}/folder",
    "tree_folder_delete": "/rest/rtm/1.0/api/tree/{testKey}/folder",
    # Jira 이슈/검색/링크/메타
    "jira_issue_get": "/rest/api/2/issue/{key}",
    "jira_issue_comments": "/rest/api/2/issue/{key}/comment",
    "jira_issue_comment": "/rest/api/2/issue/{key}/comment/{id}",
    "jira_attachment_add": "/rest/api/2/issue/{key}/attachments",
    "jira_attachment_delete": "/rest/api/2/attachment/{id}",
    "jira_search": "/rest/api/2/search",
    "jira_issue_link_types": "/rest/api/2/issueLinkType",
    "jira_priorities": "/rest/api/2/priority",
    "jira_statuses": "/rest/api/2/status",
    "jira_project": "/rest/api/2/project/{projectKey}",
    "jira_issue_link": "/rest/api/2/issueLink",
    "jira_issue_create": "/rest/api/2/issue",
    # RTM 엔티티
    "rtm_requirement": "/rest/rtm/1.0/api/requirement/{testKey}",
    "rtm_test_case": "/rest/rtm/1.0/api/test-case/{testKey}",
    "rtm_test_plan": "/rest/rtm/1.0/api/test-plan/{testKey}",
    "rtm_test_execution": "/rest/rtm/1.0/api/test-execution/{testKey}",
    "rtm_defect": "/rest/rtm/1.0/api/defect/{testKey}",
    "rtm_requirement_create": "/rest/rtm/1.0/api/requirement",
    "rtm_test_case_create": "/rest/rtm/1.0/api/test-case",
    "rtm_test_plan_create": "/rest/rtm/1.0/api/test-plan",
    "rtm_test_execution_create": "/rest/rtm/1.0/api/test-execution",
    "rtm_defect_create": "/rest/rtm/1.0/api/defect",
    # Test Case steps
    "rtm_testcase_steps": "/rest/rtm/1.0/api/test-case/{testKey}/steps",
    # Test Plan / Test Execution
    "rtm_testplan_testcases": "/rest/rtm/1.0/api/test-plan/{testKey}/testcases",
    "rtm_testexecution": "/rest/rtm/1.0/api/test-execution/{testKey}",
    "rtm_testexecution_execute": "/rest/rtm/1.0/api/test-execution/execute/{testPlanKey}",
    "rtm_testexecution_testcases": "/rest/rtm/1.0/api/test-execution/{testKey}/testcases",
    # Test Case Execution
    "rtm_tce": "/rest/rtm/1.0/api/test-case-execution/{testKey}",
    "rtm_tce_step_status": "/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/status",
    "rtm_tce_step_comment": "/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment",
    "rtm_tce_defect": "/rest/rtm/1.0/api/test-case-execution/{testKey}/defect",
    "rtm_tce_defect_item": "/rest/rtm/1.0/api/test-case-execution/{testKey}/defect/{defectTestKey}",
    "rtm_tce_attachment": "/rest/rtm/1.0/api/test-case-execution/{testKey}/attachment/{attachmentId}",
    # TCE comments
    "rtm_tce_comments": "/rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments",
    "rtm_tce_comment": "/rest/rtm/1.0/api/test-case-execution-comment/comments/{id}",
}


# 각 엔드포인트 key 별로, path 템플릿에서 사용 가능한 플레이스홀더 이름 목록
# - 엔드포인트 설정 다이얼로그에서 유효성 검사에 사용한다.
DEFAULT_ENDPOINT_PARAMS: Dict[str, List[str]] = {
    "tree_get": ["projectId", "treeType"],
    "tree_folder_create": ["projectId"],
    "tree_folder_update": ["testKey"],
    "tree_folder_delete": ["testKey"],
    "jira_issue_get": ["key"],
    "jira_issue_comments": ["key"],
    "jira_issue_comment": ["key", "id"],
    "jira_attachment_add": ["key"],
    "jira_attachment_delete": ["id"],
    "jira_search": [],
    "jira_issue_link_types": [],
    "jira_priorities": [],
    "jira_statuses": [],
    "jira_project": ["projectKey"],
    "jira_issue_link": [],
    "jira_issue_create": [],
    "rtm_requirement": ["testKey"],
    "rtm_test_case": ["testKey"],
    "rtm_test_plan": ["testKey"],
    "rtm_test_execution": ["testKey"],
    "rtm_defect": ["testKey"],
    "rtm_requirement_create": [],
    "rtm_test_case_create": [],
    "rtm_test_plan_create": [],
    "rtm_test_execution_create": [],
    "rtm_defect_create": [],
    "rtm_testcase_steps": ["testKey"],
    "rtm_testplan_testcases": ["testKey"],
    "rtm_testexecution": ["testKey"],
    "rtm_testexecution_execute": ["testPlanKey"],
    "rtm_testexecution_testcases": ["testKey"],
    "rtm_tce": ["testKey"],
    "rtm_tce_step_status": ["testKey", "stepIndex"],
    "rtm_tce_step_comment": ["testKey", "stepIndex"],
    "rtm_tce_defect": ["testKey"],
    "rtm_tce_defect_item": ["testKey", "defectTestKey"],
    "rtm_tce_attachment": ["testKey", "attachmentId"],
    "rtm_tce_comments": ["testKey"],
    "rtm_tce_comment": ["id"],
}


@dataclass
class JiraConfig:
    base_url: str           # e.g. "https://jira.example.com"
    username: str           # Jira username (또는 로그인 ID)
    api_token: str          # Jira 비밀번호 또는 Personal Access Token
    project_key: str        # e.g. "KVHSICCU"
    project_id: int         # e.g. 41500
    endpoints: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ENDPOINTS))


class JiraRTMClient:
    def __init__(self, config: JiraConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.logger = get_logger(__name__)

    # ------------------------------------------------------------------ endpoint helper

    def _ep(self, key: str, default_path: str) -> str:
        """
        설정에서 엔드포인트(path 템플릿)를 조회한다.
        - jira_config.json 에 endpoints[key] 가 있으면 그것을 사용
        - 없으면 코드 내 기본값(default_path)을 사용
        """
        if getattr(self.config, "endpoints", None) and key in self.config.endpoints:
            return self.config.endpoints[key]  # type: ignore[return-value]
        return default_path

    def _endpoint_candidates(self, key: str, default_path: str) -> List[str]:
        """
        주어진 logical key 에 대해 시도할 엔드포인트 템플릿 목록을 반환한다.
        - jira_config.json 의 endpoints[key] 가:
          - 문자열인 경우: 세미콜론(;) 으로 분리하여 여러 후보를 순서대로 사용
          - 리스트인 경우: 리스트 순서대로 사용
        - 설정에 값이 없으면 default_path 하나만 사용.
        """
        eps = getattr(self.config, "endpoints", None) or {}
        raw = eps.get(key)

        candidates: List[str] = []
        if isinstance(raw, list):
            for p in raw:
                s = str(p).strip()
                if s:
                    candidates.append(s)
        elif isinstance(raw, str):
            for part in raw.split(";"):
                s = part.strip()
                if s:
                    candidates.append(s)

        if not candidates:
            candidates = [default_path]

        return candidates

    # ------------------------------------------------------------------ low-level

    def _headers(self) -> Dict[str, str]:
        """공통 JSON 헤더 (Basic Auth는 HTTPBasicAuth에서 처리)."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, *, headers: Dict[str, str] | None = None, **kwargs) -> Any:
        """
        path: "/rest/rtm/1.0/api/...." 와 같은 RTM 상대 경로
        Basic Auth(username + api_token)을 사용하여 요청을 보낸다.
        """
        url = self.base_url + path
        auth = HTTPBasicAuth(self.config.username, self.config.api_token)
        if headers is None:
            headers = self._headers()
        self.logger.debug(
            "JIRA request %s %s kwargs=%s",
            method,
            url,
            {k: v for k, v in kwargs.items() if k != "json"},
        )
        # 네트워크 장애 시 GUI 가 오래 멈추지 않도록, 보수적인 기본 timeout 을 부여한다.
        if "timeout" not in kwargs:
            kwargs["timeout"] = 5.0

        resp = requests.request(method, url, headers=headers, auth=auth, **kwargs)
        self.logger.debug("JIRA response status=%s", resp.status_code)
        try:
            resp.raise_for_status()
        except Exception:
            self.logger.exception("JIRA request failed: %s %s", method, url)
            raise
        if not resp.text:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # ------------------------------------------------------------------ tree

    def get_tree(self, project_id: Optional[int] = None, tree_type: str | None = None) -> Any:
        """
        RTM Tree 구조 조회.
        - RTM REST API 기준:
          - V2: GET /api/v2/tree/{projectId}/{treeType}
          - V1: GET /api/tree/{projectId}/{treeType}
        - DEFAULT_ENDPOINTS 에서는 /rest/rtm/1.0/api/tree/{projectId}/{treeType} 를 기본값으로 사용한다.

        :param project_id: JIRA 프로젝트 ID (생략 시 JiraConfig.project_id 사용)
        :param tree_type: RTM 트리 타입.
                          문서 기준으로 대표적인 값은 다음과 같다.
                          - REQUIREMENTS
                          - TEST_CASES
                          - TEST_PLANS
                          - TEST_EXECUTIONS
                          (필요 시 Settings > REST API Endpoint Settings... 에서
                           각 인스턴스에 맞는 값을 사용할 수 있다.)
        """
        pid = project_id if project_id is not None else self.config.project_id

        last_exc: Exception | None = None
        for path_tpl in self._endpoint_candidates(
            "tree_get", "/rest/rtm/1.0/api/tree/{projectId}/{treeType}"
        ):
            fmt_args: Dict[str, Any] = {"projectId": pid}

            # 엔드포인트 템플릿에 treeType 플레이스홀더가 포함된 경우에만 값을 채운다.
            if "{treeType}" in path_tpl:
                # 별도 인자가 없으면 기본값 "requirements" 사용
                # (RTM REST API 문서: treeType ∈ {requirements, test-cases, test-plans, test-executions, defects})
                tt = (tree_type or "requirements").strip()
                fmt_args["treeType"] = tt

            try:
                return self._request("GET", path_tpl.format(**fmt_args))
            except Exception as e:
                last_exc = e
                self.logger.warning(
                    "tree_get failed for endpoint '%s': %s", path_tpl, e
                )

        if last_exc:
            raise last_exc
        raise RuntimeError("No valid endpoint for tree_get")

    def create_tree_folder(self, project_id: Optional[int], name: str, parent_test_key: str | None = None, issue_type: str | None = None) -> Any:
        """
        RTM Tree 에 새 폴더를 생성한다.

        사양서 기준 엔드포인트:
          POST /rest/rtm/1.0/api/tree/{projectId}/folder

        실제 RTM 버전에 따라 payload 형식은 달라질 수 있으므로,
        여기서는 최소한의 정보(name, parent, issueType)를 포함하는 예시 payload 를 사용한다.
        """
        pid = project_id if project_id is not None else self.config.project_id
        payload: Dict[str, Any] = {"name": name}
        if parent_test_key:
            payload["parentTestKey"] = parent_test_key
        if issue_type:
            payload["issueType"] = issue_type
        path_tpl = self._ep("tree_folder_create", "/rest/rtm/1.0/api/tree/{projectId}/folder")
        return self._request("POST", path_tpl.format(projectId=pid), json=payload)

    def update_tree_folder(self, test_key: str, name: Optional[str] = None, parent_test_key: str | None = None) -> Any:
        """
        기존 트리 폴더의 이름/위치를 수정한다.

        사양서 기준 엔드포인트:
          PUT /rest/rtm/1.0/api/tree/{testKey}/folder
        """
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if parent_test_key is not None:
            payload["parentTestKey"] = parent_test_key
        path_tpl = self._ep("tree_folder_update", "/rest/rtm/1.0/api/tree/{testKey}/folder")
        return self._request("PUT", path_tpl.format(testKey=test_key), json=payload)

    def delete_tree_folder(self, test_key: str) -> Any:
        """
        기존 트리 폴더를 삭제한다.

        사양서 기준 엔드포인트:
          DELETE /rest/rtm/1.0/api/tree/{testKey}/folder
        """
        path_tpl = self._ep("tree_folder_delete", "/rest/rtm/1.0/api/tree/{testKey}/folder")
        return self._request("DELETE", path_tpl.format(testKey=test_key))

    # ------------------------------------------------------------------ core Jira issue (standard REST)

    def get_jira_issue(self, jira_key: str, expand: str | None = None) -> Any:
        """
        표준 Jira Issue REST API 를 사용하여 개별 이슈를 조회한다.

        - 경로: GET /rest/api/2/issue/{key}
        - 응답 JSON 은 jira_mapping.map_jira_to_local() 과
          extract_relations_from_jira() 의 입력으로 사용된다.

        :param jira_key: 이슈 키 (예: "PROJ-1")
        :param expand: comments, changelog 등 확장 필드가 필요할 때
                       "comments,changelog" 형태로 지정 (선택 사항)
        """
        params: Dict[str, Any] | None = None
        if expand:
            params = {"expand": expand}
        path_tpl = self._ep("jira_issue_get", "/rest/api/2/issue/{key}")
        return self._request("GET", path_tpl.format(key=jira_key), params=params)

    # ---------------------------- Jira comments -----------------------------

    def get_issue_comments(self, jira_key: str) -> Any:
        """
        JIRA 이슈의 댓글 목록을 조회한다.

        GET /rest/api/2/issue/{issueIdOrKey}/comment
        """
        path_tpl = self._ep("jira_issue_comments", "/rest/api/2/issue/{key}/comment")
        return self._request("GET", path_tpl.format(key=jira_key))

    def add_issue_comment(self, jira_key: str, text: str) -> Any:
        """
        JIRA 이슈에 새 댓글을 추가한다.

        POST /rest/api/2/issue/{issueIdOrKey}/comment
        Body: { "body": "comment text" }
        """
        payload = {"body": text}
        path_tpl = self._ep("jira_issue_comments", "/rest/api/2/issue/{key}/comment")
        return self._request("POST", path_tpl.format(key=jira_key), json=payload)

    def update_issue_comment(self, jira_key: str, comment_id: str | int, text: str) -> Any:
        """
        기존 댓글을 수정한다.

        PUT /rest/api/2/issue/{issueIdOrKey}/comment/{id}
        """
        payload = {"body": text}
        path_tpl = self._ep("jira_issue_comment", "/rest/api/2/issue/{key}/comment/{id}")
        return self._request("PUT", path_tpl.format(key=jira_key, id=comment_id), json=payload)

    def delete_issue_comment(self, jira_key: str, comment_id: str | int) -> Any:
        """
        댓글을 삭제한다.

        DELETE /rest/api/2/issue/{issueIdOrKey}/comment/{id}
        """
        path_tpl = self._ep("jira_issue_comment", "/rest/api/2/issue/{key}/comment/{id}")
        return self._request("DELETE", path_tpl.format(key=jira_key, id=comment_id))

    # ---------------------------- Jira attachments --------------------------

    def add_issue_attachment_from_path(self, jira_key: str, file_path: str) -> Any:
        """
        로컬 파일을 JIRA 이슈 첨부로 업로드한다.

        POST /rest/api/2/issue/{issueIdOrKey}/attachments
        - 헤더: X-Atlassian-Token: no-check
        - multipart/form-data 로 전송
        """
        headers = {"X-Atlassian-Token": "no-check"}
        with open(file_path, "rb") as f:
            files = {"file": (file_path, f)}
            # 첨부 업로드 시에는 Content-Type 헤더를 requests 가 자동 설정하도록 둔다.
            path_tpl = self._ep("jira_attachment_add", "/rest/api/2/issue/{key}/attachments")
            return self._request("POST", path_tpl.format(key=jira_key), headers=headers, files=files)

    def delete_issue_attachment(self, attachment_id: str | int) -> Any:
        """
        첨부파일을 삭제한다.

        DELETE /rest/api/2/attachment/{id}
        """
        path_tpl = self._ep("jira_attachment_delete", "/rest/api/2/attachment/{id}")
        return self._request("DELETE", path_tpl.format(id=attachment_id))

    # ------------------------------------------------------------------ Jira issue search (JQL)

    def search_issues(self, jql: str, max_results: int = 50, start_at: int = 0) -> Any:
        """
        JQL 로 Jira 이슈를 검색한다.

        Jira Server/Data Center REST API (예: [Jira REST API 9.12.0](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.0/))
        의 표준 검색 엔드포인트를 사용:

            GET /rest/api/2/search?jql=...&startAt=...&maxResults=...

        응답 JSON 구조:
          {
            "startAt": 0,
            "maxResults": 50,
            "total": 123,
            "issues": [ { "key": "...", "fields": {...} }, ... ]
          }
        """
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
        }
        path_tpl = self._ep("jira_search", "/rest/api/2/search")
        return self._request("GET", path_tpl, params=params)

    # ------------------------------------------------------------------ Jira issue link types

    def get_issue_link_types(self) -> Any:
        """
        JIRA 에 정의된 issue link type 목록을 조회한다.

        Jira REST API (예: [Jira REST API 9.12.0](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.0/))
        의 표준 엔드포인트:

            GET /rest/api/2/issueLinkType

        응답 예:
          {
            "issueLinkTypes": [
              { "id": "10000", "name": "Relates", "inward": "relates to", "outward": "relates to" },
              { "id": "10001", "name": "Blocks", "inward": "is blocked by", "outward": "blocks" },
              ...
            ]
          }
        """
        path_tpl = self._ep("jira_issue_link_types", "/rest/api/2/issueLinkType")
        return self._request("GET", path_tpl)

    # ------------------------------------------------------------------ Jira metadata (fields, priorities, statuses, project)

    def get_priorities(self) -> Any:
        """
        JIRA 에 정의된 Priority 목록 조회.

        GET /rest/api/2/priority
        """
        path_tpl = self._ep("jira_priorities", "/rest/api/2/priority")
        return self._request("GET", path_tpl)

    def get_statuses(self) -> Any:
        """
        JIRA 에 정의된 Workflow Status 목록 조회.

        GET /rest/api/2/status
        """
        path_tpl = self._ep("jira_statuses", "/rest/api/2/status")
        return self._request("GET", path_tpl)

    def get_project_metadata(self, project_key: str | None = None) -> Any:
        """
        프로젝트 메타데이터 조회 (components, versions 등).

        GET /rest/api/2/project/{projectKey}
        """
        key = project_key or self.config.project_key
        path_tpl = self._ep("jira_project", "/rest/api/2/project/{projectKey}")
        return self._request("GET", path_tpl.format(projectKey=key))

    # ------------------------------------------------------------------ helpers (generic issue-level mapping)

    # 아래 메서드들은 Deviniti RTM REST API 문서(RTM REST API.md)를 기준으로 한다.
    # base URL:
    #   http(s)://SERVER[:PORT]/[CONTEXT]/rest/rtm/1.0/api
    #
    # 엔드포인트 패턴:
    # - Requirement:      /rest/rtm/1.0/api/requirement/{testKey}
    # - Test Case:        /rest/rtm/1.0/api/test-case/{testKey}
    # - Test Plan:        /rest/rtm/1.0/api/test-plan/{testKey}
    # - Test Execution:   /rest/rtm/1.0/api/test-execution/{testKey}
    # - Defect:           /rest/rtm/1.0/api/defect/{testKey}
    #
    # 실제 path가 다르다면 여기에서 수정하면 된다.

    def _entity_path(self, issue_type: str, key: str) -> str:
        t = issue_type.upper()
        if t == "REQUIREMENT":
            return self._ep("rtm_requirement", "/rest/rtm/1.0/api/requirement/{testKey}").format(testKey=key)
        if t == "TEST_CASE":
            return self._ep("rtm_test_case", "/rest/rtm/1.0/api/test-case/{testKey}").format(testKey=key)
        if t == "TEST_PLAN":
            return self._ep("rtm_test_plan", "/rest/rtm/1.0/api/test-plan/{testKey}").format(testKey=key)
        if t == "TEST_EXECUTION":
            return self._ep("rtm_test_execution", "/rest/rtm/1.0/api/test-execution/{testKey}").format(testKey=key)
        if t == "DEFECT":
            return self._ep("rtm_defect", "/rest/rtm/1.0/api/defect/{testKey}").format(testKey=key)
        # fallback: 일반 Jira Issue REST 사용 (예: /rest/api/2/issue/{key})
        return self._ep("jira_issue_get", "/rest/api/2/issue/{key}").format(key=key)

    # ---------------------------- pull (GET) -----------------------------

    def get_entity(self, issue_type: str, jira_key: str) -> Any:
        """
        issue_type 에 따라 적절한 RTM 엔드포인트로 GET 수행.
        """
        path = self._entity_path(issue_type, jira_key)
        return self._request("GET", path)

    # ---------------------------- push (PUT) -----------------------------

    def update_entity(self, issue_type: str, jira_key: str, payload: Dict[str, Any]) -> Any:
        """
        issue_type 에 따라 적절한 RTM 엔드포인트로 PUT 수행.

        payload 구조는 실제 RTM API 문서를 참고해서 맞춰야 하며,
        로컬 DB ↔ JIRA 간의 필드 매핑은 별도 레이어에서 구성하는 것이 좋다.
        """
        path = self._entity_path(issue_type, jira_key)
        return self._request("PUT", path, json=payload)


    # ---------------------------- delete (DELETE) -----------------------------

    def delete_entity(self, issue_type: str, jira_key: str) -> Any:
        """
        issue_type 에 따라 적절한 RTM 엔드포인트로 DELETE 수행.

        기본적으로 _entity_path() 에서 사용하는 path 에 대해 HTTP DELETE 를 호출한다.
        RTM에서 별도의 삭제 정책이 있는 경우, 현장 환경에 맞게 endpoint를 조정해야 한다.
        """
        path = self._entity_path(issue_type, jira_key)
        return self._request("DELETE", path)

    # ---------------------------- create (POST) --------------------------

    def create_entity(self, issue_type: str, payload: Dict[str, Any]) -> Any:
        """
        새 RTM entity 생성.

        Requirement, Test Case 등 엔티티 타입별 POST path는 실제 RTM 문서를
        참고해서 필요 시 별도 분기 처리하도록 한다.
        """
        t = issue_type.upper()
        if t == "REQUIREMENT":
            path = self._ep("rtm_requirement_create", "/rest/rtm/1.0/api/requirement")
        elif t == "TEST_CASE":
            path = self._ep("rtm_test_case_create", "/rest/rtm/1.0/api/test-case")
        elif t == "TEST_PLAN":
            path = self._ep("rtm_test_plan_create", "/rest/rtm/1.0/api/test-plan")
        elif t == "TEST_EXECUTION":
            path = self._ep("rtm_test_execution_create", "/rest/rtm/1.0/api/test-execution")
        elif t == "DEFECT":
            path = self._ep("rtm_defect_create", "/rest/rtm/1.0/api/defect")
        else:
            # fallback: 일반 Jira 이슈 생성 (예: /rest/api/2/issue)
            path = self._ep("jira_issue_create", "/rest/api/2/issue")
        return self._request("POST", path, json=payload)




    # ------------------------------------------------------------------ Test Case steps (RTM specific, skeleton)

    def get_testcase_steps(self, jira_key: str) -> Any:
        """
        RTM Test Case의 Steps 정보를 조회한다.

        실제 Deviniti RTM REST 문서를 참고하여 endpoint path를 조정해야 한다.
        공식 문서에는 별도 steps 엔드포인트가 명시되어 있지 않으므로,
        여기서는 예시로 다음과 같은 패턴을 사용한다:

            GET /rest/rtm/1.0/api/test-case/{testKey}/steps

        실제 환경에 맞게 수정 가능하다.
        """
        path_tpl = self._ep("rtm_testcase_steps", "/rest/rtm/1.0/api/test-case/{testKey}/steps")
        return self._request("GET", path_tpl.format(testKey=jira_key))

    def update_testcase_steps(self, jira_key: str, payload: Dict[str, Any]) -> Any:
        """
        RTM Test Case의 Steps 정보를 업데이트한다.

        실제 RTM 환경에 맞춰 payload 구조 및 endpoint path를 수정해야 한다.
        기본적인 아이디어는:

            PUT /rest/rtm/1.0/api/test-case/{testKey}/steps

        와 같은 엔드포인트에 steps 리스트를 전송하는 것이다.
        """
        path_tpl = self._ep("rtm_testcase_steps", "/rest/rtm/1.0/api/test-case/{testKey}/steps")
        return self._request("PUT", path_tpl.format(testKey=jira_key), json=payload)



    # ------------------------------------------------------------------ Jira issue links (generic, not RTM specific)

    def create_issue_link(self, link_type: str, inward_key: str, outward_key: str) -> Any:
        """
        JIRA 표준 issueLink 생성 엔드포인트에 대한 thin wrapper.

        실제 예시:
          POST /rest/api/2/issueLink
          {
            "type": {"name": "Relates"},
            "inwardIssue": {"key": "PROJ-1"},
            "outwardIssue": {"key": "PROJ-2"}
          }

        여기서는 link_type/name, inward_key, outward_key 를 그대로 payload에 넣는다.
        RTM에서 Relations 탭에서 생성되는 링크 역시 기본적으로 Jira 이슈 링크를
        활용하는 경우가 많으므로, 이 메서드를 통해 push 동기화를 구현할 수 있다.
        """
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        }
        path_tpl = self._ep("jira_issue_link", "/rest/api/2/issueLink")
        return self._request("POST", path_tpl, json=payload)



    # ------------------------------------------------------------------ Test Plan / Test Execution (RTM specific, skeleton)

    def get_testplan_testcases(self, jira_key: str) -> Any:
        """
        RTM Test Plan에 포함된 Test Case 목록을 조회한다.

        RTM REST 문서에서는 Test Plan 객체의 includedTestCases 필드를 통해
        포함된 Test Case 를 노출한다. 여기서는 편의상 별도 헬퍼 endpoint 를
        가정하며, 실제 환경에 맞게 수정 가능하다:

            GET /rest/rtm/1.0/api/test-plan/{testKey}/testcases
        """
        path_tpl = self._ep("rtm_testplan_testcases", "/rest/rtm/1.0/api/test-plan/{testKey}/testcases")
        return self._request("GET", path_tpl.format(testKey=jira_key))

    def update_testplan_testcases(self, jira_key: str, payload: Dict[str, Any]) -> Any:
        """
        RTM Test Plan의 Test Case 구성을 업데이트한다.

        예시:

            PUT /rest/rtm/1.0/api/test-plan/{testKey}/testcases
            { "testCases": [ {"key": "PROJ-1", "order": 1}, ... ] }
        """
        path_tpl = self._ep("rtm_testplan_testcases", "/rest/rtm/1.0/api/test-plan/{testKey}/testcases")
        return self._request("PUT", path_tpl.format(testKey=jira_key), json=payload)

    def get_testexecution_details(self, jira_key: str) -> Any:
        """
        RTM Test Execution의 메타 정보를 조회한다.

        RTM REST 문서의 Test Execution 섹션과 매핑:

            GET /rest/rtm/1.0/api/test-execution/{testKey}
        """
        path_tpl = self._ep("rtm_testexecution", "/rest/rtm/1.0/api/test-execution/{testKey}")
        return self._request("GET", path_tpl.format(testKey=jira_key))

    def execute_test_plan(self, testplan_key: str, payload: Dict[str, Any] | None = None) -> Any:
        """
        RTM Test Plan 을 실행하여 새로운 Test Execution 을 생성한다.

        RTM REST 명세:
          POST /rest/rtm/1.0/api/test-execution/execute/{testPlanTestKey}

        응답 JSON 구조는 RTM 버전에 따라 다를 수 있으므로,
        호출 측에서는 반환값에서 test execution key (예: testKey, key, jiraKey)를
        안전하게 추출하는 방식으로 처리해야 한다.
        """
        path_tpl = self._ep(
            "rtm_testexecution_execute",
            "/rest/rtm/1.0/api/test-execution/execute/{testPlanKey}",
        )
        kwargs: Dict[str, Any] = {}
        if payload is not None:
            kwargs["json"] = payload
        return self._request("POST", path_tpl.format(testPlanKey=testplan_key), **kwargs)

    def get_testexecution_testcases(self, jira_key: str) -> Any:
        """
        RTM Test Execution에 포함된 Test Case Execution 목록을 조회한다.

        실제 RTM에서는 Test Case Execution API(`/api/test-case-execution/...`)
        를 사용하는 것이 더 정확하다. 여기서는 간단한 헬퍼 endpoint 를
        가정하며, 필요 시 교체한다:

            GET /rest/rtm/1.0/api/test-execution/{testKey}/testcases
        """
        path_tpl = self._ep(
            "rtm_testexecution_testcases",
            "/rest/rtm/1.0/api/test-execution/{testKey}/testcases",
        )
        return self._request("GET", path_tpl.format(testKey=jira_key))

    def update_testexecution(self, jira_key: str, payload: Dict[str, Any]) -> Any:
        """
        RTM Test Execution 메타 정보 업데이트용 skeleton.

        RTM REST 문서의 Test Execution 업데이트와 매핑:

            PUT /rest/rtm/1.0/api/test-execution/{testKey}
        """
        path_tpl = self._ep("rtm_testexecution", "/rest/rtm/1.0/api/test-execution/{testKey}")
        return self._request("PUT", path_tpl.format(testKey=jira_key), json=payload)

    def update_testexecution_testcases(self, jira_key: str, payload: Dict[str, Any]) -> Any:
        """
        RTM Test Execution의 Test Case Execution 목록을 업데이트한다.

        예시 endpoint:

            PUT /rest/rtm/1.0/api/test-execution/{testKey}/testcases
            {
              "testCases": [
                {"key": "PROJ-1", "result": "PASS", "environment": "...", ...},
                ...
              ]
            }
        """
        path_tpl = self._ep(
            "rtm_testexecution_testcases",
            "/rest/rtm/1.0/api/test-execution/{testKey}/testcases",
        )
        return self._request("PUT", path_tpl.format(testKey=jira_key), json=payload)

    # ------------------------------------------------------------------ Test Case Execution (RTM specific, skeleton)

    def get_testcase_execution(self, test_key: str) -> Any:
        """
        단일 Test Case Execution(TCE)을 조회한다.

        GET /rest/rtm/1.0/api/test-case-execution/{testKey}
        """
        path_tpl = self._ep("rtm_tce", "/rest/rtm/1.0/api/test-case-execution/{testKey}")
        return self._request("GET", path_tpl.format(testKey=test_key))

    def update_testcase_execution(self, test_key: str, payload: Dict[str, Any]) -> Any:
        """
        단일 TCE 메타 정보를 업데이트한다.

        PUT /rest/rtm/1.0/api/test-case-execution/{testKey}
        """
        path_tpl = self._ep("rtm_tce", "/rest/rtm/1.0/api/test-case-execution/{testKey}")
        return self._request("PUT", path_tpl.format(testKey=test_key), json=payload)

    def set_tce_step_status(self, test_key: str, step_index: int, status_payload: Dict[str, Any]) -> Any:
        """
        TCE 의 특정 Step 상태를 변경한다.

        PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/status
        """
        path_tpl = self._ep(
            "rtm_tce_step_status",
            "/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/status",
        )
        return self._request(
            "PUT",
            path_tpl.format(testKey=test_key, stepIndex=step_index),
            json=status_payload,
        )

    def set_tce_step_comment(self, test_key: str, step_index: int, text: str) -> Any:
        """
        TCE 의 특정 Step 코멘트를 설정/수정한다.

        PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment
        Body: { "text": "Example of a comment" }
        """
        path_tpl = self._ep(
            "rtm_tce_step_comment",
            "/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment",
        )
        return self._request(
            "PUT",
            path_tpl.format(testKey=test_key, stepIndex=step_index),
            json={"text": text},
        )

    def delete_tce_step_comment(self, test_key: str, step_index: int) -> Any:
        """
        TCE 의 특정 Step 코멘트를 삭제한다.

        DELETE /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment
        """
        path_tpl = self._ep(
            "rtm_tce_step_comment",
            "/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment",
        )
        return self._request("DELETE", path_tpl.format(testKey=test_key, stepIndex=step_index))

    def link_tce_defect(self, test_key: str, defect_test_key: str, issue_id: int | None = None) -> Any:
        """
        TCE 에 Defect 를 링크한다.

        PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/defect
        Body 예시: { "testKey": "KEY-1", "issueId": 123 }
        """
        payload: Dict[str, Any] = {"testKey": defect_test_key}
        if issue_id is not None:
            payload["issueId"] = issue_id
        path_tpl = self._ep("rtm_tce_defect", "/rest/rtm/1.0/api/test-case-execution/{testKey}/defect")
        return self._request("PUT", path_tpl.format(testKey=test_key), json=payload)

    def unlink_tce_defect(self, test_key: str, defect_test_key: str) -> Any:
        """
        TCE 에서 Defect 링크를 제거한다.

        DELETE /rest/rtm/1.0/api/test-case-execution/{testKey}/defect/{defectTestKey}
        """
        path_tpl = self._ep(
            "rtm_tce_defect_item",
            "/rest/rtm/1.0/api/test-case-execution/{testKey}/defect/{defectTestKey}",
        )
        return self._request(
            "DELETE",
            path_tpl.format(testKey=test_key, defectTestKey=defect_test_key),
        )

    def delete_tce_attachment(self, test_key: str, attachment_id: int | str) -> Any:
        """
        TCE 에 연결된 첨부를 삭제한다.

        DELETE /rest/rtm/1.0/api/test-case-execution/{testKey}/attachment/{attachmentId}
        """
        path_tpl = self._ep(
            "rtm_tce_attachment",
            "/rest/rtm/1.0/api/test-case-execution/{testKey}/attachment/{attachmentId}",
        )
        return self._request(
            "DELETE",
            path_tpl.format(testKey=test_key, attachmentId=attachment_id),
        )

    # ---------------------------- TCE comments ------------------------------

    def get_tce_comments(self, test_key: str) -> Any:
        """
        TCE 코멘트 목록을 조회한다.

        PUT /rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments
        (RTM 문서 기준으로 메서드는 PUT 이지만, 서버 구현에 따라 GET 일 수도 있어
        필요 시 조정한다.)
        """
        path_tpl = self._ep(
            "rtm_tce_comments",
            "/rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments",
        )
        return self._request("PUT", path_tpl.format(testKey=test_key))

    def add_tce_comment(self, test_key: str, text: str) -> Any:
        """
        TCE 에 새 코멘트를 추가한다.

        POST /rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments
        Body: { "text": "Example of comment" }
        """
        path_tpl = self._ep(
            "rtm_tce_comments",
            "/rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments",
        )
        return self._request("POST", path_tpl.format(testKey=test_key), json={"text": text})

    def update_tce_comment(self, comment_id: int | str, text: str) -> Any:
        """
        TCE 코멘트를 수정한다.

        PUT /rest/rtm/1.0/api/test-case-execution-comment/comments/{id}
        """
        path_tpl = self._ep(
            "rtm_tce_comment",
            "/rest/rtm/1.0/api/test-case-execution-comment/comments/{id}",
        )
        return self._request("PUT", path_tpl.format(id=comment_id), json={"text": text})

    def delete_tce_comment(self, comment_id: int | str) -> Any:
        """
        TCE 코멘트를 삭제한다.

        DELETE /rest/rtm/1.0/api/test-case-execution-comment/comments/{id}
        """
        path_tpl = self._ep(
            "rtm_tce_comment",
            "/rest/rtm/1.0/api/test-case-execution-comment/comments/{id}",
        )
        return self._request("DELETE", path_tpl.format(id=comment_id))

def load_config_from_file(path: str) -> JiraConfig:
    """
    jira_config.json 을 읽어서 JiraConfig 인스턴스로 변환한다.
 
    예시 (Basic Auth):
    {
        "base_url": "https://jira.example.com",
        "username": "jira.user",
        "api_token": "PASSWORD_OR_PAT",
        "project_key": "KVHSICCU",
        "project_id": 41500
    }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
 
    base_url = str(data.get("base_url") or "").strip()
 
    endpoints = data.get("endpoints") or DEFAULT_ENDPOINTS
    # 기존 설정 파일에는 endpoints 가 없을 수 있으므로 기본값과 병합
    merged_endpoints = dict(DEFAULT_ENDPOINTS)
    merged_endpoints.update(endpoints)
    return JiraConfig(
        base_url=base_url,
        username=data["username"],
        api_token=data["api_token"],
        project_key=data["project_key"],
        project_id=int(data["project_id"]),
        endpoints=merged_endpoints,
    )


def save_config_to_file(path: str, config: JiraConfig) -> None:
    """
    JiraConfig 인스턴스를 jira_config.json 형식으로 저장한다.
    """
    data = {
        "base_url": config.base_url,
        "username": config.username,
        "api_token": config.api_token,
        "project_key": config.project_key,
        "project_id": config.project_id,
        "endpoints": config.endpoints or DEFAULT_ENDPOINTS,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
