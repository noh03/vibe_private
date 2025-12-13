"""
jira_mapping.py - Mapping layer between JIRA RTM JSON and local SQLite 'issues' table.

이 모듈은:
- JIRA/RTM REST API 응답(JSON) -> 로컬 issues 테이블 컬럼 업데이트 dict
- 로컬 issues row(dict)       -> JIRA/RTM REST API payload(fields) 생성

실제 RTM 플러그인의 JSON 구조(특히 커스텀 필드)는
프로젝트/인스턴스마다 다를 수 있으므로,
여기서 정의한 매핑은 "기본 Jira 이슈 구조"를 기준으로 한 골격이다.
현장 환경에 맞게 이 모듈만 수정하면 GUI/DB 코드는 그대로 재사용 가능하다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json


# --------------------------------------------------------------------------- helpers


def _safe_get(d: Dict[str, Any], *keys: str) -> Optional[Any]:
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def _join_names(items: Optional[List[Dict[str, Any]]]) -> str:
    """
    [{id, name}, ...] 또는 [{id}, ...] 형태의 리스트에서 name 또는 id를 추출하여 쉼표로 연결.
    name이 있으면 name을 우선 사용하고, 없으면 id를 사용.
    """
    if not items:
        return ""
    names = []
    for x in items:
        if not isinstance(x, dict):
            continue
        # name이 있으면 name 사용, 없으면 id 사용
        name = x.get("name")
        if not name:
            name = x.get("id")
        if name:
            names.append(str(name))
    return ", ".join(names)


def _join_strings(items: Optional[List[Any]]) -> str:
    if not items:
        return ""
    return ", ".join(str(x) for x in items)


# --------------------------------------------------------------------------- custom field keys (Epic / Sprint 등)
#
# JIRA 데이터센터 환경마다 Epic Link / Sprint 필드의 ID가 다르므로,
# 실제 사용하는 인스턴스에 맞게 아래 상수를 수정해서 사용한다.
#
# 예시:
#   EPIC_LINK_FIELD_KEY = "customfield_10014"
#   SPRINT_FIELD_KEY    = "customfield_10020"
#
# 설정하지 않으면(Epic/Sprint 필드 키가 None 이면) 해당 필드는 매핑에서 생략된다.

EPIC_LINK_FIELD_KEY: Optional[str] = None
SPRINT_FIELD_KEY: Optional[str] = None


# --------------------------------------------------------------------------- pull mapping (JIRA -> local)


def map_jira_to_local(issue_type: str, jira_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    JIRA/RTM JSON 응답(개별 이슈)에서 로컬 issues 테이블에 반영할 필드를 추출한다.

    반환값은 update_issue_fields() 에 바로 넘길 수 있는 dict:
      - summary
      - description
      - status
      - priority
      - assignee
      - reporter
      - labels
      - components
      - security_level
      - fix_versions
      - affects_versions
      - rtm_environment
      - due_date
      - created
      - updated
      - attachments
    """
    fields = jira_json.get("fields", jira_json) or {}

    updates: Dict[str, Any] = {}

    # summary / description
    if "summary" in fields:
        updates["summary"] = fields.get("summary") or ""
    if "description" in fields:
        desc = fields.get("description")
        if isinstance(desc, dict):
            updates["description"] = json.dumps(desc, ensure_ascii=False)
        else:
            updates["description"] = desc or ""

    # status / priority
    status_name = _safe_get(fields, "status", "name")
    if status_name:
        updates["status"] = status_name

    prio_name = _safe_get(fields, "priority", "name")
    if prio_name:
        updates["priority"] = prio_name

    # assignee / reporter (displayName 우선, 없으면 name/key)
    assignee = fields.get("assignee")
    if isinstance(assignee, dict):
        updates["assignee"] = (
            assignee.get("displayName")
            or assignee.get("name")
            or assignee.get("key")
            or ""
        )

    reporter = fields.get("reporter")
    if isinstance(reporter, dict):
        updates["reporter"] = (
            reporter.get("displayName")
            or reporter.get("name")
            or reporter.get("key")
            or ""
        )

    # labels (list[str])
    labels = fields.get("labels")
    if isinstance(labels, list):
        updates["labels"] = _join_strings(labels)

    # components (list[Component{name}])
    comps = fields.get("components")
    if isinstance(comps, list):
        updates["components"] = _join_names(comps)

    # security level (issue security)
    sec_name = _safe_get(fields, "security", "name")
    if sec_name:
        updates["security_level"] = sec_name

    # fixVersions / affectsVersions
    fix_versions = fields.get("fixVersions")
    if isinstance(fix_versions, list):
        updates["fix_versions"] = _join_names(fix_versions)

    # Jira 표준에서는 'versions' 필드가 'affects versions' 역할을 한다.
    affects = fields.get("versions")
    if isinstance(affects, list):
        updates["affects_versions"] = _join_names(affects)

    # Epic Link (custom field, 인스턴스별 ID 다름)
    if EPIC_LINK_FIELD_KEY:
        epic_val = fields.get(EPIC_LINK_FIELD_KEY)
        if isinstance(epic_val, dict):
            # key / name / id 중 사용 가능한 값을 우선적으로 사용
            key = epic_val.get("key") or epic_val.get("name") or epic_val.get("id")
            if key:
                updates["epic_link"] = str(key)
        elif epic_val is not None:
            updates["epic_link"] = str(epic_val)

    # Sprint (일반적으로 list 형태의 custom field)
    if SPRINT_FIELD_KEY:
        sprint_val = fields.get(SPRINT_FIELD_KEY)
        if isinstance(sprint_val, list):
            updates["sprint"] = _join_strings(sprint_val)
        elif sprint_val is not None:
            updates["sprint"] = str(sprint_val)

    # RTM Environment (일반 Jira에서는 'environment' 필드)
    env = fields.get("environment")
    if isinstance(env, dict):
        # RTM 플러그인에서 복합 구조일 수도 있음
        updates["rtm_environment"] = json.dumps(env, ensure_ascii=False)
    elif env:
        updates["rtm_environment"] = str(env)

    # due date
    if "duedate" in fields:
        updates["due_date"] = fields.get("duedate") or ""

    # created / updated
    if "created" in fields:
        updates["created"] = fields.get("created") or ""
    if "updated" in fields:
        updates["updated"] = fields.get("updated") or ""

    # attachments
    att = fields.get("attachment")
    if att is not None:
        # 전체 attachment 배열을 JSON 문자열로 저장
        updates["attachments"] = json.dumps(att, ensure_ascii=False)

    return updates


# --------------------------------------------------------------------------- push mapping (local -> JIRA)


def map_local_to_jira_fields(issue_type: str, local_issue: Dict[str, Any]) -> Dict[str, Any]:
    """
    로컬 issues row(dict) 를 JIRA REST 'fields' payload로 변환한다.

    여기서는 JIRA 표준 필드만 보수적으로 업데이트:
      - summary
      - description
      - labels
      - components
      - duedate
      - environment

    status / priority / assignee / reporter 등은 JIRA 워크플로/권한 설정의 영향이 크고,
    REST 업데이트 방식이 인스턴스마다 달라질 수 있어 기본 매핑에서는 제외한다.
    필요 시 현장에 맞게 이 함수를 확장하면 된다.
    """
    fields: Dict[str, Any] = {}

    # summary / description
    fields["summary"] = local_issue.get("summary") or ""
    desc = local_issue.get("description")
    # description 에 JSON 문자열이 들어 있을 수도 있으므로 그대로 보낸다.
    fields["description"] = desc or ""

    # labels: "a, b, c" 형태의 문자열 -> ["a", "b", "c"]
    labels = local_issue.get("labels")
    if labels:
        if isinstance(labels, str):
            parts = [x.strip() for x in labels.split(",") if x.strip()]
            if parts:
                fields["labels"] = parts

    # components: "Backend, Frontend" -> [{"name": "Backend"}, {"name": "Frontend"}]
    components = local_issue.get("components")
    if components:
        if isinstance(components, str):
            comp_names = [x.strip() for x in components.split(",") if x.strip()]
            if comp_names:
                fields["components"] = [{"name": name} for name in comp_names]

    # duedate
    due = local_issue.get("due_date")
    if due:
        fields["duedate"] = due

    # environment <- rtm_environment
    env = local_issue.get("rtm_environment")
    if env:
        # 문자열 그대로 세팅 (RTM에서 커스텀 필드 사용 시 이 부분을 수정)
        fields["environment"] = env

    # Epic Link / Sprint (custom field 키가 설정된 경우에만 포함)
    epic = local_issue.get("epic_link")
    if EPIC_LINK_FIELD_KEY and epic:
        fields[EPIC_LINK_FIELD_KEY] = epic

    sprint = local_issue.get("sprint")
    if SPRINT_FIELD_KEY and sprint:
        fields[SPRINT_FIELD_KEY] = sprint

    return fields


