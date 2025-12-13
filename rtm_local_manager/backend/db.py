
"""
db.py - SQLite schema and basic data access layer for RTM Local Manager.

This module:
- Creates the SQLite database and all tables if they don't exist.
- Provides a minimal repository-style API for projects, folders, and issues.
- Is intentionally simple (no external ORM) so it can run in air-gapped environments.
"""

from __future__ import annotations

import sqlite3
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any


DB_FILENAME = "rtm_local_manager.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get a sqlite3 connection. If db_path is None, use DB_FILENAME in current working directory.
    """
    if db_path is None:
        db_path = Path(DB_FILENAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Create all tables if they do not exist.
    This function is idempotent and can be safely called on startup.
    """
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key     TEXT NOT NULL,
            project_id      INTEGER NOT NULL,
            name            TEXT,
            base_url        TEXT,
            rtm_version     TEXT,
            UNIQUE(project_key)
        );

        CREATE TABLE IF NOT EXISTS folders (
            id              TEXT PRIMARY KEY,
            project_id      INTEGER NOT NULL REFERENCES projects(id),
            parent_id       TEXT REFERENCES folders(id),
            name            TEXT NOT NULL,
            node_type       TEXT NOT NULL,
            sort_order      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS issues (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id          INTEGER NOT NULL REFERENCES projects(id),
            jira_key            TEXT,
            jira_id             INTEGER,
            issue_type          TEXT NOT NULL,
            summary             TEXT,
            description         TEXT,
            status              TEXT,
            priority            TEXT,
            assignee            TEXT,
            reporter            TEXT,
            labels              TEXT,
            components          TEXT,
            security_level      TEXT,
            fix_versions        TEXT,
            affects_versions    TEXT,
            rtm_environment     TEXT,
            due_date            TEXT,
            created             TEXT,
            updated             TEXT,
            attachments         TEXT,
            epic_link           TEXT,
            sprint              TEXT,
            folder_id           TEXT REFERENCES folders(id),
            parent_issue_id     INTEGER REFERENCES issues(id),
            is_deleted          INTEGER DEFAULT 0,
            local_only          INTEGER DEFAULT 0,
            last_sync_at        TEXT,
            dirty               INTEGER DEFAULT 0,
            preconditions       TEXT,
            local_activity      TEXT
        );

        CREATE TABLE IF NOT EXISTS testcase_steps (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id        INTEGER NOT NULL REFERENCES issues(id),
            group_no        INTEGER DEFAULT 1,
            order_no        INTEGER NOT NULL,
            action          TEXT,
            input           TEXT,
            expected        TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_testcase_steps_issue ON testcase_steps(issue_id);

        CREATE TABLE IF NOT EXISTS testplan_testcases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            testplan_id     INTEGER NOT NULL REFERENCES issues(id),
            testcase_id     INTEGER NOT NULL REFERENCES issues(id),
            order_no        INTEGER,
            UNIQUE(testplan_id, testcase_id)
        );

        CREATE TABLE IF NOT EXISTS testexecutions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id            INTEGER NOT NULL REFERENCES issues(id),
            environment         TEXT,
            start_date          TEXT,
            end_date            TEXT,
            result              TEXT,
            executed_by         TEXT
        );

        CREATE TABLE IF NOT EXISTS testcase_executions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            testexecution_id    INTEGER NOT NULL REFERENCES testexecutions(id),
            testcase_id         INTEGER NOT NULL REFERENCES issues(id),
            order_no            INTEGER,
            assignee            TEXT,
            result              TEXT,
            actual_time         INTEGER,
            rtm_environment     TEXT,
            defects             TEXT,
            tce_test_key        TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tc_exec_te ON testcase_executions(testexecution_id);

        CREATE TABLE IF NOT EXISTS testcase_step_executions (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            testcase_execution_id   INTEGER NOT NULL REFERENCES testcase_executions(id),
            testcase_step_id        INTEGER NOT NULL REFERENCES testcase_steps(id),
            status                  TEXT,
            actual_result           TEXT,
            evidence                TEXT
        );

        CREATE TABLE IF NOT EXISTS relations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            src_issue_id    INTEGER NOT NULL REFERENCES issues(id),
            dst_issue_id    INTEGER NOT NULL REFERENCES issues(id),
            relation_type   TEXT NOT NULL,
            created_at      TEXT,
            UNIQUE(src_issue_id, dst_issue_id, relation_type)
        );
        CREATE INDEX IF NOT EXISTS idx_rel_src ON relations(src_issue_id);
        CREATE INDEX IF NOT EXISTS idx_rel_dst ON relations(dst_issue_id);

        CREATE TABLE IF NOT EXISTS sync_state (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id          INTEGER NOT NULL REFERENCES projects(id),
            last_full_sync_at   TEXT,
            last_tree_sync_at   TEXT,
            last_issue_sync_at  TEXT
        );
        """
    )

    # Lightweight schema migrations for existing DBs
    cur.execute("PRAGMA table_info(issues)")
    issue_cols = [r[1] for r in cur.fetchall()]
    if "preconditions" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN preconditions TEXT")
        except sqlite3.OperationalError:
            pass
    if "local_activity" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN local_activity TEXT")
        except sqlite3.OperationalError:
            pass
    # Defect / Agile 연동용 필드 (Epic Link / Sprint)
    if "epic_link" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN epic_link TEXT")
        except sqlite3.OperationalError:
            pass
    if "sprint" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN sprint TEXT")
        except sqlite3.OperationalError:
            pass

    cur.execute("PRAGMA table_info(testcase_steps)")
    step_cols = [r[1] for r in cur.fetchall()]
    if "group_no" not in step_cols:
        try:
            cur.execute("ALTER TABLE testcase_steps ADD COLUMN group_no INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass

    # testcase_executions 에 actual_time / tce_test_key 컬럼이 없으면 추가
    cur.execute("PRAGMA table_info(testcase_executions)")
    tce_cols = [r[1] for r in cur.fetchall()]
    if "actual_time" not in tce_cols:
        try:
            cur.execute("ALTER TABLE testcase_executions ADD COLUMN actual_time INTEGER")
        except sqlite3.OperationalError:
            pass
    if "tce_test_key" not in tce_cols:
        try:
            cur.execute("ALTER TABLE testcase_executions ADD COLUMN tce_test_key TEXT")
        except sqlite3.OperationalError:
            pass

    conn.commit()


# --- Simple dataclasses & repositories (minimal) --------------------------------


@dataclass
class Project:
    id: int
    project_key: str
    project_id: int
    name: Optional[str] = None
    base_url: Optional[str] = None
    rtm_version: Optional[str] = None


def get_or_create_project(
    conn: sqlite3.Connection,
    project_key: str,
    project_id: int,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Project:
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM projects WHERE project_key = ?",
        (project_key,),
    )
    row = cur.fetchone()
    if row:
        return Project(
            id=row["id"],
            project_key=row["project_key"],
            project_id=row["project_id"],
            name=row["name"],
            base_url=row["base_url"],
            rtm_version=row["rtm_version"],
        )

    cur.execute(
        """
        INSERT INTO projects (project_key, project_id, name, base_url)
        VALUES (?, ?, ?, ?)
        """,
        (project_key, project_id, name, base_url),
    )

    # Lightweight schema migrations for existing DBs
    cur.execute("PRAGMA table_info(issues)")
    issue_cols = [r[1] for r in cur.fetchall()]
    if "preconditions" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN preconditions TEXT")
        except sqlite3.OperationalError:
            pass
    if "epic_link" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN epic_link TEXT")
        except sqlite3.OperationalError:
            pass
    if "sprint" not in issue_cols:
        try:
            cur.execute("ALTER TABLE issues ADD COLUMN sprint TEXT")
        except sqlite3.OperationalError:
            pass

    cur.execute("PRAGMA table_info(testcase_steps)")
    step_cols = [r[1] for r in cur.fetchall()]
    if "group_no" not in step_cols:
        try:
            cur.execute("ALTER TABLE testcase_steps ADD COLUMN group_no INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass

    # testcase_executions 에 actual_time / tce_test_key 컬럼이 없으면 추가
    cur.execute("PRAGMA table_info(testcase_executions)")
    tce_cols = [r[1] for r in cur.fetchall()]
    if "actual_time" not in tce_cols:
        try:
            cur.execute("ALTER TABLE testcase_executions ADD COLUMN actual_time INTEGER")
        except sqlite3.OperationalError:
            pass
    if "tce_test_key" not in tce_cols:
        try:
            cur.execute("ALTER TABLE testcase_executions ADD COLUMN tce_test_key TEXT")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    return Project(
        id=cur.lastrowid,
        project_key=project_key,
        project_id=project_id,
        name=name,
        base_url=base_url,
        rtm_version=None,
    )


def upsert_folder(
    conn: sqlite3.Connection,
    project_id: int,
    folder_id: str,
    name: str,
    node_type: str,
    parent_id: Optional[str],
    sort_order: int = 0,
) -> None:
    cur = conn.cursor()
    cur.execute("SELECT id FROM folders WHERE id = ?", (folder_id,))
    if cur.fetchone():
        cur.execute(
            """
            UPDATE folders
               SET project_id = ?, parent_id = ?, name = ?, node_type = ?, sort_order = ?
             WHERE id = ?
            """,
            (project_id, parent_id, name, node_type, sort_order, folder_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO folders (id, project_id, parent_id, name, node_type, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (folder_id, project_id, parent_id, name, node_type, sort_order),
        )
    conn.commit()


def upsert_issue_from_tree(
    conn: sqlite3.Connection,
    project_id: int,
    jira_key: Optional[str],
    jira_id: Optional[int],
    issue_type: str,
    summary: str,
    folder_id: Optional[str],
) -> int:
    """
    Minimal upsert used during tree sync.
    Full issue fields will be filled later by type-specific REST calls.
    """
    cur = conn.cursor()
    if jira_key:
        cur.execute(
            "SELECT id FROM issues WHERE project_id = ? AND jira_key = ?",
            (project_id, jira_key),
        )
        row = cur.fetchone()
    else:
        row = None

    if row:
        issue_id = row["id"]
        cur.execute(
            """
            UPDATE issues
               SET jira_id = ?, issue_type = ?, summary = ?, folder_id = ?
             WHERE id = ?
            """,
            (jira_id, issue_type, summary, folder_id, issue_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO issues (project_id, jira_key, jira_id, issue_type, summary, folder_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, jira_key, jira_id, issue_type, summary, folder_id),
        )
        issue_id = cur.lastrowid

    conn.commit()
    return issue_id


def fetch_folder_tree(conn: sqlite3.Connection, project_id: int) -> Dict[str, Any]:
    """
    Fetch folders and issues for a project and build a simple in-memory tree
    structure suitable for binding to a QTreeView (via QStandardItemModel).
    This is intentionally generic: caller will convert to Qt items.
    """
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM folders WHERE project_id = ? ORDER BY sort_order, name",
        (project_id,),
    )
    folders = [dict(row) for row in cur.fetchall()]

    cur.execute(
        "SELECT * FROM issues WHERE project_id = ? AND is_deleted = 0 ORDER BY summary",
        (project_id,),
    )
    issues = [dict(row) for row in cur.fetchall()]

    folder_map: Dict[str, Dict[str, Any]] = {}
    for f in folders:
        folder_map[f["id"]] = {**f, "children": []}

    # attach issues as children of folders
    roots = []

    for issue in issues:
        folder_id = issue.get("folder_id")
        node = {**issue, "node_type": "ISSUE", "children": []}
        if folder_id and folder_id in folder_map:
            folder_map[folder_id]["children"].append(node)
        else:
            # 폴더에 속하지 않은 이슈는 트리의 루트 수준에 직접 표시한다.
            # (엑셀에서 새로 생성한 로컬 이슈 등 folder_id 가 없는 경우 보이도록 하기 위함)
            roots.append(node)

    # build tree roots (folders with no parent)
    for folder_id, folder in folder_map.items():
        parent_id = folder.get("parent_id")
        if parent_id and parent_id in folder_map:
            folder_map[parent_id]["children"].append(folder)
        else:
            roots.append(folder)

    return {"roots": roots}


def move_issue_to_folder(
    conn: sqlite3.Connection, issue_id: int, new_folder_id: Optional[int]
) -> None:
    """
    이슈를 다른 폴더(또는 루트)로 이동한다.

    - new_folder_id 가 None 이면 folder_id 를 NULL 로 설정하여 루트에 위치시킨다.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE issues SET folder_id = ? WHERE id = ?",
        (new_folder_id, issue_id),
    )
    conn.commit()


