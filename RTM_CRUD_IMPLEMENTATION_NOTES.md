# RTM CRUD 기능 구현 노트

## 구현 완료 사항

### 1. RTM API 응답 매핑 (RTM -> Local)
- ✅ `map_rtm_requirement_to_local`: Requirement GET 응답 매핑
- ✅ `map_rtm_testcase_to_local`: Test Case GET 응답 매핑
- ✅ `map_rtm_testplan_to_local`: Test Plan GET 응답 매핑
- ✅ `map_rtm_testexecution_to_local`: Test Execution GET 응답 매핑
- ✅ `map_rtm_defect_to_local`: Defect GET 응답 매핑
- ✅ `map_rtm_to_local`: 통합 매핑 함수

### 2. RTM API Payload 생성 (Local -> RTM)
- ✅ `build_rtm_requirement_payload`: Requirement 생성/수정 payload
- ✅ `build_rtm_testcase_payload`: Test Case 생성/수정 payload
- ✅ `build_rtm_testplan_payload`: Test Plan 생성/수정 payload
- ✅ `build_rtm_testexecution_payload`: Test Execution 생성/수정 payload
- ✅ `build_rtm_defect_payload`: Defect 생성/수정 payload
- ✅ `build_rtm_payload`: 통합 payload 생성 함수

### 3. 온라인 트리 이슈 선택 및 표시
- ✅ `on_online_tree_selection_changed`: RTM API 직접 호출하여 이슈 상세 정보 가져오기
- ✅ 각 이슈 타입별 데이터를 우측 패널에 표시
  - Requirement: testCasesCovered → Test Cases 탭
  - Test Case: steps, preconditions → Steps 탭
  - Test Plan: includedTestCases → Test Cases 탭
  - Test Execution: testCaseExecutions → Executions 탭
  - Defect: identifyingTestCases → Test Cases 탭

### 4. CRUD 기능
- ✅ **Read**: 온라인 트리에서 이슈 선택 시 RTM API로 조회하여 표시
- ✅ **Update**: `on_save_online_issue_clicked` 메서드 추가
- ✅ **Delete**: `on_delete_in_jira_clicked` 메서드 (기존 구현 활용)
- ⚠️ **Create**: `on_create_in_jira_clicked` 메서드 (로컬 이슈 기준, 온라인 패널에서 직접 생성 기능 추가 필요)

## 애매한 부분 및 주의사항

### 1. RTM API 응답 구조 가정
**문제점:**
- 실제 RTM API 응답 구조는 버전 및 인스턴스마다 다를 수 있습니다.
- 이미지에서 본 응답 구조를 기반으로 구현했지만, 실제 환경에서는 필드명이나 구조가 다를 수 있습니다.

**해결 방안:**
- `jira_mapping.py`의 매핑 함수들을 실제 환경에 맞게 수정
- REST API Tester를 사용하여 실제 응답 구조 확인 후 조정

### 2. Priority 및 Status 필드 처리
**문제점:**
- RTM API에서 priority와 status는 객체 형태 `{id: ..., name: "..."}`로 제공됩니다.
- 생성/수정 시에도 객체 형태가 필요한지, 문자열만으로도 되는지 불명확합니다.

**현재 구현:**
- GET 응답: `priority.name` 또는 `status.name` 추출
- POST/PUT payload: 문자열인 경우 `{name: "..."}` 형태로 변환

**주의사항:**
- 실제 환경에서 id가 필요한 경우 추가 수정 필요

### 3. Test Case Steps 형식
**문제점:**
- RTM API에서 steps는 2차원 배열 `[[{value: "..."}], [{value: "..."}], ...]` 형태입니다.
- 로컬 형식은 `[{order_no, action, input, expected}]` 형태입니다.

**현재 구현:**
- GET: 2차원 배열을 1차원 배열로 변환, HTML 태그 제거
- PUT: 1차원 배열을 2차원 배열로 변환, HTML 태그 추가

**주의사항:**
- HTML 태그 처리 방식이 실제 RTM 환경과 다를 수 있음
- input, expected 필드가 RTM에서 어떻게 처리되는지 불명확

### 4. Test Plan includedTestCases 업데이트
**문제점:**
- Test Plan의 includedTestCases는 별도 API로 관리될 수 있습니다.
- 현재는 payload에 포함하여 업데이트하지만, 실제로는 `/rest/rtm/1.0/api/test-plan/{testKey}/testcases` 같은 별도 엔드포인트가 있을 수 있습니다.

**현재 구현:**
- payload에 `includedTestCases` 배열 포함
- 별도 API가 있는 경우 `jira_api.py`의 `update_testplan_testcases` 메서드 사용

### 5. Test Execution testCaseExecutions 업데이트
**문제점:**
- Test Execution의 testCaseExecutions도 별도 API로 관리될 수 있습니다.
- 현재는 payload에 포함하여 업데이트하지만, 실제로는 `/rest/rtm/1.0/api/test-execution/{testKey}/testcases` 같은 별도 엔드포인트가 있을 수 있습니다.

