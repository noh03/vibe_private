## 1. 개요

이 문서는 `rtm_local_manager` 현재 구현 상태를 기준으로 한 **SW 구현 사양서**이다.  
JIRA + Deviniti RTM for Jira(Data Center) 환경에서, 요구사항/테스트/결함 이슈를 **로컬 SQLite DB + Excel + REST API**로 연동·관리하는 데스크톱 툴의 동작을 상세히 정의한다.

- 개발 언어 / 런타임: **Python 3.12 + PySide6(Qt6)**
- 실행 엔트리 포인트: `rtm_local_manager/main.py`
- 주요 모듈
  - GUI: `gui/main_window.py`
  - DB 스키마 및 DAO: `backend/db.py`
  - Excel Import/Export: `backend/excel_io.py`
  - JIRA / RTM REST 래퍼: `backend/jira_api.py`
  - JIRA JSON ↔ 로컬 매핑: `backend/jira_mapping.py`
  - 동기화 유틸: `backend/sync.py`

---

## 2. 실행 구조

### 2.1. 실행 플로우

1. `main.py` 실행 시:
   - `base_dir` 를 `main.py` 와 동일 디렉터리로 계산.
   - `jira_config.json`, `rtm_local.db` 파일 경로를 `base_dir` 기준으로 설정.
   - `gui.main_window.run(db_path, config_path)` 호출.
2. `run()`:
   - `QApplication` 인스턴스 생성.
   - `MainWindow(db_path, config_path, mode="both")` 생성 후 `show()`.
   - `app.exec()` 로 Qt 이벤트 루프 진입.

### 2.2. Jira 설정(`jira_config.json`)

`backend/jira_api.load_config_from_file()` 형식:

```json
{
  "base_url": "https://jira.example.com",
  "username": "jira.user",
  "api_token": "PASSWORD_OR_PAT",
  "project_key": "KVHSICCU",
  "project_id": 41500,
  "endpoints": {
    "jira_issue_get": "/rest/api/2/issue/{key}",
    "jira_issue_comments": "/rest/api/2/issue/{key}/comment",
    "...": "..."
  }
}
```

- `endpoints` 키는 JIRA REST / RTM REST 의 **논리 키별 엔드포인트 템플릿**을 담는 맵이다.
- 값이 없으면(`endpoints` 누락) 코드 내부의 `DEFAULT_ENDPOINTS` 를 사용하고,  
  값이 있으면 기본값과 병합하여(`DEFAULT_ENDPOINTS` + `endpoints`) 우선 적용한다.

로드 성공 시:
- `MainWindow.jira_config(JiraConfig)`, `MainWindow.jira_client(JiraRTMClient)` 초기화.
- `projects` 테이블에 `project_key`, `project_id` 에 해당하는 프로젝트가 없으면 생성.

로드 실패 시:
- `project_key="LOCAL", project_id=0` 인 로컬 전용 프로젝트 생성.
- `jira_client=None`, `jira_available=False` 로 설정.

---

## 3. 데이터 모델 (SQLite)

### 3.1. 주요 테이블

1. `projects`
   - `id` (PK, AUTOINCREMENT)
   - `project_key` (JIRA 프로젝트 키 또는 "LOCAL")
   - `project_id` (JIRA 프로젝트 ID, 로컬 전용일 경우 0)
   - `name`, `base_url`, `rtm_version`

2. `folders`
   - RTM 트리 구조(요구사항/TC/TP/TE/Defect 폴더)를 로컬에서 표현.
   - 컬럼: `id(TEXT, PK)`, `project_id`, `parent_id`, `name`, `node_type`, `sort_order`.
   - `id` 는 JIRA RTM 트리의 testKey 혹은 `LOCAL-<TYPE>-<uuid>` 형태.

3. `issues`
   - RTM 이슈 5종(Requirement, Test Case, Test Plan, Test Execution, Defect)을 통합 저장.
   - 핵심 컬럼:
     - 식별자: `id(PK)`, `project_id`, `jira_key`, `jira_id`, `issue_type`
     - 메타: `summary`, `description`, `status`, `priority`, `assignee`, `reporter`
     - 분류: `labels`, `components`, `security_level`
     - 버전: `fix_versions`, `affects_versions`
     - RTM: `rtm_environment`
     - 일정: `due_date`, `created`, `updated`
     - Agile: `epic_link`, `sprint`
     - 기타: `attachments(JSON 문자열)`, `folder_id`, `parent_issue_id`, `is_deleted`, `local_only`, `last_sync_at`, `dirty`, `preconditions`

4. `testcase_steps`
   - Test Case 의 Step 정보를 그룹/순서 기반으로 저장.
   - 컬럼: `id`, `issue_id(issues.id)`, `group_no`, `order_no`, `action`, `input`, `expected`

5. `testplan_testcases`
   - Test Plan ↔ Test Case 매핑 및 순서를 유지.
   - 컬럼: `id`, `testplan_id`, `testcase_id`, `order_no`

6. `testexecutions`, `testcase_executions`, `testcase_step_executions`
   - Test Execution, Test Case Execution(TCE), Step Execution 실행 결과 저장.
   - `testexecutions`: `issue_id`, `environment`, `start_date`, `end_date`, `result`, `executed_by`
   - `testcase_executions`:
     - `testexecution_id`, `testcase_id`, `order_no`
     - `assignee`, `result`, `actual_time(분)`, `rtm_environment`, `defects(JSON 문자열)`
   - `testcase_step_executions`:
     - `testcase_execution_id`, `testcase_step_id`
     - `status`, `actual_result`, `evidence(문자열 또는 파일 경로 리스트 직렬화)`

7. `relations`
   - Requirement ↔ Test Case, Test Case ↔ Test Plan 등 이슈 간 관계.
   - 컬럼: `src_issue_id`, `dst_issue_id`, `relation_type`, `created_at`

8. `sync_state`
   - 프로젝트별 동기화 시각 기록: `last_full_sync_at`, `last_tree_sync_at`, `last_issue_sync_at`.

### 3.2. 마이그레이션