def move_folder(
    conn: sqlite3.Connection, folder_id: int, new_parent_id: Optional[int]
) -> None:
    """
    폴더를 다른 부모 폴더(또는 루트)로 이동한다.

    - new_parent_id 가 None 이면 parent_id 를 NULL 로 설정하여 루트에 위치시킨다.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE folders SET parent_id = ? WHERE id = ?",
        (new_parent_id, folder_id),
    )
    conn.commit()


def get_issue_by_id(conn: sqlite3.Connection, issue_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a single issue row as a dict.
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
    row = cur.fetchone()
    return dict(row) if row else None

def get_issue_by_jira_key(conn: sqlite3.Connection, project_id: int, jira_key: str) -> Optional[Dict[str, Any]]:
    """
    Given a project_id and JIRA issue key, return the corresponding local issues row as dict, or None.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM issues WHERE project_id = ? AND jira_key = ? AND is_deleted = 0",
        (project_id, jira_key),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_local_issues_without_jira_key(
    conn: sqlite3.Connection,
    project_id: int,
    issue_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    jira_key가 NULL이거나 빈 문자열인 로컬 이슈들을 조회합니다.
    
    Args:
        conn: SQLite 연결
        project_id: 프로젝트 ID
        issue_type: 이슈 타입 필터 (선택적, None이면 모든 타입)
    
    Returns:
        jira_key가 없는 이슈 목록 (dict 리스트)
    """
    cur = conn.cursor()
    
    if issue_type:
        cur.execute(
            """
            SELECT * FROM issues 
            WHERE project_id = ? 
              AND (jira_key IS NULL OR jira_key = '')
              AND is_deleted = 0
              AND issue_type = ?
            ORDER BY id
            """,
            (project_id, issue_type.upper()),
        )
    else:
        cur.execute(
            """
            SELECT * FROM issues 
            WHERE project_id = ? 
              AND (jira_key IS NULL OR jira_key = '')
              AND is_deleted = 0
            ORDER BY issue_type, id
            """,
            (project_id,),
        )
    
    rows = cur.fetchall()
    return [dict(row) for row in rows]



def update_issue_fields(conn: sqlite3.Connection, issue_id: int, fields: Dict[str, Any]) -> None:
    """
    Update given columns of an issue identified by id.
    Only keys present in `fields` will be updated.
    """
    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values())
    values.append(issue_id)
    sql = f"UPDATE issues SET {columns}, dirty = 1 WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, values)
    conn.commit()


def create_local_issue(
    conn: sqlite3.Connection,
    project_id: int,
    issue_type: str,
    folder_id: Optional[str] = None,
    summary: str = "",
) -> int:
    """
    Create a new local-only issue row and return its id.

    - Used by GUI when user clicks 'New Issue' on the local panel.
    - Minimal fields are populated; user will fill Details/Steps/etc. afterwards.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO issues (
            project_id,
            jira_key,
            jira_id,
            issue_type,
            summary,
            description,
            status,
            priority,
            assignee,
            reporter,
            labels,
            components,
            security_level,
            fix_versions,
            affects_versions,
            rtm_environment,
            due_date,
            created,
            updated,
            attachments,
            folder_id,
            parent_issue_id,
            is_deleted,
            local_only,
            last_sync_at,
            dirty
        )
        VALUES (?, NULL, NULL, ?, ?, '', '', '', '', '', '', '', '', '', '', '', '', datetime('now'), datetime('now'),
                '', ?, NULL, 0, 1, NULL, 1)
        """,
        (project_id, issue_type, summary, folder_id),
    )
    conn.commit()
    return int(cur.lastrowid)


def soft_delete_issue(conn: sqlite3.Connection, issue_id: int) -> None:
    """
    Soft delete an issue by setting is_deleted = 1.
    The row remains in DB but is hidden from trees and lists.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE issues SET is_deleted = 1, dirty = 1 WHERE id = ?",
        (issue_id,),
    )
    conn.commit()


