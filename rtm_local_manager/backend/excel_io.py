"""
excel_io.py - Excel import/export helpers for RTM Local Manager.

- Export:
    export_project_to_excel(conn, project_id, file_path)

- Import:
    import_project_from_excel(conn, project_id, file_path)

주의사항:
- .xlsx 처리를 위해 openpyxl 라이브러리를 사용한다. (사용 PC에 설치되어 있어야 함)
- 이 모듈은 main import 시점에는 openpyxl 을 import 하지 않는다.
  (함수 내부에서 import 하므로, openpyxl 미설치 환경에서도 프로그램 실행 자체는 가능)
"""

from __future__ import annotations

from typing import Any, Dict, List

import sqlite3


def _ensure_openpyxl():
    try:
        import openpyxl  # type: ignore
    except Exception as e:  # pragma: no cover - runtime 오류 표시용
        raise RuntimeError(
            "openpyxl 이 설치되어 있지 않아 Excel 기능을 사용할 수 없습니다.\n"
            "pip install openpyxl 로 설치 후 다시 시도해 주세요."
        ) from e
    return openpyxl


# --------------------------------------------------------------------------- Export helpers


def export_project_to_excel(conn: sqlite3.Connection, project_id: int, file_path: str) -> None:
    """
    현재 project_id 에 속한 주요 엔티티들을 하나의 Excel 워크북(.xlsx)으로 내보낸다.

    시트 구성:
      - Issues
      - TestcaseSteps
      - Relations
      - TestPlanTestcases
      - TestExecutions
      - TestcaseExecutions

    각 시트는 최소한의 식별자(jira_key, summary 등)를 포함하여,
    나중에 Import 시 jira_key 를 기준으로 매핑할 수 있도록 설계한다.
    """
    openpyxl = _ensure_openpyxl()
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    # default sheet 제거
    default_sheet = wb.active
    wb.remove(default_sheet)

    cur = conn.cursor()

    # --- Issues 시트
    ws = wb.create_sheet("Issues")
    # 컬럼 정의
    issue_cols = [
        "id",
        "jira_key",
        "issue_type",
        "summary",
        "status",
        "priority",
        "assignee",
        "reporter",
        "labels",
        "components",
        "security_level",
        "fix_versions",
        "affects_versions",
        "rtm_environment",
        "due_date",
        "created",
        "updated",
    ]
    ws.append(issue_cols)
    cur.execute(
        """
        SELECT id, jira_key, issue_type, summary, status, priority, assignee, reporter,
               labels, components, security_level, fix_versions, affects_versions,
               rtm_environment, due_date, created, updated
          FROM issues
         WHERE project_id = ? AND is_deleted = 0
         ORDER BY id
        """,
        (project_id,),
    )
    for row in cur.fetchall():
        ws.append(list(row))

    # --- TestcaseSteps 시트
    ws = wb.create_sheet("TestcaseSteps")
    # SW 사양 기준으로 Test Case Steps 구조 확장:
    # - Preconditions: Test Case 단위 필드
    # - group_no: Step 그룹 번호 (각 그룹 내에서 order_no 가 1부터 시작)
    step_cols = ["issue_jira_key", "preconditions", "group_no", "order_no", "action", "input", "expected"]
    ws.append(step_cols)
    cur.execute(
        """
        SELECT i.jira_key,
               i.preconditions,
               COALESCE(t.group_no, 1) AS group_no,
               t.order_no,
               t.action,
               t.input,
               t.expected
          FROM testcase_steps t
          JOIN issues i ON t.issue_id = i.id
         WHERE i.project_id = ? AND i.is_deleted = 0
         ORDER BY i.jira_key, group_no, order_no
        """,
        (project_id,),
    )
    for row in cur.fetchall():
        ws.append(list(row))

    # --- Relations 시트
    ws = wb.create_sheet("Relations")
    rel_cols = ["src_jira_key", "dst_jira_key", "relation_type"]
    ws.append(rel_cols)
    cur.execute(
        """
        SELECT s.jira_key AS src_key,
               d.jira_key AS dst_key,
               r.relation_type
          FROM relations r
          JOIN issues s ON r.src_issue_id = s.id
          JOIN issues d ON r.dst_issue_id = d.id
         WHERE s.project_id = ? AND s.is_deleted = 0 AND d.is_deleted = 0
         ORDER BY src_key, dst_key
        """,
        (project_id,),
    )
    for row in cur.fetchall():
        ws.append(list(row))

    # --- TestPlanTestcases 시트
    ws = wb.create_sheet("TestPlanTestcases")
    tp_cols = ["testplan_jira_key", "testcase_jira_key", "order_no"]
    ws.append(tp_cols)
    cur.execute(
        """
        SELECT tp.jira_key AS testplan_key,
               tc.jira_key AS testcase_key,
               t.order_no
          FROM testplan_testcases t
          JOIN issues tp ON t.testplan_id = tp.id
          JOIN issues tc ON t.testcase_id = tc.id
         WHERE tp.project_id = ? AND tp.is_deleted = 0 AND tc.is_deleted = 0
         ORDER BY testplan_key, t.order_no
        """,
        (project_id,),
    )
    for row in cur.fetchall():
        ws.append(list(row))

    # --- TestExecutions 시트
    ws = wb.create_sheet("TestExecutions")
    te_cols = ["testexecution_jira_key", "environment", "start_date", "end_date", "result", "executed_by"]
    ws.append(te_cols)
    cur.execute(
        """
        SELECT i.jira_key,
               t.environment,
               t.start_date,
               t.end_date,
               t.result,
               t.executed_by
          FROM testexecutions t
          JOIN issues i ON t.issue_id = i.id
         WHERE i.project_id = ? AND i.is_deleted = 0
         ORDER BY i.jira_key
        """,
        (project_id,),
    )
    for row in cur.fetchall():
        ws.append(list(row))

    # --- TestcaseExecutions 시트
    ws = wb.create_sheet("TestcaseExecutions")
    tce_cols = [
        "testexecution_jira_key",
        "testcase_jira_key",
        "order_no",
        "assignee",
        "result",
        "rtm_environment",
        "defects",
    ]
    ws.append(tce_cols)
    cur.execute(
        """
        SELECT tei.jira_key AS te_key,
               tci.jira_key AS tc_key,
               t.order_no,
               t.assignee,
               t.result,
               t.rtm_environment,
               t.defects
          FROM testcase_executions t
          JOIN testexecutions te ON t.testexecution_id = te.id
          JOIN issues tei ON te.issue_id = tei.id
          JOIN issues tci ON t.testcase_id = tci.id
         WHERE tei.project_id = ? AND tei.is_deleted = 0 AND tci.is_deleted = 0
         ORDER BY te_key, t.order_no
        """,
        (project_id,),
    )
    for row in cur.fetchall():
        ws.append(list(row))

    # 약간의 자동 너비 조정 (간단히)
    for ws in wb.worksheets:
        for col_idx, col in enumerate(ws.columns, start=1):
            max_len = 0
            for cell in col:
                try:
                    val = str(cell.value) if cell.value is not None else ""
                except Exception:
                    val = ""
                if len(val) > max_len:
                    max_len = len(val)
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 80)

    wb.save(file_path)


