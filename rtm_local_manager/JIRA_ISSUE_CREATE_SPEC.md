# JIRA 이슈 생성 기능 요구사양 및 설계

## 1. 요구사양

### 1.1 기능 개요
온라인 패널(우측 패널)에서 각 이슈 타입별로 JIRA RTM에 새 이슈를 직접 생성할 수 있는 기능을 제공합니다.

### 1.2 사용자 시나리오
1. 사용자가 온라인 패널의 모듈 탭(Requirements, Test Cases, Test Plans, Test Executions, Defects) 중 하나를 선택
2. "Create in JIRA" 버튼 클릭
3. 새 이슈 생성 다이얼로그가 열림
4. 필수 필드(Summary 등) 및 선택 필드 입력
5. "Create" 버튼 클릭하여 JIRA에 생성
6. 생성된 이슈가 온라인 트리에 표시되고 자동 선택됨

### 1.3 기능 요구사항

#### FR-1: 이슈 타입별 생성 지원
- **REQUIREMENT**: 요구사항 생성
- **TEST_CASE**: 테스트 케이스 생성
- **TEST_PLAN**: 테스트 플랜 생성
- **TEST_EXECUTION**: 테스트 실행 생성 (Test Plan 기반)
- **DEFECT**: 결함 생성

#### FR-2: 필수 필드
- **모든 타입**: `summary` (제목)
- **REQUIREMENT**: `projectKey`, `issueTypeId` (선택적)
- **TEST_CASE**: `projectKey`, `issueTypeId` (선택적)
- **TEST_PLAN**: `projectKey`, `issueTypeId` (선택적)
- **TEST_EXECUTION**: `testPlanTestKey` (Test Plan에서 생성 시)

#### FR-3: 선택 필드
- `description`: 설명
- `assigneeId`: 담당자
- `priority`: 우선순위
- `status`: 상태
- `labels`: 라벨 목록
- `components`: 컴포넌트 목록
- `versions`: 버전 목록
- `timeEstimate`: 예상 소요 시간
- `environment`: 환경 (Test Case, Test Plan, Test Execution)
- `preconditions`: 전제조건 (Test Case)
- `parentTestKey`: 부모 폴더/이슈 키

#### FR-4: 부모 폴더 선택
- 온라인 트리에서 선택된 폴더가 있으면 `parentTestKey`로 자동 설정
- 폴더가 선택되지 않았으면 루트에 생성

#### FR-5: 생성 후 처리
- 생성된 이슈의 `testKey`를 받아온다
- 온라인 트리를 새로고침한다
- 생성된 이슈를 자동으로 선택하여 상세 정보를 표시한다

### 1.4 제약사항
- JIRA RTM API 연결이 활성화되어 있어야 함
- 프로젝트가 설정되어 있어야 함 (`projectKey` 필요)
- 각 이슈 타입에 대한 생성 권한이 있어야 함

## 2. 설계

### 2.1 아키텍처

```
[GUI Layer]
  └─ MainWindow.on_create_new_online_issue_clicked()
      └─ CreateIssueDialog (이슈 타입별 다이얼로그)
          └─ 사용자 입력 수집
              └─ [Mapping Layer]
                  └─ jira_mapping.build_rtm_payload()
                      └─ [API Layer]
                          └─ JiraRTMClient.create_entity()
                              └─ RTM REST API POST 요청
```

### 2.2 데이터 흐름

1. **사용자 입력** → `CreateIssueDialog`에서 필드 값 수집
2. **로컬 형식 변환** → 입력값을 `local_issue` dict로 변환
3. **RTM Payload 생성** → `build_rtm_payload()`로 RTM API 형식 변환
4. **API 호출** → `create_entity()`로 POST 요청
5. **응답 처리** → 생성된 `testKey` 추출
6. **UI 업데이트** → 트리 새로고침 및 선택

### 2.3 클래스 설계

#### 2.3.1 CreateIssueDialog
```python
class CreateIssueDialog(QDialog):
    """
    새 JIRA 이슈 생성 다이얼로그
    
    Attributes:
        issue_type: 생성할 이슈 타입 (REQUIREMENT, TEST_CASE, ...)
        project_key: 프로젝트 키 (자동 설정)
        parent_test_key: 부모 폴더/이슈 키 (선택적)
        fields: 입력 필드들 (summary, description, ...)
    """
```

#### 2.3.2 주요 메서드
- `__init__(issue_type, project_key, parent_test_key=None)`: 다이얼로그 초기화
- `_init_ui()`: UI 구성 (이슈 타입별 필드 표시)
- `_collect_data()`: 사용자 입력 수집
- `accept()`: 생성 요청 처리

### 2.4 API Payload 구조

#### 2.4.1 Requirement
```json
{
  "projectKey": "PROJ",
  "issueTypeId": 123,
  "summary": "Requirement title",
  "description": "Description text",
  "assigneeId": "user123",
  "parentTestKey": "PROJ-100",
  "priority": {"name": "High"},
  "status": {"id": 1, "statusName": "To Do"},
  "labels": ["label1", "label2"],
  "components": [{"id": 1}],
  "versions": [{"id": "1"}],
  "timeEstimate": "2h 30m",
  "epicName": "Epic Name"
}
```

