"""
create_issue_dialog.py - 새 JIRA 이슈 생성 다이얼로그

온라인 패널에서 각 이슈 타입별로 새 이슈를 생성할 수 있는 다이얼로그를 제공합니다.
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

from rtm_local_manager.backend import jira_mapping


class CreateIssueDialog(QDialog):
    """
    새 JIRA 이슈 생성 다이얼로그
    
    이슈 타입별로 필요한 필드를 표시하고, 사용자 입력을 수집하여
    JIRA RTM API로 새 이슈를 생성합니다.
    """
    
    def __init__(
        self,
        issue_type: str,
        project_key: str,
        parent_test_key: Optional[str] = None,
        jira_client=None,
        parent=None
    ):
        super().__init__(parent)
        self.issue_type = issue_type.upper()
        self.project_key = project_key
        self.parent_test_key = parent_test_key
        self.jira_client = jira_client
        self.created_key: Optional[str] = None
        
        self.setWindowTitle(f"Create New {issue_type}")
        self.setMinimumWidth(500)
        
        self._init_ui()
    
    def _init_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 프로젝트 정보 표시
        info_label = QLabel(f"Project: {self.project_key}")
        if self.parent_test_key:
            info_label.setText(f"Project: {self.project_key} | Parent: {self.parent_test_key}")
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
        self.ed_assignee.setPlaceholderText("Assignee ID (optional)")
        form_layout.addRow("Assignee ID:", self.ed_assignee)
        
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
        
        # Versions
        self.ed_versions = QLineEdit()
        self.ed_versions.setPlaceholderText("Comma-separated versions (optional)")
        form_layout.addRow("Versions:", self.ed_versions)
        
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
            self.ed_epic_name = QLineEdit()
            self.ed_epic_name.setPlaceholderText("Epic name (optional)")
            form_layout.addRow("Epic Name:", self.ed_epic_name)
        
        # Time Estimate
        self.ed_time_estimate = QLineEdit()
        self.ed_time_estimate.setPlaceholderText("e.g., 2h 30m (optional)")
        form_layout.addRow("Time Estimate:", self.ed_time_estimate)
        
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
        local_issue: Dict[str, Any] = {
            "summary": summary,
            "description": self.ed_description.toPlainText().strip(),
            "assignee": self.ed_assignee.text().strip(),
            "priority": self.ed_priority.currentText().strip(),
            "status": self.ed_status.currentText().strip(),
            "labels": self.ed_labels.text().strip(),
            "components": self.ed_components.text().strip(),
            "fix_versions": self.ed_versions.text().strip(),
        }
        
        # 이슈 타입별 특수 필드
        if self.issue_type == "TEST_CASE":
            local_issue["rtm_environment"] = self.ed_environment.text().strip()
            local_issue["preconditions"] = self.ed_preconditions.toPlainText().strip()
        elif self.issue_type in ("TEST_PLAN", "TEST_EXECUTION"):
            local_issue["rtm_environment"] = self.ed_environment.text().strip()
        elif self.issue_type == "REQUIREMENT":
            local_issue["epic_link"] = self.ed_epic_name.text().strip()
        
        # Time Estimate
        time_estimate = self.ed_time_estimate.text().strip()
        if time_estimate:
            local_issue["timeEstimate"] = time_estimate
        
        # RTM Payload 생성
        try:
            payload = jira_mapping.build_rtm_payload(
                self.issue_type,
                local_issue,
                self.parent_test_key,
                self.project_key
            )
            
            # API 호출
            if not self.jira_client:
                QMessageBox.critical(self, "Error", "JIRA client is not available.")
                return
            
            resp = self.jira_client.create_entity(self.issue_type, payload)
            
            # 응답에서 생성된 키 추출
            if isinstance(resp, dict):
                self.created_key = (
                    resp.get("testKey") or
                    resp.get("issueKey") or
                    resp.get("key") or
                    resp.get("jiraKey")
                )
            
            if not self.created_key:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "Issue was created but the key could not be determined.\n"
                    f"Response: {resp}"
                )
            else:
                # 성공
                self.accept()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Creation Failed",
                f"Failed to create issue in JIRA:\n{str(e)}"
            )