`init_db()` 에서 PRAGMA `table_info` 를 활용하여 다음 컬럼들을 **존재하지 않을 경우에만** 추가:

- `issues.preconditions`, `issues.epic_link`, `issues.sprint`
- `testcase_steps.group_no`
- `testcase_executions.actual_time`

이는 기존 DB 파일을 유지하면서 기능을 확장하기 위한 경량 마이그레이션이다.

---

## 4. Excel Import / Export

### 4.1. Export (`export_project_to_excel`)

`backend/excel_io.py` 의 `export_project_to_excel(conn, project_id, file_path)`:

1. 워크북 생성 및 기본 시트 삭제.
2. 아래 시트들을 생성하고 로컬 DB 내용을 덤프.

- **Issues**
  - 컬럼:  
    `id, jira_key, issue_type, folder_path, summary, description, status, priority, assignee, reporter, labels, components, security_level, fix_versions, affects_versions, rtm_environment, due_date, created, updated, attachments, epic_link, sprint`
  - `folder_path` 는 `folders` 트리를 문자열 경로로 변환하여 저장 (`get_folder_path()` 사용).

- **TestcaseSteps**
  - 컬럼:  
    `issue_id, issue_jira_key, preconditions, group_no, order_no, action, input, expected`
  - `issues.preconditions` 를 함께 출력하여, Excel 단에서 TC 단위 Precondition 관리 가능.

- **Relations**
  - 컬럼: `src_jira_key, dst_jira_key, relation_type`

- **TestPlanTestcases**
  - 컬럼: `testplan_jira_key, testcase_jira_key, order_no`

- **TestExecutions**
  - 컬럼: `testexecution_jira_key, environment, start_date, end_date, result, executed_by`

- **TestcaseExecutions**
  - 컬럼:  
    `testexecution_jira_key, testcase_jira_key, order_no, assignee, result, actual_time, rtm_environment, defects, tce_test_key`
  - `tce_test_key` 는 RTM 의 Test Case Execution 식별자(testKey)로,
    Step Execution API / TCE Defect 링크 API 에서 사용된다.

- **TestcaseStepExecutions**
  - 컬럼:  
    `testexecution_jira_key, testcase_jira_key, group_no, order_no, status, actual_result, evidence`
  - 설계된 Step(`TestcaseSteps`) 기준으로, 실행 시점의 상태/실제결과/증거를 저장한다.

### 4.2. Import (`import_project_from_excel`)

현재 구현은 Issues/Steps/Relations/TestPlanTestcases/TestExecutions/TestcaseExecutions 시트에서 데이터를 읽어 **로컬 DB에 반영**하도록 설계되어 있다.  
구체적인 매핑 규칙:

- `jira_key` 가 있는 이슈는 기존 `issues` 레코드와 매칭 후 업데이트.
- `jira_key` 가 없는 이슈는 `local_only=1` 인 신규 이슈로 생성.
- `TestcaseSteps.issue_id` 또는 `issue_jira_key` 로 해당 TC 를 찾아 Steps 를 재구성.
- Relations, TestPlanTestcases, TestcaseExecutions, TestExecutions 역시 동일 기준으로 매핑.

Excel 을 **싱글 소스 오브 트루스**로 활용하고, 필요에 따라 JIRA/RTM 으로 업로드/동기화하는 것이 목표이다.

---

## 5. JIRA / RTM REST 연동 및 설정

### 5.1. REST 설정/편집 기능 개요

- 설정 파일: `rtm_local_manager/jira_config.json`
- 코드 상 설정 구조: `backend/jira_api.JiraConfig`
  - 필드:
    - `base_url`: JIRA 서버 베이스 URL
    - `username`, `api_token`: Basic Auth 용 계정/토큰
    - `project_key`, `project_id`
    - `endpoints: Dict[str, str]`: 엔드포인트 템플릿(키별 path)
- 기본 엔드포인트 집합: `backend/jira_api.DEFAULT_ENDPOINTS`
- 엔드포인트별 허용 플레이스홀더 정의: `backend/jira_api.DEFAULT_ENDPOINT_PARAMS`

GUI 상에서의 설정 편집:

- **Settings > REST API & Auth Settings...**
  - `base_url`, `username`, `api_token`, `project_key`, `project_id` 를 폼으로 편집.
  - `Test Connection` 버튼으로 `get_priorities()` 호출을 수행하여 REST 연결 시험.
  - OK 시 `jira_config.json` 저장 후 내부 `jira_config`/`jira_client` 재생성.

- **Settings > REST API Endpoint Settings...**
  - `DEFAULT_ENDPOINTS` + 현재 `jira_config.endpoints` 를 병합한 목록을 테이블로 표시:
    - `Key`: 논리 이름 (읽기 전용)
    - `Path Template`: 실제 REST path 템플릿(편집 가능)
    - `Allowed Placeholders`: 해당 key 에서 사용할 수 있는 플레이스홀더 목록(읽기 전용)
  - OK 시:
    - `Path Template` 에 포함된 `{name}` 패턴들을 정규식으로 추출.
    - `DEFAULT_ENDPOINT_PARAMS[key]` 에 정의된 이름 목록과 비교하여,
      **허용되지 않은 플레이스홀더가 있으면 저장을 막고 경고 메시지 표시.**
    - 유효한 경우에만 `jira_config.endpoints` 에 반영하고 `jira_config.json` 저장.

- **Settings > REST API Tester...**
  - `base_url`, HTTP Method, Path, Request Body 를 직접 입력하여 REST 호출을 시험하는 도구.
  - 필드:
    - `Base URL`: `jira_config.base_url` 로 초기화되며, **테스터 내에서만 임시 변경 가능**.
    - `Method`: GET / POST / PUT / DELETE
    - `Path`: `/rest/api/2/...` 또는 `/rest/rtm/1.0/api/...` 등 상대 경로
    - `Request Body`: JSON 또는 일반 텍스트(선택 사항)
  - 동작:
    - `Base URL` + `Path` 를 합쳐 최종 URL 생성.
    - Body 가 JSON 형식이면 `json=...`, 아니면 `data=...` 로 전송.
    - 응답 Status 코드와 Body 를 하단에 표시하고, Body 가 JSON 이면 pretty-print 한다.

