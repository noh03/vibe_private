## 1. 개요

이 문서는 `rtm_local_manager`에서 사용하는 **Excel 파일 구조**와  
각 시트 / 각 열에 사용자가 어떤 값을 입력해야 하는지 설명하는 사용 매뉴얼입니다.

- 파일 형식: `.xlsx` (openpyxl 기반)
- 주요 시트:
  - `Issues`
  - `TestcaseSteps`
  - `Relations`
  - `TestPlanTestcases`
  - `TestExecutions`
  - `TestcaseExecutions`
  - `TestcaseStepExecutions` (Step 실행 결과용, 선택적)
- Excel 은 **로컬 DB의 싱글 소스 오브 트루스**로 설계되어 있으며,
  Import → DB → GUI → REST(JIRA/RTM) 순으로 흐릅니다.

## 2. 공통 작성 규칙

- **빈 행**: 한 행의 모든 셀이 비어 있으면 무시됩니다.
- **ID / jira_key**
  - `id` 는 **로컬 DB 내부 ID**입니다.  
    - 직접 임의로 만들지 말고, 보통 **Export 한 파일에서만** 사용합니다.
  - `jira_key` 는 JIRA/RTM 의 이슈 키 (`PROJ-123` 형식)입니다.
    - 이미 존재하는 JIRA 이슈를 수정하려면 필수입니다.
    - 새 이슈를 **JIRA 에서 바로 만들고 싶지 않은 경우** 비워두고,
      로컬에서 관리 후 GUI의 `Create in JIRA` / `Sync → JIRA` 를 사용합니다.
- **날짜 형식**
  - 기본적으로 `YYYY-MM-DD` 형식의 텍스트 또는 Excel 날짜 셀을 권장합니다.
  - Import 시 문자열로 처리되므로, 한 프로젝트 내에서 일관되게 사용하면 됩니다.
- **여러 값 리스트**
  - `labels`, `components`, `attachments`, `defects` 등 다중 값은 **쉼표(,) + 공백** 구분을 권장합니다.
    - 예: `label-a, label-b`
- **issue_type 값**
  - 다음 상수 중 하나를 사용합니다(대문자 권장):
    - `REQUIREMENT`, `TEST_CASE`, `TEST_PLAN`, `TEST_EXECUTION`, `DEFECT`
- **excel_key (엑셀 전용 키)**
  - DB 에는 저장되지 않는 **임시 식별자**입니다.
  - **새 Test Case + Steps 를 한 번에 설계**할 때 사용합니다.
  - `Issues` 시트와 `TestcaseSteps` 시트에 **동일한 문자열**을 넣어 매핑합니다.

---

## 3. `Issues` 시트

### 3.1. 컬럼 목록

- **id**
  - 로컬 DB 의 `issues.id`.
  - **Export 시에만** 채워지며, 사용자는 일반적으로 수정하지 않습니다.
  - Import 시:
    - 값이 있으면 해당 ID 를 가진 이슈를 찾아 **업데이트**합니다.
    - ID 가 없거나 잘못된 경우 무시되고, 아래 `jira_key` / 신규 생성 로직이 사용됩니다.

- **jira_key**
  - JIRA/RTM 이슈 키 (예: `PROJ-123`).
  - Import 시:
    - 값이 있으면 해당 키를 가진 이슈를 찾아 **업데이트 또는 신규 JIRA 연동 이슈 생성**.
    - 값이 없으면 **로컬 전용 이슈**로 새로 생성됩니다 (`local_only=1`).

- **issue_type**
  - 이슈 타입 (`REQUIREMENT`, `TEST_CASE`, `TEST_PLAN`, `TEST_EXECUTION`, `DEFECT`).
  - **신규 행**에서는 필수입니다.

- **folder_path**
  - 트리 상의 폴더 경로 문자열.
  - 예: `Requirements/Release 1/Module A`
  - Import 시:
    - 경로에 해당하는 폴더가 없으면 자동으로 생성됩니다.
    - 비워두면 루트 또는 기본 폴더 아래에 생성됩니다.

- **summary**
  - 이슈 제목. 신규 이슈에서는 사실상 필수입니다.

- **description**
  - 긴 설명/본문. 자유롭게 텍스트를 작성합니다.

