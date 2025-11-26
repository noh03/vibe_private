from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal

class IssueTreeView(QWidget):
    add_issue_requested = pyqtSignal(object, str) # passes parent item or None, issue_type
    delete_issue_requested = pyqtSignal(object) # passes item to delete

    def __init__(self, title="Tree View"):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        self.layout.addWidget(self.title_label)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Key", "Status"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        self.layout.addWidget(self.tree)

    def add_item(self, parent, data):
        item = QTreeWidgetItem(parent) if parent else QTreeWidgetItem(self.tree)
        item.setText(0, data.get("summary", "No Summary"))
        item.setText(1, data.get("key", ""))
        item.setText(2, data.get("status", ""))
        
        # Store data
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        return item

    def open_menu(self, position):
        item = self.tree.itemAt(position)
        
        menu = QMenu()
        
        # Add Issue Submenu
        add_menu = menu.addMenu("Add Issue")
        actions = {
            "Requirement": add_menu.addAction("Requirement"),
            "Test Case": add_menu.addAction("Test Case"),
            "Test Plan": add_menu.addAction("Test Plan"),
            "Test Execution": add_menu.addAction("Test Execution"),
            "Defect": add_menu.addAction("Defect"),
            "Folder": add_menu.addAction("Folder")
        }
        
        delete_action = menu.addAction("Delete Issue")
        
        if not item:
            delete_action.setEnabled(False)
            
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == delete_action and item:
            self.delete_issue_requested.emit(item)
        else:
            for type_name, act in actions.items():
                if action == act:
                    self.add_issue_requested.emit(item, type_name)
                    break