이로써, **코드 수정 없이도 GUI 상에서 REST 인증/엔드포인트를 모두 수정/시험할 수 있는 구조**를 갖춘다.

### 5.2. JIRA 표준 REST (`/rest/api/2/...`)

`backend/jira_api.py` 의 `JiraRTMClient` 는 다음 기능을 제공한다.

- 이슈 조회: `get_jira_issue(jira_key, expand=...)`
- JQL 검색: `search_issues(jql, max_results, start_at)`
- 이슈 링크 타입 조회: `get_issue_link_types()`
- 이슈 링크 생성: `create_issue_link(link_type, inward_key, outward_key)`
- 댓글/첨부, Transition 등은 필요 시 추가 확장 가능(현재 일부 기본 댓글/첨부 wrapper 가 구현됨).

### 5.3. RTM 전용 REST (`/rest/rtm/1.0/api/...`)

엔드포인트 패턴(실제 RTM REST API.md 기준):

- Requirement: `/rest/rtm/1.0/api/requirement/{testKey}`
- Test Case: `/rest/rtm/1.0/api/test-case/{testKey}`
- Test Plan: `/rest/rtm/1.0/api/test-plan/{testKey}`
- Test Execution: `/rest/rtm/1.0/api/test-execution/{testKey}`
- Defect: `/rest/rtm/1.0/api/defect/{testKey}`

`JiraRTMClient` 제공 메서드:

- 공통 CRUD:
  - `_entity_path(issue_type, key)` → 위 패턴에 따라 path 생성.
  - `get_entity(issue_type, jira_key)`
  - `update_entity(issue_type, jira_key, payload)`
  - `delete_entity(issue_type, jira_key)`
  - `create_entity(issue_type, payload)` (각 타입별 POST path 사용)

- Test Case Steps:
  - `get_testcase_steps(jira_key)` → `GET /test-case/{key}/steps` (예시)
  - `update_testcase_steps(jira_key, payload)` → `PUT /test-case/{key}/steps`

- Test Plan:
  - `get_testplan_testcases(jira_key)` → `GET /test-plan/{key}/testcases`
  - `update_testplan_testcases(jira_key, payload)` → `PUT /test-plan/{key}/testcases`

- Test Execution:
  - `get_testexecution_details(jira_key)` → `GET /test-execution/{key}`
  - `get_testexecution_testcases(jira_key)` → `GET /test-execution/{key}/testcases`
  - `update_testexecution(jira_key, payload)` → `PUT /test-execution/{key}`
  - `update_testexecution_testcases(jira_key, payload)` → `PUT /test-execution/{key}/testcases`

- Tree:
  - `get_tree(project_id)` → `GET /rest/rtm/1.0/api/tree/{projectId}`

HTTP 인증은 `HTTPBasicAuth(username, api_token)` 을 사용.

### 5.3. JIRA JSON ↔ 로컬 매핑

`backend/jira_mapping.py`:

- `map_jira_to_local(issue_type, jira_json) -> Dict[str, Any]`
  - Jira Issue JSON(`fields`)에서 로컬 `issues` 컬럼에 반영할 값 추출.
  - Summary, Description, Status, Priority, Assignee/Reporter, Labels, Components, Security Level, Fix/Affects Versions, Environment, DueDate, Created/Updated, Attachments, Epic/Sprint 등.
  - Epic/Sprint 는 인스턴스별 custom field ID 를 `EPIC_LINK_FIELD_KEY`, `SPRINT_FIELD_KEY` 상수로 지정.

- `map_local_to_jira_fields(issue_type, local_issue) -> Dict[str, Any]`
  - 로컬 `issues` 레코드를 Jira Issue `fields` payload 로 변환.
  - Summary, Description, Labels, Components, DueDate, Environment, Epic/Sprint 를 중심으로 보수적 업데이트.

이 모듈만 수정하면, GUI/DB 코드는 그대로 두고 Jira 필드 구성을 현장 환경에 맞게 조정할 수 있다.

---

## 6. GUI 구조

### 6.1. MainWindow

클래스: `gui/main_window.py::MainWindow(QMainWindow)`

- 상단 메뉴바
  - File: Excel Import/Export, Exit
  - Local: Save Current Issue, Refresh Local Tree
  - JIRA/RTM: Pull from JIRA, Push to JIRA, Create/Delete in JIRA
  - View:
    - Show Local Window (좌측 패널 표시/숨김)
    - Show Online Window (우측 패널 표시/숨김)
    - Layout:
      - Left/Right (Local | Online)  … 기본 값
      - Top/Bottom (Online / Local)
  - Help: About

- 상단 리본(툴바)
  - Local 그룹: `Import Excel`, `Export Excel`
  - Sync 그룹: `Full Sync (Tree)` – JIRA RTM Tree → Local 동기화
  - JQL 입력창: `QLineEdit` (`returnPressed` 시 `on_jira_filter_search` 호출)

- 중앙 영역
  - `self.main_splitter: QSplitter` – 초기에는 `Qt.Horizontal` (좌/우),  
    레이아웃 변경 시 `Qt.Vertical` (상/하) 로 전환.
  - 내부 구성:
    - `self.left_panel: PanelWidget("Local (SQLite)", is_online=False)`
    - `self.mid_panel: QWidget` – 중앙 세로 버튼 영역 (`Pull from JIRA`, `Push to JIRA`)
    - `self.right_panel: PanelWidget("JIRA RTM (Online)", is_online=True)`

- 상태바
  - `JIRA: Online/Offline` 인디케이터 라벨.
  - 메시지 출력용 `status_bar.showMessage(...)`.

### 6.2. 레이아웃 전환 (View > Layout)

- `MainWindow.layout_mode: str` – `"horizontal"` 또는 `"vertical"`.
- `View > Layout > Left / Right`:
  - `layout_mode="horizontal"`
  - `main_splitter.setOrientation(Qt.Horizontal)`
  - 위젯 순서: `Left(Local) | Mid(Pull/Push) | Right(Online)`