# --------------------------------------------------------------------------- Import helpers


def import_project_from_excel(conn: sqlite3.Connection, project_id: int, file_path: str) -> None:
    """
    Excel 파일(.xlsx)에서 주요 엔티티를 읽어와 로컬 DB에 반영한다.

    처리 범위:
      - Issues 시트:
          - jira_key 기준으로 존재 여부 확인
          - 있으면 주요 필드 update, 없으면 신규 issue insert (folder_id 는 None)
      - TestcaseSteps 시트:
          - issue_jira_key 기준으로 대상 issue 찾은 뒤, 해당 issue 의 steps 전체 교체
      - Relations 시트:
          - src_jira_key / dst_jira_key 기준으로 양쪽 issue 찾고 relations 교체
      - TestPlanTestcases 시트:
          - testplan_jira_key / testcase_jira_key 기준으로 testplan_testcases 교체
      - TestExecutions 시트:
          - testexecution_jira_key 기준으로 testexecution 메타 정보 update/신규 생성
      - TestcaseExecutions 시트:
          - testexecution_jira_key / testcase_jira_key 기준으로 testcase_executions 교체

    Excel 컬럼 헤더는 export_project_to_excel()에서 생성한 것과 동일해야 한다.
    """
    openpyxl = _ensure_openpyxl()
    from backend.db import (
        get_issue_by_jira_key,
        get_issue_by_id,
        update_issue_fields,
        replace_steps_for_issue,
        replace_relations_for_issue,
        replace_testplan_testcases,
        get_or_create_testexecution_for_issue,
        update_testexecution_for_issue,
        replace_testcase_executions,
        create_local_issue,
        ensure_folder_path,
    )

    wb = openpyxl.load_workbook(file_path, data_only=True)

    cur = conn.cursor()

    # --- Issues 시트 처리
    if "Issues" in wb.sheetnames:
        ws = wb["Issues"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(h) if h is not None else "" for h in rows[0]]
            col_idx = {name: i for i, name in enumerate(header)}
            for row in rows[1:]:
                if not any(row):
                    continue

                # 0) id 컬럼이 있고 값이 있으면, 로컬 ID 기준 "수정"으로 처리
                local_id = None
                id_idx = col_idx.get("id")
                if id_idx is not None and 0 <= id_idx < len(row):
                    raw_id = row[id_idx]
                    if raw_id not in (None, ""):
                        try:
                            # 엑셀에서 숫자가 float 로 넘어오는 경우까지 고려
                            local_id = int(str(raw_id).split(".")[0])
                        except Exception:
                            local_id = None

                # 공통 필드 추출 (id/jira_key 를 제외한 나머지)
                # jira_key 컬럼이 있으면 JIRA 이슈 기준으로 upsert,
                # jira_key 가 비어 있으면 "로컬 전용 이슈" 로 신규 생성한다.
                jira_key_idx = col_idx.get("jira_key")
                jira_key: str | None
                if jira_key_idx is None or jira_key_idx < 0 or jira_key_idx >= len(row):
                    jira_key = None
                else:
                    raw_key = row[jira_key_idx]
                    jira_key = str(raw_key) if raw_key not in (None, "") else None

                fields: Dict[str, Any] = {}
                for name in [
                    "issue_type",
                    "summary",
                    "status",
                    "priority",
                    "assignee",
                    "reporter",
                    "labels",
                    "components",
                    "security_level",
                    "fix_versions",
                    "affects_versions",
                    "rtm_environment",
                    "due_date",
                ]:
                    idx = col_idx.get(name)
                    if idx is None or idx < 0 or idx >= len(row):
                        continue
                    val = row[idx]
                    if val is not None:
                        fields[name] = str(val)

                # 폴더 경로 (optional): folder_path 컬럼이 있으면 이를 기반으로 folder_id 를 계산
                folder_id = None
                folder_idx = col_idx.get("folder_path")
                if folder_idx is not None and 0 <= folder_idx < len(row):
                    raw_path = row[folder_idx]
                    if raw_path not in (None, ""):
                        issue_type_for_folder = fields.get("issue_type")
                        folder_id = ensure_folder_path(
                            conn,
                            project_id=project_id,
                            path=str(raw_path),
                            issue_type=issue_type_for_folder,
                        )
                        if folder_id:
                            fields["folder_id"] = folder_id

                # 0-1) local_id 로 업데이트 가능한 경우: 해당 행은 "수정"으로만 처리
                if local_id is not None:
                    issue = get_issue_by_id(conn, local_id)
                    if issue and issue.get("project_id") == project_id:
                        update_issue_fields(conn, local_id, fields)
                        continue
                    # ID 가 없거나 다른 프로젝트인 경우에는 아래 jira_key / 신규 생성 로직으로 넘어간다.

                if jira_key:
                    # JIRA Key 가 있는 경우: 기존 이슈 update 또는 신규 JIRA-연동 이슈 insert
                    issue = get_issue_by_jira_key(conn, project_id, jira_key)
                    if issue:
                        update_issue_fields(conn, issue["id"], fields)
                    else:
                        cur.execute(
                            """
                            INSERT INTO issues (
                                project_id, folder_id, jira_key, issue_type, summary,
                                status, priority, assignee, reporter, labels, components,
                                security_level, fix_versions, affects_versions,
                                rtm_environment, due_date, created, updated, is_deleted
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0)
                            """,
                            (
                                project_id,
                                folder_id,
                                jira_key,
                                fields.get("issue_type") or "",
                                fields.get("summary") or "",
                                fields.get("status") or "",
                                fields.get("priority") or "",
                                fields.get("assignee") or "",
                                fields.get("reporter") or "",
                                fields.get("labels") or "",
                                fields.get("components") or "",
                                fields.get("security_level") or "",
                                fields.get("fix_versions") or "",
                                fields.get("affects_versions") or "",
                                fields.get("rtm_environment") or "",
                                fields.get("due_date") or "",
                            ),
                        )
                    conn.commit()
                else:
                    # jira_key が 비어 있는 경우:
                    #   - 엑셀에 local ID 가 없어도, issue_type / summary 정보만 있으면
                    #     로컬 전용 이슈를 자동으로 생성한다.
                    issue_type = fields.get("issue_type")
                    summary = fields.get("summary", "")
                    if not issue_type:
                        # issue_type 이 없는 행은 스킵 (스키마상 NOT NULL)
                        continue

                    new_issue_id = create_local_issue(
                        conn,
                        project_id=project_id,
                        issue_type=issue_type,
                        folder_id=folder_id,
                        summary=summary,
                    )
                    # create_local_issue 로 기본 값은 들어갔으므로,
                    # 나머지 필드가 있다면 추가로 업데이트한다.
                    # (issue_type / summary 는 동일 값으로 한 번 더 세팅해도 무방)
                    update_issue_fields(conn, new_issue_id, fields)

    # --- TestcaseSteps 시트 처리
    if "TestcaseSteps" in wb.sheetnames:
        ws = wb["TestcaseSteps"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(h) if h is not None else "" for h in rows[0]]
            col_idx = {name: i for i, name in enumerate(header)}
            steps_by_key: Dict[str, List[Dict[str, Any]]] = {}
            preconditions_by_key: Dict[str, str] = {}
            for row in rows[1:]:
                if not any(row):
                    continue
                key_idx = col_idx.get("issue_jira_key")
                if key_idx is None or key_idx < 0 or key_idx >= len(row):
                    continue
                jira_key = row[key_idx]
                if not jira_key:
                    continue
                jira_key = str(jira_key)
                order_no = None
                action = None
                inp = None
                expected = None
                group_no = None

                # Preconditions (Test Case 단위, 마지막 값이 우선)
                idx_pre = col_idx.get("preconditions")
                if idx_pre is not None and 0 <= idx_pre < len(row):
                    pre_val = row[idx_pre]
                    if pre_val not in (None, ""):
                        preconditions_by_key[jira_key] = str(pre_val)

                idx_group = col_idx.get("group_no")
                if idx_group is not None and 0 <= idx_group < len(row):
                    group_no = row[idx_group]

                idx_order = col_idx.get("order_no")
                if idx_order is not None and 0 <= idx_order < len(row):
                    order_no = row[idx_order]
                idx_action = col_idx.get("action")
                if idx_action is not None and 0 <= idx_action < len(row):
                    action = row[idx_action]
                idx_input = col_idx.get("input")
                if idx_input is not None and 0 <= idx_input < len(row):
                    inp = row[idx_input]
                idx_expected = col_idx.get("expected")
                if idx_expected is not None and 0 <= idx_expected < len(row):
                    expected = row[idx_expected]

                steps_by_key.setdefault(jira_key, []).append(
                    {
                        "group_no": int(group_no) if group_no is not None else 1,
                        "order_no": int(order_no) if order_no is not None else 0,
                        "action": str(action) if action is not None else "",
                        "input": str(inp) if inp is not None else "",
                        "expected": str(expected) if expected is not None else "",
                    }
                )
            for jira_key, steps in steps_by_key.items():
                issue = get_issue_by_jira_key(conn, project_id, jira_key)
                if not issue:
                    continue
                replace_steps_for_issue(conn, issue["id"], steps)
                pre = preconditions_by_key.get(jira_key)
                if pre is not None:
                    update_issue_fields(conn, issue["id"], {"preconditions": pre})

    # --- Relations 시트 처리
    if "Relations" in wb.sheetnames:
        ws = wb["Relations"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(h) if h is not None else "" for h in rows[0]]
            col_idx = {name: i for i, name in enumerate(header)}
            rels_by_src: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows[1:]:
                if not any(row):
                    continue
                src_idx = col_idx.get("src_jira_key")
                dst_idx = col_idx.get("dst_jira_key")
                type_idx = col_idx.get("relation_type")
                if src_idx is None or dst_idx is None:
                    continue
                src_key = row[src_idx]
                dst_key = row[dst_idx]
                if not src_key or not dst_key:
                    continue
                src_key = str(src_key)
                dst_key = str(dst_key)
                rel_type = ""
                if type_idx is not None and 0 <= type_idx < len(row):
                    val = row[type_idx]
                    if val is not None:
                        rel_type = str(val)
                rels_by_src.setdefault(src_key, []).append(
                    {"dst_jira_key": dst_key, "relation_type": rel_type}
                )

            for src_key, rel_list in rels_by_src.items():
                src_issue = get_issue_by_jira_key(conn, project_id, src_key)
                if not src_issue:
                    continue
                records: List[Dict[str, Any]] = []
                for rel in rel_list:
                    dst_issue = get_issue_by_jira_key(conn, project_id, rel["dst_jira_key"])
                    if not dst_issue:
                        continue
                    records.append(
                        {
                            "dst_issue_id": dst_issue["id"],
                            "relation_type": rel.get("relation_type") or "",
                        }
                    )
                if records:
                    replace_relations_for_issue(conn, src_issue["id"], records)

    # --- TestPlanTestcases 시트 처리
    if "TestPlanTestcases" in wb.sheetnames:
        ws = wb["TestPlanTestcases"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(h) if h is not None else "" for h in rows[0]]
            col_idx = {name: i for i, name in enumerate(header)}
            by_tp: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows[1:]:
                if not any(row):
                    continue
                tp_idx = col_idx.get("testplan_jira_key")
                tc_idx = col_idx.get("testcase_jira_key")
                order_idx = col_idx.get("order_no")
                if tp_idx is None or tc_idx is None:
                    continue
                tp_key = row[tp_idx]
                tc_key = row[tc_idx]
                if not tp_key or not tc_key:
                    continue
                tp_key = str(tp_key)
                tc_key = str(tc_key)
                order_no = 0
                if order_idx is not None and 0 <= order_idx < len(row):
                    val = row[order_idx]
                    if val is not None:
                        try:
                            order_no = int(val)
                        except Exception:
                            order_no = 0
                by_tp.setdefault(tp_key, []).append(
                    {"testcase_jira_key": tc_key, "order_no": order_no}
                )

            for tp_key, mappings in by_tp.items():
                tp_issue = get_issue_by_jira_key(conn, project_id, tp_key)
                if not tp_issue:
                    continue
                records: List[Dict[str, Any]] = []
                for m in mappings:
                    tc_issue = get_issue_by_jira_key(conn, project_id, m["testcase_jira_key"])
                    if not tc_issue:
                        continue
                    records.append(
                        {
                            "testplan_id": tp_issue["id"],
                            "testcase_id": tc_issue["id"],
                            "order_no": m["order_no"],
                        }
                    )
                if records:
                    replace_testplan_testcases(conn, tp_issue["id"], records)

    # --- TestExecutions 시트 처리
    if "TestExecutions" in wb.sheetnames:
        ws = wb["TestExecutions"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(h) if h is not None else "" for h in rows[0]]
            col_idx = {name: i for i, name in enumerate(header)}
            for row in rows[1:]:
                if not any(row):
                    continue
                key_idx = col_idx.get("testexecution_jira_key")
                if key_idx is None or key_idx < 0 or key_idx >= len(row):
                    continue
                te_key = row[key_idx]
                if not te_key:
                    continue
                te_key = str(te_key)
                te_issue = get_issue_by_jira_key(conn, project_id, te_key)
                if not te_issue:
                    continue
                env = None
                start_date = None
                end_date = None
                result_val = None
                executed_by = None

                idx_env = col_idx.get("environment")
                if idx_env is not None and 0 <= idx_env < len(row):
                    env = row[idx_env]
                idx_start = col_idx.get("start_date")
                if idx_start is not None and 0 <= idx_start < len(row):
                    start_date = row[idx_start]
                idx_end = col_idx.get("end_date")
                if idx_end is not None and 0 <= idx_end < len(row):
                    end_date = row[idx_end]
                idx_result = col_idx.get("result")
                if idx_result is not None and 0 <= idx_result < len(row):
                    result_val = row[idx_result]
                idx_exec = col_idx.get("executed_by")
                if idx_exec is not None and 0 <= idx_exec < len(row):
                    executed_by = row[idx_exec]

                te_row = get_or_create_testexecution_for_issue(conn, te_issue["id"])
                meta = {}
                if env is not None:
                    meta["environment"] = str(env)
                if start_date is not None:
                    meta["start_date"] = str(start_date)
                if end_date is not None:
                    meta["end_date"] = str(end_date)
                if result_val is not None:
                    meta["result"] = str(result_val)
                if executed_by is not None:
                    meta["executed_by"] = str(executed_by)
                if meta:
                    update_testexecution_for_issue(conn, te_issue["id"], meta)

    # --- TestcaseExecutions 시트 처리
    if "TestcaseExecutions" in wb.sheetnames:
        ws = wb["TestcaseExecutions"]
        rows = list(ws.iter_rows(values_only=True))
        if rows:
            header = [str(h) if h is not None else "" for h in rows[0]]
            col_idx = {name: i for i, name in enumerate(header)}
            by_te: Dict[str, List[Dict[str, Any]]] = {}
            for row in rows[1:]:
                if not any(row):
                    continue
                te_idx = col_idx.get("testexecution_jira_key")
                tc_idx = col_idx.get("testcase_jira_key")
                if te_idx is None or tc_idx is None:
                    continue
                te_key = row[te_idx]
                tc_key = row[tc_idx]
                if not te_key or not tc_key:
                    continue
                te_key = str(te_key)
                tc_key = str(tc_key)

                order_no = 0
                assignee = ""
                result_val = ""
                env = ""
                defects = ""

                idx_order = col_idx.get("order_no")
                if idx_order is not None and 0 <= idx_order < len(row):
                    val = row[idx_order]
                    if val is not None:
                        try:
                            order_no = int(val)
                        except Exception:
                            order_no = 0
                idx_assignee = col_idx.get("assignee")
                if idx_assignee is not None and 0 <= idx_assignee < len(row):
                    val = row[idx_assignee]
                    if val is not None:
                        assignee = str(val)
                idx_res = col_idx.get("result")
                if idx_res is not None and 0 <= idx_res < len(row):
                    val = row[idx_res]
                    if val is not None:
                        result_val = str(val)
                idx_env = col_idx.get("rtm_environment")
                if idx_env is not None and 0 <= idx_env < len(row):
                    val = row[idx_env]
                    if val is not None:
                        env = str(val)
                idx_def = col_idx.get("defects")
                if idx_def is not None and 0 <= idx_def < len(row):
                    val = row[idx_def]
                    if val is not None:
                        defects = str(val)

                by_te.setdefault(te_key, []).append(
                    {
                        "testcase_jira_key": tc_key,
                        "order_no": order_no,
                        "assignee": assignee,
                        "result": result_val,
                        "rtm_environment": env,
                        "defects": defects,
                    }
                )

            for te_key, items in by_te.items():
                te_issue = get_issue_by_jira_key(conn, project_id, te_key)
                if not te_issue:
                    continue
                te_row = get_or_create_testexecution_for_issue(conn, te_issue["id"])
                records: List[Dict[str, Any]] = []
                for item in items:
                    tc_issue = get_issue_by_jira_key(conn, project_id, item["testcase_jira_key"])
                    if not tc_issue:
                        continue
                    records.append(
                        {
                            "testexecution_id": te_row["id"],
                            "testcase_id": tc_issue["id"],
                            "order_no": item["order_no"],
                            "assignee": item["assignee"],
                            "result": item["result"],
                            "rtm_environment": item["rtm_environment"],
                            "defects": item["defects"],
                        }
                    )
                if records:
                    replace_testcase_executions(conn, te_row["id"], records)
