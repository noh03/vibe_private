from PyQt6.QtWidgets import QMainWindow, QSplitter, QWidget, QVBoxLayout, QToolBar, QFileDialog, QMessageBox, QToolButton, QHBoxLayout, QPushButton, QMenu, QTableWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from .tree_view import IssueTreeView
from .detail_view import IssueDetailView
from .settings_dialog import JiraSettingsDialog
from .link_dialog import LinkIssueDialog
from utils.excel_manager import excel_manager
from database.repository import issue_repository
from api.jira_client import JiraRTMClient
import random

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JIRA RTM Manager")
        self.resize(1400, 900)
        
        self.jira_client = None
        self.init_toolbar()
        self.init_ui()

    def init_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        sync_action = QAction("Sync with JIRA", self)
        sync_action.triggered.connect(self.sync_with_jira)
        toolbar.addAction(sync_action)
        
        toolbar.addSeparator()
        
        import_action = QAction("Import Excel", self)
        import_action.triggered.connect(self.import_excel)
        toolbar.addAction(import_action)
        
        export_action = QAction("Export Excel", self)
        export_action.triggered.connect(self.export_excel)
        toolbar.addAction(export_action)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Main Splitter (Left: Local, Right: Remote)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # --- Local Panel (Left) ---
        self.local_container = QSplitter(Qt.Orientation.Vertical)
        
        # [New] Local Panel Container Widget to hold Buttons + Tree
        local_top_widget = QWidget()
        local_top_layout = QVBoxLayout(local_top_widget)
        local_top_layout.setContentsMargins(0, 0, 0, 0)
        
        # [New] Button Toolbar
        btn_layout = QHBoxLayout()
        
        # Add Button with Menu
        self.add_btn = QToolButton()
        self.add_btn.setText("➕ Add Issue")
        self.add_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        
        add_menu = QMenu(self.add_btn)
        for type_name in ["Requirement", "Test Case", "Test Plan", "Test Execution", "Defect", "Folder"]:
            action = add_menu.addAction(type_name)
            action.triggered.connect(lambda checked, t=type_name: self.add_local_issue_btn(t))
        self.add_btn.setMenu(add_menu)
        
        # Delete Button
        self.del_btn = QPushButton("🗑️ Delete Issue")
        self.del_btn.setStyleSheet("padding: 5px;")
        self.del_btn.clicked.connect(self.delete_local_issue_btn)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        
        local_top_layout.addLayout(btn_layout)
        
        self.local_tree = IssueTreeView("Local Data")
        local_top_layout.addWidget(self.local_tree)
        
        self.local_detail = IssueDetailView()
        
        self.local_container.addWidget(local_top_widget)
        self.local_container.addWidget(self.local_detail)
        self.main_splitter.addWidget(self.local_container)
        
        # --- Remote Panel (Right) ---
        self.remote_container = QSplitter(Qt.Orientation.Vertical)
        self.remote_tree = IssueTreeView("JIRA Online Data")
        self.remote_detail = IssueDetailView()
        self.remote_container.addWidget(self.remote_tree)
        self.remote_container.addWidget(self.remote_detail)
        self.main_splitter.addWidget(self.remote_container)
        
        # Set initial sizes
        self.main_splitter.setSizes([700, 700])

        # Connect Signals
        self.local_tree.tree.itemClicked.connect(self.on_local_tree_clicked)
        self.local_tree.add_issue_requested.connect(self.add_local_issue)
        self.local_tree.delete_issue_requested.connect(self.delete_local_issue)
        
        self.local_detail.save_btn.clicked.connect(self.save_local_issue)
        self.local_detail.add_link_requested.connect(self.open_link_dialog)
        
        # Initial Load
        self.refresh_local_tree()

    def sync_with_jira(self):
        # Open Settings Dialog
        dialog = JiraSettingsDialog(self)
        if dialog.exec():
            url, token = dialog.get_settings()
            if not url or not token:
                QMessageBox.warning(self, "Warning", "Please provide JIRA URL and Token.")
                return
                
            try:
                self.jira_client = JiraRTMClient(url, token)
                # Optional: Validate connection
                # if not self.jira_client.test_connection(): ...

                QMessageBox.information(self, "Info", "Connected! Fetching Tree...")
                
                # Fetch Tree (Project ID from spec: 41500)
                tree_data = self.jira_client.get_tree_structure(41500)
                
                # Populate Remote Tree
                self.remote_tree.tree.clear()
                self.populate_remote_tree(tree_data)
                QMessageBox.information(self, "Success", "JIRA Tree Synced.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Sync failed: {e}")

    def populate_remote_tree(self, data):
        if isinstance(data, list):
            for item in data:
                self.add_remote_item(None, item)
        elif isinstance(data, dict):
            if 'roots' in data:
                for item in data['roots']:
                    self.add_remote_item(None, item)
            else:
                self.add_remote_item(None, data)

    def add_remote_item(self, parent, item_data):
        name = item_data.get("name") or item_data.get("summary") or "No Name"
        key = item_data.get("issueKey") or item_data.get("key") or str(item_data.get("id", ""))
        status = item_data.get("status", "")
        
        ui_data = {"summary": name, "key": key, "status": status}
        tree_item = self.remote_tree.add_item(parent, ui_data)
        
        if "children" in item_data and isinstance(item_data["children"], list):
            for child in item_data["children"]:
                self.add_remote_item(tree_item, child)

    def refresh_local_tree(self):
        self.local_tree.tree.clear()
        issues = issue_repository.get_all_issues()
        issues.sort(key=lambda x: x.get('id', 0))
        
        for data in issues:
            if 'issue_key' in data:
                data['key'] = data['issue_key']
            self.local_tree.add_item(None, data)

    def add_local_issue(self, parent_item, issue_type):
        # Called from Context Menu
        self._create_issue_logic(issue_type)

    def add_local_issue_btn(self, issue_type):
        # Called from Top Button
        self._create_issue_logic(issue_type)

    def _create_issue_logic(self, issue_type):
        new_key = f"NEW-{random.randint(1000,9999)}"
        data = {
            "issue_key": new_key,
            "summary": f"New {issue_type}",
            "issue_type": issue_type,
            "status": "Open"
        }
        try:
            issue_repository.create_issue(data)
            self.refresh_local_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create issue: {e}")
        
    def delete_local_issue(self, item):
        # Called from Context Menu
        self._delete_issue_logic(item)

    def delete_local_issue_btn(self):
        # Called from Top Button
        item = self.local_tree.tree.currentItem()
        if item:
            self._delete_issue_logic(item)
        else:
            QMessageBox.warning(self, "Warning", "No issue selected to delete.")

    def _delete_issue_logic(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and "id" in data:
            confirm = QMessageBox.question(self, "Confirm", f"Delete {data.get('key')}?")
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    issue_repository.delete_issue(data["id"], data["issue_type"])
                    self.refresh_local_tree()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete issue: {e}")

    def save_local_issue(self):
        issue_id = self.local_detail.current_issue_id
        if not issue_id:
            QMessageBox.warning(self, "Warning", "No issue selected to save.")
            return
            
        data = self.local_detail.get_data()
        issue_type = self.local_detail.current_issue_type
        
        try:
            issue_repository.update_issue(issue_id, issue_type, data)
            QMessageBox.information(self, "Success", "Issue saved successfully.")
            self.refresh_local_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save issue: {e}")

    def on_local_tree_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.local_detail.load_issue_data(data)
            key = data.get("key") or data.get("issue_key")
            self.refresh_links(key)

    def open_link_dialog(self):
        current_key = self.local_detail.key_label.text()
        if not current_key or "NEW" in current_key:
            QMessageBox.warning(self, "Warning", "Save the issue first before linking.")
            return
            
        all_issues = issue_repository.get_all_issues()
        filtered = [i for i in all_issues if i.get('issue_key') != current_key and i.get('key') != current_key]
        
        dialog = LinkIssueDialog(filtered, self)
        if dialog.exec():
            target_issue, link_type = dialog.get_data()
            if target_issue:
                target_key = target_issue.get('issue_key', target_issue.get('key'))
                try:
                    issue_repository.add_link(current_key, target_key, link_type)
                    QMessageBox.information(self, "Success", "Link created.")
                    self.refresh_links(current_key)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to link: {e}")

    def refresh_links(self, key):
        if not key: return
        links = issue_repository.get_links(key)
        
        self.local_detail.relations_list.setRowCount(0)
        for link in links:
            row = self.local_detail.relations_list.rowCount()
            self.local_detail.relations_list.insertRow(row)
            
            self.local_detail.relations_list.setItem(row, 0, QTableWidgetItem(link['link_type']))
            self.local_detail.relations_list.setItem(row, 1, QTableWidgetItem(link['other_key']))
            self.local_detail.relations_list.setItem(row, 2, QTableWidgetItem(link['direction']))

    def export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            issues = issue_repository.get_all_issues()
            steps = []
            for issue in issues:
                if issue.get("steps"):
                    for step in issue["steps"]:
                        step_row = step.copy()
                        step_row["key"] = issue.get("issue_key")
                        steps.append(step_row)
            try:
                excel_manager.export_data(issues, steps, file_path)
                QMessageBox.information(self, "Success", "Export completed successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                data = excel_manager.import_data(file_path)
                count = 0
                for issue_data in data.get('issues', []):
                    if 'key' in issue_data and 'issue_key' not in issue_data:
                        issue_data['issue_key'] = issue_data['key']
                    
                    if issue_data.get('issue_type') == 'Test Case':
                        related_steps = [s for s in data.get('steps', []) if s.get('key') == issue_data.get('key')]
                        issue_data['steps'] = related_steps
                        
                    issue_repository.create_issue(issue_data)
                    count += 1
                
                QMessageBox.information(self, "Success", f"Imported {count} issues.")
                self.refresh_local_tree()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")