- `View > Layout > Top / Bottom`:
  - `layout_mode="vertical"`
  - `main_splitter.setOrientation(Qt.Vertical)`
  - 위젯 순서: `Top(Online) / Middle(Pull/Push) / Bottom(Local)`

사용자는 **보기 > Layout** 과 스플리터 드래그를 통해 좌/우 또는 상/하 배치 및 각 영역 크기를 자유롭게 조정할 수 있다.

### 6.3. PanelWidget (좌/우 내부 창)

클래스: `PanelWidget(QWidget)`

- 상단 헤더
  - Local 패널(`is_online=False`):
    - `Add Folder`, `Delete Folder`
    - `New Issue`, `Save Local Issue`, `Delete Issue`
    - Test Case 전용: `Execute`, `Add to Test Plan`, `Link to Requirement` (Test Cases 탭에서만 표시)
    - `Sync → JIRA`
  - Online 패널(`is_online=True`):
    - `Refresh`, `Sync → Local`, `Create in JIRA`, `Delete in JIRA`

- 모듈 탭바 (`module_tab_bar: QTabBar`)
  - 공통: `Dashboard`, `Requirements`, `Test Cases`, `Test Plans`, `Test Executions`, `Defects`
  - 좌/우 각각 독립적으로 동작하며, 탭 변경 시 해당 패널의 트리를 해당 이슈 타입으로 필터링.

- 하단 메인 영역 (`QSplitter(Qt.Horizontal)`)
  - 좌: `QTreeView` – 폴더/이슈 트리
  - 우: `IssueTabWidget` – 이슈 상세 탭 (Details / Steps / Requirements / Relations / Test Cases / Executions / Defects)

---

## 7. 이슈 트리 및 필터링

### 7.1. 로컬 트리 (`reload_local_tree`)

- `fetch_folder_tree(conn, project.id)` 로 전체 폴더+이슈 트리 구조(JSON 유사)를 로드.
- `local_issue_type_filter` 에 따라:
  - **이슈 노드**: `node.issue_type.upper() == local_issue_type_filter` 인 경우만 표시.
  - **폴더 노드**:
    - 하위에 표시 가능한 이슈/폴더가 하나도 없으면 트리에서 숨김.
    - `folder_id` 가 `LOCAL-<TYPE>-...` 인 경우, 현재 탭 타입과 다른 `<TYPE>` 폴더는 숨김.

### 7.2. 온라인 트리 (`on_refresh_online_tree`)

- RTM Tree REST (`get_tree(project_id)`) 호출 결과를 `JIRA RTM Tree` 라벨을 가진 `QStandardItemModel` 로 변환.
- `online_issue_type_filter` 에 따라:
  - 이슈 노드: `node.type.upper()` 가 필터와 불일치하면 숨김.
  - 폴더 노드: 하위에 표시 가능한 이슈/폴더가 없으면 숨김.

이로써, 상단 모듈 탭에서 **Requirements / Test Cases / Test Plans / Test Executions / Defects** 를 선택하면  
각 패널(로컬/온라인) 트리에 해당 타입의 이슈와 폴더만 표시되며, 다른 타입의 노드는 감춰진다.

### 7.3. 트리 선택 및 이슈 로드

- 좌측(Local) 트리에서 이슈 노드를 선택하면:
  - `MainWindow.on_local_tree_selection_changed()` 가 호출.
  - `current_issue_id`, `current_issue_type` 가 업데이트.
  - `backend.db.get_issue_by_id()` 로 해당 이슈 로드 후
    - `left_panel.issue_tabs.set_issue(issue_dict)` 호출.
    - Relations, Requirements, Linked Test Cases, Executions 탭 내용도 함께 로드.
- 우측(Online) 트리에서 이슈 노드를 선택하면:
  - `MainWindow.on_online_tree_selection_changed()` 가 호출.
  - 선택된 JIRA Key 를 기준으로 `jira_client.get_jira_issue()` / `get_entity()` 를 사용하여
    - 온라인 이슈 메타 정보를 조회하고,
    - `right_panel.issue_tabs.set_issue(issue_dict)` 형태로 표시.  
    (현재는 로컬 DB에 동기화된 이슈 기반 표시가 중심이며, 추후 순수 온라인 전용 표현으로 확장 가능)

---

## 8. 이슈 상세 탭 (`IssueTabWidget`)

### 8.1. 탭 구성

`IssueTabWidget(QTabWidget)` 은 다음 7개 탭으로 구성된다.

1. `Details`
2. `Steps`
3. `Requirements`
4. `Relations`
5. `Test Cases`
6. `Executions`
7. `Defects`

`update_tabs_for_issue_type(issue_type)` 에 따라 이슈 타입별로 필요한 탭만 보이도록 제어된다.

- REQUIREMENT : Details / Test Cases / Relations
- TEST_CASE   : Details / Steps / Requirements / Relations
- TEST_PLAN   : Details / Test Cases / Executions / Relations
- TEST_EXECUTION : Details / Executions / Relations
- DEFECT      : Details / Test Cases / Relations

### 8.2. Details 탭

#### 8.2.1. 상단 메타 필드

- 동적 그리드 레이아웃(`QGridLayout`)으로 구성되며, **내부 창 폭**에 따라 1~4단으로 자동 재배치된다.
  - 폭 \< 550px → 1단
  - 550 ~ 900px → 2단
  - 900 ~ 1300px → 3단
  - 1300px 이상 → 4단
- 필드 목록 (Description 제외):
  - Local ID (읽기 전용)
  - JIRA Key (읽기 전용)
  - Issue Type (읽기 전용)
  - Status
  - Summary
  - Priority
  - Assignee
  - Reporter
  - RTM Environment
  - Components
  - Labels
  - Fix Versions
  - Affects Versions
  - Epic Link
  - Sprint
  - Security Level
  - Due Date
  - Created (읽기 전용)
  - Updated (읽기 전용)
  - Attachments (JIRA 첨부 메타 요약)