#### 2.4.2 Test Case
```json
{
  "projectKey": "PROJ",
  "summary": "Test Case title",
  "description": "Description text",
  "parentTestKey": "PROJ-100",
  "priority": {"name": "High"},
  "status": {"id": 1, "statusName": "To Do"},
  "environment": "Chrome",
  "preconditions": "Precondition text",
  "steps": [[{"value": "Step 1"}], [{"value": "Step 2"}]],
  "labels": ["label1"],
  "components": [{"id": 1}],
  "versions": [{"id": "1"}]
}
```

### 2.5 에러 처리

- **API 연결 실패**: "Cannot create: Jira RTM not configured."
- **프로젝트 키 없음**: "Project key is required."
- **필수 필드 누락**: "Summary is required."
- **API 오류**: 응답 메시지를 사용자에게 표시
- **생성 실패**: 에러 로그 기록 및 사용자 알림

## 3. 구현 계획

### 3.1 단계별 구현

1. **build_rtm_payload 함수 개선**
   - `projectKey` 필드 추가
   - `issueTypeId` 필드 추가 (선택적)
   - `labels`, `components`, `versions` 등 추가 필드 지원

2. **CreateIssueDialog 구현**
   - 이슈 타입별 필드 표시
   - 필수 필드 검증
   - 사용자 입력 수집

3. **MainWindow 메서드 추가**
   - `on_create_new_online_issue_clicked()`: 다이얼로그 호출
   - 생성 후 트리 새로고침 및 선택

4. **UI 버튼 연결**
   - 온라인 패널의 "Create in JIRA" 버튼 연결
   - 리본 메뉴의 "Create in JIRA" 버튼 연결

### 3.2 파일 수정 목록

- `rtm_local_manager/backend/jira_mapping.py`: `build_rtm_*_payload` 함수들 개선
- `rtm_local_manager/gui/main_window.py`: `CreateIssueDialog` 클래스 및 메서드 추가
- `rtm_local_manager/backend/jira_api.py`: `create_entity` 메서드 확인 (이미 구현됨)

## 4. 구현 완료

### 4.1 구현된 기능

✅ **build_rtm_payload 함수들 개선**
- 모든 `build_rtm_*_payload` 함수에 `project_key` 파라미터 추가
- `labels`, `components`, `versions`, `timeEstimate`, `environment` 등 추가 필드 지원
- `build_rtm_payload` 통합 함수에 `project_key` 파라미터 추가

✅ **CreateIssueDialog 구현**
- 새 파일: `rtm_local_manager/gui/create_issue_dialog.py`
- 이슈 타입별 필드 표시 (Summary, Description, Assignee, Priority, Status 등)
- 이슈 타입별 특수 필드:
  - **TEST_CASE**: Environment, Preconditions
  - **TEST_PLAN/TEST_EXECUTION**: Environment
  - **REQUIREMENT**: Epic Name
- 필수 필드 검증 (Summary)
- 사용자 입력 수집 및 RTM Payload 생성
- JIRA API 호출 및 응답 처리

✅ **MainWindow 메서드 추가**
- `on_create_new_online_issue_clicked()`: 온라인 패널에서 새 이슈 생성
- `_select_issue_in_online_tree()`: 생성된 이슈를 트리에서 찾아서 선택
- 온라인 트리에서 선택된 폴더의 `testKey` 자동 감지
- 생성 후 트리 새로고침 및 자동 선택

✅ **UI 버튼 연결**
- 온라인 패널의 "Create in JIRA" 버튼 → `on_create_new_online_issue_clicked()` 연결

✅ **기존 기능 개선**
- `on_create_in_jira_clicked()`: 로컬 이슈 기반 생성 시 `project_key` 추가

### 4.2 사용 방법

1. **온라인 패널에서 새 이슈 생성**
   - 온라인 패널의 모듈 탭(Requirements, Test Cases, Test Plans, Test Executions, Defects) 선택
   - "Create in JIRA" 버튼 클릭
   - 다이얼로그에서 필수 필드(Summary) 및 선택 필드 입력
   - "OK" 버튼 클릭하여 생성
   - 생성된 이슈가 온라인 트리에 표시되고 자동 선택됨

2. **부모 폴더 지정**
   - 온라인 트리에서 폴더를 선택한 후 "Create in JIRA" 버튼 클릭
   - 선택된 폴더가 `parentTestKey`로 자동 설정됨

### 4.3 주요 개선 사항

- **프로젝트 키 자동 설정**: `self.project.key`에서 자동으로 가져옴
- **부모 폴더 자동 감지**: 온라인 트리에서 선택된 폴더의 `testKey` 자동 감지
- **이슈 타입별 필드**: 각 이슈 타입에 맞는 필드만 표시
- **에러 처리**: 필수 필드 검증 및 API 오류 처리
- **생성 후 자동 선택**: 생성된 이슈를 트리에서 찾아서 자동 선택

### 4.4 참고 사항

- **Test Execution 생성**: Test Plan 기반 생성은 별도 API (`/api/test-execution/execute/{testPlanTestKey}`)를 사용해야 할 수 있음
- **issueTypeId**: RTM에서 자동 설정될 수 있으므로 선택적 필드로 처리
- **Steps**: Test Case 생성 시 Steps는 별도 API로 관리될 수 있음 (현재는 기본 구조만 지원)

