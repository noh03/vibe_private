1. 기능
 - JIRA RTM에 각 이슈 등록(단수/복수)/조회/수정/삭제 가능
 - 로컬에서 RTM과 동일한 구조로 각 이슈 관리 (DB)
    - 요구사항, 테스트 케이스, 테스트플랜, 테스트 수행, 결함 관리 기능 포함 CRUD 포함
    - 아래에서 언급한 이슈 타입 별 필드 참조할 것
    - JIRA RTM에서 관리되는 필드, 데이터 구조와 동일하게 로컬에서 관리 가능할 것
    - 엑셀로 데이터 불러오기, 내보내기 가능할 것
 - 로컬 데이터와 JIRA 데이터를 동시에 볼 수 있도록 창을 분리할 것 (좌측: 로컬, 우측: 온라인 JIRA 데이터)
    - 각 창에서 데이터는 RTM의 트리 형태대로 디스플레이 구성할 것 (아래 참조 문서의 트리 부분 참고할 것)
 - REST API 사용은 아래 정보를 참조할 것 (개인용 토큰 인증 타입)
 - 파이썬 사용, 사용자 친화적 GUI, 윈도우용 프로그램 생성/배포 예정

2. 이슈 별 탭 구조 및 탭 별 필드
 - Requirements: 아래 3개 탭을 가짐
   - Details : Status, Priority, Assignee, Created, Issue Type, Labels, Fix Version/s Last updated, Component/s, Security Level, RTM Environment, Reporter, Due Date, Affects Version/s, Test Key, Description, Attachment, Activity (Comment, History)
   - Test Cases: 테이블 (Key, Summary, Priority, Assignee, Components, RTM Envronment), 버튼(Cover by Test Case:클릭 시 팝업창 뜸. 팝업창에 테이블 포함(Issue Key, Summary, Assignee, Labels, Priority, Fix Version, Status)하며 Add 버튼 및 Cancel 버튼 있음, Create New Test Case: Details/Steps/Requirements 탭 있음. Detatils 탭에는 필드들 포함(Issue Type, Folder, Test Plan, Summary, Component/s(선택), Description, Reporter(선택),priority(선택), Attachments(첨부), Label(선택), Due Date(날짜선택), Assignee(선택), Fix Version/s(선택), RTM Environment(선택), Affects Version/s(선택), Steps 탭에는 Preconditions(멀티라인 텍스트), Steps(스텝 그룹추가 버튼:누르면 Action, input, expected result 각각 텍스트 입력)))
   - Relations : Add Requirement 버튼있으며 클릭 시 팝업창 떠서 입력하도록 함
 - Test Cases : Details, Steps, Requirements, Relations 탭 가짐
   - Details 탭의 필드: Requirements의 Details 탭의 필드 참조
   - Steps: 
   - Requirements:
   - Relations: Create Link 버튼 있고 누르면 팝업창 뜸 (jira issue 선택 시 type of link 선택하고 이슈 선택하도록 되어 있음. web link 선택 시 URL, link text 입력하도록 되어 있음)
 - Test Plan: Details, Test Cases, Executions, Relations 탭 존재
 - Test Executions : Test Cases (Executions), Detatils, Relations 탭 존재, 탭 상단에 대시보드 표시됨(TE executed, RTM Environment, TE Start Date, TE End Date, Result(선택가능))
    - Test Cases (Executions): 테이블 표시 (Order, Summary, Priority, Assignee, Result, RTM Environment, Defects 열 포함)
 - Defects: Detatils, Test Cased, Relations 탭 포함

3. JIRA RTM
 - Requirement: https://deviniti.com/support/addon/server/requirements-test-management/latest/requirement/
 - Test Case: https://deviniti.com/support/addon/server/requirements-test-management/latest/test-case/
 - Test Plan: https://deviniti.com/support/addon/server/requirements-test-management/latest/test-plan/
 - Test Execution: https://deviniti.com/support/addon/server/requirements-test-management/latest/test-plan/
 - Defect: https://deviniti.com/support/addon/server/requirements-test-management/latest/defect/
- import: https://deviniti.com/support/addon/server/requirements-test-management/latest/import/


4. REST API 사용 법: 각 이슈 타입에 대해서 아래 참조 링크 내에서 V1 API 참조할 것
  - Authentication: https://deviniti.com/support/addon/server/requirements-test-management/latest/authentication/
  - https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api/
  - requirements: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-requirements/
  - Test Case: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-test-case/
  - Test Plan: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-test-plan/
  - Test Execution: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-test-execution/
  - Test Case Execution: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-test-case-execution/
  - Defects: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-defects/
  - Tree structure: https://deviniti.com/support/addon/server/requirements-test-management/latest/rest-api-tree-structure/
  - example: https://deviniti.com/support/addon/server/requirements-test-management/latest/example-of-use/


 5. 정보
  - JIRA: data center version, v9.12.28
  - ProjectKey: KVHSICCU
  - projectId: 41500
  - parentTestKey: /rest/rtm/1.0/api/tree/{projectId}
  - 