- 단 수가 바뀔 때마다 `_rebuild_details_grid(columns)` 가 기존 레이블을 모두 삭제·재생성하여,
  중복 레이블이 남지 않도록 한다.

#### 8.2.2. Description / Activity

- `Description`: Details 하단에 **항상 1단 전체 폭**으로 배치된 `QTextEdit`.
  - 로컬 `issues.description` 과 Jira Issue `fields.description` 간 매핑.
- `Activity (Comments / History)` 그룹:
  - `Load Activity from JIRA` 버튼: `get_jira_issue(..., expand="comments,changelog")` 로
    JIRA 댓글/히스토리를 조회한 후 HTML/텍스트로 요약 표시.
  - 추후: 댓글 추가/수정/삭제를 위한 별도 UI 로 확장 가능.

### 8.3. Steps 탭

- Test Case 의 Preconditions + Step 그룹/순서를 편집하는 화면.
  - `Preconditions`: 상단 `QTextEdit` 로 TC 단위 전제조건 입력.
  - Steps 테이블(`QTableWidget`):
    - 컬럼: Group, Order, Action, Input, Expected
    - `Add Group`: 새로운 `group_no` 생성, 첫 스텝 추가 후 그룹 내 순서 재정렬.
    - `Add Step`: 현재 그룹에 스텝 추가, 그룹별 Order 자동 재배치.
    - `Delete Group`: 선택된 행의 `group_no` 전체 삭제.
    - `Delete Step`: 선택된 행만 삭제, 나머지 스텝의 Order 재배치.
- 저장 시 `backend.db.replace_steps_for_issue()` 를 사용하여 `testcase_steps` 테이블을 완전히 교체한다.

### 8.4. Requirements / Relations / Test Cases 탭

- `Requirements` 탭
  - 현재 이슈(대부분 Test Case)가 커버하는 Requirement 목록을 read-only 테이블로 표시.
  - 컬럼: Req ID (dst_issue_id), Jira Key, Summary.
  - 데이터 소스: `relations` 테이블에서 `relation_type` 이 Requirement 관련인 항목 필터.

- `Relations` 탭
  - 임의의 이슈 간 link를 관리하는 UI.
  - 테이블 컬럼: Relation Type, Dst Issue ID, Dst JIRA Key, Dst Summary.
  - `Add Relation...`:
    - 프로젝트 내 이슈 목록에서 대상 이슈를 선택하거나,
    - 단순 Web Link(Url + Text)를 Relations 행으로 추가.
    - JIRA Issue Link Type 목록(JIRA REST `/issueLinkType`)을 사용해 Link Type 콤보박스 채우기.
  - `Delete Selected Relation`:
    - 선택된 행 삭제. 저장 시 `replace_relations_for_issue()` 로 DB 갱신.

- `Test Cases` 탭
  - 이슈 타입에 따라 두 가지 모드로 동작:
    - REQUIREMENT / DEFECT: Linked Test Cases 뷰
      - 컬럼: Jira Key, Summary, Priority, Assignee, Components, RTM Env.
      - `Cover by TC...`, `Create New Test Case...` 버튼 제공
        (구체 동작은 Requirement/Test Case 관리 플로우와 연계).
    - TEST_PLAN: Test Plan – Test Case 매핑 뷰
      - 버튼: `Add Test Case`, `Delete Selected`, `Edit order`.
      - `Add Test Case`: 프로젝트 내 `TEST_CASE` 이슈 목록에서 선택 후 Test Plan 에 추가,
        `testplan_testcases` 재정렬·저장.
      - `Edit order`: Order 컬럼 직접 편집 후 `Accept order` 시 DB 반영.

### 8.5. Executions 탭

- TEST_PLAN:
  - 헤더: "Executions for this Test Plan".
  - `Execute Test Plan` 버튼만 활성화 (실제 실행 생성 로직은 RTM REST API와 연동 예정).
  - TCE 테이블은 숨겨진 상태.
- TEST_EXECUTION:
  - 헤더: "Test Case Executions".
  - 상단 필터: Assignee / Result / RTM Env 콤보박스.
  - TE 메타:
    - Environment, Start Date, End Date, Result, Executed By.
  - 버튼: `Add Test Case Execution`, `Delete Selected`, `Edit Selected...`.
  - 하단 TCE 테이블:
    - 컬럼: Order, Test Case ID, Jira Key, Summary, Assignee, Result, RTM Env, Actual Time(min), Defects.
  - `Edit Selected...`:
    - 선택된 행들에 대해 Assignee / Result / Env / Actual Time / Defects 값을 일괄 변경.
  - Step 실행 상세:
    - 더블클릭(`cellDoubleClicked`) 시 선택된 TCE 의 Step Execution 다이얼로그 호출
      (별도 UI 모듈로 구현 예정).

### 8.6. Defects 탭

- 현재 구현 상태:
  - `IssueTabWidget._init_defects_tab()` 에서 "Linked Defects table" 라벨만 배치되어 있으며,
    실제 Defect 목록 테이블 및 연동 로직은 추후 구현 예정 상태이다.
- 향후 확장 방향:
  - RTM Defect API (`/api/defect/...`) 와 `relations`, `testcase_executions.defects` 필드를 활용하여
    - 특정 이슈(특히 TCE, TC, TP, TE, Defect)에 연결된 모든 Defect 목록을 표시.
    - "Create Defect...", "Link Existing Defect...", "Unlink" 액션을 제공.
  - Defects 탭에서 선택한 Defect 를 더블클릭하면, 해당 Defect 이슈의 Details/Relations 를
    다른 패널(또는 새 창)에 표시.

---

## 9. 동기화 및 작업 플로우

### 9.1. Excel 기반 로컬 관리 플로우