def build_jira_update_payload(issue_type: str, local_issue: Dict[str, Any], project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 JIRA/RTM 업데이트 payload로 변환.
    
    RTM 타입인 경우 build_rtm_payload를 사용하고,
    일반 JIRA 타입인 경우 map_local_to_jira_fields를 사용합니다.
    """
    issue_type_upper = (issue_type or "").upper()
    
    # RTM 타입인 경우 build_rtm_payload 사용
    if issue_type_upper in ("REQUIREMENT", "TEST_CASE", "TEST_PLAN", "TEST_EXECUTION", "DEFECT"):
        return build_rtm_payload(issue_type, local_issue, None, project_key)
    else:
        # 일반 JIRA 타입
        return {"fields": map_local_to_jira_fields(issue_type, local_issue)}

def build_jira_create_payload(issue_type: str, local_issue: Dict[str, Any]) -> Dict[str, Any]:
    """
    새 RTM 엔티티 생성 시 사용할 payload 구성.

    기본적으로 update payload 와 동일한 'fields' 구조를 사용하되,
    실제 환경에서 요구하는 project / issuetype / customfield 값 등은
    map_local_to_jira_fields() 내부에서 적절히 채워지도록 조정한다.
    """
    return {"fields": map_local_to_jira_fields(issue_type, local_issue)}



# --------------------------------------------------------------------------- Test Case steps mapping


def map_jira_testcase_steps_to_local(jira_steps_json: Any) -> List[Dict[str, Any]]:
    """
    JIRA RTM의 Test Case "Steps" JSON을 로컬 testcase_steps 테이블용 리스트로 변환한다.

    로컬 testcase_steps 구조:
      - order_no (int)
      - action (str)
      - input (str)
      - expected (str)

    실제 RTM JSON 구조는 인스턴스마다 다를 수 있으므로,
    여기서는 대표적인 필드명 패턴만 가정한다.

    예시 패턴 (필요 시 수정):
      - 각 step 객체에 다음 키가 있을 수 있음:
        - "action" 또는 "step"
        - "data" 또는 "input"
        - "expectedResult" 또는 "expected"
    """
    steps_local: List[Dict[str, Any]] = []

    if jira_steps_json is None:
        return steps_local

    # RTM 구현에 따라 {"steps":[...]} 래핑이 있을 수 있음
    if isinstance(jira_steps_json, dict) and "steps" in jira_steps_json:
        raw_list = jira_steps_json.get("steps") or []
    else:
        raw_list = jira_steps_json

    if not isinstance(raw_list, list):
        return steps_local

    for idx, step in enumerate(raw_list, start=1):
        if not isinstance(step, dict):
            continue
        action = (
            step.get("action")
            or step.get("step")
            or ""
        )
        inp = (
            step.get("data")
            or step.get("input")
            or ""
        )
        expected = (
            step.get("expectedResult")
            or step.get("expected")
            or ""
        )
        steps_local.append(
            {
                "order_no": idx,
                "action": action,
                "input": inp,
                "expected": expected,
            }
        )
    return steps_local


def build_jira_testcase_steps_payload(local_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    로컬 testcase_steps 리스트를 RTM Test Case Steps 업데이트용 payload로 변환한다.

    여기서는 다음과 같은 JSON 구조를 가정한다.
      {
        "steps": [
          {"action": "...", "data": "...", "expectedResult": "..."},
          ...
        ]
      }

    실제 RTM REST API 명세에 맞게 필드명을 조정해 사용하면 된다.
    """
    steps: List[Dict[str, Any]] = []
    for s in local_steps:
        steps.append(
            {
                "action": s.get("action") or "",
                "data": s.get("input") or "",
                "expectedResult": s.get("expected") or "",
            }
        )
    return {"steps": steps}


# --------------------------------------------------------------------------- Relations (Jira issue links) mapping


def extract_relations_from_jira(jira_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    JIRA 이슈 JSON에서 issuelinks 배열을 파싱하여, RTM Local Manager의 relations 테이블에
    대응 가능한 최소 정보를 추출한다.

    반환 형식 (리스트의 각 원소):
      {
        "relation_type": "<link type + 방향>",
        "dst_jira_key": "<상대 이슈 key>",
        "dst_summary": "<상대 이슈 summary (있으면)>",
      }

    - relation_type 은 Jira 내부 link type name에 "(out)" 또는 "(in)" 을 붙인 단순 문자열이다.
      예: "Relates (out)", "Relates (in)", "Tests (out)" 등
    - 실제 RTM 플러그인의 relation 타입/명칭에 맞춰 세분화하려면 이 함수를 수정하면 된다.
    """
    fields = jira_json.get("fields", jira_json) or {}
    links = fields.get("issuelinks") or []
    results: List[Dict[str, Any]] = []

    if not isinstance(links, list):
        return results

    for link in links:
        if not isinstance(link, Dict):
            continue
        type_name = _safe_get(link, "type", "name") or ""
        # outwardIssue: 현재 이슈 -> outwardIssue
        if isinstance(link.get("outwardIssue"), Dict):
            other = link["outwardIssue"]
            direction = "out"
        elif isinstance(link.get("inwardIssue"), Dict):
            other = link["inwardIssue"]
            direction = "in"
        else:
            continue

        key = other.get("key")
        if not key:
            continue
        other_fields = other.get("fields") or {}
        summary = other_fields.get("summary") or ""

        rel_type = type_name or "Link"
        rel_type = f"{rel_type} ({direction})"

        results.append(
            {
                "relation_type": rel_type,
                "dst_jira_key": key,
                "dst_summary": summary,
            }
        )

    return results


# --------------------------------------------------------------------------- Test Plan / Test Execution mapping


def map_jira_testplan_testcases_to_local(jira_json: Any) -> List[Dict[str, Any]]:
    """
    RTM Test Plan의 Test Case 목록 JSON을 로컬 testplan_testcases 구조에 가까운 형태로 변환한다.

    반환 형식 (각 원소):
      {
        "order_no": <int>,
        "testcase_key": "<Jira test case key>",
        "summary": "<optional summary>",
      }

    실제 RTM JSON 구조는 예를 들어 다음과 같이 가정한다.
      {
        "testCases": [
          {"key": "PROJ-1", "order": 1, "summary": "..."},
          ...
        ]
      }
    """
    results: List[Dict[str, Any]] = []

    if jira_json is None:
        return results

    # 래핑 여부 처리
    if isinstance(jira_json, dict) and "testCases" in jira_json:
        items = jira_json.get("testCases") or []
    else:
        items = jira_json

    if not isinstance(items, list):
        return results

    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not key:
            continue
        order_no = item.get("order") or item.get("orderNo") or 0
        summary = item.get("summary") or ""
        results.append(
            {
                "order_no": int(order_no) if order_no else 0,
                "testcase_key": key,
                "summary": summary,
            }
        )

    return results


def build_jira_testplan_testcases_payload(local_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    로컬 Test Plan - Test Case 매핑 레코드들을 RTM Test Plan 업데이트용 payload로 변환한다.

    local_records 형식(예상):
      - get_testplan_testcases() JOIN 결과 또는 GUI 수집에서:
        {
          "order_no": ...,
          "testcase_jira_key": "...",
          "summary": "...",
        }
    """
    items: List[Dict[str, Any]] = []
    for rec in local_records:
        key = rec.get("testcase_jira_key") or rec.get("jira_key")
        if not key:
            continue
        order_no = rec.get("order_no") or 0
        items.append(
            {
                "key": key,
                "order": int(order_no) if order_no else 0,
            }
        )
    return {"testCases": items}


def map_jira_testexecution_meta_to_local(jira_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM Test Execution 상세 JSON에서 로컬 testexecutions 테이블에 반영할 메타 정보 추출.

    로컬 testexecutions 컬럼(이미 정의된 구조를 가정):
      - environment
      - start_date
      - end_date
      - result
      - executed_by
    """
    fields = jira_json.get("fields", jira_json) or {}

    meta: Dict[str, Any] = {}

    # environment
    env = fields.get("environment")
    if env:
        if isinstance(env, dict):
            meta["environment"] = json.dumps(env, ensure_ascii=False)
        else:
            meta["environment"] = str(env)

    # start/end/result 는 실제 RTM Test Execution 필드에 맞춰 조정 필요
    # 여기서는 대표적인 필드 이름만 가정한다.
    if "customfield_te_start" in fields:
        meta["start_date"] = fields.get("customfield_te_start")
    if "customfield_te_end" in fields:
        meta["end_date"] = fields.get("customfield_te_end")
    if "customfield_te_result" in fields:
        meta["result"] = fields.get("customfield_te_result")

    # 실행자 (executed_by)
    executor = fields.get("customfield_te_executor")
    if isinstance(executor, dict):
        meta["executed_by"] = (
            executor.get("displayName")
            or executor.get("name")
            or executor.get("key")
            or ""
        )
    elif executor:
        meta["executed_by"] = str(executor)

    return meta


def map_jira_testexecution_testcases_to_local(jira_json: Any) -> List[Dict[str, Any]]:
    """
    RTM Test Execution의 Test Case Execution 목록 JSON을 로컬 testcase_executions 용 리스트로 변환.

    로컬 testcase_executions 구조(중간 형태):
      - order_no
      - testcase_key (-> 매핑 단계에서 local issue_id 로 바꾸어야 함)
      - assignee
      - result
      - rtm_environment
      - defects (문자열)
      - actual_time (분 단위 또는 RTM JSON 의 actualTime 값)
      - tce_test_key (RTM Test Case Execution 의 testKey, 있으면 Step API 연동에 사용)
    """
    results: List[Dict[str, Any]] = []

    if jira_json is None:
        return results

    if isinstance(jira_json, dict) and "testCases" in jira_json:
        items = jira_json.get("testCases") or []
    else:
        items = jira_json

    if not isinstance(items, list):
        return results

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        # Test Case key (필수)
        key = item.get("testcase_key") or item.get("testCaseKey") or item.get("key")
        assignee = ""
        if isinstance(item.get("assignee"), dict):
            a = item["assignee"]
            assignee = a.get("displayName") or a.get("name") or a.get("key") or ""
        elif item.get("assignee"):
            assignee = str(item.get("assignee"))

        result_val = item.get("result") or item.get("status") or ""
        env = item.get("environment") or ""
        defects = ""

        # defects 정보가 별도 배열로 주어지면 간단히 key 들을 , 로 join
        defect_list = item.get("defects")
        if isinstance(defect_list, list):
            defect_keys = []
            for d in defect_list:
                if isinstance(d, dict) and d.get("key"):
                    defect_keys.append(d["key"])
                elif isinstance(d, str):
                    defect_keys.append(d)
            if defect_keys:
                defects = ", ".join(defect_keys)

        actual_time = item.get("actualTime") or item.get("actual_time")

        # RTM Test Case Execution testKey (있을 수도, 없을 수도 있음)
        # 실제 필드명은 RTM 버전에 따라 다를 수 있으므로 여러 후보를 보수적으로 체크한다.
        tce_test_key = (
            item.get("testCaseExecutionKey")
            or item.get("tceKey")
            or item.get("executionKey")
        )

        results.append(
            {
                "order_no": item.get("order") or item.get("orderNo") or idx,
                "testcase_key": key,
                "assignee": assignee,
                "result": result_val,
                "rtm_environment": env,
                "defects": defects,
                "actual_time": actual_time,
                "tce_test_key": tce_test_key,
            }
        )

    return results


def build_jira_testexecution_payload(local_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    로컬 testexecutions 메타 dict -> RTM Test Execution 업데이트 payload.

    실제 RTM에서 사용하는 필드명에 맞춰 customfield_* 부분을 수정해야 한다.
    """
    fields: Dict[str, Any] = {}

    env = local_meta.get("environment")
    if env:
        fields["environment"] = env

    if local_meta.get("start_date"):
        fields["customfield_te_start"] = local_meta["start_date"]
    if local_meta.get("end_date"):
        fields["customfield_te_end"] = local_meta["end_date"]
    if local_meta.get("result"):
        fields["customfield_te_result"] = local_meta["result"]

    if local_meta.get("executed_by"):
        fields["customfield_te_executor"] = local_meta["executed_by"]

    return {"fields": fields}


def build_jira_testexecution_testcases_payload(local_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    로컬 testcase_executions 리스트 -> RTM Test Execution TestCases 업데이트 payload.

    local_records 형식:
      - get_testcase_executions() 결과 또는 GUI 수집에서:
        {
          "order_no": ...,
          "testcase_jira_key": "...",
          "assignee": "...",
          "result": "...",
          "rtm_environment": "...",
          "defects": "...",
        }
    """
    items: List[Dict[str, Any]] = []
    for rec in local_records:
        key = rec.get("testcase_jira_key") or rec.get("jira_key") or rec.get("testcase_key")
        if not key:
            continue
        item = {
            "key": key,
            "order": rec.get("order_no") or 0,
        }
        if rec.get("assignee"):
            item["assignee"] = rec["assignee"]
        if rec.get("result"):
            item["result"] = rec["result"]
        if rec.get("rtm_environment"):
            item["environment"] = rec["rtm_environment"]
        if rec.get("defects"):
            # 간단히 문자열로 전달 (실제 RTM에서는 defect 링크 정보로 변환 필요)
            item["defects"] = rec["defects"]
        if rec.get("actual_time") is not None:
            item["actualTime"] = rec["actual_time"]
        items.append(item)

    return {"testCases": items}


# --------------------------------------------------------------------------- RTM API Response Mapping (RTM -> Local)
#
# RTM API는 JIRA 표준 API와 다른 구조를 사용합니다.
# 각 이슈 타입별 GET 응답을 로컬 issues 테이블 형식으로 변환합니다.


def map_rtm_requirement_to_local(rtm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM Requirement GET 응답을 로컬 issues 형식으로 변환.
    
    RTM 응답 구조 (RTM REST API.md 참조):
    - testKey, summary, description, assigneeId, parentTestKey, projectKey
    - priority: {id, name}
    - status: {id, name, statusName}
    - labels: [string, ...]
    - components: [{id}, ...]
    - versions: [{id}, ...]
    - timeEstimate: string
    - epicName: string
    - issueTypeId: int
    - testCasesCovered: [{testKey, issueId}, ...]
    """
    updates: Dict[str, Any] = {}
    
    # 기본 필드
    if "testKey" in rtm_json:
        updates["jira_key"] = rtm_json["testKey"]
    if "summary" in rtm_json:
        updates["summary"] = rtm_json["summary"] or ""
    if "description" in rtm_json:
        updates["description"] = rtm_json["description"] or ""
    if "assigneeId" in rtm_json:
        updates["assignee"] = rtm_json["assigneeId"] or ""
    if "projectKey" in rtm_json:
        updates["_rtm_projectKey"] = rtm_json["projectKey"] or ""
    if "parentTestKey" in rtm_json:
        updates["_rtm_parentTestKey"] = rtm_json["parentTestKey"] or ""
    
    # priority
    if "priority" in rtm_json and isinstance(rtm_json["priority"], dict):
        updates["priority"] = rtm_json["priority"].get("name") or ""
    
    # status
    if "status" in rtm_json and isinstance(rtm_json["status"], dict):
        updates["status"] = rtm_json["status"].get("name") or rtm_json["status"].get("statusName") or ""
    
    # labels
    if "labels" in rtm_json and isinstance(rtm_json["labels"], list):
        updates["labels"] = _join_strings(rtm_json["labels"])
    
    # components
    if "components" in rtm_json and isinstance(rtm_json["components"], list):
        # components는 [{id}, ...] 또는 [{id, name}, ...] 형태
        updates["components"] = _join_names(rtm_json["components"])
    
    # versions (fixVersions/affectsVersions로 사용 가능)
    if "versions" in rtm_json and isinstance(rtm_json["versions"], list):
        updates["fix_versions"] = _join_names(rtm_json["versions"])
    
    # timeEstimate
    if "timeEstimate" in rtm_json:
        updates["_rtm_timeEstimate"] = rtm_json["timeEstimate"] or ""
    
    # epicName
    if "epicName" in rtm_json:
        updates["epic_link"] = rtm_json["epicName"] or ""
    
    # issueTypeId
    if "issueTypeId" in rtm_json:
        updates["_rtm_issueTypeId"] = rtm_json["issueTypeId"]
    
    # testCasesCovered는 별도로 처리 (Requirements 탭에서 사용)
    updates["_rtm_testCasesCovered"] = rtm_json.get("testCasesCovered") or []
    
    return updates


def map_rtm_testcase_to_local(rtm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM Test Case GET 응답을 로컬 issues 형식으로 변환.
    
    RTM 응답 구조 (RTM REST API.md 참조):
    - testKey, summary, description, assigneeId, parentTestKey, projectKey
    - priority: {id, name}
    - status: {id, name, statusName}
    - labels: [string, ...]
    - components: [{id}, ...]
    - versions: [{id}, ...]
    - timeEstimate: string
    - environment: string
    - preconditions: string
    - steps: [[{value: string}], ...] (2차원 배열)
    - coveredRequirements: [{testKey, issueId}, ...]
    """
    updates: Dict[str, Any] = {}
    
    # 기본 필드
    if "testKey" in rtm_json:
        updates["jira_key"] = rtm_json["testKey"]
    if "summary" in rtm_json:
        updates["summary"] = rtm_json["summary"] or ""
    if "description" in rtm_json:
        updates["description"] = rtm_json["description"] or ""
    if "assigneeId" in rtm_json:
        updates["assignee"] = rtm_json["assigneeId"] or ""
    if "projectKey" in rtm_json:
        updates["_rtm_projectKey"] = rtm_json["projectKey"] or ""
    if "parentTestKey" in rtm_json:
        updates["_rtm_parentTestKey"] = rtm_json["parentTestKey"] or ""
    
    # priority
    if "priority" in rtm_json and isinstance(rtm_json["priority"], dict):
        updates["priority"] = rtm_json["priority"].get("name") or ""
    
    # status
    if "status" in rtm_json and isinstance(rtm_json["status"], dict):
        updates["status"] = rtm_json["status"].get("name") or rtm_json["status"].get("statusName") or ""
    
    # labels
    if "labels" in rtm_json and isinstance(rtm_json["labels"], list):
        updates["labels"] = _join_strings(rtm_json["labels"])
    
    # components
    if "components" in rtm_json and isinstance(rtm_json["components"], list):
        updates["components"] = _join_names(rtm_json["components"])
    
    # versions
    if "versions" in rtm_json and isinstance(rtm_json["versions"], list):
        updates["fix_versions"] = _join_names(rtm_json["versions"])
    
    # timeEstimate
    if "timeEstimate" in rtm_json:
        updates["_rtm_timeEstimate"] = rtm_json["timeEstimate"] or ""
    
    # environment
    if "environment" in rtm_json:
        updates["rtm_environment"] = rtm_json["environment"] or ""
    
    # preconditions
    if "preconditions" in rtm_json:
        updates["_rtm_preconditions"] = rtm_json["preconditions"] or ""
    
    # steps는 별도로 처리 (Steps 탭에서 사용)
    # RTM steps는 stepGroups 구조 또는 2차원 배열 형태일 수 있음
    import re
    
    steps_local: List[Dict[str, Any]] = []
    
    # stepGroups가 있으면 그것을 우선 사용
    if "stepGroups" in rtm_json and isinstance(rtm_json["stepGroups"], list):
        # stepGroups 구조: [{id, name, steps: [{stepColumns: [{name, value}]}], ...}, ...]
        # 또는 [{id, name, stepColumns: [{name, value}], ...}, ...] (단일 step인 경우)
        for group_idx, group in enumerate(rtm_json["stepGroups"], start=1):
            if not isinstance(group, dict):
                continue
            
            # 그룹 안에 steps 배열이 있는 경우 (여러 step)
            if "steps" in group and isinstance(group["steps"], list):
                for step_order, step in enumerate(group["steps"], start=1):
                    if not isinstance(step, dict):
                        continue
                    
                    step_columns = step.get("stepColumns") or []
                    if not isinstance(step_columns, list):
                        continue
                    
                    # stepColumns에서 action, input, expected 추출
                    action = ""
                    input_val = ""
                    expected = ""
                    
                    for col in step_columns:
                        if not isinstance(col, dict):
                            continue
                        
                        col_name = (col.get("name") or "").lower()
                        col_value = col.get("value") or ""
                        
                        # HTML 태그 제거
                        col_value = re.sub(r'<[^>]+>', '', col_value).strip()
                        
                        # 컬럼 이름에 따라 분류
                        if "action" in col_name or "step" in col_name:
                            action = col_value
                        elif "input" in col_name or "data" in col_name:
                            input_val = col_value
                        elif "expected" in col_name or "result" in col_name or "output" in col_name:
                            expected = col_value
                    
                    # action 또는 expected가 있으면 step 추가
                    if action or expected:
                        steps_local.append({
                            "order_no": len(steps_local) + 1,
                            "group_no": group_idx,
                            "action": action,
                            "input": input_val,
                            "expected": expected,
                        })
            
            # 그룹에 stepColumns가 직접 있는 경우 (단일 step)
            elif "stepColumns" in group:
                step_columns = group.get("stepColumns") or []
                if isinstance(step_columns, list):
                    # stepColumns에서 action, input, expected 추출
                    action = ""
                    input_val = ""
                    expected = ""
                    
                    for col in step_columns:
                        if not isinstance(col, dict):
                            continue
                        
                        col_name = (col.get("name") or "").lower()
                        col_value = col.get("value") or ""
                        
                        # HTML 태그 제거
                        col_value = re.sub(r'<[^>]+>', '', col_value).strip()
                        
                        # 컬럼 이름에 따라 분류
                        if "action" in col_name or "step" in col_name:
                            action = col_value
                        elif "input" in col_name or "data" in col_name:
                            input_val = col_value
                        elif "expected" in col_name or "result" in col_name or "output" in col_name:
                            expected = col_value
                    
                    # action 또는 expected가 있으면 step 추가
                    if action or expected:
                        steps_local.append({
                            "order_no": len(steps_local) + 1,
                            "group_no": group_idx,
                            "action": action,
                            "input": input_val,
                            "expected": expected,
                        })
    
    # stepGroups가 없고 steps가 직접 있는 경우
    elif "steps" in rtm_json:
        steps_raw = rtm_json.get("steps") or []
        
        if isinstance(steps_raw, list):
            for step_group_idx, step_group in enumerate(steps_raw, start=1):
                if isinstance(step_group, list):
                    # 2차원 배열 형태: [[{value: "..."}], ...]
                    for step_item in step_group:
                        if isinstance(step_item, dict):
                            value = step_item.get("value") or ""
                            # HTML 태그 제거
                            value = re.sub(r'<[^>]+>', '', value).strip()
                            steps_local.append({
                                "order_no": len(steps_local) + 1,
                                "group_no": step_group_idx,
                                "action": value,
                                "input": "",
                                "expected": "",
                            })
                elif isinstance(step_group, dict):
                    # 단일 step 객체 형태
                    step_columns = step_group.get("stepColumns") or []
                    if step_columns:
                        # stepColumns에서 value 추출
                        action = ""
                        input_val = ""
                        expected = ""
                        for col in step_columns:
                            if isinstance(col, dict):
                                col_name = (col.get("name") or "").lower()
                                col_value = col.get("value") or ""
                                col_value = re.sub(r'<[^>]+>', '', col_value).strip()
                                
                                if "action" in col_name or "step" in col_name:
                                    action = col_value
                                elif "input" in col_name or "data" in col_name:
                                    input_val = col_value
                                elif "expected" in col_name or "result" in col_name:
                                    expected = col_value
                        
                        if action or expected:
                            steps_local.append({
                                "order_no": len(steps_local) + 1,
                                "group_no": step_group_idx,
                                "action": action,
                                "input": input_val,
                                "expected": expected,
                            })
    
    updates["_rtm_steps"] = steps_local
    
    # coveredRequirements
    if "coveredRequirements" in rtm_json:
        updates["_rtm_coveredRequirements"] = rtm_json.get("coveredRequirements") or []
    
    return updates


def map_rtm_testplan_to_local(rtm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM Test Plan GET 응답을 로컬 issues 형식으로 변환.
    
    RTM 응답 구조 (RTM REST API.md 참조):
    - testKey, summary, description, assigneeId, parentTestKey, projectKey
    - priority: {id, name}
    - status: {id, name, statusName}
    - labels: [string, ...]
    - components: [{id}, ...]
    - versions: [{id}, ...]
    - timeEstimate: string
    - environment: string
    - executions: [{testKey, issueId}, ...]
    - includedTestCases: [{testKey, issueId}, ...]
    """
    updates: Dict[str, Any] = {}
    
    # 기본 필드
    if "testKey" in rtm_json:
        updates["jira_key"] = rtm_json["testKey"]
    if "summary" in rtm_json:
        updates["summary"] = rtm_json["summary"] or ""
    if "description" in rtm_json:
        updates["description"] = rtm_json["description"] or ""
    if "assigneeId" in rtm_json:
        updates["assignee"] = rtm_json["assigneeId"] or ""
    if "projectKey" in rtm_json:
        updates["_rtm_projectKey"] = rtm_json["projectKey"] or ""
    if "parentTestKey" in rtm_json:
        updates["_rtm_parentTestKey"] = rtm_json["parentTestKey"] or ""
    
    # priority
    if "priority" in rtm_json and isinstance(rtm_json["priority"], dict):
        updates["priority"] = rtm_json["priority"].get("name") or ""
    
    # status
    if "status" in rtm_json and isinstance(rtm_json["status"], dict):
        updates["status"] = rtm_json["status"].get("name") or rtm_json["status"].get("statusName") or ""
    
    # labels
    if "labels" in rtm_json and isinstance(rtm_json["labels"], list):
        updates["labels"] = _join_strings(rtm_json["labels"])
    
    # components
    if "components" in rtm_json and isinstance(rtm_json["components"], list):
        updates["components"] = _join_names(rtm_json["components"])
    
    # versions
    if "versions" in rtm_json and isinstance(rtm_json["versions"], list):
        updates["fix_versions"] = _join_names(rtm_json["versions"])
    
    # timeEstimate
    if "timeEstimate" in rtm_json:
        updates["_rtm_timeEstimate"] = rtm_json["timeEstimate"] or ""
    
    # environment
    if "environment" in rtm_json:
        updates["rtm_environment"] = rtm_json["environment"] or ""
    
    # executions
    if "executions" in rtm_json:
        updates["_rtm_executions"] = rtm_json.get("executions") or []
    
    # includedTestCases는 별도로 처리 (Test Cases 탭에서 사용)
    updates["_rtm_includedTestCases"] = rtm_json.get("includedTestCases") or []
    
    return updates


def map_rtm_testexecution_to_local(rtm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM Test Execution GET 응답을 로컬 issues 형식으로 변환.
    
    RTM 응답 구조 (RTM REST API.md 참조):
    - testKey, summary, description, assigneeId, parentTestKey
    - priority: {id, name}
    - labels: [string, ...]
    - components: [{id}, ...]
    - versions: [{id}, ...]
    - timeEstimate: string
    - environment: string
    - result: {id, name, statusName, statusId, finalStatus}
    - executeTransition: {id, name}
    - testCaseExecutions: [{testKey, summary, result, priority, ...}, ...]
    """
    updates: Dict[str, Any] = {}
    
    # 기본 필드
    if "testKey" in rtm_json:
        updates["jira_key"] = rtm_json["testKey"]
    if "summary" in rtm_json:
        updates["summary"] = rtm_json["summary"] or ""
    if "description" in rtm_json:
        updates["description"] = rtm_json["description"] or ""
    if "assigneeId" in rtm_json:
        updates["assignee"] = rtm_json["assigneeId"] or ""
    if "parentTestKey" in rtm_json:
        updates["_rtm_parentTestKey"] = rtm_json["parentTestKey"] or ""
    
    # priority
    if "priority" in rtm_json and isinstance(rtm_json["priority"], dict):
        updates["priority"] = rtm_json["priority"].get("name") or ""
    
    # labels
    if "labels" in rtm_json and isinstance(rtm_json["labels"], list):
        updates["labels"] = _join_strings(rtm_json["labels"])
    
    # components
    if "components" in rtm_json and isinstance(rtm_json["components"], list):
        updates["components"] = _join_names(rtm_json["components"])
    
    # versions
    if "versions" in rtm_json and isinstance(rtm_json["versions"], list):
        updates["fix_versions"] = _join_names(rtm_json["versions"])
    
    # timeEstimate
    if "timeEstimate" in rtm_json:
        updates["_rtm_timeEstimate"] = rtm_json["timeEstimate"] or ""
    
    # environment
    if "environment" in rtm_json:
        updates["rtm_environment"] = rtm_json["environment"] or ""
    
    # result
    if "result" in rtm_json and isinstance(rtm_json["result"], dict):
        updates["_rtm_result"] = rtm_json["result"]
    
    # executeTransition
    if "executeTransition" in rtm_json:
        updates["_rtm_executeTransition"] = rtm_json["executeTransition"]
    
    # testCaseExecutions는 별도로 처리 (Executions 탭에서 사용)
    updates["_rtm_testCaseExecutions"] = rtm_json.get("testCaseExecutions") or []
    
    return updates


def map_rtm_defect_to_local(rtm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM Defect GET 응답을 로컬 issues 형식으로 변환.
    
    RTM 응답 구조 (RTM REST API.md 참조):
    - testKey, summary, description, assigneeId, parentTestKey, projectKey
    - issueTypeId: int
    - priority: {id, name}
    - status: {id, name, statusName}
    - labels: [string, ...]
    - components: [{id}, ...]
    - versions: [{id}, ...]
    - timeEstimate: string
    - environment: string
    - detectingExecutions: [{testKey, issueId}, ...]
    - identifyingTestCases: [{testKey, issueId}, ...]
    """
    updates: Dict[str, Any] = {}
    
    # 기본 필드
    if "testKey" in rtm_json:
        updates["jira_key"] = rtm_json["testKey"]
    if "summary" in rtm_json:
        updates["summary"] = rtm_json["summary"] or ""
    if "description" in rtm_json:
        updates["description"] = rtm_json["description"] or ""
    if "assigneeId" in rtm_json:
        updates["assignee"] = rtm_json["assigneeId"] or ""
    if "projectKey" in rtm_json:
        updates["_rtm_projectKey"] = rtm_json["projectKey"] or ""
    if "parentTestKey" in rtm_json:
        updates["_rtm_parentTestKey"] = rtm_json["parentTestKey"] or ""
    
    # issueTypeId
    if "issueTypeId" in rtm_json:
        updates["_rtm_issueTypeId"] = rtm_json["issueTypeId"]
    
    # priority
    if "priority" in rtm_json and isinstance(rtm_json["priority"], dict):
        updates["priority"] = rtm_json["priority"].get("name") or ""
    
    # status
    if "status" in rtm_json and isinstance(rtm_json["status"], dict):
        updates["status"] = rtm_json["status"].get("name") or rtm_json["status"].get("statusName") or ""
    
    # labels
    if "labels" in rtm_json and isinstance(rtm_json["labels"], list):
        updates["labels"] = _join_strings(rtm_json["labels"])
    
    # components
    if "components" in rtm_json and isinstance(rtm_json["components"], list):
        updates["components"] = _join_names(rtm_json["components"])
    
    # versions
    if "versions" in rtm_json and isinstance(rtm_json["versions"], list):
        updates["fix_versions"] = _join_names(rtm_json["versions"])
    
    # timeEstimate
    if "timeEstimate" in rtm_json:
        updates["_rtm_timeEstimate"] = rtm_json["timeEstimate"] or ""
    
    # environment
    if "environment" in rtm_json:
        updates["rtm_environment"] = rtm_json["environment"] or ""
    
    # detectingExecutions
    if "detectingExecutions" in rtm_json:
        updates["_rtm_detectingExecutions"] = rtm_json.get("detectingExecutions") or []
    
    # identifyingTestCases는 별도로 처리 (Test Cases 탭에서 사용)
    updates["_rtm_identifyingTestCases"] = rtm_json.get("identifyingTestCases") or []
    
    return updates


def map_rtm_to_local(issue_type: str, rtm_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    RTM API 응답을 로컬 issues 형식으로 변환하는 통합 함수.
    
    issue_type에 따라 적절한 매핑 함수를 호출합니다.
    """
    issue_type_upper = (issue_type or "").upper()
    
    if issue_type_upper == "REQUIREMENT":
        return map_rtm_requirement_to_local(rtm_json)
    elif issue_type_upper == "TEST_CASE":
        return map_rtm_testcase_to_local(rtm_json)
    elif issue_type_upper == "TEST_PLAN":
        return map_rtm_testplan_to_local(rtm_json)
    elif issue_type_upper == "TEST_EXECUTION":
        return map_rtm_testexecution_to_local(rtm_json)
    elif issue_type_upper == "DEFECT":
        return map_rtm_defect_to_local(rtm_json)
    else:
        # 기본 매핑 (JIRA 표준 형식 가정)
        return map_jira_to_local(issue_type, rtm_json)


# --------------------------------------------------------------------------- RTM API Payload Building (Local -> RTM)
#
# 로컬 issues 형식 또는 GUI에서 수집한 데이터를 RTM API payload로 변환합니다.


def build_rtm_requirement_payload(local_issue: Dict[str, Any], parent_test_key: Optional[str] = None, project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 RTM Requirement 생성/수정 payload로 변환.
    
    Args:
        local_issue: 로컬 이슈 데이터
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        project_key: 프로젝트 키 (생성 시 필수)
    """
    payload: Dict[str, Any] = {}
    
    # projectKey (생성 시 필수)
    if project_key:
        payload["projectKey"] = project_key
    elif "_rtm_projectKey" in local_issue:
        payload["projectKey"] = local_issue["_rtm_projectKey"]
    
    # issueTypeId (선택적, RTM에서 자동 설정될 수 있음)
    if "issueTypeId" in local_issue:
        payload["issueTypeId"] = local_issue["issueTypeId"]
    elif "_rtm_issueTypeId" in local_issue:
        payload["issueTypeId"] = local_issue["_rtm_issueTypeId"]
    
    if "summary" in local_issue:
        payload["summary"] = local_issue["summary"] or ""
    if "description" in local_issue:
        payload["description"] = local_issue["description"] or ""
    if "assigneeId" in local_issue:
        payload["assigneeId"] = local_issue["assigneeId"]
    elif "assignee" in local_issue and local_issue["assignee"]:
        # assignee가 문자열인 경우 assigneeId로 변환 시도
        payload["assigneeId"] = local_issue["assignee"]
    
    if parent_test_key:
        payload["parentTestKey"] = parent_test_key
    elif "_rtm_parentTestKey" in local_issue:
        payload["parentTestKey"] = local_issue["_rtm_parentTestKey"]
    
    # priority, status는 RTM에서 객체 형태로 요구할 수 있음
    if "priority" in local_issue and local_issue["priority"]:
        if isinstance(local_issue["priority"], str):
            payload["priority"] = {"name": local_issue["priority"]}
        else:
            payload["priority"] = local_issue["priority"]
    
    if "status" in local_issue and local_issue["status"]:
        if isinstance(local_issue["status"], str):
            payload["status"] = {"name": local_issue["status"]}
        else:
            payload["status"] = local_issue["status"]
    
    # labels
    if "labels" in local_issue and local_issue["labels"]:
        if isinstance(local_issue["labels"], str):
            labels = [x.strip() for x in local_issue["labels"].split(",") if x.strip()]
            if labels:
                payload["labels"] = labels
        elif isinstance(local_issue["labels"], list):
            payload["labels"] = local_issue["labels"]
    
    # components
    if "components" in local_issue and local_issue["components"]:
        if isinstance(local_issue["components"], str):
            comp_names = [x.strip() for x in local_issue["components"].split(",") if x.strip()]
            payload["components"] = [{"name": name} for name in comp_names]
        elif isinstance(local_issue["components"], list):
            payload["components"] = local_issue["components"]
    
    # versions
    if "fix_versions" in local_issue and local_issue["fix_versions"]:
        if isinstance(local_issue["fix_versions"], str):
            ver_names = [x.strip() for x in local_issue["fix_versions"].split(",") if x.strip()]
            payload["versions"] = [{"id": name} for name in ver_names]
        elif isinstance(local_issue["fix_versions"], list):
            payload["versions"] = local_issue["fix_versions"]
    
    # timeEstimate
    if "timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["timeEstimate"]
    elif "_rtm_timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["_rtm_timeEstimate"]
    
    # epicName
    if "epic_link" in local_issue and local_issue["epic_link"]:
        payload["epicName"] = local_issue["epic_link"]
    
    # testCasesCovered는 별도 API로 관리될 수 있음
    if "_rtm_testCasesCovered" in local_issue:
        payload["testCasesCovered"] = local_issue["_rtm_testCasesCovered"]
    
    return payload


def build_rtm_testcase_payload(local_issue: Dict[str, Any], parent_test_key: Optional[str] = None, project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 RTM Test Case 생성/수정 payload로 변환.
    
    Args:
        local_issue: 로컬 이슈 데이터
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        project_key: 프로젝트 키 (생성 시 필수)
    """
    payload: Dict[str, Any] = {}
    
    # projectKey (생성 시 필수)
    if project_key:
        payload["projectKey"] = project_key
    elif "_rtm_projectKey" in local_issue:
        payload["projectKey"] = local_issue["_rtm_projectKey"]
    
    if "summary" in local_issue:
        payload["summary"] = local_issue["summary"] or ""
    if "description" in local_issue:
        payload["description"] = local_issue["description"] or ""
    
    if parent_test_key:
        payload["parentTestKey"] = parent_test_key
    elif "_rtm_parentTestKey" in local_issue:
        payload["parentTestKey"] = local_issue["_rtm_parentTestKey"]
    
    if "priority" in local_issue and local_issue["priority"]:
        if isinstance(local_issue["priority"], str):
            payload["priority"] = {"name": local_issue["priority"]}
        else:
            payload["priority"] = local_issue["priority"]
    
    if "status" in local_issue and local_issue["status"]:
        if isinstance(local_issue["status"], str):
            payload["status"] = {"name": local_issue["status"]}
        else:
            payload["status"] = local_issue["status"]
    
    # components
    if "components" in local_issue and local_issue["components"]:
        if isinstance(local_issue["components"], str):
            comp_names = [x.strip() for x in local_issue["components"].split(",") if x.strip()]
            payload["components"] = [{"name": name} for name in comp_names]
        elif isinstance(local_issue["components"], list):
            payload["components"] = local_issue["components"]
    
    # versions
    if "fix_versions" in local_issue and local_issue["fix_versions"]:
        if isinstance(local_issue["fix_versions"], str):
            ver_names = [x.strip() for x in local_issue["fix_versions"].split(",") if x.strip()]
            payload["versions"] = [{"id": name} for name in ver_names]
        elif isinstance(local_issue["fix_versions"], list):
            payload["versions"] = local_issue["fix_versions"]
    
    # timeEstimate
    if "timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["timeEstimate"]
    elif "_rtm_timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["_rtm_timeEstimate"]
    
    # environment
    if "rtm_environment" in local_issue and local_issue["rtm_environment"]:
        payload["environment"] = local_issue["rtm_environment"]
    elif "environment" in local_issue:
        payload["environment"] = local_issue["environment"]
    
    # preconditions
    if "_rtm_preconditions" in local_issue:
        payload["preconditions"] = local_issue["_rtm_preconditions"]
    elif "preconditions" in local_issue:
        payload["preconditions"] = local_issue["preconditions"]
    
    # steps는 별도 API로 관리될 수 있음
    if "_rtm_steps" in local_issue:
        steps_rtm = []
        for step in local_issue["_rtm_steps"]:
            if isinstance(step, dict):
                action = step.get("action") or ""
                value = f"<p>{action}</p>" if action else "<p>-</p>"
                steps_rtm.append([{"value": value}])
        payload["steps"] = steps_rtm
    
    # coveredRequirements
    if "_rtm_coveredRequirements" in local_issue:
        payload["coveredRequirements"] = local_issue["_rtm_coveredRequirements"]
    
    return payload


def build_rtm_testplan_payload(local_issue: Dict[str, Any], parent_test_key: Optional[str] = None, project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 RTM Test Plan 생성/수정 payload로 변환.
    
    Args:
        local_issue: 로컬 이슈 데이터
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        project_key: 프로젝트 키 (생성 시 필수)
    """
    payload: Dict[str, Any] = {}
    
    # projectKey (생성 시 필수)
    if project_key:
        payload["projectKey"] = project_key
    elif "_rtm_projectKey" in local_issue:
        payload["projectKey"] = local_issue["_rtm_projectKey"]
    
    if "summary" in local_issue:
        payload["summary"] = local_issue["summary"] or ""
    if "description" in local_issue:
        payload["description"] = local_issue["description"] or ""
    if "assigneeId" in local_issue:
        payload["assigneeId"] = local_issue["assigneeId"]
    elif "assignee" in local_issue and local_issue["assignee"]:
        payload["assigneeId"] = local_issue["assignee"]
    
    if parent_test_key:
        payload["parentTestKey"] = parent_test_key
    elif "_rtm_parentTestKey" in local_issue:
        payload["parentTestKey"] = local_issue["_rtm_parentTestKey"]
    
    if "priority" in local_issue and local_issue["priority"]:
        if isinstance(local_issue["priority"], str):
            payload["priority"] = {"name": local_issue["priority"]}
        else:
            payload["priority"] = local_issue["priority"]
    
    if "status" in local_issue and local_issue["status"]:
        if isinstance(local_issue["status"], str):
            payload["status"] = {"name": local_issue["status"]}
        else:
            payload["status"] = local_issue["status"]
    
    # labels, components, versions, timeEstimate, environment
    if "labels" in local_issue and local_issue["labels"]:
        if isinstance(local_issue["labels"], str):
            labels = [x.strip() for x in local_issue["labels"].split(",") if x.strip()]
            if labels:
                payload["labels"] = labels
        elif isinstance(local_issue["labels"], list):
            payload["labels"] = local_issue["labels"]
    
    if "components" in local_issue and local_issue["components"]:
        if isinstance(local_issue["components"], str):
            comp_names = [x.strip() for x in local_issue["components"].split(",") if x.strip()]
            payload["components"] = [{"name": name} for name in comp_names]
        elif isinstance(local_issue["components"], list):
            payload["components"] = local_issue["components"]
    
    if "fix_versions" in local_issue and local_issue["fix_versions"]:
        if isinstance(local_issue["fix_versions"], str):
            ver_names = [x.strip() for x in local_issue["fix_versions"].split(",") if x.strip()]
            payload["versions"] = [{"id": name} for name in ver_names]
        elif isinstance(local_issue["fix_versions"], list):
            payload["versions"] = local_issue["fix_versions"]
    
    if "timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["timeEstimate"]
    elif "_rtm_timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["_rtm_timeEstimate"]
    
    if "rtm_environment" in local_issue and local_issue["rtm_environment"]:
        payload["environment"] = local_issue["rtm_environment"]
    elif "environment" in local_issue:
        payload["environment"] = local_issue["environment"]
    
    # executions
    if "_rtm_executions" in local_issue:
        payload["executions"] = local_issue["_rtm_executions"]
    
    # includedTestCases는 별도 API로 관리될 수 있음
    if "_rtm_includedTestCases" in local_issue:
        payload["includedTestCases"] = local_issue["_rtm_includedTestCases"]
    
    return payload


def build_rtm_testexecution_payload(local_issue: Dict[str, Any], parent_test_key: Optional[str] = None, project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 RTM Test Execution 생성/수정 payload로 변환.
    
    Args:
        local_issue: 로컬 이슈 데이터
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        project_key: 프로젝트 키 (생성 시 필수, Test Plan 기반 생성 시에는 불필요)
    """
    payload: Dict[str, Any] = {}
    
    # projectKey는 Test Plan 기반 생성 시에는 불필요
    if project_key:
        payload["projectKey"] = project_key
    elif "_rtm_projectKey" in local_issue:
        payload["projectKey"] = local_issue["_rtm_projectKey"]
    
    if "summary" in local_issue:
        payload["summary"] = local_issue["summary"] or ""
    if "description" in local_issue:
        payload["description"] = local_issue["description"] or ""
    if "assigneeId" in local_issue:
        payload["assigneeId"] = local_issue["assigneeId"]
    elif "assignee" in local_issue and local_issue["assignee"]:
        payload["assigneeId"] = local_issue["assignee"]
    
    if parent_test_key:
        payload["parentTestKey"] = parent_test_key
    elif "_rtm_parentTestKey" in local_issue:
        payload["parentTestKey"] = local_issue["_rtm_parentTestKey"]
    
    if "priority" in local_issue and local_issue["priority"]:
        if isinstance(local_issue["priority"], str):
            payload["priority"] = {"name": local_issue["priority"]}
        else:
            payload["priority"] = local_issue["priority"]
    
    if "status" in local_issue and local_issue["status"]:
        if isinstance(local_issue["status"], str):
            payload["status"] = {"name": local_issue["status"]}
        else:
            payload["status"] = local_issue["status"]
    
    # labels, components, versions, timeEstimate, environment
    if "labels" in local_issue and local_issue["labels"]:
        if isinstance(local_issue["labels"], str):
            labels = [x.strip() for x in local_issue["labels"].split(",") if x.strip()]
            if labels:
                payload["labels"] = labels
        elif isinstance(local_issue["labels"], list):
            payload["labels"] = local_issue["labels"]
    
    if "components" in local_issue and local_issue["components"]:
        if isinstance(local_issue["components"], str):
            comp_names = [x.strip() for x in local_issue["components"].split(",") if x.strip()]
            payload["components"] = [{"name": name} for name in comp_names]
        elif isinstance(local_issue["components"], list):
            payload["components"] = local_issue["components"]
    
    if "fix_versions" in local_issue and local_issue["fix_versions"]:
        if isinstance(local_issue["fix_versions"], str):
            ver_names = [x.strip() for x in local_issue["fix_versions"].split(",") if x.strip()]
            payload["versions"] = [{"id": name} for name in ver_names]
        elif isinstance(local_issue["fix_versions"], list):
            payload["versions"] = local_issue["fix_versions"]
    
    if "timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["timeEstimate"]
    elif "_rtm_timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["_rtm_timeEstimate"]
    
    if "rtm_environment" in local_issue and local_issue["rtm_environment"]:
        payload["environment"] = local_issue["rtm_environment"]
    elif "environment" in local_issue:
        payload["environment"] = local_issue["environment"]
    
    # result
    if "_rtm_result" in local_issue:
        payload["result"] = local_issue["_rtm_result"]
    
    # executeTransition
    if "_rtm_executeTransition" in local_issue:
        payload["executeTransition"] = local_issue["_rtm_executeTransition"]
    
    # testPlan
    if "_rtm_testPlan" in local_issue:
        payload["testPlan"] = local_issue["_rtm_testPlan"]
    
    # testCaseExecutions는 별도 API로 관리될 수 있음
    if "_rtm_testCaseExecutions" in local_issue:
        payload["testCaseExecutions"] = local_issue["_rtm_testCaseExecutions"]
    
    return payload


def build_rtm_defect_payload(local_issue: Dict[str, Any], parent_test_key: Optional[str] = None, project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 RTM Defect 생성/수정 payload로 변환.
    
    Args:
        local_issue: 로컬 이슈 데이터
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        project_key: 프로젝트 키 (생성 시 필수)
    """
    payload: Dict[str, Any] = {}
    
    # projectKey (생성 시 필수)
    if project_key:
        payload["projectKey"] = project_key
    elif "_rtm_projectKey" in local_issue:
        payload["projectKey"] = local_issue["_rtm_projectKey"]
    
    # issueTypeId (선택적)
    if "issueTypeId" in local_issue:
        payload["issueTypeId"] = local_issue["issueTypeId"]
    elif "_rtm_issueTypeId" in local_issue:
        payload["issueTypeId"] = local_issue["_rtm_issueTypeId"]
    
    if "summary" in local_issue:
        payload["summary"] = local_issue["summary"] or ""
    if "description" in local_issue:
        payload["description"] = local_issue["description"] or ""
    if "assigneeId" in local_issue:
        payload["assigneeId"] = local_issue["assigneeId"]
    elif "assignee" in local_issue and local_issue["assignee"]:
        payload["assigneeId"] = local_issue["assignee"]
    
    if parent_test_key:
        payload["parentTestKey"] = parent_test_key
    elif "_rtm_parentTestKey" in local_issue:
        payload["parentTestKey"] = local_issue["_rtm_parentTestKey"]
    
    if "priority" in local_issue and local_issue["priority"]:
        if isinstance(local_issue["priority"], str):
            payload["priority"] = {"name": local_issue["priority"]}
        else:
            payload["priority"] = local_issue["priority"]
    
    if "status" in local_issue and local_issue["status"]:
        if isinstance(local_issue["status"], str):
            payload["status"] = {"name": local_issue["status"]}
        else:
            payload["status"] = local_issue["status"]
    
    # labels, components, versions, timeEstimate, environment
    if "labels" in local_issue and local_issue["labels"]:
        if isinstance(local_issue["labels"], str):
            labels = [x.strip() for x in local_issue["labels"].split(",") if x.strip()]
            if labels:
                payload["labels"] = labels
        elif isinstance(local_issue["labels"], list):
            payload["labels"] = local_issue["labels"]
    
    if "components" in local_issue and local_issue["components"]:
        if isinstance(local_issue["components"], str):
            comp_names = [x.strip() for x in local_issue["components"].split(",") if x.strip()]
            payload["components"] = [{"name": name} for name in comp_names]
        elif isinstance(local_issue["components"], list):
            payload["components"] = local_issue["components"]
    
    if "fix_versions" in local_issue and local_issue["fix_versions"]:
        if isinstance(local_issue["fix_versions"], str):
            ver_names = [x.strip() for x in local_issue["fix_versions"].split(",") if x.strip()]
            payload["versions"] = [{"id": name} for name in ver_names]
        elif isinstance(local_issue["fix_versions"], list):
            payload["versions"] = local_issue["fix_versions"]
    
    if "timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["timeEstimate"]
    elif "_rtm_timeEstimate" in local_issue:
        payload["timeEstimate"] = local_issue["_rtm_timeEstimate"]
    
    if "rtm_environment" in local_issue and local_issue["rtm_environment"]:
        payload["environment"] = local_issue["rtm_environment"]
    elif "environment" in local_issue:
        payload["environment"] = local_issue["environment"]
    
    # detectingExecutions
    if "_rtm_detectingExecutions" in local_issue:
        payload["detectingExecutions"] = local_issue["_rtm_detectingExecutions"]
    
    # identifyingTestCases는 별도 API로 관리될 수 있음
    if "_rtm_identifyingTestCases" in local_issue:
        payload["identifyingTestCases"] = local_issue["_rtm_identifyingTestCases"]
    
    return payload


def build_rtm_payload(issue_type: str, local_issue: Dict[str, Any], parent_test_key: Optional[str] = None, project_key: Optional[str] = None) -> Dict[str, Any]:
    """
    로컬 이슈 데이터를 RTM API payload로 변환하는 통합 함수.
    
    Args:
        issue_type: 이슈 타입 (REQUIREMENT, TEST_CASE, ...)
        local_issue: 로컬 이슈 데이터
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        project_key: 프로젝트 키 (생성 시 필수)
    
    issue_type에 따라 적절한 payload 생성 함수를 호출합니다.
    """
    issue_type_upper = (issue_type or "").upper()
    
    if issue_type_upper == "REQUIREMENT":
        return build_rtm_requirement_payload(local_issue, parent_test_key, project_key)
    elif issue_type_upper == "TEST_CASE":
        return build_rtm_testcase_payload(local_issue, parent_test_key, project_key)
    elif issue_type_upper == "TEST_PLAN":
        return build_rtm_testplan_payload(local_issue, parent_test_key, project_key)
    elif issue_type_upper == "TEST_EXECUTION":
        return build_rtm_testexecution_payload(local_issue, parent_test_key, project_key)
    elif issue_type_upper == "DEFECT":
        return build_rtm_defect_payload(local_issue, parent_test_key, project_key)
    else:
        # 기본 payload (JIRA 표준 형식 가정)
        return build_jira_create_payload(issue_type, local_issue)