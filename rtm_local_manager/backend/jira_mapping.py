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
    if not items:
        return ""
    names = []
    for x in items:
        if not isinstance(x, dict):
            continue
        name = x.get("name")
        if name:
            names.append(str(name))
    return ", ".join(names)


def _join_strings(items: Optional[List[Any]]) -> str:
    if not items:
        return ""
    return ", ".join(str(x) for x in items)


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

    return fields


def build_jira_update_payload(issue_type: str, local_issue: Dict[str, Any]) -> Dict[str, Any]:
    """
    map_local_to_jira_fields() 결과를 'fields' 키 아래에 넣어 최종 payload 구성.
    """
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

    로컬 testcase_executions 구조:
      - order_no
      - testcase_id (-> 매핑 단계에서 local issue_id 로 바꾸어야 함)
      - assignee
      - result
      - rtm_environment
      - defects (문자열)
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
        key = item.get("key")
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

        results.append(
            {
                "order_no": item.get("order") or item.get("orderNo") or idx,
                "testcase_key": key,
                "assignee": assignee,
                "result": result_val,
                "rtm_environment": env,
                "defects": defects,
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
        items.append(item)

    return {"testCases": items}