1. 사용자는 Excel 에서 Requirements / Test Cases / Test Plans / Test Executions / Defects 및 Steps, Relations 등을 작성한다.
2. `Import Excel` 버튼 또는 File > Import from Excel... 메뉴로 `.xlsx` 파일을 선택한다.
3. `backend.excel_io.import_project_from_excel()` 이 각 시트를 읽어 로컬 DB 를 갱신한다.
4. 좌측(Local) 트리에서 해당 이슈들을 탐색·편집하고, 필요 시 세부 탭(Details, Steps, Relations 등)을 통해 수정한다.
5. 변경된 로컬 데이터를 `Export Excel` 버튼 또는 File > Export to Excel... 메뉴로 내보내어,
   백업/검토/공유 목적으로 활용한다.

### 9.2. JIRA RTM 동기화 플로우 (트리 기준)

1. `Full Sync (Tree)` 버튼:
   - `jira_client.get_tree(project_id)` 호출로 RTM 트리 구조를 로드한다.
   - `backend.sync.sync_tree()` 가 로컬 `folders`/`issues` 테이블과 비교·병합하여,
     누락된 노드는 추가하고, 삭제된 노드는 플래그 처리하는 등 트리를 동기화한다.
   - 좌측(Local) 트리와 우측(Online) 트리를 모두 재로드한다.
2. 개별 이슈 단위 동기화:
   - Pull from JIRA:
     - 선택된 로컬 이슈의 JIRA Key 기준으로 `get_jira_issue()` 및 필요 시 RTM `get_entity()` 를 호출.
     - `jira_mapping.map_jira_to_local()` 을 통해 로컬 `issues` 를 업데이트.
   - Push to JIRA:
     - 로컬 이슈를 `jira_mapping.map_local_to_jira_fields()` 및 RTM REST API payload 로 변환.
     - `create_entity()` 또는 `update_entity()` 를 통해 RTM/JIRA 에 반영.
   - Create/Delete in JIRA:
     - 로컬에서만 존재하는 이슈를 RTM/JIRA 이슈로 생성하거나,
     - JIRA 상의 이슈를 삭제 후, 로컬 상태(`is_deleted`, `local_only`) 및 트리를 갱신.

---

## 10. REST API 상세 사양 (현재 사용/계획 API 전부 + 매핑)

### 10.1. JIRA / RTM 엔드포인트 매핑 (DEFAULT_ENDPOINTS)

코드 내부에서 사용하는 엔드포인트 템플릿은 `backend/jira_api.DEFAULT_ENDPOINTS`/`DEFAULT_ENDPOINT_PARAMS` 로 정의되며,  
`jira_config.json` 의 `endpoints` 항목으로 오버라이드할 수 있다.

#### 10.1.1. JIRA REST (`/rest/api/2/...`) 매핑

| Key | 기본 메서드 | 기본 Path 템플릿 | 설명 |
| --- | --- | --- | --- |
| `jira_issue_get` | GET | `/rest/api/2/issue/{key}` | 특정 JIRA 이슈 상세 조회 (`get_jira_issue`) |
| `jira_issue_create` | POST | `/rest/api/2/issue` | JIRA 이슈 생성 (`create_entity` 의 fallback) |
| `jira_issue_comments` | GET/POST | `/rest/api/2/issue/{key}/comment` | 이슈 댓글 목록 조회/추가 |
| `jira_issue_comment` | PUT/DELETE | `/rest/api/2/issue/{key}/comment/{id}` | 특정 댓글 수정/삭제 |
| `jira_attachment_add` | POST | `/rest/api/2/issue/{key}/attachments` | 이슈 첨부파일 업로드 |
| `jira_attachment_delete` | DELETE | `/rest/api/2/attachment/{id}` | 첨부파일 삭제 |
| `jira_search` | GET | `/rest/api/2/search` | JQL 기반 이슈 검색 (`search_issues`) |
| `jira_issue_link_types` | GET | `/rest/api/2/issueLinkType` | 이슈 링크 타입 목록 조회 |
| `jira_issue_link` | POST | `/rest/api/2/issueLink` | 이슈 간 링크 생성 (`create_issue_link`) |
| `jira_priorities` | GET | `/rest/api/2/priority` | Priority 목록 조회 (`get_priorities`) |
| `jira_statuses` | GET | `/rest/api/2/status` | Workflow Status 목록 조회 (`get_statuses`) |
| `jira_project` | GET | `/rest/api/2/project/{projectKey}` | 프로젝트 메타데이터 조회 (`get_project_metadata`) |

#### 10.1.2. RTM REST (`/rest/rtm/1.0/api/...`) 매핑

