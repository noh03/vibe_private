from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QDialogButtonBox,
    QComboBox,
    QLabel,
    QAbstractItemView,
    QHeaderView,
)


class LinkIssueDialog(QDialog):
    def __init__(self, issues, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Link Issue")
        self.resize(600, 400)
        self.selected_issue = None
        self.link_type = "Relates"

        self.layout = QVBoxLayout(self)

        self.layout.addWidget(QLabel("Link Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Relates", "Blocks", "Tests", "Caused By", "Covered By"])
        self.layout.addWidget(self.type_combo)

        self.layout.addWidget(QLabel("Select Issue to Link:"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Key", "Summary", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.layout.addWidget(self.table)

        self.populate_table(issues)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept_selection)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def populate_table(self, issues):
        self.table.setRowCount(0)
        for issue in issues:
            row = self.table.rowCount()
            self.table.insertRow(row)
            key = issue.get("issue_key", issue.get("key", ""))
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem(issue.get("summary", "")))
            self.table.setItem(row, 2, QTableWidgetItem(issue.get("issue_type", "")))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, issue)

    def accept_selection(self):
        rows = self.table.selectedItems()
        if rows:
            row = self.table.currentRow()
            self.selected_issue = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.link_type = self.type_combo.currentText()
            self.accept()

    def get_data(self):
        return self.selected_issue, self.link_type