- **status**
  - JIRA 상태 이름(예: `To Do`, `In Progress`, `Done`).
  - Import 시 로컬 DB 의 `status` 필드를 갱신하며,
    실제 JIRA 워크플로 Transition 은 REST 동기화 시점에 별도로 처리됩니다.

- **priority**
  - 우선순위(예: `Highest`, `High`, `Medium`, `Low`).

- **assignee**
  - 담당자 이름 또는 JIRA 사용자 표시명.

- **reporter**
  - 보고자 이름 또는 JIRA 사용자 표시명.

- **labels**
  - 라벨 리스트. 예: `regression, smoke, api`.

- **components**
  - 컴포넌트 리스트. 예: `Backend, API`.

- **security_level**
  - JIRA 보안 레벨 이름.

- **fix_versions**, **affects_versions**
  - 버전 이름 리스트. 예: `1.0.0, 1.0.1`.

- **rtm_environment**
  - RTM 환경 이름 또는 태그(예: `DEV`, `QA`, `PROD`).

- **due_date**
  - 마감일. `YYYY-MM-DD` 권장.

- **created**, **updated**
  - 생성/수정 시각.
  - 보통 Export 된 값을 참고용으로만 사용하고, 수동 변경은 권장하지 않습니다.

- **attachments**
  - 첨부 파일 정보 문자열.
  - 실제 첨부/삭제는 GUI 의 `Attachments` 영역과 REST API 를 사용하는 것을 권장합니다.

- **epic_link**
  - 연결된 Epic 이슈 키 (`PROJ-1` 등).

- **sprint**
  - 스프린트 이름 또는 JIRA 의 Sprint 필드 문자열 표현.

- **excel_key** (옵션, 수동 추가 가능)
  - 새로 설계하는 이슈(특히 Test Case)에 부여하는 임시 키.
  - 같은 키를 `TestcaseSteps.excel_key` 에도 적어 두면, Import 시 해당 Test Case 와 Steps 를 자동으로 연결합니다.
  - 기존 Export 파일에는 포함되지 않을 수 있으므로, 필요 시 사용자가 열을 **추가**해서 사용합니다.

### 3.2. 사용 예시 (새 Test Case 설계)

1. `Issues` 시트에 새 행 추가:
   - `id`: 비움
   - `jira_key`: 비움
   - `issue_type`: `TEST_CASE`
   - `summary`: `로그인 성공 시 메인 화면 이동`
   - `excel_key`: `TC_LOGIN_SUCCESS`
2. 이후 `TestcaseSteps` 시트에서 같은 `excel_key` 를 사용하여 Steps 를 작성합니다.

---

## 4. `TestcaseSteps` 시트

### 4.1. 컬럼 목록

- **issue_id**
  - 이 Step 이 속한 Test Case 의 로컬 ID (`Issues.id`).
  - **가장 높은 우선순위 매핑 키**입니다.
  - 보통 Export 된 파일에서만 사용하며, 새 TC 설계 시에는 비워둡니다.

- **issue_jira_key**
  - 이 Step 이 속한 Test Case 의 JIRA 키.
  - `issue_id` 와 `excel_key` 가 모두 없을 때 fallback 으로 사용됩니다.

- **preconditions**
  - Test Case 단위 전제조건 텍스트.
  - 같은 `issue_id`(또는 같은 excel_key)를 가진 여러 행이 있을 경우,
    **마지막 행의 값이 우선 적용**됩니다.

- **group_no**
  - Step 그룹 번호. 없으면 기본값 `1`.
  - 여러 그룹으로 Step 을 묶어 관리하고 싶을 때 사용합니다.

- **order_no**
  - 그룹 내 Step 순번(1부터 시작 권장).

- **action**
  - 수행할 동작(What to do).

- **input**
  - 입력 값(With what).

- **expected**
  - 기대 결과(What is expected).

- **excel_key** (옵션, 수동 추가 가능)
  - `Issues` 시트의 `excel_key` 와 연결되는 키.
  - 새 Test Case 를 처음부터 Excel 로 설계할 때:
    - `issue_id`, `issue_jira_key` 는 비워두고,
    - `excel_key` 에만 값을 넣으면,
    - Import 시 `Issues.excel_key` 를 통해 해당 TC 를 찾아 Steps 를 연결합니다.

### 4.2. 매핑 우선순위

한 행이 어느 Test Case 에 속하는지 결정하는 순서는 다음과 같습니다.

1. `issue_id` (있으면 최우선)
2. `excel_key` (Issues 시트에서 매핑된 경우)
3. `issue_jira_key`