| Key | 기본 메서드 | 기본 Path 템플릿 | 설명 |
| --- | --- | --- | --- |
| `tree_get` | GET | `/rest/rtm/1.0/api/tree/{projectId}/{treeType}` | RTM 트리 조회 (`get_tree`) |
| `tree_folder_create` | POST | `/rest/rtm/1.0/api/tree/{projectId}/folder` | 트리 폴더 생성 (`create_tree_folder`) |
| `tree_folder_update` | PUT | `/rest/rtm/1.0/api/tree/{testKey}/folder` | 폴더 이름/부모 변경 (`update_tree_folder`) |
| `tree_folder_delete` | DELETE | `/rest/rtm/1.0/api/tree/{testKey}/folder` | 폴더 삭제 (`delete_tree_folder`) |
| `rtm_requirement` | GET/PUT/DELETE | `/rest/rtm/1.0/api/requirement/{testKey}` | Requirement 조회/수정/삭제 (`get_entity` 등) |
| `rtm_test_case` | GET/PUT/DELETE | `/rest/rtm/1.0/api/test-case/{testKey}` | Test Case 조회/수정/삭제 |
| `rtm_test_plan` | GET/PUT/DELETE | `/rest/rtm/1.0/api/test-plan/{testKey}` | Test Plan 조회/수정/삭제 |
| `rtm_test_execution` | GET/PUT/DELETE | `/rest/rtm/1.0/api/test-execution/{testKey}` | Test Execution 조회/수정/삭제/상세 |
| `rtm_defect` | GET/PUT/DELETE | `/rest/rtm/1.0/api/defect/{testKey}` | Defect 조회/수정/삭제 |
| `rtm_requirement_create` | POST | `/rest/rtm/1.0/api/requirement` | Requirement 생성 |
| `rtm_test_case_create` | POST | `/rest/rtm/1.0/api/test-case` | Test Case 생성 |
| `rtm_test_plan_create` | POST | `/rest/rtm/1.0/api/test-plan` | Test Plan 생성 |
| `rtm_test_execution_create` | POST | `/rest/rtm/1.0/api/test-execution` | Test Execution 생성 |
| `rtm_defect_create` | POST | `/rest/rtm/1.0/api/defect` | Defect 생성 |
| `rtm_testcase_steps` | GET/PUT | `/rest/rtm/1.0/api/test-case/{testKey}/steps` | Test Case 설계 Step 조회/업데이트 |
| `rtm_testplan_testcases` | GET/PUT | `/rest/rtm/1.0/api/test-plan/{testKey}/testcases` | Test Plan 내 Test Case 구성 관리 |
| `rtm_testexecution` | GET/PUT | `/rest/rtm/1.0/api/test-execution/{testKey}` | Test Execution 메타 정보 조회/업데이트 |
| `rtm_testexecution_execute` | POST | `/rest/rtm/1.0/api/test-execution/execute/{testPlanKey}` | Test Plan 실행 (TE 생성) |
| `rtm_testexecution_testcases` | GET/PUT | `/rest/rtm/1.0/api/test-execution/{testKey}/testcases` | Test Execution 내 TCE 목록 관리 |
| `rtm_tce` | GET/PUT | `/rest/rtm/1.0/api/test-case-execution/{testKey}` | 단일 TCE 조회/업데이트 |
| `rtm_tce_step_status` | PUT | `/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/status` | TCE Step 상태 변경 |
| `rtm_tce_step_comment` | PUT/DELETE | `/rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment` | TCE Step 코멘트 설정/삭제 |
| `rtm_tce_defect` | PUT | `/rest/rtm/1.0/api/test-case-execution/{testKey}/defect` | TCE 에 Defect 링크 추가 |
| `rtm_tce_defect_item` | DELETE | `/rest/rtm/1.0/api/test-case-execution/{testKey}/defect/{defectTestKey}` | 특정 Defect 링크 제거 |
| `rtm_tce_attachment` | DELETE | `/rest/rtm/1.0/api/test-case-execution/{testKey}/attachment/{attachmentId}` | TCE 첨부 삭제 |
| `rtm_tce_comments` | PUT/POST | `/rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments` | TCE 코멘트 목록 조회/추가 |
| `rtm_tce_comment` | PUT/DELETE | `/rest/rtm/1.0/api/test-case-execution-comment/comments/{id}` | TCE 코멘트 수정/삭제 |

각 Key 에 대해 사용할 수 있는 플레이스홀더 이름은 `DEFAULT_ENDPOINT_PARAMS[key]` 로 정의되어 있으며,  

현재 코드에서 사용하거나, 사용을 전제로 설계된 JIRA 표준 REST API 들은 다음과 같다.

1. **이슈 조회**
   - 메서드: `GET`
   - 경로: `/rest/api/2/issue/{issueIdOrKey}`
   - 쿼리 파라미터:
     - `expand` (선택): `comments,changelog` 등.
   - 사용처:
     - `JiraRTMClient.get_jira_issue()`
     - Details 탭 Activity 조회, 로컬 이슈 Pull 동기화.

2. **JQL 검색**
   - 메서드: `GET`
   - 경로: `/rest/api/2/search`
   - 쿼리 파라미터:
     - `jql`: JQL 문자열
     - `startAt`, `maxResults`
   - 사용처:
     - MainWindow JQL 입력창 → `on_jira_filter_search()` → `search_issues()`.
     - 검색 결과를 우측(Online) 트리 또는 별도 리스트로 표시.

3. **이슈 링크 타입 목록**
   - 메서드: `GET`
   - 경로: `/rest/api/2/issueLinkType`
   - 사용처:
     - Relations 탭 `Add Relation...` 다이얼로그에서 Link Type 콤보박스 채우기.

4. **이슈 링크 생성**
   - 메서드: `POST`
   - 경로: `/rest/api/2/issueLink`
   - Request Body(JSON):
     ```json
     {
       "type": { "name": "Relates" },
       "inwardIssue": { "key": "PROJ-1" },
       "outwardIssue": { "key": "PROJ-2" }
     }
     ```
   - 사용처:
     - Relations 정보를 JIRA 이슈 링크로 푸시하는 기능(`create_issue_link()`).

5. **이슈 코멘트 관련 (계획/부분 구현)**
   - 코멘트 목록 조회
     - `GET /rest/api/2/issue/{issueIdOrKey}/comment`
   - 코멘트 추가
     - `POST /rest/api/2/issue/{issueIdOrKey}/comment`
   - 코멘트 수정
     - `PUT /rest/api/2/issue/{issueIdOrKey}/comment/{id}`
   - 코멘트 삭제
     - `DELETE /rest/api/2/issue/{issueIdOrKey}/comment/{id}`
   - 사용처(계획):
     - Details 탭 Activity 영역에서 JIRA 이슈 댓글을 직접 추가/수정/삭제.

6. **첨부파일 관련 (계획/부분 구현)**
   - 첨부 조회:
     - `GET /rest/api/2/attachment/{id}`
   - 첨부 추가:
     - `POST /rest/api/2/issue/{issueIdOrKey}/attachments`
   - 첨부 삭제:
     - `DELETE /rest/api/2/attachment/{id}`
   - 사용처(계획):
     - Details 탭 Attachments 필드 및 별도 첨부 리스트에서
       파일 업로드/삭제/다운로드/열기 기능 제공.

7. **기타 사용 가능한 JIRA REST API (현재는 미사용, 필요 시 추가)**
   - Issue Transition: `/rest/api/2/issue/{issueIdOrKey}/transitions`
   - Worklog: `/rest/api/2/issue/{issueIdOrKey}/worklog`
   - Project/Field/Status/Version 등 메타데이터 조회.  
   이들 엔드포인트는 **SW사양서 상 요구가 생길 때** `JiraRTMClient` 에 메서드 추가 형태로 확장한다.

