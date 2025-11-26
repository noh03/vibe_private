from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout, QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor


class IssueTreeView(QWidget):
    add_issue_requested = pyqtSignal(object, str)  # parent item or None, issue_type
    delete_issue_requested = pyqtSignal(object)  # item to delete

    def __init__(self, title: str = "Tree View") -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "font-weight: bold; font-size: 14px; padding: 5px;"
        )
        self.layout.addWidget(self.title_label)

        self.tree = QTreeWidget()
        # 컬럼 헤더를 한국어로 표시
        self.tree.setHeaderLabels(["이름", "키", "상태"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        self.layout.addWidget(self.tree)

    def add_item(self, parent, data):
        item = QTreeWidgetItem(parent) if parent else QTreeWidgetItem(self.tree)
        item.setText(0, data.get("summary", "No Summary"))
        item.setText(1, data.get("key", ""))
        item.setText(2, data.get("status", ""))

        # 동기화 상태에 따른 색상 표시
        sync_status = data.get("sync_status")
        if sync_status == "dirty":
            # 로컬에서 수정되었지만 JIRA에 반영되지 않은 이슈: 주황색
            brush = QBrush(QColor("#e67e22"))
            for col in range(3):
                item.setForeground(col, brush)
        elif sync_status == "clean":
            # JIRA와 동기화된 이슈: 기본 색 (변경 없음)
            pass
        # 기타 상태(conflict 등)는 추후 필요 시 스타일링 추가 가능

        item.setData(0, Qt.ItemDataRole.UserRole, data)
        return item

    def open_menu(self, position):
        item = self.tree.itemAt(position)

        menu = QMenu()

        add_menu = menu.addMenu("이슈 추가")
        actions = {
            "Requirement": add_menu.addAction("Requirement"),
            "Test Case": add_menu.addAction("Test Case"),
            "Test Plan": add_menu.addAction("Test Plan"),
            "Test Execution": add_menu.addAction("Test Execution"),
            "Defect": add_menu.addAction("Defect"),
            "Folder": add_menu.addAction("Folder"),
        }

        delete_action = menu.addAction("이슈 삭제")

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