해당 키들로도 대상을 찾지 못하면 그 행은 무시됩니다.

---

## 5. `Relations` 시트

### 5.1. 컬럼 목록

- **src_jira_key**
  - 관계의 출발 이슈 키 (예: Requirement, Test Case, Defect 등).

- **dst_jira_key**
  - 관계의 도착 이슈 키.
  - 예: Requirement → Test Case, Test Case → Requirement, Defect → Test Case 등.

- **relation_type**
  - 관계 타입 문자열.
  - 예: `Tests`, `Is tested by`, `Relates`, `Blocks`, `Is blocked by` 등
    (JIRA Issue Link 타입 이름 또는 RTM 용어와 맞춰 사용).

### 5.2. 동작

- Import 시:
  - `src_jira_key` 로 출발 이슈를 찾고,
  - 해당 이슈의 기존 `relations` 를 **모두 교체**합니다.
  - 각 행마다 `dst_jira_key` 를 찾아 `dst_issue_id` + `relation_type` 로 저장합니다.

---

## 6. `TestPlanTestcases` 시트

### 6.1. 컬럼 목록

- **testplan_jira_key**
  - Test Plan 이슈의 Jira Key.

- **testcase_jira_key**
  - 이 Test Plan 에 포함될 Test Case 의 Jira Key.

- **order_no**
  - Test Plan 내에서의 실행 순서(정수).

### 6.2. 동작

- Import 시:
  - 각 Test Plan 에 대해 `testplan_testcases` 매핑을 **전부 교체**합니다.
  - 존재하지 않는 Jira Key 를 가진 행은 무시됩니다.

---

## 7. `TestExecutions` 시트

### 7.1. 컬럼 목록

- **testexecution_jira_key**
  - Test Execution 이슈의 Jira Key (`TEST_EXECUTION` 타입).
  - 이미 `Issues` 시트에 존재해야 합니다.

- **environment**
  - 실행 환경(예: `QA`, `PROD`).

- **start_date**, **end_date**
  - 실행 시작/종료 일시(문자열).

- **result**
  - 실행 결과(예: `In progress`, `Pass`, `Fail`, `Blocked` 등).

- **executed_by**
  - 실행자 이름.

### 7.2. 동작

- Import 시:
  - `testexecution_jira_key` 로 TE 이슈를 찾고,
  - 해당 이슈의 `testexecutions` 메타 정보를 업데이트합니다.
  - TE 이슈가 존재하지 않으면 해당 행은 무시됩니다.

---

## 8. `TestcaseExecutions` 시트

### 8.1. 컬럼 목록

- **testexecution_jira_key**
  - 상위 Test Execution 의 Jira Key.

- **testcase_jira_key**
  - 실행 대상 Test Case 의 Jira Key.

- **order_no**
  - 해당 Test Execution 내에서 Test Case 의 순번.

- **assignee**
  - 이 Test Case Execution 의 담당자.

- **result**
  - TCE 결과 (예: `Not Executed`, `Pass`, `Fail`, `Blocked` 등 RTM 결과 값).

- **actual_time**
  - 실제 소요 시간(분 단위 정수).

- **rtm_environment**
  - RTM 환경(문자열).

- **defects**
  - 이 TCE 와 연결된 Defect Jira Key 목록.
  - 예: `PROJ-101, PROJ-102`.

- **tce_test_key**
  - RTM 상의 **Test Case Execution key**.
  - 보통 RTM 에서 Pull 해오면 자동으로 채워지며,
    RTM Step API 및 Defect 링크 API 에 사용됩니다.

### 8.2. 동작

- Import 시:
  - `testexecution_jira_key` → TE 이슈 찾기.
  - 그 아래에서 `testcase_jira_key` 로 TC 이슈를 찾아 TCE 레코드 목록을 구성합니다.
  - 같은 TE 에 대한 기존 TCE 목록은 **교체**됩니다.
  - `actual_time`, `rtm_environment`, `defects`, `tce_test_key` 가 있으면 그대로 저장됩니다.

---

## 9. `TestcaseStepExecutions` 시트 (선택)

### 9.1. 컬럼 목록

- **testexecution_jira_key**
  - 상위 Test Execution 의 Jira Key.

- **testcase_jira_key**
  - 실행 대상 Test Case 의 Jira Key.

