"""
bulk_create.py - 대량 이슈 생성 모듈

로컬 DB의 이슈들을 JIRA RTM에 대량으로 생성하는 기능을 제공합니다.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Callable, Any as AnyType
from rtm_local_manager.backend import jira_mapping
from rtm_local_manager.backend.db import update_issue_fields


def bulk_create_issues_in_jira(
    conn,
    issues: List[Dict[str, Any]],
    jira_client,
    project_key: str,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, Any]:
    """
    여러 로컬 이슈를 JIRA RTM에 일괄 생성합니다.
    
    Args:
        conn: SQLite 연결
        issues: 생성할 이슈 목록 (dict 리스트)
        jira_client: JiraRTMClient 인스턴스
        project_key: 프로젝트 키
        progress_cb: 진행 상황 콜백 함수 (message, current, total)
    
    Returns:
        {
            "success_count": int,
            "failure_count": int,
            "successes": List[Dict[str, Any]],  # {issue_id, jira_key, summary}
            "failures": List[Dict[str, Any]]     # {issue_id, summary, error}
        }
    """
    total = len(issues)
    success_count = 0
    failure_count = 0
    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    
    if progress_cb:
        progress_cb(f"대량 생성 시작: {total}개 이슈", 0, total)
    
    for idx, issue in enumerate(issues, start=1):
        issue_id = issue.get("id")
        issue_type = issue.get("issue_type", "").upper()
        summary = issue.get("summary", "")
        
        if progress_cb:
            progress_cb(
                f"생성 중: {issue_type} - {summary[:50]}... ({idx}/{total})",
                idx - 1,
                total
            )
        
        try:
            # 부모 폴더의 testKey 가져오기 (folder_id가 있으면)
            parent_test_key = None
            folder_id = issue.get("folder_id")
            if folder_id:
                # 폴더의 testKey를 가져오려면 폴더 조회가 필요하지만,
                # 현재는 폴더 정보가 없으므로 None으로 설정
                # TODO: 폴더의 testKey 조회 로직 추가
                pass
            
            # RTM Payload 생성
            payload = jira_mapping.build_rtm_payload(
                issue_type,
                issue,
                parent_test_key,
                project_key
            )
            
            # 필수 필드 검증
            if not payload.get("summary"):
                raise ValueError("Summary is required")
            
            # API 호출
            resp = jira_client.create_entity(issue_type, payload)
            
            # 응답에서 생성된 키 추출
            new_key = None
            if isinstance(resp, dict):
                new_key = (
                    resp.get("testKey") or
                    resp.get("issueKey") or
                    resp.get("key") or
                    resp.get("jiraKey")
                )
            
            if not new_key:
                raise ValueError(f"Failed to get issue key from response: {resp}")
            
            # 로컬 DB에 jira_key 업데이트
            update_issue_fields(conn, issue_id, {"jira_key": new_key})
            
            success_count += 1
            successes.append({
                "issue_id": issue_id,
                "jira_key": new_key,
                "summary": summary,
                "issue_type": issue_type,
            })
            
            if progress_cb:
                progress_cb(
                    f"✅ 생성 완료: {new_key} - {summary[:50]}...",
                    idx,
                    total
                )
        
        except Exception as e:
            failure_count += 1
            error_msg = str(e)
            failures.append({
                "issue_id": issue_id,
                "summary": summary,
                "issue_type": issue_type,
                "error": error_msg,
            })
            
            if progress_cb:
                progress_cb(
                    f"❌ 생성 실패: {summary[:50]}... - {error_msg}",
                    idx,
                    total
                )
    
    result = {
        "success_count": success_count,
        "failure_count": failure_count,
        "successes": successes,
        "failures": failures,
    }
    
    if progress_cb:
        progress_cb(
            f"대량 생성 완료: 성공 {success_count}개, 실패 {failure_count}개",
            total,
            total
        )
    
    return result

