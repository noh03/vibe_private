from sqlalchemy.orm import Session
from .db_manager import db_manager
from .models import Requirement, TestCase, TestPlan, TestExecution, Defect, IssueLink
from typing import List, Dict, Any, Optional, Type

class IssueRepository:
    def __init__(self):
        self.db = db_manager

    def _get_model_class(self, issue_type: str) -> Type:
        """Map issue type string to SQLAlchemy Model class"""
        mapping = {
            "Requirement": Requirement,
            "Test Case": TestCase,
            "Test Plan": TestPlan,
            "Test Execution": TestExecution,
            "Defect": Defect,
            "Folder": Requirement # Treat folders as Requirements for simplicity or handle separately
        }
        return mapping.get(issue_type, Requirement)

    def create_issue(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue in the DB"""
        session = self.db.get_session()
        try:
            issue_type = data.get("issue_type", "Requirement")
            ModelClass = self._get_model_class(issue_type)
            
            # Basic filtering of keys
            valid_keys = [c.key for c in ModelClass.__table__.columns]
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            
            new_issue = ModelClass(**filtered_data)
            session.add(new_issue)
            session.commit()
            session.refresh(new_issue)
            
            # Return dict representation
            return {c.name: getattr(new_issue, c.name) for c in new_issue.__table__.columns}
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_issue(self, issue_id: int, issue_type: str, data: Dict[str, Any]):
        """Update existing issue"""
        session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if issue:
                for key, value in data.items():
                    if hasattr(issue, key):
                        setattr(issue, key, value)
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_issue(self, issue_id: int, issue_type: str):
        session = self.db.get_session()
        try:
            ModelClass = self._get_model_class(issue_type)
            issue = session.query(ModelClass).filter(ModelClass.id == issue_id).first()
            if issue:
                session.delete(issue)
                session.commit()
        finally:
            session.close()

    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Fetch all issues from all tables to build the tree"""
        session = self.db.get_session()
        results = []
        try:
            # Iterate over all types
            for cls in [Requirement, TestCase, TestPlan, TestExecution, Defect]:
                items = session.query(cls).all()
                for item in items:
                    # Convert to dict
                    item_dict = {c.name: getattr(item, c.name) for c in item.__table__.columns}
                    # Add helper field to identify type later if issue_type is generic
                    if 'issue_type' not in item_dict or not item_dict['issue_type']:
                         item_dict['issue_type'] = "Requirement" if cls == Requirement else "Test Case"
                    results.append(item_dict)
            return results
        finally:
            session.close()

    def add_link(self, source_key: str, target_key: str, link_type: str):
        session = self.db.get_session()
        try:
            link = IssueLink(source_key=source_key, target_key=target_key, link_type=link_type)
            session.add(link)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_links(self, issue_key: str) -> List[Dict[str, Any]]:
        session = self.db.get_session()
        try:
            links = session.query(IssueLink).filter(
                (IssueLink.source_key == issue_key) | (IssueLink.target_key == issue_key)
            ).all()
            
            results = []
            for link in links:
                other_key = link.target_key if link.source_key == issue_key else link.source_key
                direction = "Outward" if link.source_key == issue_key else "Inward"
                
                results.append({
                    "id": link.id,
                    "link_type": link.link_type,
                    "other_key": other_key,
                    "direction": direction
                })
            return results
        finally:
            session.close()

issue_repository = IssueRepository()