**현재 구현:**
- payload에 `testCaseExecutions` 배열 포함
- 별도 API가 있는 경우 `jira_api.py`의 `update_testexecution_testcases` 메서드 사용

### 6. Requirement testCasesCovered 업데이트
**문제점:**
- Requirement의 testCasesCovered는 어떻게 업데이트하는지 불명확합니다.
- 별도 API가 있을 수 있지만, 현재는 payload에 포함하는 방식만 구현했습니다.

**현재 구현:**
- payload에 `testCasesCovered` 배열 포함
- 실제 환경에서 별도 API가 있는 경우 추가 구현 필요

### 7. Defect identifyingTestCases 업데이트
**문제점:**
- Defect의 identifyingTestCases도 어떻게 업데이트하는지 불명확합니다.

**현재 구현:**
- payload에 `identifyingTestCases` 배열 포함
- 실제 환경에서 별도 API가 있는 경우 추가 구현 필요

### 8. Parent Test Key 처리
**문제점:**
- 이슈 생성 시 `parentTestKey`를 어떻게 결정할지 불명확합니다.
- 온라인 트리에서 폴더를 선택한 상태에서 새 이슈를 생성하는 경우, 해당 폴더의 testKey를 parentTestKey로 사용해야 할 수 있습니다.

**현재 구현:**
- `build_rtm_payload` 함수에 `parent_test_key` 파라미터 추가
- 실제 사용 시 온라인 트리에서 선택된 폴더의 testKey를 전달해야 함

### 9. Assignee ID 형식
**문제점:**
- RTM API에서 assigneeId는 사용자 ID 문자열 (예: "JIRAUSER296958")인 것으로 보입니다.
- 로컬에서는 assignee가 displayName일 수 있어 변환이 필요할 수 있습니다.

**현재 구현:**
- assignee 문자열을 그대로 assigneeId로 사용
- 실제 환경에서 사용자 ID 조회가 필요한 경우 추가 구현 필요

### 10. 온라인 이슈 생성 UI
**문제점:**
- 현재 `on_create_in_jira_clicked`는 로컬 이슈를 기준으로 생성합니다.
- 온라인 패널에서 직접 새 이슈를 생성하는 UI가 없습니다.

**해결 방안:**
- 온라인 패널의 "Create in JIRA" 버튼 클릭 시:
  1. 새 이슈 다이얼로그 표시
  2. 이슈 타입 선택 (현재 트리 타입에 맞춤)
  3. 기본 필드 입력 (summary, description 등)
  4. RTM API로 생성
  5. 생성된 이슈를 트리에 표시

### 11. 온라인 이슈 저장 버튼 연결
**문제점:**
- `on_save_online_issue_clicked` 메서드를 추가했지만, UI 버튼과 연결되지 않았습니다.

**해결 방안:**
- 온라인 패널의 이슈 탭에 "Save" 버튼 추가
- 또는 기존 "Save" 버튼이 온라인 이슈인 경우 `on_save_online_issue_clicked` 호출

### 12. 에러 처리 및 사용자 피드백
**주의사항:**
- RTM API 호출 실패 시 적절한 에러 메시지 표시
- 네트워크 오류, 인증 오류, 권한 오류 등 구분하여 처리
- 부분 업데이트 실패 시 롤백 또는 부분 성공 메시지 표시

## 테스트 권장 사항

1. **각 이슈 타입별 GET 테스트**
   - 온라인 트리에서 각 이슈 타입의 이슈를 선택하여 상세 정보가 올바르게 표시되는지 확인

2. **각 이슈 타입별 UPDATE 테스트**
   - 이슈 필드 수정 후 저장하여 RTM API로 올바르게 업데이트되는지 확인

3. **각 이슈 타입별 CREATE 테스트**
   - 새 이슈 생성 후 트리에 올바르게 표시되는지 확인

4. **각 이슈 타입별 DELETE 테스트**
   - 이슈 삭제 후 트리에서 사라지는지 확인

5. **관계 데이터 테스트**
   - Test Plan의 includedTestCases
   - Test Execution의 testCaseExecutions
   - Requirement의 testCasesCovered
   - Defect의 identifyingTestCases
   - Test Case의 steps

## 추가 구현 필요 사항

1. ✅ 온라인 이슈 저장 메서드 (`on_save_online_issue_clicked`)
2. ⚠️ 온라인 패널에서 새 이슈 생성 UI 및 로직
3. ⚠️ 온라인 이슈 저장 버튼 연결
4. ⚠️ 실제 RTM 환경 테스트 및 필드명/구조 조정
5. ⚠️ 에러 처리 강화
6. ⚠️ 부분 업데이트 실패 시 롤백 로직

## 참고 사항

- RTM API 엔드포인트는 `jira_config.json`의 `endpoints` 섹션에서 커스터마이징 가능
- 실제 RTM 버전 및 인스턴스에 맞게 `jira_mapping.py`의 매핑 함수들을 수정해야 함
- REST API Tester를 사용하여 실제 API 응답 구조 확인 권장

