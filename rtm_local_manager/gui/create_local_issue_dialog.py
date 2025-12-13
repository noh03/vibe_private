"""
create_local_issue_dialog.py - 새 로컬 이슈 생성 다이얼로그

로컬 패널에서 각 이슈 타입별로 새 이슈를 생성할 수 있는 다이얼로그를 제공합니다.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt

from backend.db import create_local_issue, update_issue_fields


class CreateLocalIssueDialog(QDialog):
    """
    새 로컬 이슈 생성 다이얼로그
    
    이슈 타입별로 필요한 필드를 표시하고, 사용자 입력을 수집하여
    로컬 DB에 새 이슈를 생성합니다.
    """
    
    def __init__(
        self,
        issue_type: str,
        project_id: int,
        folder_id: Optional[str] = None,
        conn=None,
        parent=None
    ):
        super().__init__(parent)
        self.issue_type = issue_type.upper()
        self.project_id = project_id
        self.folder_id = folder_id
        self.conn = conn
        self.created_issue_id: Optional[int] = None
        
        self.setWindowTitle(f"Create New {issue_type}")
        self.setMinimumWidth(500)
        
        self._init_ui()
    
    def _init_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 프로젝트 정보 표시
        info_text = f"Project ID: {self.project_id}"
        if self.folder_id:
            info_text += f" | Folder ID: {self.folder_id}"
        info_label = QLabel(info_text)
        layout.addWidget(info_label)
        
        # 폼 레이아웃
        form_layout = QFormLayout()
        
        # 필수 필드: Summary
        self.ed_summary = QLineEdit()
        self.ed_summary.setPlaceholderText("Enter summary (required)")
        form_layout.addRow("Summary *:", self.ed_summary)
        
        # Description
        self.ed_description = QTextEdit()
        self.ed_description.setMaximumHeight(100)
        self.ed_description.setPlaceholderText("Enter description")
        form_layout.addRow("Description:", self.ed_description)
        
        # Assignee
        self.ed_assignee = QLineEdit()
        self.ed_assignee.setPlaceholderText("Assignee (optional)")
        form_layout.addRow("Assignee:", self.ed_assignee)
        
        # Priority
        self.ed_priority = QComboBox()
        self.ed_priority.setEditable(True)
        self.ed_priority.addItems(["", "Lowest", "Low", "Medium", "High", "Highest"])
        form_layout.addRow("Priority:", self.ed_priority)
        
        # Status
        self.ed_status = QComboBox()
        self.ed_status.setEditable(True)
        self.ed_status.addItems(["", "To Do", "In Progress", "Done"])
        form_layout.addRow("Status:", self.ed_status)
        
        # Labels
        self.ed_labels = QLineEdit()
        self.ed_labels.setPlaceholderText("Comma-separated labels (optional)")
        form_layout.addRow("Labels:", self.ed_labels)
        
        # Components
        self.ed_components = QLineEdit()
        self.ed_components.setPlaceholderText("Comma-separated components (optional)")
        form_layout.addRow("Components:", self.ed_components)
        
        # Versions (Fix Versions)
        self.ed_fix_versions = QLineEdit()
        self.ed_fix_versions.setPlaceholderText("Comma-separated versions (optional)")
        form_layout.addRow("Fix Versions:", self.ed_fix_versions)
        
        # Affects Versions
        self.ed_affects_versions = QLineEdit()
        self.ed_affects_versions.setPlaceholderText("Comma-separated versions (optional)")
        form_layout.addRow("Affects Versions:", self.ed_affects_versions)
        
        # 이슈 타입별 특수 필드
        if self.issue_type == "TEST_CASE":
            self.ed_environment = QLineEdit()
            self.ed_environment.setPlaceholderText("Test environment (optional)")
            form_layout.addRow("Environment:", self.ed_environment)
            
            self.ed_preconditions = QTextEdit()
            self.ed_preconditions.setMaximumHeight(80)
            self.ed_preconditions.setPlaceholderText("Preconditions (optional)")
            form_layout.addRow("Preconditions:", self.ed_preconditions)
        
        elif self.issue_type in ("TEST_PLAN", "TEST_EXECUTION"):
            self.ed_environment = QLineEdit()
            self.ed_environment.setPlaceholderText("Test environment (optional)")
            form_layout.addRow("Environment:", self.ed_environment)
        
        elif self.issue_type == "REQUIREMENT":
            self.ed_epic_link = QLineEdit()
            self.ed_epic_link.setPlaceholderText("Epic link (optional)")
            form_layout.addRow("Epic Link:", self.ed_epic_link)
        
        elif self.issue_type == "DEFECT":
            # Defect 특별 필드 없음 (기본 필드만 사용)
            pass
        
        # Time Estimate
        self.ed_time_estimate = QLineEdit()
        self.ed_time_estimate.setPlaceholderText("e.g., 2h 30m (optional)")
        form_layout.addRow("Time Estimate:", self.ed_time_estimate)
        
        # Due Date
        self.ed_due_date = QLineEdit()
        self.ed_due_date.setPlaceholderText("YYYY-MM-DD (optional)")
        form_layout.addRow("Due Date:", self.ed_due_date)
        
        layout.addLayout(form_layout)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_create_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _on_create_clicked(self):
        """Create 버튼 클릭 시 처리"""
        # 필수 필드 검증
        summary = self.ed_summary.text().strip()
        if not summary:
            QMessageBox.warning(self, "Validation Error", "Summary is required.")
            self.ed_summary.setFocus()
            return
        
        # 사용자 입력 수집
        fields: Dict[str, Any] = {
            "summary": summary,
            "description": self.ed_description.toPlainText().strip(),
            "assignee": self.ed_assignee.text().strip() or None,
            "priority": self.ed_priority.currentText().strip() or None,
            "status": self.ed_status.currentText().strip() or None,
            "labels": self.ed_labels.text().strip() or None,
            "components": self.ed_components.text().strip() or None,
            "fix_versions": self.ed_fix_versions.text().strip() or None,
            "affects_versions": self.ed_affects_versions.text().strip() or None,
        }
        
        # 이슈 타입별 특수 필드
        if self.issue_type == "TEST_CASE":
            env = self.ed_environment.text().strip()
            if env:
                fields["rtm_environment"] = env
            preconditions = self.ed_preconditions.toPlainText().strip()
            if preconditions:
                fields["preconditions"] = preconditions
        elif self.issue_type in ("TEST_PLAN", "TEST_EXECUTION"):
            env = self.ed_environment.text().strip()
            if env:
                fields["rtm_environment"] = env
        elif self.issue_type == "REQUIREMENT":
            epic = self.ed_epic_link.text().strip()
            if epic:
                fields["epic_link"] = epic
        
        # Time Estimate
        time_estimate = self.ed_time_estimate.text().strip()
        if time_estimate:
            fields["timeEstimate"] = time_estimate
        
        # Due Date
        due_date = self.ed_due_date.text().strip()
        if due_date:
            fields["due_date"] = due_date
        
        # 로컬 DB에 이슈 생성
        try:
            if not self.conn:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Database connection is not available."
                )
                return
            
            # 기본 이슈 생성
            new_issue_id = create_local_issue(
                self.conn,
                project_id=self.project_id,
                issue_type=self.issue_type,
                folder_id=self.folder_id,
                summary=summary
            )
            
            # 추가 필드 업데이트
            update_fields = {k: v for k, v in fields.items() if v is not None and k != "summary"}
            if update_fields:
                update_issue_fields(self.conn, new_issue_id, update_fields)
            
            self.created_issue_id = new_issue_id
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Creation Failed",
                f"Failed to create local issue:\n{str(e)}"
            )

