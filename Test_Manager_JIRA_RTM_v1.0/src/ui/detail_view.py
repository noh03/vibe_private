from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QFormLayout, 
    QLineEdit, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem, 
    QPushButton, QHBoxLayout, QHeaderView, QDateEdit, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from datetime import datetime

class IssueDetailView(QWidget):
    add_link_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_issue_type = "Requirement"
        self.current_issue_id = None
        self.current_issue_data = {}
        self.layout = QVBoxLayout(self)
        
        # Top Header (Title & Toolbar)
        self.header_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.cancel_btn = QPushButton("Cancel")
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.save_btn)
        self.header_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(self.header_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Initialize Tabs
        self.init_tabs()

    def init_tabs(self):
        # 1. Details Tab
        self.details_tab = QWidget()
        self.setup_details_tab()
        self.tabs.addTab(self.details_tab, "Details")
        
        # 2. Steps Tab (For Test Cases)
        self.steps_tab = QWidget()
        self.setup_steps_tab()
        self.tabs.addTab(self.steps_tab, "Steps")
        
        # 3. Relations Tab
        self.relations_tab = QWidget()
        self.setup_relations_tab()
        self.tabs.addTab(self.relations_tab, "Relations")
        
        # 4. Execution Tab (For Test Execution)
        self.execution_tab = QWidget()
        self.setup_execution_tab()
        self.tabs.addTab(self.execution_tab, "Execution")
        
        # Hide type-specific tabs initially
        self.tabs.setTabVisible(1, False)
        self.tabs.setTabVisible(3, False)

    def setup_details_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QFormLayout(content_widget)
        
        # --- Basic Info ---
        self.key_label = QLabel("NEW")
        self.summary_edit = QLineEdit()
        self.issue_type_combo = QComboBox()
        self.issue_type_combo.addItems(["Requirement", "Test Case", "Test Plan", "Test Execution", "Defect", "Folder"])
        self.issue_type_combo.setEnabled(False)
        self.issue_type_combo.currentTextChanged.connect(self.on_issue_type_changed)

        layout.addRow("Key:", self.key_label)
        layout.addRow("Issue Type:", self.issue_type_combo)
        layout.addRow("Summary:", self.summary_edit)
        
        # --- Description ---
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        layout.addRow("Description:", self.description_edit)

        # --- Fields Group ---
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
        
        # New Fields
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
        
        # Main Details Layout
        details_layout = QVBoxLayout(self.details_tab)
        details_layout.addWidget(scroll)

    def setup_steps_tab(self):
        layout = QVBoxLayout(self.steps_tab)
        
        # Preconditions
        layout.addWidget(QLabel("Preconditions:"))
        self.preconditions_edit = QTextEdit()
        self.preconditions_edit.setMaximumHeight(60)
        layout.addWidget(self.preconditions_edit)
        
        # Steps Table
        layout.addWidget(QLabel("Test Steps:"))
        self.steps_table = QTableWidget(0, 3)
        self.steps_table.setHorizontalHeaderLabels(["Action", "Input Data", "Expected Result"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.steps_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_step_btn = QPushButton("Add Step")
        add_step_btn.clicked.connect(self.add_step_row)
        remove_step_btn = QPushButton("Remove Step")
        remove_step_btn.clicked.connect(self.remove_step_row)
        
        btn_layout.addWidget(add_step_btn)
        btn_layout.addWidget(remove_step_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def setup_relations_tab(self):
        layout = QVBoxLayout(self.relations_tab)
        self.relations_list = QTableWidget(0, 3)
        self.relations_list.setHorizontalHeaderLabels(["Link Type", "Issue Key", "Summary"])
        self.relations_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.relations_list)
        
        btn_layout = QHBoxLayout()
        self.add_link_btn = QPushButton("Add Link")
        self.add_link_btn.clicked.connect(self.add_link_requested.emit)
        btn_layout.addWidget(self.add_link_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def setup_execution_tab(self):
        layout = QVBoxLayout(self.execution_tab)
        
        # Dashboard Group
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
        
        # Test Cases List (for Execution)
        layout.addWidget(QLabel("Test Cases Execution:"))
        self.exec_table = QTableWidget(0, 4)
        self.exec_table.setHorizontalHeaderLabels(["TC Key", "Summary", "Result", "Defect"])
        self.exec_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.exec_table)

    def add_step_row(self):
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        self.steps_table.setItem(row, 0, QTableWidgetItem(""))
        self.steps_table.setItem(row, 1, QTableWidgetItem(""))
        self.steps_table.setItem(row, 2, QTableWidgetItem(""))

    def remove_step_row(self):
        current_row = self.steps_table.currentRow()
        if current_row >= 0:
            self.steps_table.removeRow(current_row)

    def on_issue_type_changed(self, text):
        self.current_issue_type = text
        # Show/Hide tabs based on type
        is_test_case = (text == "Test Case")
        is_execution = (text == "Test Execution")
        
        self.tabs.setTabVisible(1, is_test_case) # Steps Tab
        self.tabs.setTabVisible(3, is_execution) # Execution Tab
        
    def load_issue_data(self, data):
        """Load data into the UI"""
        self.current_issue_id = data.get("id")
        self.current_issue_data = data
        
        key = data.get("key") or data.get("issue_key") or "NEW"
        self.key_label.setText(key)
        
        self.summary_edit.setText(data.get("summary", ""))
        self.description_edit.setText(data.get("description", ""))
        self.issue_type_combo.setCurrentText(data.get("issue_type", "Requirement"))
        
        self.status_combo.setCurrentText(data.get("status", "Open"))
        self.priority_combo.setCurrentText(data.get("priority", "Medium"))
        self.assignee_edit.setText(data.get("assignee", ""))
        self.fix_version_edit.setText(data.get("fix_version", ""))
        self.components_edit.setText(data.get("components", ""))
        self.labels_edit.setText(data.get("labels", ""))
        
        # New Fields
        self.security_edit.setText(data.get("security_level", ""))
        self.rtm_env_edit.setText(data.get("rtm_environment", ""))
        self.affects_version_edit.setText(data.get("affects_version", ""))
        
        due_date = data.get("due_date")
        if due_date:
            if isinstance(due_date, str):
                try:
                    dt = datetime.fromisoformat(due_date)
                    self.due_date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                except:
                    pass
            elif isinstance(due_date, datetime):
                self.due_date_edit.setDate(QDate(due_date.year, due_date.month, due_date.day))
        else:
             self.due_date_edit.setDate(QDate.currentDate())
        
        # Load steps if available
        if data.get("issue_type") == "Test Case" and "steps" in data and isinstance(data["steps"], list):
            self.steps_table.setRowCount(0)
            for step in data["steps"]:
                self.add_step_row()
                row = self.steps_table.rowCount() - 1
                self.steps_table.item(row, 0).setText(step.get("action", ""))
                self.steps_table.item(row, 1).setText(step.get("input", ""))
                self.steps_table.item(row, 2).setText(step.get("expected", ""))
        else:
            self.steps_table.setRowCount(0)

    def get_data(self):
        """Return dict of current UI values"""
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
        
        # Date handling
        qdate = self.due_date_edit.date()
        data["due_date"] = datetime(qdate.year(), qdate.month(), qdate.day())
        
        if self.current_issue_type == "Test Case":
            steps = []
            for row in range(self.steps_table.rowCount()):
                action_item = self.steps_table.item(row, 0)
                input_item = self.steps_table.item(row, 1)
                expected_item = self.steps_table.item(row, 2)
                
                step = {
                    "action": action_item.text() if action_item else "",
                    "input": input_item.text() if input_item else "",
                    "expected": expected_item.text() if expected_item else ""
                }
                steps.append(step)
            data["steps"] = steps
            
        return data
