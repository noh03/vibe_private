from datetime import datetime
from typing import List, Dict, Any, Type

from sqlalchemy.orm import Session

from .db_manager import db_manager
from .models import Requirement, TestCase, TestPlan, TestExecution, Defect, IssueLink


class IssueRepository:
    def __init__(self) -> None:
        self.db = db_manager

    def _get_model_class(self, issue_type: str) -> Type:
        """issue_type 문자열을 SQLAlchemy 모델 클래스로 매핑"""
        mapping = {
            "Requirement": Requirement,
            "Test Case": TestCase,
            "Test Plan": TestPlan,
            "Test Execution": TestExecution,
            "Defect": Defect,
            "Folder": Requirement,  # 단순화를 위해 Folder도 Requirement 테이블로 처리
        }
        return mapping.get(issue_type, Requirement)

    # ---------- 로컬 편집용 CRUD ----------

    def create_issue(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """로컬에서 신규 이슈 생성 (JIRA 미반영 상태: sync_status=dirty)"""
        session: Session = self.db.get_session()
        try:
            issue_type = data.get("issue_type", "Requirement")
            ModelClass = self._get_model_class(issue_type)

            valid_keys = [c.key for c in ModelClass.__table__.columns]
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}

            # 로컬에서 새로 만든 이슈는 dirty 상태로 시작
            if "sync_status" in valid_keys and "sync_status" not in filtered_data:
                filtered_data["sync_status"] = "dirty"

            new_issue = ModelClass(**filtered_data)
            session.add(new_issue)
            session.commit()
            session.refresh(new_issue)

            return {c.name: getattr(new_issue, c.name) for c in new_issue.__table__.columns}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_issue(self, issue_id: int, issue_type: str, data: Dict[str, Any]) -> None:
        """로컬에서 이슈 수정 (수정 시 sync_status=dirty 표시)"""
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if issue:
                for key, value in data.items():
                    if hasattr(issue, key):
                        setattr(issue, key, value)
                # 로컬 수정이므로 dirty 플래그
                if hasattr(issue, "sync_status"):
                    issue.sync_status = "dirty"
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_issue(self, issue_id: int, issue_type: str) -> None:
        """이슈 삭제"""
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if issue:
                session.delete(issue)
                session.commit()
        finally:
            session.close()

    def get_all_issues(self) -> List[Dict[str, Any]]:
        """트리 구성을 위해 모든 타입의 이슈를 조회"""
        session: Session = self.db.get_session()
        results: List[Dict[str, Any]] = []
        try:
            for cls in [Requirement, TestCase, TestPlan, TestExecution, Defect]:
                items = session.query(cls).all()
                for item in items:
                    item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
                    if not item_dict.get("issue_type"):
                        item_dict["issue_type"] = "Requirement" if cls == Requirement else "Test Case"
                    results.append(item_dict)
            return results
        finally:
            session.close()

    def get_issue(self, issue_id: int, issue_type: str) -> Dict[str, Any] | None:
        """단일 이슈 조회 (동기화 시 편의용)."""
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            item = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if not item:
                return None
            return {c.name: getattr(item, c.name) for c in item.__table__.columns}
        finally:
            session.close()

    # ---------- JIRA 동기화용 유틸 ----------

    def get_dirty_issues(self) -> List[Dict[str, Any]]:
        """JIRA로 동기화되지 않은(dirty) 이슈 목록 조회"""
        session: Session = self.db.get_session()
        results: List[Dict[str, Any]] = []
        try:
            for cls in [Requirement, TestCase, TestPlan, TestExecution, Defect]:
                items = session.query(cls).filter(cls.sync_status == "dirty").all()
                for item in items:
                    item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
                    if not item_dict.get("issue_type"):
                        item_dict["issue_type"] = "Requirement" if cls == Requirement else "Test Case"
                    results.append(item_dict)
            return results
        finally:
            session.close()

    def mark_issue_clean(self, issue_type: str, issue_key: str) -> None:
        """동기화 완료된 이슈를 clean 상태로 표시"""
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.issue_key == issue_key).first()
            if issue and hasattr(issue, "sync_status"):
                issue.sync_status = "clean"
                issue.last_synced_at = datetime.utcnow()
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_issue_key(self, issue_type: str, old_key: str, new_key: str) -> None:
        """
        NEW- 로 시작하는 임시 key를 JIRA에서 발급된 실제 issue key로 교체.
        - 해당 타입 테이블의 issue_key 수정
        - IssueLink 테이블에서 source/target_key 도 같이 수정
        """
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)

            issue = session.query(ModelClass).filter(ModelClass.issue_key == old_key).first()
            if issue:
                issue.issue_key = new_key

            # 링크 테이블 갱신
            links = session.query(IssueLink).filter(
                (IssueLink.source_key == old_key) | (IssueLink.target_key == old_key)
            ).all()
            for link in links:
                if link.source_key == old_key:
                    link.source_key = new_key
                if link.target_key == old_key:
                    link.target_key = new_key

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_issue_from_jira(self, issue_type: str, issue_key: str, data: Dict[str, Any]) -> None:
        """
        JIRA에서 가져온 데이터를 기준으로 issue_key 단위 upsert.
        sync_status=clean, last_synced_at=now 로 설정.
        """
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.issue_key == issue_key).first()

            now = datetime.utcnow()

            valid_keys = [c.key for c in ModelClass.__table__.columns]
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}

            filtered_data["sync_status"] = "clean"
            if "last_synced_at" in valid_keys:
                filtered_data["last_synced_at"] = now

            if issue:
                # update
                for key, value in filtered_data.items():
                    setattr(issue, key, value)
            else:
                # create
                filtered_data.setdefault("issue_key", issue_key)
                issue = ModelClass(**filtered_data)
                session.add(issue)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_issue_synced(self, issue_id: int, issue_type: str) -> None:
        """JIRA 반영 후 sync_status=clean, last_synced_at 갱신."""
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if issue:
                if hasattr(issue, "sync_status"):
                    issue.sync_status = "clean"
                if hasattr(issue, "last_synced_at"):
                    issue.last_synced_at = datetime.utcnow()
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_issue_key_and_mark_clean(self, issue_id: int, issue_type: str, new_key: str) -> None:
        """JIRA에 새로 생성된 이슈 키를 반영하고 clean 상태로 전환."""
        session: Session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if issue:
                issue.issue_key = new_key
                if hasattr(issue, "sync_status"):
                    issue.sync_status = "clean"
                if hasattr(issue, "last_synced_at"):
                    issue.last_synced_at = datetime.utcnow()
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ---------- 링크 ----------

    def add_link(self, source_key: str, target_key: str, link_type: str) -> None:
        """이슈 간 링크 추가"""
        session: Session = self.db.get_session()
        try:
            link = IssueLink(source_key=source_key, target_key=target_key, link_type=link_type)
            session.add(link)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_links(self, issue_key: str) -> List[Dict[str, Any]]:
        """특정 이슈와 연관된 링크 조회"""
        session: Session = self.db.get_session()
        try:
            links = session.query(IssueLink).filter(
                (IssueLink.source_key == issue_key) | (IssueLink.target_key == issue_key)
            ).all()

            results: List[Dict[str, Any]] = []
            for link in links:
                other_key = link.target_key if link.source_key == issue_key else link.source_key
                direction = "Outward" if link.source_key == issue_key else "Inward"

                results.append(
                    {
                        "id": link.id,
                        "link_type": link.link_type,
                        "other_key": other_key,
                        "direction": direction,
                    }
                )
            return results
        finally:
            session.close()


issue_repository = IssueRepository()