def create_folder_node(
    conn: sqlite3.Connection,
    project_id: int,
    name: str,
    parent_id: Optional[str] = None,
    sort_order: int = 0,
    issue_type: Optional[str] = None,
) -> str:
    """
    Create a new folder row under the given parent (or as root if parent_id is None).
    Returns the generated folder id.

    issue_type 가 주어지면, 폴더 id 에 타입 정보를 포함시켜
    탭(이슈 타입)별로 자신이 생성한 폴더만 보이도록 사용할 수 있다.
    예: LOCAL-TEST_CASE-<uuid>
    """
    prefix = "LOCAL-"
    if issue_type:
        prefix = f"LOCAL-{issue_type.upper()}-"
    folder_id = f"{prefix}{uuid.uuid4().hex}"
    upsert_folder(
        conn,
        project_id=project_id,
        folder_id=folder_id,
        name=name,
        node_type="FOLDER",
        parent_id=parent_id,
        sort_order=sort_order,
    )
    return folder_id


def delete_folder_if_empty(conn: sqlite3.Connection, folder_id: str) -> bool:
    """
    Delete a folder only if it has no child folders and no non-deleted issues.
    Returns True if deleted, False if not empty.
    """
    cur = conn.cursor()

    # Check child folders
    cur.execute("SELECT COUNT(*) FROM folders WHERE parent_id = ?", (folder_id,))
    child_folders = cur.fetchone()[0]

    # Check issues attached to this folder
    cur.execute(
        "SELECT COUNT(*) FROM issues WHERE folder_id = ? AND is_deleted = 0",
        (folder_id,),
    )
    child_issues = cur.fetchone()[0]

    if child_folders or child_issues:
        return False

    cur.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
    conn.commit()
    return True