- **group_no**
  - 설계된 Step 의 그룹 번호 (`TestcaseSteps.group_no` 와 동일).

- **order_no**
  - 설계된 Step 의 순번 (`TestcaseSteps.order_no` 와 동일).

- **status**
  - Step 실행 상태 (예: `Not Executed`, `Pass`, `Fail`, `Blocked` 등).

- **actual_result**
  - 실제 실행 결과(텍스트).

- **evidence**
  - 증거(로그 경로, 파일명, URL 등 텍스트).
  - 실제 파일 첨부는 RTM/JIRA 첨부 API 와 연동하는 GUI 기능을 사용하는 것이 일반적이며,
    이 필드는 설명/메모 용도로 활용할 수 있습니다.

### 9.2. 동작

- Import 시:
  1. `testexecution_jira_key` / `testcase_jira_key` 로 TE / TC 를 찾습니다.
  2. 해당 조합에 대해 **TCE 레코드**를 찾거나 생성합니다.
  3. `group_no` + `order_no` 로 `testcase_steps` 테이블의 설계 Step 을 찾습니다.
  4. 각 Step 에 대한 실행 정보(`status`, `actual_result`, `evidence`)를
     `testcase_step_executions` 테이블에 저장합니다.
  5. 같은 TCE 의 기존 Step 실행 정보는 **교체**됩니다.

---

## 10. 새 데이터 설계 시 권장 절차 요약

- **새 Test Case + Steps (JIRA 키 없음)**  
  1. `Issues` 시트에 새 행 추가:
     - `issue_type = TEST_CASE`, `jira_key` 비움, `summary` 입력.
     - `excel_key` 에 고유 문자열 입력 (예: `TC_LOGIN_001`).
  2. `TestcaseSteps` 시트에 해당 TC 의 Step 행들을 추가:
     - `issue_id`, `issue_jira_key` 는 비움.
     - `excel_key` 에 위에서 사용한 값(`TC_LOGIN_001`)을 입력.
     - `group_no`, `order_no`, `action`, `input`, `expected` 작성.
  3. Excel Import 실행 → 로컬 DB 에 TC + Steps 가 함께 생성.
  4. 이후 GUI 에서 내용을 확인/수정 후, 필요 시 JIRA/RTM 으로 Push.

- **기존 JIRA 이슈 보정**  
  - `Issues` 시트에 `jira_key` 를 채운 행을 넣고,
  - 수정하고 싶은 메타 필드만 채워 Import 하면,
    해당 이슈에 대해 로컬 DB 메타가 갱신됩니다.

- **실행 결과/Defect 관리**  
  - `TestExecutions`, `TestcaseExecutions`, `TestcaseStepExecutions` 시트를 통해
    Execution 메타, 각 TCE 결과, Step 수준 실행 결과를 Excel 로 편집한 뒤 Import 할 수 있습니다.
  - Defect 링크는 `TestcaseExecutions.defects` 에 Jira Key 목록으로 관리되며,
    GUI 의 Executions 탭과 Defects 탭에서 함께 확인/편집할 수 있습니다.

- **기존 로컬 DB 데이터 수정**  
  - Export 된 엑셀에서 `Issues.id` / 각 시트의 `...jira_key` / `issue_id` 값은 **그대로 두고**, 나머지 필드만 수정합니다.
  - Import 시:
    - `Issues.id` 가 있는 행은 해당 ID 레코드를 그대로 수정합니다.
    - `id` 가 없고 `jira_key` 가 있는 행은 해당 Jira Key 레코드를 수정하거나(없으면 새로 생성) 합니다.
    - Steps/Relations/TestPlanTestcases/TestExecutions/TestcaseExecutions/StepExecutions 는 각 시트 설명에 나온 키(`issue_id`, `issue_jira_key`, `...jira_key`) 기준으로 기존 구조를 **덮어쓰는 방식**으로 동작합니다.
  - 이 경우 `excel_key` 는 새 데이터 추가에만 사용하며, 기존 데이터 수정에는 필수가 아닙니다.

이 문서를 참고하여 각 시트/컬럼에 의미 있는 값을 일관되게 작성하면,  
Excel 하나로 요구사항–테스트–실행–결함 데이터를 설계·리뷰하고,  
필요할 때마다 Import/Export 기능을 통해 로컬 DB 및 JIRA/RTM 과 안전하게 동기화할 수 있습니다.