### 10.2. Deviniti RTM REST (`/rest/rtm/1.0/api/...`)

아래 엔드포인트는 `RTM REST API.md` 를 기준으로, 현재 SW 구현에서 사용 중이거나 사용을 전제로 설계된 전체 목록이다.

#### 10.2.1. Requirement

1. Requirement 조회
   - `GET /rest/rtm/1.0/api/requirement/{testKey}`
   - 응답: Requirement 메타 + `testCasesCovered` 리스트.

2. Requirement 생성
   - `POST /rest/rtm/1.0/api/requirement`

3. Requirement 수정
   - `PUT /rest/rtm/1.0/api/requirement/{testKey}`

4. Requirement 삭제
   - `DELETE /rest/rtm/1.0/api/requirement/{testKey}`

#### 10.2.2. Test Case

1. Test Case 조회
   - `GET /rest/rtm/1.0/api/test-case/{testKey}`

2. Test Case 생성
   - `POST /rest/rtm/1.0/api/test-case`

3. Test Case 수정
   - `PUT /rest/rtm/1.0/api/test-case/{testKey}`

4. Test Case 삭제
   - `DELETE /rest/rtm/1.0/api/test-case/{testKey}`

5. Test Case Steps
   - `GET /rest/rtm/1.0/api/test-case/{testKey}/steps`
   - `PUT /rest/rtm/1.0/api/test-case/{testKey}/steps`

#### 10.2.3. Test Plan

1. Test Plan 조회
   - `GET /rest/rtm/1.0/api/test-plan/{testKey}`

2. Test Plan 생성
   - `POST /rest/rtm/1.0/api/test-plan`

3. Test Plan 수정
   - `PUT /rest/rtm/1.0/api/test-plan/{testKey}`

4. Test Plan 삭제
   - `DELETE /rest/rtm/1.0/api/test-plan/{testKey}`

5. Test Plan – Test Case 구성 변경
   - `GET /rest/rtm/1.0/api/test-plan/{testKey}/testcases`
   - `PUT /rest/rtm/1.0/api/test-plan/{testKey}/testcases`

6. Test Case 순서 변경
   - `PUT /rest/rtm/1.0/api/test-plan/{testKey}/tc-order`

#### 10.2.4. Test Execution

1. Test Execution 조회
   - `GET /rest/rtm/1.0/api/test-execution/{testKey}`

2. Test Execution 생성 (Test Plan 실행)
   - `POST /rest/rtm/1.0/api/test-execution/execute/{testPlanTestKey}`

3. Test Execution 수정
   - `PUT /rest/rtm/1.0/api/test-execution/{testKey}`

4. Test Execution 삭제
   - `DELETE /rest/rtm/1.0/api/test-execution/{testKey}`

5. Test Execution 상태 조회
   - `GET /rest/rtm/1.0/api/test-execution/status/{testKey}`

6. 포함된 Test Case Executions 목록
   - `GET /rest/rtm/1.0/api/test-execution/{testKey}/testcases`
   - `PUT /rest/rtm/1.0/api/test-execution/{testKey}/testcases`

#### 10.2.5. Test Case Execution (TCE)

1. TCE 조회
   - `GET /rest/rtm/1.0/api/test-case-execution/{testKey}`

2. TCE 수정
   - `PUT /rest/rtm/1.0/api/test-case-execution/{testKey}`

3. Step 상태/코멘트
   - `PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}`
   - `PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/status`
   - `PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment`
   - `DELETE /rest/rtm/1.0/api/test-case-execution/{testKey}/step/{stepIndex}/comment`

4. TCE – Defect 링크
   - `PUT /rest/rtm/1.0/api/test-case-execution/{testKey}/defect`
   - `DELETE /rest/rtm/1.0/api/test-case-execution/{testKey}/defect/{defectTestKey}`

5. TCE – Attachment/Evidence
   - `DELETE /rest/rtm/1.0/api/test-case-execution/{testKey}/attachment/{attachmentId}`

6. TCE 코멘트
   - `PUT /rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments`
   - `POST /rest/rtm/1.0/api/test-case-execution-comment/{testKey}/comments`
   - `PUT /rest/rtm/1.0/api/test-case-execution-comment/comments/{id}`
   - `DELETE /rest/rtm/1.0/api/test-case-execution-comment/comments/{id}`

#### 10.2.6. Defect

1. Defect 조회
   - `GET /rest/rtm/1.0/api/defect/{testKey}`

2. Defect 생성
   - `POST /rest/rtm/1.0/api/defect`

3. Defect 수정
   - `PUT /rest/rtm/1.0/api/defect/{testKey}`

4. Defect 삭제
   - `DELETE /rest/rtm/1.0/api/defect/{testKey}`

#### 10.2.7. Tree Structure

1. RTM 트리 조회
   - `GET /rest/rtm/1.0/api/tree/{projectId}`
   - 또는 버전에 따라 `GET /rest/rtm/1.0/api/v2/tree/{projectId}/{treeType}`

2. 폴더 생성/수정/삭제 (계획)
   - `POST /rest/rtm/1.0/api/tree/{projectId}/folder`
   - `PUT /rest/rtm/1.0/api/tree/{testKey}/folder`
   - `DELETE /rest/rtm/1.0/api/tree/{testKey}/folder`

3. 노드 이동/삭제 (계획)
   - `PUT /rest/rtm/1.0/api/tree/{testKey}/node`
   - `DELETE /rest/rtm/1.0/api/tree/{testKey}/node`

4. JIRA 이슈 Import (계획)
   - `PUT /rest/rtm/1.0/api/v2/tree/import`

---

이로써 **현재 코드에서 사용 중이거나, 사양상 사용을 전제로 한 JIRA/RTM REST API 전체 목록**과,  
각 GUI/DB 구성요소의 역할 및 동작 플로우를 SW 구현 사양서에 반영하였다.  
향후 요구사항 변경 시, 이 문서를 기준으로 API/GUI/DB 설계 변경 사항을 추적·업데이트한다.