# --- Test case steps helpers ----------------------------------------------------


def get_steps_for_issue(conn: sqlite3.Connection, issue_id: int) -> List[Dict[str, Any]]:
    """
    Return all testcase_steps rows for given issue_id, ordered by group_no, order_no.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM testcase_steps WHERE issue_id = ? ORDER BY group_no ASC, order_no ASC, id ASC",
        (issue_id,),
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def replace_steps_for_issue(conn: sqlite3.Connection, issue_id: int, steps: List[Dict[str, Any]]) -> None:
    """
    Replace all steps for given issue_id with provided list.

    Each item in `steps` is expected to have keys:
      - group_no (int, optional; default = 1)
      - order_no (int)
      - action (str)
      - input (str)
      - expected (str)
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM testcase_steps WHERE issue_id = ?", (issue_id,))
    for step in steps:
        cur.execute(
            """
            INSERT INTO testcase_steps (issue_id, group_no, order_no, action, input, expected)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                issue_id,
                int(step.get("group_no", 1) or 1),
                int(step.get("order_no", 0) or 0),
                step.get("action") or "",
                step.get("input") or "",
                step.get("expected") or "",
            ),
        )
    conn.commit()


def get_folder_path(conn: sqlite3.Connection, folder_id: Optional[str]) -> str:
    """
    주어진 folder_id 에 대한 전체 경로를 "Root/Sub/Child" 형태의 문자열로 반환.
    루트 폴더가 없거나 id 가 None 이면 빈 문자열을 반환한다.
    """
    if not folder_id:
        return ""
    cur = conn.cursor()
    parts: List[str] = []
    current = folder_id
    while current:
        cur.execute("SELECT id, name, parent_id FROM folders WHERE id = ?", (current,))
        row = cur.fetchone()
        if not row:
            break
        parts.append(row["name"] or "")
        current = row["parent_id"]
    parts = [p for p in reversed(parts) if p]
    return "/".join(parts)


def ensure_folder_path(
    conn: sqlite3.Connection,
    project_id: int,
    path: str,
    issue_type: Optional[str] = None,
) -> Optional[str]:
    """
    "Root/Sub/Child" 또는 "Root\\Sub\\Child" 형태의 경로 문자열을 받아,
    해당 경로의 폴더 트리를 projects/folders 테이블에 보장하고 마지막 폴더 id 를 반환한다.

    - 경로가 비어있으면 None 반환.
    - 이미 존재하는 폴더는 재사용하고, 없으면 create_folder_node() 로 생성한다.
    """
    if not path:
        return None
    cleaned = path.strip().strip("/\\")
    if not cleaned:
        return None

    parts = [p.strip() for p in re.split(r"[\\/]", cleaned) if p.strip()]
    if not parts:
        return None

    cur = conn.cursor()
    parent_id: Optional[str] = None

    for name in parts:
        if parent_id is None:
            cur.execute(
                "SELECT id FROM folders WHERE project_id = ? AND parent_id IS NULL AND name = ?",
                (project_id, name),
            )
        else:
            cur.execute(
                "SELECT id FROM folders WHERE project_id = ? AND parent_id = ? AND name = ?",
                (project_id, parent_id, name),
            )
        row = cur.fetchone()
        if row:
            folder_id = row["id"]
        else:
            folder_id = create_folder_node(
                conn,
                project_id=project_id,
                name=name,
                parent_id=parent_id,
                issue_type=issue_type,
            )
        parent_id = folder_id

    return parent_id


# --- Relations helpers ----------------------------------------------------------


def get_relations_for_issue(conn: sqlite3.Connection, src_issue_id: int) -> List[Dict[str, Any]]:
    """
    Return all relations where the given issue is the source (src_issue_id),
    joined with destination issue basic info.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id as relation_id,
               r.src_issue_id,
               r.dst_issue_id,
               r.relation_type,
               r.created_at,
               i.issue_type as dst_issue_type,
               i.jira_key as dst_jira_key,
               i.summary as dst_summary
          FROM relations r
          JOIN issues i ON r.dst_issue_id = i.id
         WHERE r.src_issue_id = ?
         ORDER BY r.id ASC
        """,
        (src_issue_id,),
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def replace_relations_for_issue(conn: sqlite3.Connection, src_issue_id: int, relations: List[Dict[str, Any]]) -> None:
    """
    Replace all relations for a given src_issue_id with the provided list.

    Each item in `relations` is expected to have keys:
      - dst_issue_id (int)
      - relation_type (str)
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM relations WHERE src_issue_id = ?", (src_issue_id,))
    for rel in relations:
        dst_id = rel.get("dst_issue_id")
        rel_type = rel.get("relation_type") or ""
        if not dst_id:
            continue
        cur.execute(
            """
            INSERT INTO relations (src_issue_id, dst_issue_id, relation_type, created_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (src_issue_id, int(dst_id), rel_type),
        )
    conn.commit()


# --- Test plan / test execution helpers ----------------------------------------


def get_testplan_testcases(conn: sqlite3.Connection, testplan_id: int) -> List[Dict[str, Any]]:
    """
    Return all test cases linked to a given Test Plan (issues.id) using testplan_testcases.
    Joined with issues to get jira_key and summary.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id              AS link_id,
               t.testcase_id     AS testcase_id,
               t.order_no        AS order_no,
               i.jira_key        AS jira_key,
               i.summary         AS summary
          FROM testplan_testcases t
          JOIN issues i ON t.testcase_id = i.id
         WHERE t.testplan_id = ?
         ORDER BY t.order_no ASC, t.id ASC
        """,
        (testplan_id,),
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def replace_testplan_testcases(conn: sqlite3.Connection, testplan_id: int, records: List[Dict[str, Any]]) -> None:
    """
    Replace all Test Plan - Test Case links for the given testplan_id.

    Each record is expected to have:
      - testcase_id (int)
      - order_no (int)
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM testplan_testcases WHERE testplan_id = ?", (testplan_id,))
    for rec in records:
        tc_id = rec.get("testcase_id")
        if not tc_id:
            continue
        order_no = int(rec.get("order_no", 0) or 0)
        cur.execute(
            """
            INSERT INTO testplan_testcases (testplan_id, testcase_id, order_no)
            VALUES (?, ?, ?)
            """,
            (testplan_id, int(tc_id), order_no),
        )
    conn.commit()


def get_or_create_testexecution_for_issue(conn: sqlite3.Connection, issue_id: int) -> Dict[str, Any]:
    """
    Ensure there is a testexecutions row for a given TEST_EXECUTION issue (issues.id).
    Returns the row as a dict.
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM testexecutions WHERE issue_id = ?", (issue_id,))
    row = cur.fetchone()
    if row:
        return dict(row)

    cur.execute(
        """
        INSERT INTO testexecutions (issue_id, environment, start_date, end_date, result, executed_by)
        VALUES (?, '', '', '', '', '')
        """,
        (issue_id,),
    )
    conn.commit()
    cur.execute("SELECT * FROM testexecutions WHERE id = ?", (cur.lastrowid,))
    return dict(cur.fetchone())


def update_testexecution_for_issue(conn: sqlite3.Connection, issue_id: int, fields: Dict[str, Any]) -> None:
    """
    Update the testexecutions row for a given issue_id with provided fields.
    Creates the row if needed.
    """
    te_row = get_or_create_testexecution_for_issue(conn, issue_id)
    te_id = te_row["id"]
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields.keys())
    values = list(fields.values())
    values.append(te_id)
    sql = f"UPDATE testexecutions SET {cols} WHERE id = ?"
    cur = conn.cursor()
    cur.execute(sql, values)
    conn.commit()


def get_testcase_executions(conn: sqlite3.Connection, testexecution_id: int) -> List[Dict[str, Any]]:
    """
    Return all Test Case Executions for a given testexecution_id, joined with testcase issues.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id                 AS id,
               t.testcase_id        AS testcase_id,
               t.order_no           AS order_no,
               t.assignee           AS assignee,
               t.result             AS result,
               t.actual_time        AS actual_time,
               t.rtm_environment    AS rtm_environment,
               t.defects            AS defects,
               t.tce_test_key       AS tce_test_key,
               i.jira_key           AS jira_key,
               i.summary            AS summary
          FROM testcase_executions t
          JOIN issues i ON t.testcase_id = i.id
         WHERE t.testexecution_id = ?
         ORDER BY t.order_no ASC, t.id ASC
        """,
        (testexecution_id,),
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def replace_testcase_executions(conn: sqlite3.Connection, testexecution_id: int, records: List[Dict[str, Any]]) -> None:
    """
    Replace all Test Case Execution rows for the given testexecution_id.

    Each record is expected to have:
      - testcase_id (int)
      - order_no (int)
      - assignee (str)
      - result (str)
      - actual_time (int, optional)
      - rtm_environment (str)
      - defects (str)
      - tce_test_key (str, optional; RTM Test Case Execution key)
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM testcase_executions WHERE testexecution_id = ?", (testexecution_id,))
    for rec in records:
        tc_id = rec.get("testcase_id")
        if not tc_id:
            continue
        order_no = int(rec.get("order_no", 0) or 0)
        actual_time = rec.get("actual_time")
        try:
            actual_time_int = int(actual_time) if actual_time not in (None, "") else 0
        except (TypeError, ValueError):
            actual_time_int = 0
        tce_test_key = rec.get("tce_test_key") or ""
        cur.execute(
            """
            INSERT INTO testcase_executions
                (testexecution_id, testcase_id, order_no, assignee, result, actual_time, rtm_environment, defects, tce_test_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                testexecution_id,
                int(tc_id),
                order_no,
                rec.get("assignee") or "",
                rec.get("result") or "",
                actual_time_int,
                rec.get("rtm_environment") or "",
                rec.get("defects") or "",
                tce_test_key,
            ),
        )
    conn.commit()


# --- Single Test Case Execution helper -----------------------------------------


def get_testcase_execution_by_id(conn: sqlite3.Connection, tce_id: int) -> Dict[str, Any] | None:
    """
    단일 Test Case Execution 레코드를 id 기준으로 조회한다.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id,
               testexecution_id,
               testcase_id,
               order_no,
               assignee,
               result,
               actual_time,
               rtm_environment,
               defects,
               tce_test_key
          FROM testcase_executions
         WHERE id = ?
        """,
        (tce_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None

# --- Test Case Step Execution helpers -------------------------------------------


def get_step_executions_for_tce(conn: sqlite3.Connection, testcase_execution_id: int) -> List[Dict[str, Any]]:
    """
    주어진 testcase_execution_id 에 대한 Step 실행 상태 목록을 반환한다.

    반환되는 각 dict 필드:
      - testcase_step_id
      - status
      - actual_result
      - evidence
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT testcase_step_id, status, actual_result, evidence
          FROM testcase_step_executions
         WHERE testcase_execution_id = ?
         ORDER BY id ASC
        """,
        (testcase_execution_id,),
    )
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def replace_step_executions_for_tce(
    conn: sqlite3.Connection,
    testcase_execution_id: int,
    records: List[Dict[str, Any]],
) -> None:
    """
    주어진 testcase_execution_id 에 대한 Step 실행 상태를 records 로 완전히 교체한다.

    각 record 는 다음 키를 포함해야 한다:
      - testcase_step_id (int)
      - status (str)
      - actual_result (str)
      - evidence (str)
    """
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM testcase_step_executions WHERE testcase_execution_id = ?",
        (testcase_execution_id,),
    )
    for rec in records:
        step_id = rec.get("testcase_step_id")
        if not step_id:
            continue
        cur.execute(
            """
            INSERT INTO testcase_step_executions
                (testcase_execution_id, testcase_step_id, status, actual_result, evidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                testcase_execution_id,
                int(step_id),
                rec.get("status") or "",
                rec.get("actual_result") or "",
                rec.get("evidence") or "",
            ),
        )
    conn.commit()
