# 엑셀 임포트 후 온라인 자동/대량 등록 기능 분석 및 구현 계획

## 1. 현재 구현 상태 분석

### 1.1 엑셀 임포트 기능 (이미 구현됨)
- **위치**: `rtm_local_manager/backend/excel_io.py` - `import_project_from_excel()`
- **기능**: Excel 파일에서 데이터를 읽어 로컬 DB에 저장
- **처리 로직**:
  - `jira_key`가 있으면: 기존 이슈 업데이트 또는 신규 JIRA 연동 이슈 생성
  - `jira_key`가 없으면: 로컬 전용 이슈로 생성 (`local_only=1`, `jira_key=NULL`)
- **지원 시트**: Issues, TestcaseSteps, Relations, TestPlanTestcases, TestExecutions, TestcaseExecutions

### 1.2 온라인 이슈 생성 기능 (이미 구현됨)
- **위치**: `rtm_local_manager/gui/main_window.py` - `on_create_in_jira_clicked()`
- **기능**: 현재 선택된 로컬 이슈를 JIRA RTM에 생성
- **제한사항**: 한 번에 하나의 이슈만 생성 가능

### 1.3 누락된 기능
- ❌ 로컬 DB에서 `jira_key`가 없는 이슈들을 조회하는 기능
- ❌ 여러 이슈를 일괄적으로 온라인에 생성하는 기능
- ❌ 엑셀 임포트 후 자동으로 온라인 등록하는 옵션
- ❌ 대량 등록 진행 상황 표시 및 에러 처리

## 2. 요구사항

### 2.1 사용자 시나리오
1. **시나리오 A: 엑셀 임포트 후 자동 등록**
   - 사용자가 엑셀 파일을 임포트
   - 임포트 완료 후 "온라인으로 자동 등록하시겠습니까?" 확인 다이얼로그 표시
   - 확인 시 `jira_key`가 없는 모든 이슈를 온라인에 생성
   - 생성된 `jira_key`를 로컬 DB에 업데이트

2. **시나리오 B: 수동 대량 등록**
   - 사용자가 "대량 등록" 버튼 클릭
   - `jira_key`가 없는 이슈 목록 표시
   - 이슈 타입별 필터링 옵션
   - 선택한 이슈들을 온라인에 일괄 생성

### 2.2 기능 요구사항

#### FR-1: 로컬 이슈 조회
- `jira_key`가 NULL이거나 빈 문자열인 이슈 조회
- 이슈 타입별 필터링 지원
- 프로젝트 ID 기준 필터링

#### FR-2: 대량 생성 기능
- 여러 이슈를 순차적으로 또는 배치로 생성
- 각 이슈 생성 시 진행 상황 표시
- 실패한 이슈는 건너뛰고 계속 진행
- 생성 결과 요약 (성공/실패 개수)

#### FR-3: 에러 처리
- API 오류 시 해당 이슈만 실패 처리
- 네트워크 오류 시 재시도 옵션
- 실패한 이슈 목록 표시

#### FR-4: UI 개선
- 엑셀 임포트 후 자동 등록 옵션 추가
- 대량 등록 진행 상황 다이얼로그
- 대량 등록 결과 리포트

## 3. 설계

### 3.1 아키텍처

```
[Excel Import]
  └─ import_project_from_excel()
      └─ [Optional] 자동 등록 확인
          └─ [Bulk Create Module]
              └─ get_local_issues_without_jira_key()
                  └─ bulk_create_issues_in_jira()
                      └─ for each issue:
                          ├─ build_rtm_payload()
                          ├─ create_entity()
                          └─ update_issue_fields(jira_key)
```

### 3.2 데이터베이스 쿼리

```sql
-- jira_key가 없는 이슈 조회
SELECT * FROM issues 
WHERE project_id = ? 
  AND (jira_key IS NULL OR jira_key = '')
  AND is_deleted = 0
  AND issue_type = ?  -- 선택적
ORDER BY id;
```

### 3.3 클래스 설계

#### 3.3.1 BulkCreateDialog
```python
class BulkCreateDialog(QDialog):
    """
    대량 이슈 생성 다이얼로그
    
    Attributes:
        issues: 생성할 이슈 목록
        project_key: 프로젝트 키
        jira_client: JIRA 클라이언트
        results: 생성 결과 (성공/실패)
    """
```

#### 3.3.2 주요 함수
- `get_local_issues_without_jira_key(conn, project_id, issue_type=None)`: 로컬 이슈 조회
- `bulk_create_issues_in_jira(conn, issues, jira_client, project_key, progress_cb)`: 대량 생성

## 4. 구현 계획

### 4.1 단계별 구현

#### Phase 1: 데이터베이스 함수 추가
1. `get_local_issues_without_jira_key()` 함수 구현
   - 위치: `rtm_local_manager/backend/db.py`
   - 기능: `jira_key`가 없는 이슈 조회

#### Phase 2: 대량 생성 모듈 구현
2. `bulk_create_issues_in_jira()` 함수 구현
   - 위치: `rtm_local_manager/backend/bulk_create.py` (신규 파일)
   - 기능: 여러 이슈를 순차적으로 생성
   - 진행 상황 콜백 지원

#### Phase 3: UI 구현
3. `BulkCreateDialog` 클래스 구현
   - 위치: `rtm_local_manager/gui/bulk_create_dialog.py` (신규 파일)
   - 기능: 대량 생성 진행 상황 표시

4. `MainWindow` 메서드 추가
   - `on_bulk_create_clicked()`: 대량 등록 버튼 핸들러
   - `on_import_excel_clicked()` 수정: 자동 등록 옵션 추가

#### Phase 4: 통합 및 테스트
5. 엑셀 임포트 후 자동 등록 옵션 통합
6. 에러 처리 및 로깅 강화
7. 사용자 가이드 작성

### 4.2 파일 수정/생성 목록

#### 수정할 파일
- `rtm_local_manager/backend/db.py`: `get_local_issues_without_jira_key()` 추가
- `rtm_local_manager/gui/main_window.py`: 
  - `on_import_excel_clicked()` 수정 (자동 등록 옵션)
  - `on_bulk_create_clicked()` 추가
  - UI 버튼 추가

#### 생성할 파일
- `rtm_local_manager/backend/bulk_create.py`: 대량 생성 로직
- `rtm_local_manager/gui/bulk_create_dialog.py`: 대량 생성 다이얼로그

### 4.3 주요 고려사항

#### 4.3.1 성능
- 대량 생성 시 API 호출 제한 고려
- 순차 생성 vs 배치 생성 (RTM API가 배치를 지원하는지 확인 필요)
- 진행 상황 표시로 사용자 경험 개선

#### 4.3.2 에러 처리
- 일부 이슈 생성 실패 시에도 나머지 계속 진행
- 실패한 이슈 목록을 사용자에게 제공
- 재시도 옵션 제공

#### 4.3.3 데이터 일관성
- 생성 중 프로그램 종료 시 일관성 보장
- 트랜잭션 처리 (각 이슈별로 독립적)
- 생성된 `jira_key` 즉시 업데이트

## 5. 구현 우선순위

1. **High Priority**: 
   - `get_local_issues_without_jira_key()` 함수
   - `bulk_create_issues_in_jira()` 기본 기능
   - `BulkCreateDialog` 기본 UI

2. **Medium Priority**:
   - 엑셀 임포트 후 자동 등록 옵션
   - 진행 상황 표시 개선
   - 에러 처리 강화

3. **Low Priority**:
   - 이슈 타입별 필터링
   - 재시도 기능
   - 결과 리포트 내보내기

