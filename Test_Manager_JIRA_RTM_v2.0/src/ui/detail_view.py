from datetime import datetime

from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
    QDateEdit,
    QGroupBox,
    QScrollArea,
)


class IssueDetailView(QWidget):
    add_link_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.current_issue_type = "Requirement"
        self.current_issue_id = None
        self.current_issue_data = {}
        self.layout = QVBoxLayout(self)

        # Header (Save/Cancel)
        self.header_layout = QHBoxLayout()
        self.save_btn = QPushButton("저장")
        self.save_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        self.cancel_btn = QPushButton("취소")
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.save_btn)
        self.header_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(self.header_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.init_tabs()

        # 버튼 동작
        self.cancel_btn.clicked.connect(self.reset_form)

    def init_tabs(self) -> None:
        # Details
        self.details_tab = QWidget()
        self.setup_details_tab()
        self.tabs.addTab(self.details_tab, "Details")

        # Steps (Test Case)
        self.steps_tab = QWidget()
        self.setup_steps_tab()
        self.tabs.addTab(self.steps_tab, "Steps")

        # Relations
        self.relations_tab = QWidget()
        self.setup_relations_tab()
        self.tabs.addTab(self.relations_tab, "Relations")

        # Execution (Test Execution)
        self.execution_tab = QWidget()
        self.setup_execution_tab()
        self.tabs.addTab(self.execution_tab, "Execution")

        self.tabs.setTabVisible(1, False)
        self.tabs.setTabVisible(3, False)

    def setup_details_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QFormLayout(content_widget)

        # Basic Info
        self.key_label = QLabel("NEW")
        self.summary_edit = QLineEdit()
        self.issue_type_combo = QComboBox()
        self.issue_type_combo.addItems(
            ["Requirement", "Test Case", "Test Plan", "Test Execution", "Defect", "Folder"]
        )
        self.issue_type_combo.setEnabled(False)
        self.issue_type_combo.currentTextChanged.connect(self.on_issue_type_changed)

        layout.addRow("Key:", self.key_label)
        layout.addRow("Issue Type:", self.issue_type_combo)
        layout.addRow("Summary:", self.summary_edit)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        layout.addRow("Description:", self.description_edit)

        # Fields
        fields_group = QGroupBox("Fields")
        fields_layout = QFormLayout()

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Open", "In Progress", "Done", "Closed"])

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])

        self.assignee_edit = QLineEdit()
        self.fix_version_edit = QLineEdit()
        self.components_edit = QLineEdit()
        self.labels_edit = QLineEdit()

        self.security_edit = QLineEdit()
        self.rtm_env_edit = QLineEdit()
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.affects_version_edit = QLineEdit()

        fields_layout.addRow("Status:", self.status_combo)
        fields_layout.addRow("Priority:", self.priority_combo)
        fields_layout.addRow("Assignee:", self.assignee_edit)
        fields_layout.addRow("Labels:", self.labels_edit)
        fields_layout.addRow("Fix Version/s:", self.fix_version_edit)
        fields_layout.addRow("Affects Version/s:", self.affects_version_edit)
        fields_layout.addRow("Component/s:", self.components_edit)
        fields_layout.addRow("Security Level:", self.security_edit)
        fields_layout.addRow("RTM Environment:", self.rtm_env_edit)
        fields_layout.addRow("Due Date:", self.due_date_edit)

        fields_group.setLayout(fields_layout)
        layout.addRow(fields_group)

        scroll.setWidget(content_widget)

        details_layout = QVBoxLayout(self.details_tab)
        details_layout.addWidget(scroll)

    def setup_steps_tab(self) -> None:
        layout = QVBoxLayout(self.steps_tab)

        layout.addWidget(QLabel("Preconditions:"))
        self.preconditions_edit = QTextEdit()
        self.preconditions_edit.setMaximumHeight(60)
        layout.addWidget(self.preconditions_edit)

        layout.addWidget(QLabel("Test Steps:"))
        self.steps_table = QTableWidget(0, 3)
        self.steps_table.setHorizontalHeaderLabels(["Action", "Input Data", "Expected Result"])
        self.steps_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.steps_table)

        btn_layout = QHBoxLayout()
        add_step_btn = QPushButton("Add Step")
        add_step_btn.clicked.connect(self.add_step_row)
        remove_step_btn = QPushButton("Remove Step")
        remove_step_btn.clicked.connect(self.remove_step_row)

        btn_layout.addWidget(add_step_btn)
        btn_layout.addWidget(remove_step_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def setup_relations_tab(self) -> None:
        layout = QVBoxLayout(self.relations_tab)
        self.relations_list = QTableWidget(0, 3)
        self.relations_list.setHorizontalHeaderLabels(["Link Type", "Issue Key", "Summary"])
        self.relations_list.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.relations_list)

        btn_layout = QHBoxLayout()
        self.add_link_btn = QPushButton("Add Link")
        self.add_link_btn.clicked.connect(self.add_link_requested.emit)
        btn_layout.addWidget(self.add_link_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def setup_execution_tab(self) -> None:
        layout = QVBoxLayout(self.execution_tab)

        dash_group = QGroupBox("Execution Dashboard")
        dash_layout = QHBoxLayout()

        self.exec_progress = QLabel("Progress: 0%")
        self.exec_result_combo = QComboBox()
        self.exec_result_combo.addItems(["In Progress", "PASS", "FAIL"])

        dash_layout.addWidget(self.exec_progress)
        dash_layout.addWidget(QLabel("Overall Result:"))
        dash_layout.addWidget(self.exec_result_combo)
        dash_layout.addStretch()
        dash_group.setLayout(dash_layout)
        layout.addWidget(dash_group)

        layout.addWidget(QLabel("Test Cases Execution:"))
        self.exec_table = QTableWidget(0, 4)
        self.exec_table.setHorizontalHeaderLabels(["TC Key", "Summary", "Result", "Defect"])
        self.exec_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.exec_table)

    def add_step_row(self) -> None:
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        self.steps_table.setItem(row, 0, QTableWidgetItem(""))
        self.steps_table.setItem(row, 1, QTableWidgetItem(""))
        self.steps_table.setItem(row, 2, QTableWidgetItem(""))

    def remove_step_row(self) -> None:
        current_row = self.steps_table.currentRow()
        if current_row >= 0:
            self.steps_table.removeRow(current_row)

    def on_issue_type_changed(self, text: str) -> None:
        self.current_issue_type = text
        self._apply_issue_type_ui(text)

    def _apply_issue_type_ui(self, issue_type: str) -> None:
        """이슈 타입별로 탭/필드 가시성과 편집 가능 여부를 제어."""
        is_requirement = issue_type == "Requirement"
        is_test_case = issue_type == "Test Case"
        is_test_plan = issue_type == "Test Plan"
        is_execution = issue_type == "Test Execution"
        is_defect = issue_type == "Defect"
        is_folder = issue_type == "Folder"

        # 탭 가시성
        self.tabs.setTabVisible(1, is_test_case)    # Steps: Test Case 전용
        self.tabs.setTabVisible(3, is_execution)    # Execution: Test Execution 전용

        # 기본: Requirement/Test Plan/Defect 등은 Details + Relations만 사용
        # (추후 필요 시 탭 추가 확장)

        # 폴더/그룹은 읽기 전용으로 취급
        readonly = is_folder
        editable_widgets = [
            self.summary_edit,
            self.description_edit,
            self.status_combo,
            self.priority_combo,
            self.assignee_edit,
            self.fix_version_edit,
            self.components_edit,
            self.labels_edit,
            self.security_edit,
            self.rtm_env_edit,
            self.due_date_edit,
            self.affects_version_edit,
            self.preconditions_edit,
            self.steps_table,
            self.exec_result_combo,
        ]
        for w in editable_widgets:
            w.setEnabled(not readonly)

        # 링크 추가 버튼도 폴더에서는 비활성화
        self.add_link_btn.setEnabled(not readonly)

        # Save 버튼도 폴더에서는 비활성화
        self.save_btn.setEnabled(not readonly)

    def load_issue_data(self, data: dict) -> None:
        self.current_issue_id = data.get("id")
        self.current_issue_data = data

        key = data.get("key") or data.get("issue_key") or "NEW"
        self.key_label.setText(key)

        self.summary_edit.setText(data.get("summary", ""))
        self.description_edit.setText(data.get("description", ""))
        issue_type = data.get("issue_type", "Requirement")
        self.issue_type_combo.setCurrentText(issue_type)
        self._apply_issue_type_ui(issue_type)

        self.status_combo.setCurrentText(data.get("status", "Open"))
        self.priority_combo.setCurrentText(data.get("priority", "Medium"))
        self.assignee_edit.setText(data.get("assignee", ""))
        self.fix_version_edit.setText(data.get("fix_version", ""))
        self.components_edit.setText(data.get("components", ""))
        self.labels_edit.setText(data.get("labels", ""))

        self.security_edit.setText(data.get("security_level", ""))
        self.rtm_env_edit.setText(data.get("rtm_environment", ""))
        self.affects_version_edit.setText(data.get("affects_version", ""))

        due_date = data.get("due_date")
        if due_date:
            if isinstance(due_date, str):
                try:
                    dt = datetime.fromisoformat(due_date)
                    self.due_date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                except Exception:
                    pass
            elif isinstance(due_date, datetime):
                self.due_date_edit.setDate(QDate(due_date.year, due_date.month, due_date.day))
        else:
            self.due_date_edit.setDate(QDate.currentDate())

        if data.get("issue_type") == "Test Case" and isinstance(data.get("steps"), list):
            self.steps_table.setRowCount(0)
            for step in data["steps"]:
                self.add_step_row()
                row = self.steps_table.rowCount() - 1
                self.steps_table.item(row, 0).setText(step.get("action", ""))
                self.steps_table.item(row, 1).setText(step.get("input", ""))
                self.steps_table.item(row, 2).setText(step.get("expected", ""))
        else:
            self.steps_table.setRowCount(0)

    def get_data(self) -> dict:
        data = {
            "summary": self.summary_edit.text(),
            "description": self.description_edit.toPlainText(),
            "issue_type": self.issue_type_combo.currentText(),
            "status": self.status_combo.currentText(),
            "priority": self.priority_combo.currentText(),
            "assignee": self.assignee_edit.text(),
            "fix_version": self.fix_version_edit.text(),
            "components": self.components_edit.text(),
            "labels": self.labels_edit.text(),
            "security_level": self.security_edit.text(),
            "rtm_environment": self.rtm_env_edit.text(),
            "affects_version": self.affects_version_edit.text(),
        }

        qdate = self.due_date_edit.date()
        data["due_date"] = datetime(qdate.year(), qdate.month(), qdate.day())

        if self.current_issue_type == "Test Case":
            steps = []
            for row in range(self.steps_table.rowCount()):
                action_item = self.steps_table.item(row, 0)
                input_item = self.steps_table.item(row, 1)
                expected_item = self.steps_table.item(row, 2)
                steps.append(
                    {
                        "action": action_item.text() if action_item else "",
                        "input": input_item.text() if input_item else "",
                        "expected": expected_item.text() if expected_item else "",
                    }
                )
            data["steps"] = steps

        return data

    def reset_form(self) -> None:
        """취소 버튼: 현재 선택된 이슈의 원본 데이터로 되돌리기."""
        if self.current_issue_data:
            # 기존 데이터를 다시 로드
            self.load_issue_data(self.current_issue_data)
        else:
            # 신규 이슈 등 데이터가 없으면 필드 초기화
            self.current_issue_id = None
            self.key_label.setText("NEW")
            self.summary_edit.clear()
            self.description_edit.clear()
            self.status_combo.setCurrentIndex(0)
            self.priority_combo.setCurrentIndex(1)  # Medium
            self.assignee_edit.clear()
            self.fix_version_edit.clear()
            self.components_edit.clear()
            self.labels_edit.clear()
            self.security_edit.clear()
            self.rtm_env_edit.clear()
            self.affects_version_edit.clear()
            self.due_date_edit.setDate(QDate.currentDate())
            self.preconditions_edit.clear()
            self.steps_table.setRowCount(0)


