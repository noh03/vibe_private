from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class IssueBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # JIRA Key (e.g. PROJ-123)
    summary: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Common Metadata
    project_id: Mapped[int] = mapped_column(Integer, nullable=True)
    issue_type: Mapped[str] = mapped_column(String(50)) # Requirement, Test Case, etc.
    status: Mapped[Optional[str]] = mapped_column(String(50))
    priority: Mapped[Optional[str]] = mapped_column(String(50))
    assignee: Mapped[Optional[str]] = mapped_column(String(100))
    reporter: Mapped[Optional[str]] = mapped_column(String(100))
    
    # For Tree Structure
    parent_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) 
    folder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Extended Fields from Spec
    security_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rtm_environment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    labels: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    affects_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Dynamic/Extra Fields stored as JSON
    custom_fields: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)

class Requirement(IssueBase):
    __tablename__ = "requirements"
    
    fix_version: Mapped[Optional[str]] = mapped_column(String(50))
    components: Mapped[Optional[str]] = mapped_column(String(255))

class TestCase(IssueBase):
    __tablename__ = "test_cases"
    
    # Steps: [{step, data, expected_result}, ...]
    steps: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text)

class TestPlan(IssueBase):
    __tablename__ = "test_plans"
    
    target_env: Mapped[Optional[str]] = mapped_column(String(100))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

class TestExecution(IssueBase):
    __tablename__ = "test_executions"
    
    test_plan_key: Mapped[Optional[str]] = mapped_column(String(50)) # Link to TestPlan
    result: Mapped[Optional[str]] = mapped_column(String(50)) # PASS, FAIL, etc.
    executed_by: Mapped[Optional[str]] = mapped_column(String(100))
    execution_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    test_case_snapshot: Mapped[Optional[Dict]] = mapped_column(JSON)

class Defect(IssueBase):
    __tablename__ = "defects"
    
    severity: Mapped[Optional[str]] = mapped_column(String(50))
    environment: Mapped[Optional[str]] = mapped_column(String(100))

class IssueLink(Base):
    __tablename__ = "issue_links"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(50), nullable=False)
    target_key: Mapped[str] = mapped_column(String(50), nullable=False)
    link_type: Mapped[str] = mapped_column(String(50)) # e.g., "tests", "blocks"
