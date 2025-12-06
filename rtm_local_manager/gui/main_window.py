
"""
gui/main_window.py - PySide6 GUI for RTM Local Manager.

This file provides:
- MainWindow: QMainWindow with left(Local)/right(JIRA) split view
- PanelWidget: reusable panel containing tree + issue tabs
- IssueTabWidget: RTM-style tabbed issue view (wireframe)
- Simple binding from DB folder/issue tree to QTreeView using QStandardItemModel
"""

from __future__ import annotations

import sys
from typing import Dict, Any, List



from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTreeView,
    QTabWidget,
    QTabBar,
    QLabel,
    QPushButton,
    QToolBar,
    QStatusBar,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QStyle,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QButtonGroup,
    QComboBox,
    QFormLayout,
)



from backend.db import (
    get_connection,
    init_db,
    get_or_create_project,
    fetch_folder_tree,
    Project,
    get_issue_by_id,
    get_issue_by_jira_key,
    update_issue_fields,
    get_steps_for_issue,
    replace_steps_for_issue,
    get_relations_for_issue,
    replace_relations_for_issue,
    get_testplan_testcases,
    replace_testplan_testcases,
    get_or_create_testexecution_for_issue,
    update_testexecution_for_issue,
    get_testcase_executions,
    replace_testcase_executions,
    get_step_executions_for_tce,
    replace_step_executions_for_tce,
    create_local_issue,
    soft_delete_issue,
    create_folder_node,
    delete_folder_if_empty,
)
from backend import jira_mapping, excel_io

from backend.jira_api import load_config_from_file, JiraRTMClient
from backend.logger import get_logger
from backend.sync import sync_tree, map_rtm_type_to_local



class IssueTabWidget(QTabWidget):
    """
    RTM 스타일 이슈 탭(Details / Steps / Requirements / Relations / Test Cases / Executions / Defects).

    - Details 탭: Summary, Status, Priority, Assignee, Reporter, Labels, Components,
                  RTM Environment, Due Date, Description 등을 편집 가능하도록 구성
    - 나머지 탭은 현재 와이어프레임 수준(라벨만)이며, 점진적으로 구현 예정
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_issue: Dict[str, Any] | None = None
        self._current_details_columns: int = 2
        self._detail_label_widgets: list[QLabel] = []

        self.details_tab = QWidget()
        self._init_details_tab()

        self.steps_tab = QWidget()
        self._init_steps_tab()

        self.requirements_tab = QWidget()
        self._init_requirements_tab()

        self.relations_tab = QWidget()
        self._init_relations_tab()

        self.testcases_tab = QWidget()
        self._init_testcases_tab()

        self.executions_tab = QWidget()
        self._init_executions_tab()

        self.defects_tab = QWidget()
        self._init_defects_tab()

        self.addTab(self.details_tab, "Details")
        self.addTab(self.steps_tab, "Steps")
        self.addTab(self.requirements_tab, "Requirements")
        self.addTab(self.relations_tab, "Relations")
        self.addTab(self.testcases_tab, "Test Cases")
        self.addTab(self.executions_tab, "Executions")
        self.addTab(self.defects_tab, "Defects")

    # ------------------------------------------------------------------ Details

    def _init_details_tab(self):
        from PySide6.QtWidgets import (
            QGridLayout,
            QLineEdit,
            QTextEdit,
            QVBoxLayout,
            QGroupBox,
            QPushButton,
            QLabel,
        )

        main_layout = QVBoxLayout()
        self._details_grid = QGridLayout()

        # issues 테이블 스키마 기반 필드들
        self.ed_local_id = QLineEdit()
        self.ed_jira_key = QLineEdit()
        self.ed_issue_type = QLineEdit()
        self.ed_summary = QLineEdit()
        self.ed_status = QLineEdit()
        self.ed_priority = QLineEdit()
        self.ed_assignee = QLineEdit()
        self.ed_reporter = QLineEdit()
        self.ed_labels = QLineEdit()
        self.ed_components = QLineEdit()
        self.ed_security_level = QLineEdit()
        self.ed_fix_versions = QLineEdit()
        self.ed_affects_versions = QLineEdit()
        self.ed_epic_link = QLineEdit()
        self.ed_sprint = QLineEdit()
        self.ed_rtm_env = QLineEdit()
        self.ed_due_date = QLineEdit()
        self.ed_created = QLineEdit()
        self.ed_updated = QLineEdit()
        self.ed_attachments = QLineEdit()
        self.txt_description = QTextEdit()

        # 생성/수정 일시는 보통 읽기 전용
        self.ed_local_id.setReadOnly(True)
        self.ed_jira_key.setReadOnly(True)
        self.ed_issue_type.setReadOnly(True)
        self.ed_created.setReadOnly(True)
        self.ed_updated.setReadOnly(True)

        # 동적 다단 레이아웃을 위한 필드 정의 (Description 제외)
        self._details_fields: list[tuple[str, QLineEdit]] = [
            ("Local ID", self.ed_local_id),
            ("JIRA Key", self.ed_jira_key),
            ("Issue Type", self.ed_issue_type),
            ("Status", self.ed_status),
            ("Priority", self.ed_priority),
            ("Assignee", self.ed_assignee),
            ("Reporter", self.ed_reporter),
            ("RTM Environment", self.ed_rtm_env),
            ("Components", self.ed_components),
            ("Labels", self.ed_labels),
            ("Fix Versions", self.ed_fix_versions),
            ("Affects Versions", self.ed_affects_versions),
            ("Epic Link", self.ed_epic_link),
            ("Sprint", self.ed_sprint),
            ("Security Level", self.ed_security_level),
            ("Due Date", self.ed_due_date),
            ("Created", self.ed_created),
            ("Updated", self.ed_updated),
            ("Attachments", self.ed_attachments),
        ]

        # 초기에는 2단 레이아웃으로 구성
        self._current_details_columns = 2
        self._rebuild_details_grid(self._current_details_columns)
        main_layout.addLayout(self._details_grid)

        # Description 은 하단에 단일 열로 크게 배치
        main_layout.addWidget(QLabel("Description"))
        main_layout.addWidget(self.txt_description)

        # Activity (Comments / History from JIRA)
        activity_group = QGroupBox("Activity (Comments / History)")
        activity_layout = QVBoxLayout(activity_group)
        self.btn_refresh_activity = QPushButton("Load Activity from JIRA")
        self.txt_activity = QTextEdit()
        self.txt_activity.setReadOnly(True)
        self.txt_activity.setPlaceholderText("JIRA 이슈의 Comments / History 를 여기에서 조회합니다.")
        activity_layout.addWidget(self.btn_refresh_activity)
        activity_layout.addWidget(self.txt_activity)

        main_layout.addWidget(activity_group)

        self.details_tab.setLayout(main_layout)

    # ------------------------------------------------------------------ Details layout helpers (responsive columns)

    def _rebuild_details_grid(self, columns: int) -> None:
        """
        Details 상단 메타 필드를 주어진 columns 수(1~4)로 재배치한다.
        - 각 필드는 (Label, Editor) 쌍으로, 한 column 당 Label+Editor 를 차지한다.
        """
        if columns < 1:
            columns = 1
        if columns > 4:
            columns = 4

        grid = self._details_grid

        # 이전에 생성된 레이블 위젯은 완전히 제거 (레이아웃에서도, 부모 관계에서도)
        for lbl in getattr(self, "_detail_label_widgets", []):
            try:
                lbl.setParent(None)
                lbl.deleteLater()
            except Exception:
                pass
        self._detail_label_widgets = []

        # 기존 레이아웃 아이템 제거 (에디터는 나중에 다시 addWidget 으로 배치)
        while grid.count():
            grid.takeAt(0)

        # 필드 재배치
        row = 0
        col_count = columns * 2  # Label / Editor 쌍

        for idx, (label_text, editor) in enumerate(self._details_fields):
            col_group = idx % columns
            row = idx // columns
            label_col = col_group * 2
            editor_col = label_col + 1

            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lbl, row, label_col)
            grid.addWidget(editor, row, editor_col)
            self._detail_label_widgets.append(lbl)

        # 컬럼 폭 비율: label 는 좁게, field 는 넓게
        for c in range(col_count):
            if c % 2 == 0:  # label
                grid.setColumnStretch(c, 0)
            else:           # editor
                grid.setColumnStretch(c, 1)

        self._current_details_columns = columns

    def resizeEvent(self, event) -> None:
        """
        탭 위젯(각 내부 창)의 실제 폭에 따라 Details 상단 필드의 단 수(1~4단)를 동적으로 조정한다.
        """
        super().resizeEvent(event)

        # 이 IssueTabWidget 이 속한 내부 창(좌/우 패널)의 실제 폭을 기준으로 columns 결정
        details_width = self.width()

        # 폭 기준 임계값 (pixel)
        if details_width < 550:
            cols = 1
        elif details_width < 900:
            cols = 2
        elif details_width < 1300:
            cols = 3
        else:
            cols = 4

        if cols != getattr(self, "_current_details_columns", 2):
            self._rebuild_details_grid(cols)

    # ------------------------------------------------------------------ Other tabs (wireframe for now)

    def _init_steps_tab(self):
        from PySide6.QtWidgets import (
            QVBoxLayout,
            QHBoxLayout,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QLabel,
            QTextEdit,
        )

        layout = QVBoxLayout()

        # 상단 설명
        layout.addWidget(QLabel("Preconditions & Test Case Steps (Group, Order, Action, Input, Expected)"))

        # Preconditions 입력 영역
        layout.addWidget(QLabel("Preconditions"))
        self.txt_preconditions = QTextEdit()
        self.txt_preconditions.setPlaceholderText("Enter preconditions for this test case...")
        layout.addWidget(self.txt_preconditions)

        # 버튼 영역 (그룹/스텝 추가/삭제)
        btn_layout = QHBoxLayout()
        self.btn_add_group = QPushButton("Add Group")
        self.btn_delete_group = QPushButton("Delete Selected Group")
        self.btn_add_step = QPushButton("Add Step")
        self.btn_delete_step = QPushButton("Delete Selected Step")
        btn_layout.addWidget(self.btn_add_group)
        btn_layout.addWidget(self.btn_delete_group)
        btn_layout.addWidget(self.btn_add_step)
        btn_layout.addWidget(self.btn_delete_step)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 테이블: Group / Order / Action / Input / Expected
        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels(["Group", "Order", "Action", "Input", "Expected"])
        self.steps_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.steps_table)

        # 시그널
        self.btn_add_group.clicked.connect(self._on_add_group_clicked)
        self.btn_delete_group.clicked.connect(self._on_delete_group_clicked)
        self.btn_add_step.clicked.connect(self._on_add_step_clicked)
        self.btn_delete_step.clicked.connect(self._on_delete_step_clicked)

        self.steps_tab.setLayout(layout)

    # --------------------------- Steps UI helpers ---------------------------

    def _current_group_no(self) -> int:
        """현재 선택된 행의 group_no, 없으면 마지막 그룹 번호(또는 1)를 돌려준다."""
        row = self.steps_table.currentRow()
        if row >= 0:
            item = self.steps_table.item(row, 0)
            if item and item.text().strip():
                try:
                    return int(item.text())
                except ValueError:
                    pass
        # 선택이 없으면 현재 테이블에서 가장 큰 group_no 를 사용 (없으면 1)
        max_group = 0
        for r in range(self.steps_table.rowCount()):
            it = self.steps_table.item(r, 0)
            if not it or not it.text().strip():
                continue
            try:
                g = int(it.text())
                if g > max_group:
                    max_group = g
            except ValueError:
                continue
        return max_group if max_group > 0 else 1

    def _next_group_no(self) -> int:
        """새 그룹을 만들 때 사용할 group_no (현재 최대값 + 1, 없으면 1)."""
        max_group = 0
        for r in range(self.steps_table.rowCount()):
            it = self.steps_table.item(r, 0)
            if not it or not it.text().strip():
                continue
            try:
                g = int(it.text())
                if g > max_group:
                    max_group = g
            except ValueError:
                continue
        return max_group + 1 if max_group > 0 else 1

    def _renumber_orders_per_group(self) -> None:
        """각 group_no 별로 order_no 를 1부터 다시 매겨준다."""
        # group_no, row 인덱스를 모아서 그룹별로 정렬 후 order 재부여
        groups: Dict[int, List[int]] = {}
        for r in range(self.steps_table.rowCount()):
            item_group = self.steps_table.item(r, 0)
            try:
                g = int(item_group.text()) if item_group and item_group.text().strip() else 1
            except ValueError:
                g = 1
            groups.setdefault(g, []).append(r)
        for g, rows in groups.items():
            for idx, r in enumerate(rows, start=1):
                item_order = self.steps_table.item(r, 1)
                if item_order is None:
                    item_order = QTableWidgetItem(str(idx))
                    self.steps_table.setItem(r, 1, item_order)
                else:
                    item_order.setText(str(idx))

    def _on_add_group_clicked(self):
        """새 그룹을 추가하고 첫 스텝 한 줄을 만든다."""
        from PySide6.QtWidgets import QTableWidgetItem

        # 항상 새로운 그룹 번호 사용
        new_group = self._next_group_no()
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        self.steps_table.setItem(row, 0, QTableWidgetItem(str(new_group)))
        self.steps_table.setItem(row, 1, QTableWidgetItem("1"))
        self._renumber_orders_per_group()

    def _on_delete_group_clicked(self):
        """선택된 행의 group_no 에 해당하는 모든 스텝을 삭제."""
        row = self.steps_table.currentRow()
        if row < 0:
            return
        item_group = self.steps_table.item(row, 0)
        if not item_group or not item_group.text().strip():
            return
        try:
            target_group = int(item_group.text())
        except ValueError:
            return

        rows_to_delete = [r for r in range(self.steps_table.rowCount()) if
                          (self.steps_table.item(r, 0) and self.steps_table.item(r, 0).text().strip() == str(target_group))]
        for r in reversed(rows_to_delete):
            self.steps_table.removeRow(r)
        self._renumber_orders_per_group()

    def _on_add_step_clicked(self):
        """현재 그룹에 새 Step 한 줄 추가."""
        from PySide6.QtWidgets import QTableWidgetItem

        group_no = self._current_group_no()
        # 현재 그룹의 마지막 행 뒤에 삽입
        insert_row = self.steps_table.rowCount()
        for r in range(self.steps_table.rowCount()):
            item_group = self.steps_table.item(r, 0)
            if not item_group or not item_group.text().strip():
                continue
            try:
                g = int(item_group.text())
            except ValueError:
                continue
            if g > group_no and r < insert_row:
                insert_row = r
                break

        self.steps_table.insertRow(insert_row)
        self.steps_table.setItem(insert_row, 0, QTableWidgetItem(str(group_no)))
        # order_no 는 나중에 _renumber_orders_per_group 에서 재계산
        self._renumber_orders_per_group()

    def _on_delete_step_clicked(self):
        # 선택된 행 삭제 (복수 선택 시 모두 삭제).
        selected = self.steps_table.selectedIndexes()
        if not selected:
            return
        rows = sorted({idx.row() for idx in selected}, reverse=True)
        for r in rows:
            self.steps_table.removeRow(r)
        self._renumber_orders_per_group()

    # --------------------------- Steps binding helpers ---------------------------

    def load_steps(self, steps: List[Dict[str, Any]]):
        """DB 등에서 읽어온 steps 리스트를 테이블에 로드."""
        from PySide6.QtWidgets import QTableWidgetItem

        self.steps_table.setRowCount(0)
        for s in steps:
            row = self.steps_table.rowCount()
            self.steps_table.insertRow(row)
            group_val = str(s.get("group_no", 1))
            order_val = str(s.get("order_no", 1))
            self.steps_table.setItem(row, 0, QTableWidgetItem(group_val))
            self.steps_table.setItem(row, 1, QTableWidgetItem(order_val))
            self.steps_table.setItem(row, 2, QTableWidgetItem(s.get("action") or ""))
            self.steps_table.setItem(row, 3, QTableWidgetItem(s.get("input") or ""))
            self.steps_table.setItem(row, 4, QTableWidgetItem(s.get("expected") or ""))
        self._renumber_orders_per_group()

    def collect_steps(self) -> List[Dict[str, Any]]:
        """테이블의 내용을 읽어 steps 리스트로 반환."""
        steps: List[Dict[str, Any]] = []
        rows = self.steps_table.rowCount()
        for r in range(rows):
            group_item = self.steps_table.item(r, 0)
            order_item = self.steps_table.item(r, 1)
            action_item = self.steps_table.item(r, 2)
            input_item = self.steps_table.item(r, 3)
            expected_item = self.steps_table.item(r, 4)
            try:
                group_no = int(group_item.text()) if group_item and group_item.text().strip() else 1
            except ValueError:
                group_no = 1
            try:
                order_no = int(order_item.text()) if order_item and order_item.text().strip() else 1
            except ValueError:
                order_no = 1
            steps.append(
                {
                    "group_no": group_no,
                    "order_no": order_no,
                    "action": action_item.text().strip() if action_item else "",
                    "input": input_item.text().strip() if input_item else "",
                    "expected": expected_item.text().strip() if expected_item else "",
                }
            )
        return steps

    def set_preconditions_text(self, text: str) -> None:
        if hasattr(self, "txt_preconditions"):
            self.txt_preconditions.setPlainText(text or "")

    def get_preconditions_text(self) -> str:
        if hasattr(self, "txt_preconditions"):
            return self.txt_preconditions.toPlainText().strip()
        return ""

    def _init_requirements_tab(self):
        from PySide6.QtWidgets import QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Linked Requirements (read-only, derived from relations)"))

        self.requirements_table = QTableWidget()
        self.requirements_table.setColumnCount(3)
        self.requirements_table.setHorizontalHeaderLabels(["Req ID", "Jira Key", "Summary"])
        self.requirements_table.horizontalHeader().setStretchLastSection(True)
        self.requirements_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.requirements_table)

        self.requirements_tab.setLayout(layout)

    def load_requirements(self, requirements: List[Dict[str, Any]]):
        """Relations 정보에서 필터링한 Requirements 리스트를 테이블에 로드."""
        self.requirements_table.setRowCount(0)
        for req in requirements:
            row = self.requirements_table.rowCount()
            self.requirements_table.insertRow(row)
            self.requirements_table.setItem(row, 0, QTableWidgetItem(str(req.get("dst_issue_id"))))
            self.requirements_table.setItem(row, 1, QTableWidgetItem(req.get("dst_jira_key") or ""))
            self.requirements_table.setItem(row, 2, QTableWidgetItem(req.get("dst_summary") or ""))

    def _init_relations_tab(self):
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLabel

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Relations (src = current issue)"))

        btn_layout = QHBoxLayout()
        self.btn_add_relation = QPushButton("Add Relation")
        self.btn_delete_relation = QPushButton("Delete Selected Relation")
        btn_layout.addWidget(self.btn_add_relation)
        btn_layout.addWidget(self.btn_delete_relation)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.relations_table = QTableWidget()
        self.relations_table.setColumnCount(4)
        self.relations_table.setHorizontalHeaderLabels(["Relation Type", "Dst Issue ID", "Dst Jira Key", "Dst Summary"])
        self.relations_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.relations_table)

        self.btn_add_relation.clicked.connect(self._on_add_relation_clicked)
        self.btn_delete_relation.clicked.connect(self._on_delete_relation_clicked)

        self.relations_tab.setLayout(layout)

    def _on_add_relation_clicked(self):
        """
        Relations 추가 팝업:
        - 기존에 등록된 이슈 목록에서 선택 (Dst Issue)
        - Relation Type 선택
        - 또는 Web Link(URL + Text) 를 입력하여 Relations 테이블에 추가
        """
        # 메인 윈도우와 DB/프로젝트 정보 가져오기
        main_win = self.window()
        issues: List[Dict[str, Any]] = []
        if hasattr(main_win, "conn") and getattr(main_win, "project", None) is not None:
            try:
                cur = main_win.conn.cursor()
                cur.execute(
                    """
                    SELECT id, issue_type, jira_key, summary
                      FROM issues
                     WHERE project_id = ? AND is_deleted = 0
                     ORDER BY issue_type, jira_key, summary
                    """,
                    (main_win.project.id,),
                )
                rows = cur.fetchall()
                issues = [dict(row) for row in rows]
            except Exception as e:
                print(f"[WARN] Failed to load issues for relations dialog: {e}")

        dlg = QDialog(self)
        dlg.setWindowTitle("Add Relation")

        layout = QVBoxLayout(dlg)

        # 모드 선택: 이슈 / Web Link
        mode_group = QButtonGroup(dlg)
        rb_issue = QRadioButton("Link to existing issue")
        rb_weblink = QRadioButton("Web link")
        rb_issue.setChecked(True)
        mode_group.addButton(rb_issue)
        mode_group.addButton(rb_weblink)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(rb_issue)
        mode_layout.addWidget(rb_weblink)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 이슈 목록
        issue_list = QListWidget()
        for iss in issues:
            key = iss.get("jira_key") or f"ID={iss.get('id')}"
            itype = (iss.get("issue_type") or "").upper()
            summary = iss.get("summary") or ""
            text = f"[{itype}] {key}"
            if summary:
                text += f" - {summary}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, iss.get("id"))          # dst_issue_id
            item.setData(Qt.UserRole + 1, iss.get("jira_key") or "")
            item.setData(Qt.UserRole + 2, summary)
            issue_list.addItem(item)
        layout.addWidget(issue_list)

        # Web link 입력 영역
        url_layout = QFormLayout()
        url_edit = QLineEdit()
        text_edit = QLineEdit()
        url_layout.addRow("URL", url_edit)
        url_layout.addRow("Link Text", text_edit)
        layout.addLayout(url_layout)

        # Link type 선택 (JIRA issue link type 목록 사용)
        rel_type_combo = QComboBox()
        rel_type_combo.setEditable(True)
        link_type_names: List[str] = []
        if getattr(main_win, "jira_available", False) and getattr(main_win, "jira_client", None):
            try:
                link_types_json = main_win.jira_client.get_issue_link_types()
                for lt in link_types_json.get("issueLinkTypes", []):
                    name = lt.get("name")
                    if name:
                        link_type_names.append(str(name))
            except Exception as e_lt:
                print(f"[WARN] Failed to load JIRA issue link types: {e_lt}")
        # 중복 제거 및 정렬
        link_type_names = sorted(set(link_type_names))
        if not link_type_names:
            # JIRA에서 가져오지 못한 경우 기본값
            link_type_names = ["Relates", "Blocks", "Cloners", "Duplicates"]
        rel_type_combo.addItems(link_type_names + ["Web Link"])
        rel_layout = QHBoxLayout()
        # JIRA 용어에 맞게 Link Type 으로 표기
        rel_layout.addWidget(QLabel("Link Type:"))
        rel_layout.addWidget(rel_type_combo)
        layout.addLayout(rel_layout)

        # 버튼 박스
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(btn_box)

        def on_accept():
            row = self.relations_table.rowCount()
            self.relations_table.insertRow(row)

            rel_type = rel_type_combo.currentText().strip() or ""

            if rb_issue.isChecked():
                item = issue_list.currentItem()
                if not item:
                    # 선택된 이슈가 없으면 행을 추가하지 않고 종료
                    self.relations_table.removeRow(row)
                    dlg.reject()
                    return
                dst_id = item.data(Qt.UserRole)
                dst_key = item.data(Qt.UserRole + 1) or ""
                dst_summary = item.data(Qt.UserRole + 2) or ""

                self.relations_table.setItem(row, 0, QTableWidgetItem(rel_type))
                self.relations_table.setItem(row, 1, QTableWidgetItem(str(dst_id)))
                self.relations_table.setItem(row, 2, QTableWidgetItem(dst_key))
                self.relations_table.setItem(row, 3, QTableWidgetItem(dst_summary))
            else:
                # Web link 모드: 현재 DB 스키마상 dst_issue_id 기반으로만 저장되므로,
                # 우선 Relations UI 에서만 관리하고, dst_issue_id 는 비워 둔다.
                url = url_edit.text().strip()
                link_text = text_edit.text().strip() or url

                if not url:
                    self.relations_table.removeRow(row)
                    dlg.reject()
                    return

                if not rel_type:
                    rel_type = "Web Link"

                self.relations_table.setItem(row, 0, QTableWidgetItem(rel_type))
                self.relations_table.setItem(row, 1, QTableWidgetItem(""))  # dst_issue_id 비움
                self.relations_table.setItem(row, 2, QTableWidgetItem(url))
                self.relations_table.setItem(row, 3, QTableWidgetItem(link_text))

            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def _on_delete_relation_clicked(self):
        """선택된 relation 행 삭제."""
        selected = self.relations_table.selectedIndexes()
        if not selected:
            return
        rows = sorted({idx.row() for idx in selected}, reverse=True)
        for r in rows:
            self.relations_table.removeRow(r)

    # --------------------------- Relations binding helpers ---------------------------

    def load_relations(self, relations: List[Dict[str, Any]]):
        """DB에서 읽어온 relations 리스트를 테이블에 로드."""
        self.relations_table.setRowCount(0)
        for rel in relations:
            row = self.relations_table.rowCount()
            self.relations_table.insertRow(row)
            self.relations_table.setItem(row, 0, QTableWidgetItem(rel.get("relation_type") or ""))
            self.relations_table.setItem(row, 1, QTableWidgetItem(str(rel.get("dst_issue_id"))))
            self.relations_table.setItem(row, 2, QTableWidgetItem(rel.get("dst_jira_key") or ""))
            self.relations_table.setItem(row, 3, QTableWidgetItem(rel.get("dst_summary") or ""))

    def collect_relations(self) -> List[Dict[str, Any]]:
        """Relations 테이블에서 relation 리스트를 수집 (dst_issue_id, relation_type)."""
        rels: List[Dict[str, Any]] = []
        rows = self.relations_table.rowCount()
        for r in range(rows):
            type_item = self.relations_table.item(r, 0)
            dst_id_item = self.relations_table.item(r, 1)
            rel_type = type_item.text().strip() if type_item else ""
            dst_id_text = dst_id_item.text().strip() if dst_id_item else ""
            if not dst_id_text:
                continue
            try:
                dst_id = int(dst_id_text)
            except ValueError:
                continue
            rels.append(
                {
                    "relation_type": rel_type,
                    "dst_issue_id": dst_id,
                }
            )
        return rels

    def _init_testcases_tab(self):
        from PySide6.QtWidgets import (
            QVBoxLayout,
            QHBoxLayout,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QLabel,
        )

        layout = QVBoxLayout()
        # 헤더 라벨은 이슈 타입에 따라 동적으로 변경된다.
        self.lbl_testcases_header = QLabel("")
        layout.addWidget(self.lbl_testcases_header)

        btn_layout = QHBoxLayout()
        # REQUIREMENT / DEFECT 등에서 사용하는 버튼
        self.btn_cover_by_tc = QPushButton("Cover by TC...")
        self.btn_create_tc = QPushButton("Create New Test Case...")
        # TEST_PLAN 에서 사용하는 버튼
        self.btn_add_tp_tc = QPushButton("Add Test Case")
        self.btn_del_tp_tc = QPushButton("Delete Selected")
        self.btn_edit_tp_order = QPushButton("Edit order")

        btn_layout.addWidget(self.btn_cover_by_tc)
        btn_layout.addWidget(self.btn_create_tc)
        btn_layout.addWidget(self.btn_add_tp_tc)
        btn_layout.addWidget(self.btn_del_tp_tc)
        btn_layout.addWidget(self.btn_edit_tp_order)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 단일 테이블을 이슈 타입에 따라 다르게 사용한다.
        self.testplan_tc_table = QTableWidget()
        self.testplan_tc_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.testplan_tc_table)

        # 시그널 연결
        self.btn_cover_by_tc.clicked.connect(self._on_cover_by_testcase_clicked)
        self.btn_create_tc.clicked.connect(self._on_create_testcase_clicked)
        self.btn_add_tp_tc.clicked.connect(self._on_add_tp_tc_clicked)
        self.btn_del_tp_tc.clicked.connect(self._on_del_tp_tc_clicked)
        self.btn_edit_tp_order.clicked.connect(self._on_toggle_tp_order_edit)

        # Test Plan order 편집 모드 상태
        self._tp_order_edit_mode: bool = False

        self.testcases_tab.setLayout(layout)

    def _on_add_tp_tc_clicked(self):
        """
        Test Plan - Test Case 매핑에 기존 Test Case 들을 추가한다.
        (Test Plan 이슈의 Test Cases 탭에서 'Add Test Case' 버튼)
        """
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QDialogButtonBox,
            QTableWidget,
            QTableWidgetItem,
            QLabel,
        )

        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return

        if getattr(main_win, "current_issue_id", None) is None:
            main_win.status_bar.showMessage("No Test Plan selected.")
            return

        issue = get_issue_by_id(main_win.conn, main_win.current_issue_id)
        if not issue or (issue.get("issue_type") or "").upper() != "TEST_PLAN":
            main_win.status_bar.showMessage("Current issue is not a TEST_PLAN.")
            return

        # 프로젝트 내 TEST_CASE 이슈 목록 조회
        cur = main_win.conn.cursor()
        cur.execute(
            """
            SELECT id, jira_key, summary, priority, assignee, components, rtm_environment
              FROM issues
             WHERE project_id = ? AND is_deleted = 0 AND UPPER(issue_type) = 'TEST_CASE'
             ORDER BY jira_key, summary
            """,
            (main_win.project.id,),
        )
        rows = cur.fetchall()
        testcases = [dict(r) for r in rows]
        if not testcases:
            main_win.status_bar.showMessage("No TEST_CASE issues found in this project.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Add Test Case to Test Plan")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Select Test Cases to add to this Test Plan:"))

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Jira Key", "Summary", "Priority", "Assignee", "Components", "RTM Env"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.MultiSelection)

        for tc in testcases:
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            table.setItem(row_idx, 0, QTableWidgetItem(tc.get("jira_key") or ""))
            table.setItem(row_idx, 1, QTableWidgetItem(tc.get("summary") or ""))
            table.setItem(row_idx, 2, QTableWidgetItem(tc.get("priority") or ""))
            table.setItem(row_idx, 3, QTableWidgetItem(tc.get("assignee") or ""))
            table.setItem(row_idx, 4, QTableWidgetItem(tc.get("components") or ""))
            table.setItem(row_idx, 5, QTableWidgetItem(tc.get("rtm_environment") or ""))
            table.item(row_idx, 0).setData(Qt.UserRole, tc.get("id"))

        vbox.addWidget(table)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            selected_rows = {idx.row() for idx in table.selectedIndexes()}
            if not selected_rows:
                dlg.reject()
                return

            tp_id = int(main_win.current_issue_id)
            # 기존 매핑 읽기
            existing = get_testplan_testcases(main_win.conn, tp_id)
            existing_tc_ids = {
                int(r.get("testcase_id")) for r in existing if r.get("testcase_id")
            }
            records = [
                {
                    "testcase_id": int(r["testcase_id"]),
                    "order_no": int(r.get("order_no", 0) or 0),
                }
                for r in existing
            ]

            for r_idx in selected_rows:
                item = table.item(r_idx, 0)
                if not item:
                    continue
                tc_id = item.data(Qt.UserRole)
                if not tc_id or int(tc_id) in existing_tc_ids:
                    continue
                records.append({"testcase_id": int(tc_id), "order_no": 0})

            # order_no 재정렬
            for i, rec in enumerate(records, start=1):
                rec["order_no"] = i

            replace_testplan_testcases(main_win.conn, tp_id, records)

            # UI 갱신
            tp_records = get_testplan_testcases(main_win.conn, tp_id)
            if hasattr(main_win.left_panel.issue_tabs, "load_testplan_testcases"):
                main_win.left_panel.issue_tabs.load_testplan_testcases(tp_records)

            main_win.status_bar.showMessage(
                f"Added {len(selected_rows)} Test Case(s) to Test Plan."
            )
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def _on_del_tp_tc_clicked(self):
        """선택된 매핑 행 삭제 및 DB 반영."""
        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return
        if getattr(main_win, "current_issue_id", None) is None:
            main_win.status_bar.showMessage("No Test Plan selected.")
            return

        selected = self.testplan_tc_table.selectedIndexes()
        if not selected:
            return
        rows = sorted({idx.row() for idx in selected}, reverse=True)
        for r in rows:
            self.testplan_tc_table.removeRow(r)

        # 남은 행 기준으로 order_no 재계산 후 DB 갱신
        try:
            tp_records = self.collect_testplan_testcases()
            # 순서 재정렬
            for i, rec in enumerate(tp_records, start=1):
                rec["order_no"] = i
            replace_testplan_testcases(main_win.conn, int(main_win.current_issue_id), tp_records)

            # UI 재로드
            new_records = get_testplan_testcases(
                main_win.conn, int(main_win.current_issue_id)
            )
            if hasattr(main_win.left_panel.issue_tabs, "load_testplan_testcases"):
                main_win.left_panel.issue_tabs.load_testplan_testcases(new_records)
        except Exception as e:
            print(f"[WARN] Failed to delete test plan testcases: {e}")

    def _on_toggle_tp_order_edit(self):
        """
        Test Plan Test Cases 탭의 'Edit order' / 'Accept order' 토글 버튼.
        - 사용자는 Order 컬럼을 수정한 뒤, 'Accept order' 를 눌러 순서를 확정한다.
        """
        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return
        if getattr(main_win, "current_issue_id", None) is None:
            main_win.status_bar.showMessage("No Test Plan selected.")
            return

        # 첫 클릭: 편집 모드 진입
        if not self._tp_order_edit_mode:
            self._tp_order_edit_mode = True
            self.btn_edit_tp_order.setText("Accept order")
            main_win.status_bar.showMessage(
                "Edit the 'Order' column, then click 'Accept order' to save."
            )
            return

        # 두 번째 클릭: 현재 Order 값을 기준으로 순서 확정 및 DB 저장
        try:
            tp_id = int(main_win.current_issue_id)
            records = self.collect_testplan_testcases()
            # 사용자가 입력한 order_no 기준으로 정렬
            records.sort(key=lambda r: int(r.get("order_no", 0) or 0))
            # 1..N 으로 재번호 부여
            for i, rec in enumerate(records, start=1):
                rec["order_no"] = i

            replace_testplan_testcases(main_win.conn, tp_id, records)

            # UI 재로드
            new_records = get_testplan_testcases(main_win.conn, tp_id)
            if hasattr(main_win.left_panel.issue_tabs, "load_testplan_testcases"):
                main_win.left_panel.issue_tabs.load_testplan_testcases(new_records)

            main_win.status_bar.showMessage("Test Plan Test Cases order has been saved.")
        except Exception as e:
            print(f"[WARN] Failed to accept Test Plan order: {e}")
            main_win.status_bar.showMessage(f"Failed to save order: {e}")
        finally:
            self._tp_order_edit_mode = False
            self.btn_edit_tp_order.setText("Edit order")

    # --------------------------- Requirement: Cover by / Create Test Case --------

    def _on_cover_by_testcase_clicked(self):
        """
        REQUIREMENT 이슈에서 'Cover by Test Case...' 버튼을 눌렀을 때:
        - 현재 프로젝트의 TEST_CASE 이슈 목록을 보여주고
        - 선택된 Test Case 들을 현재 Requirement 와 relations 로 연결한다.
        """
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QHBoxLayout,
            QDialogButtonBox,
            QTableWidgetItem,
            QLabel,
        )

        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return

        if getattr(main_win, "current_issue_id", None) is None:
            main_win.status_bar.showMessage("No issue selected; cannot cover by test case.")
            return

        # 현재 이슈가 REQUIREMENT 인지 확인
        src_issue = get_issue_by_id(main_win.conn, main_win.current_issue_id)
        if not src_issue or (src_issue.get("issue_type") or "").upper() != "REQUIREMENT":
            main_win.status_bar.showMessage("Current issue is not a REQUIREMENT; 'Cover by Test Case' is disabled.")
            return

        # 프로젝트 내 TEST_CASE 이슈 목록 조회
        cur = main_win.conn.cursor()
        cur.execute(
            """
            SELECT id, jira_key, summary, priority, assignee, components, rtm_environment
              FROM issues
             WHERE project_id = ? AND is_deleted = 0 AND UPPER(issue_type) = 'TEST_CASE'
             ORDER BY jira_key, summary
            """,
            (main_win.project.id,),
        )
        rows = cur.fetchall()
        testcases = [dict(r) for r in rows]

        if not testcases:
            main_win.status_bar.showMessage("No TEST_CASE issues found in this project.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Cover by Test Case")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Select Test Cases to cover this Requirement:"))

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Jira Key", "Summary", "Priority", "Assignee", "Components", "RTM Env"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.MultiSelection)

        for tc in testcases:
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            table.setItem(row_idx, 0, QTableWidgetItem(tc.get("jira_key") or ""))
            table.setItem(row_idx, 1, QTableWidgetItem(tc.get("summary") or ""))
            table.setItem(row_idx, 2, QTableWidgetItem(tc.get("priority") or ""))
            table.setItem(row_idx, 3, QTableWidgetItem(tc.get("assignee") or ""))
            table.setItem(row_idx, 4, QTableWidgetItem(tc.get("components") or ""))
            table.setItem(row_idx, 5, QTableWidgetItem(tc.get("rtm_environment") or ""))
            # 내부적으로 issue_id 저장
            table.item(row_idx, 0).setData(Qt.UserRole, tc.get("id"))

        vbox.addWidget(table)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            selected_rows = {idx.row() for idx in table.selectedIndexes()}
            if not selected_rows:
                dlg.reject()
                return

            # 기존 relations 를 가져와서, 선택된 Test Case 들을 추가한 새 리스트 구성
            existing_rels = get_relations_for_issue(main_win.conn, main_win.current_issue_id)
            existing_dst_ids = {int(r.get("dst_issue_id")) for r in existing_rels if r.get("dst_issue_id")}
            new_rels = [
                {"dst_issue_id": r.get("dst_issue_id"), "relation_type": r.get("relation_type") or ""}
                for r in existing_rels
            ]

            for r in selected_rows:
                item = table.item(r, 0)
                if not item:
                    continue
                tc_id = item.data(Qt.UserRole)
                if not tc_id or tc_id in existing_dst_ids:
                    continue
                new_rels.append({"dst_issue_id": int(tc_id), "relation_type": "Tests"})

            replace_relations_for_issue(main_win.conn, main_win.current_issue_id, new_rels)

            # UI 갱신: Relations / Requirements / Linked Test Cases
            rels = get_relations_for_issue(main_win.conn, main_win.current_issue_id)
            if hasattr(main_win.left_panel.issue_tabs, "load_relations"):
                main_win.left_panel.issue_tabs.load_relations(rels)
            if hasattr(main_win.left_panel.issue_tabs, "load_requirements"):
                reqs = [
                    r for r in rels if (r.get("dst_issue_type") or "").upper() == "REQUIREMENT"
                ]
                main_win.left_panel.issue_tabs.load_requirements(reqs)
            if hasattr(main_win.left_panel.issue_tabs, "load_linked_testcases"):
                tcs = [
                    r for r in rels if (r.get("dst_issue_type") or "").upper() == "TEST_CASE"
                ]
                main_win.left_panel.issue_tabs.load_linked_testcases(tcs)

            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def _on_create_testcase_clicked(self):
        """
        REQUIREMENT 이슈에서 'Create New Test Case...' 버튼:
        - 간단한 팝업에서 Summary 등을 입력 받아
        - 동일 프로젝트 / 동일 폴더에 TEST_CASE 로컬 이슈를 생성하고
        - 현재 Requirement 와 relation 으로 연결한다.
        """
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QFormLayout,
            QLineEdit,
            QDialogButtonBox,
            QLabel,
        )

        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return
        if getattr(main_win, "current_issue_id", None) is None:
            QMessageBox.warning(
                self,
                "Create Test Case",
                "No Requirement is selected.\n\n"
                "Please select a Requirement in the left tree first.",
            )
            return

        src_issue = get_issue_by_id(main_win.conn, main_win.current_issue_id)
        if not src_issue or (src_issue.get("issue_type") or "").upper() != "REQUIREMENT":
            QMessageBox.warning(
                self,
                "Create Test Case",
                "Current issue is not a REQUIREMENT.\n\n"
                "Select a Requirement in the tree to create a Test Case linked to it.",
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Create New Test Case")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("New Test Case will be created as local-only issue linked to this Requirement."))

        form = QFormLayout()
        ed_summary = QLineEdit()
        ed_summary.setPlaceholderText("Summary")
        ed_priority = QLineEdit()
        ed_assignee = QLineEdit()
        form.addRow("Summary*", ed_summary)
        form.addRow("Priority", ed_priority)
        form.addRow("Assignee", ed_assignee)
        vbox.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            summary = ed_summary.text().strip()
            if not summary:
                main_win.status_bar.showMessage("Summary is required to create a Test Case.")
                return

            folder_id = src_issue.get("folder_id")
            from backend.db import create_local_issue, update_issue_fields
            new_tc_id = create_local_issue(
                main_win.conn,
                project_id=main_win.project.id,
                issue_type="TEST_CASE",
                folder_id=folder_id,
                summary=summary,
            )
            fields: Dict[str, Any] = {}
            if ed_priority.text().strip():
                fields["priority"] = ed_priority.text().strip()
            if ed_assignee.text().strip():
                fields["assignee"] = ed_assignee.text().strip()
            if fields:
                update_issue_fields(main_win.conn, new_tc_id, fields)

            # Requirement 와 새 Test Case 를 relation 으로 연결
            existing_rels = get_relations_for_issue(main_win.conn, main_win.current_issue_id)
            new_rels = [
                {"dst_issue_id": r.get("dst_issue_id"), "relation_type": r.get("relation_type") or ""}
                for r in existing_rels
            ]
            new_rels.append({"dst_issue_id": new_tc_id, "relation_type": "Tests"})
            replace_relations_for_issue(main_win.conn, main_win.current_issue_id, new_rels)

            # UI 갱신
            rels = get_relations_for_issue(main_win.conn, main_win.current_issue_id)
            if hasattr(main_win.left_panel.issue_tabs, "load_relations"):
                main_win.left_panel.issue_tabs.load_relations(rels)
            if hasattr(main_win.left_panel.issue_tabs, "load_requirements"):
                reqs = [
                    r for r in rels if (r.get("dst_issue_type") or "").upper() == "REQUIREMENT"
                ]
                main_win.left_panel.issue_tabs.load_requirements(reqs)
            if hasattr(main_win.left_panel.issue_tabs, "load_linked_testcases"):
                tcs = [
                    r for r in rels if (r.get("dst_issue_type") or "").upper() == "TEST_CASE"
                ]
                main_win.left_panel.issue_tabs.load_linked_testcases(tcs)

            main_win.reload_local_tree()
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    # ------------------------------------------------------------------ Test Cases top-level actions

    def _selected_local_testcase_ids(self) -> list[int]:
        """
        좌측(Local) 트리에서 선택된 TEST_CASE 이슈들의 로컬 ID 리스트를 반환.
        현재 상단 탭이 Test Cases 일 때 Add to Test Plan / Link to Requirement 에서 사용한다.
        """
        ids: list[int] = []
        view = self.left_panel.tree_view
        model = view.model()
        if model is None:
            return ids
        for idx in view.selectedIndexes():
            if idx.column() != 0:
                continue
            item = model.itemFromIndex(idx)
            if not item:
                continue
            node_type = item.data(Qt.UserRole)
            if node_type != "ISSUE":
                continue
            issue_id = item.data(Qt.UserRole + 1)
            issue_type = (item.data(Qt.UserRole + 3) or "").upper()
            if not issue_id or issue_type != "TEST_CASE":
                continue
            try:
                ids.append(int(issue_id))
            except (TypeError, ValueError):
                continue
        return ids

    def on_add_testcases_to_testplan_clicked(self):
        """
        상단 Test Cases 탭에서 'Add to Test Plan' 버튼:
        - 트리에서 선택된 TEST_CASE 이슈들을 하나의 Test Plan 에 추가한다.
        """
        tc_ids = self._selected_local_testcase_ids()
        if not tc_ids:
            self.status_bar.showMessage("No Test Cases selected in the tree.")
            return

        # 프로젝트 내 TEST_PLAN 목록 조회
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, jira_key, summary
              FROM issues
             WHERE project_id = ? AND is_deleted = 0 AND UPPER(issue_type) = 'TEST_PLAN'
             ORDER BY jira_key, summary
            """,
            (self.project.id,),
        )
        rows = cur.fetchall()
        plans = [dict(r) for r in rows]
        if not plans:
            self.status_bar.showMessage("No TEST_PLAN issues found; cannot add Test Cases.")
            return

        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QDialogButtonBox,
            QListWidget,
            QListWidgetItem,
            QLabel,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Add to Test Plan")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Select a Test Plan to add the selected Test Cases:"))

        lst = QListWidget()
        for p in plans:
            key = p.get("jira_key") or f"ID={p.get('id')}"
            text = key
            if p.get("summary"):
                text += f" - {p.get('summary')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p.get("id"))
            lst.addItem(item)
        vbox.addWidget(lst)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            item = lst.currentItem()
            if not item:
                self.status_bar.showMessage("No Test Plan selected.")
                return
            tp_id = item.data(Qt.UserRole)
            if not tp_id:
                return

            # 기존 매핑을 읽고 선택된 Test Case 들을 추가
            existing = get_testplan_testcases(self.conn, int(tp_id))
            existing_tc_ids = {int(r.get("testcase_id")) for r in existing if r.get("testcase_id")}
            records = [
                {"testcase_id": int(r["testcase_id"]), "order_no": int(r.get("order_no", 0) or 0)}
                for r in existing
            ]

            for tc_id in tc_ids:
                if tc_id in existing_tc_ids:
                    continue
                records.append({"testcase_id": tc_id, "order_no": 0})

            # order_no 재정렬
            for idx, rec in enumerate(records, start=1):
                rec["order_no"] = idx

            replace_testplan_testcases(self.conn, int(tp_id), records)
            self.status_bar.showMessage(
                f"Added {len(tc_ids)} Test Case(s) to Test Plan (id={tp_id})."
            )
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def on_link_testcases_to_requirement_clicked(self):
        """
        상단 Test Cases 탭에서 'Link to Requirement' 버튼:
        - 트리에서 선택된 TEST_CASE 이슈들을 선택한 Requirement 와 relation 으로 연결한다.
        """
        tc_ids = self._selected_local_testcase_ids()
        if not tc_ids:
            self.status_bar.showMessage("No Test Cases selected in the tree.")
            return

        # 프로젝트 내 REQUIREMENT 목록 조회
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, jira_key, summary
              FROM issues
             WHERE project_id = ? AND is_deleted = 0 AND UPPER(issue_type) = 'REQUIREMENT'
             ORDER BY jira_key, summary
            """,
            (self.project.id,),
        )
        rows = cur.fetchall()
        reqs = [dict(r) for r in rows]
        if not reqs:
            self.status_bar.showMessage("No REQUIREMENT issues found; cannot link.")
            return

        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QDialogButtonBox,
            QListWidget,
            QListWidgetItem,
            QLabel,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Link to Requirement")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Select a Requirement to link the selected Test Cases:"))

        lst = QListWidget()
        for r in reqs:
            key = r.get("jira_key") or f"ID={r.get('id')}"
            text = key
            if r.get("summary"):
                text += f" - {r.get('summary')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r.get("id"))
            lst.addItem(item)
        vbox.addWidget(lst)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            item = lst.currentItem()
            if not item:
                self.status_bar.showMessage("No Requirement selected.")
                return
            req_id = item.data(Qt.UserRole)
            if not req_id:
                return

            # Requirement 를 src 로 하는 relations 를 읽고, 선택된 Test Case 들을 추가
            existing_rels = get_relations_for_issue(self.conn, int(req_id))
            existing_dst_ids = {
                int(r.get("dst_issue_id")) for r in existing_rels if r.get("dst_issue_id")
            }
            new_rels = [
                {"dst_issue_id": r.get("dst_issue_id"), "relation_type": r.get("relation_type") or ""}
                for r in existing_rels
            ]
            for tc_id in tc_ids:
                if tc_id in existing_dst_ids:
                    continue
                new_rels.append({"dst_issue_id": tc_id, "relation_type": "Tests"})

            replace_relations_for_issue(self.conn, int(req_id), new_rels)

            # 현재 선택 이슈/탭이 이 Requirement 이거나 관련 있을 경우, UI 갱신
            if self.current_issue_id == int(req_id):
                rels = get_relations_for_issue(self.conn, int(req_id))
                if hasattr(self.left_panel.issue_tabs, "load_relations"):
                    self.left_panel.issue_tabs.load_relations(rels)
                if hasattr(self.left_panel.issue_tabs, "load_requirements"):
                    reqs2 = [
                        r
                        for r in rels
                        if (r.get("dst_issue_type") or "").upper() == "REQUIREMENT"
                    ]
                    self.left_panel.issue_tabs.load_requirements(reqs2)
                if hasattr(self.left_panel.issue_tabs, "load_linked_testcases"):
                    tcs2 = [
                        r
                        for r in rels
                        if (r.get("dst_issue_type") or "").upper() == "TEST_CASE"
                    ]
                    self.left_panel.issue_tabs.load_linked_testcases(tcs2)

            self.status_bar.showMessage(
                f"Linked {len(tc_ids)} Test Case(s) to Requirement (id={req_id})."
            )
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    # --------------------------- Test Plan / Test Cases binding ------------------

    def load_testplan_testcases(self, records: List[Dict[str, Any]]):
        """DB에서 읽어온 Test Plan - Test Case 매핑을 테이블에 로드."""
        # TEST_PLAN 용 컬럼 구성 보장
        self.testplan_tc_table.setColumnCount(4)
        self.testplan_tc_table.setHorizontalHeaderLabels(
            ["Order", "Test Case ID", "Jira Key", "Summary"]
        )
        self.testplan_tc_table.setRowCount(0)
        for rec in records:
            row = self.testplan_tc_table.rowCount()
            self.testplan_tc_table.insertRow(row)
            self.testplan_tc_table.setItem(row, 0, QTableWidgetItem(str(rec.get("order_no", row + 1))))
            self.testplan_tc_table.setItem(row, 1, QTableWidgetItem(str(rec.get("testcase_id"))))
            self.testplan_tc_table.setItem(row, 2, QTableWidgetItem(rec.get("jira_key") or ""))
            self.testplan_tc_table.setItem(row, 3, QTableWidgetItem(rec.get("summary") or ""))

    def collect_testplan_testcases(self) -> List[Dict[str, Any]]:
        """테이블에서 Test Plan - Test Case 매핑 정보를 수집."""
        records: List[Dict[str, Any]] = []
        rows = self.testplan_tc_table.rowCount()
        for r in range(rows):
            order_item = self.testplan_tc_table.item(r, 0)
            tcid_item = self.testplan_tc_table.item(r, 1)
            try:
                order_no = int(order_item.text()) if order_item and order_item.text().strip() else r + 1
            except ValueError:
                order_no = r + 1
            if not tcid_item or not tcid_item.text().strip():
                continue
            try:
                testcase_id = int(tcid_item.text().strip())
            except ValueError:
                continue
            records.append(
                {
                    "order_no": order_no,
                    "testcase_id": testcase_id,
                }
            )
        return records

    def _init_executions_tab(self):
        from PySide6.QtWidgets import (
            QVBoxLayout,
            QHBoxLayout,
            QFormLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QComboBox,
        )

        layout = QVBoxLayout()
        # 실행/실행결과 탭 헤더는 이슈 타입에 따라 동적으로 변경
        self.lbl_exec_header = QLabel("Executions")
        layout.addWidget(self.lbl_exec_header)

        # 상단 대시보드: TE executed 요약
        dash_layout = QHBoxLayout()
        self.lbl_te_executed = QLabel("TE executed: 0/0 (0%)")
        dash_layout.addWidget(self.lbl_te_executed)
        dash_layout.addStretch()
        layout.addLayout(dash_layout)

        # 상단 필터바: Assignee / Result / RTM Env 기준 필터
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Assignee:"))
        self.cmb_te_filter_assignee = QComboBox()
        self.cmb_te_filter_assignee.setEditable(False)
        filter_layout.addWidget(self.cmb_te_filter_assignee)

        filter_layout.addWidget(QLabel("Result:"))
        self.cmb_te_filter_result = QComboBox()
        self.cmb_te_filter_result.setEditable(False)
        filter_layout.addWidget(self.cmb_te_filter_result)

        filter_layout.addWidget(QLabel("RTM Env:"))
        self.cmb_te_filter_env = QComboBox()
        self.cmb_te_filter_env.setEditable(False)
        filter_layout.addWidget(self.cmb_te_filter_env)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 상단: Test Execution 메타 정보 (Environment, Start/End, Result, Executed By)
        form_layout = QFormLayout()
        self.ed_te_env = QLineEdit()
        self.ed_te_start = QLineEdit()
        self.ed_te_end = QLineEdit()
        self.cmb_te_result = QComboBox()
        self.cmb_te_result.setEditable(False)
        self.cmb_te_result.addItems(
            [
                "",
                "In progress",
                "Pass",
                "Fail",
                "Blocked",
                "Passed with restrictions",
            ]
        )
        self.ed_te_executed_by = QLineEdit()
        form_layout.addRow("Environment", self.ed_te_env)
        form_layout.addRow("Start Date", self.ed_te_start)
        form_layout.addRow("End Date", self.ed_te_end)
        form_layout.addRow("Result", self.cmb_te_result)
        form_layout.addRow("Executed By", self.ed_te_executed_by)
        layout.addLayout(form_layout)

        # 중간: 버튼
        btn_layout = QHBoxLayout()
        # TEST_PLAN 용: Execute Test Plan
        self.btn_execute_plan = QPushButton("Execute Test Plan")
        # TEST_EXECUTION 용: Test Case Execution 행 추가/삭제/일괄 편집
        self.btn_add_tc_exec = QPushButton("Add Test Case Execution")
        self.btn_del_tc_exec = QPushButton("Delete Selected")
        self.btn_edit_tc_exec = QPushButton("Edit Selected...")
        btn_layout.addWidget(self.btn_execute_plan)
        btn_layout.addWidget(self.btn_add_tc_exec)
        btn_layout.addWidget(self.btn_del_tc_exec)
        btn_layout.addWidget(self.btn_edit_tc_exec)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 하단: Test Case Executions 테이블
        self.tc_exec_table = QTableWidget()
        self.tc_exec_table.setColumnCount(9)
        self.tc_exec_table.setHorizontalHeaderLabels(
            [
                "Order",
                "Test Case ID",
                "Jira Key",
                "Summary",
                "Assignee",
                "Result",
                "RTM Env",
                "Actual Time (min)",
                "Defects",
            ]
        )
        self.tc_exec_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tc_exec_table)

        self.btn_execute_plan.clicked.connect(self._on_execute_test_plan_clicked)
        self.btn_add_tc_exec.clicked.connect(self._on_add_tc_exec_clicked)
        self.btn_del_tc_exec.clicked.connect(self._on_del_tc_exec_clicked)
        self.btn_edit_tc_exec.clicked.connect(self._on_edit_tc_exec_clicked)

        # 더블클릭 시 선택된 Test Case Execution 의 Step 실행 상세를 여는 핸들러 연결
        self.tc_exec_table.cellDoubleClicked.connect(self._on_tc_exec_double_clicked)

        # 필터 변경 시 실시간으로 테이블 필터링
        self.cmb_te_filter_assignee.currentIndexChanged.connect(self._apply_tc_exec_filters)
        self.cmb_te_filter_result.currentIndexChanged.connect(self._apply_tc_exec_filters)
        self.cmb_te_filter_env.currentIndexChanged.connect(self._apply_tc_exec_filters)

        self.executions_tab.setLayout(layout)

    # --------------------------- Linked Test Cases (Requirement / Defect 등) -----

    def load_linked_testcases(self, records: List[Dict[str, Any]]):
        """
        Relations 정보 등에서 필터링한 Test Case 리스트를 Test Cases 탭에 로드.
        REQUIREMENT / DEFECT 등의 이슈 타입에서 사용한다.
        """
        # REQUIREMENT / DEFECT 용 컬럼 구성
        self.testplan_tc_table.setColumnCount(6)
        self.testplan_tc_table.setHorizontalHeaderLabels(
            ["Jira Key", "Summary", "Priority", "Assignee", "Components", "RTM Env"]
        )
        self.testplan_tc_table.setRowCount(0)
        from PySide6.QtWidgets import QTableWidgetItem

        for rec in records:
            row = self.testplan_tc_table.rowCount()
            self.testplan_tc_table.insertRow(row)
            self.testplan_tc_table.setItem(row, 0, QTableWidgetItem(rec.get("dst_jira_key") or ""))
            self.testplan_tc_table.setItem(row, 1, QTableWidgetItem(rec.get("dst_summary") or ""))
            # 아래 필드들은 relations 조회 결과에 아직 없을 수 있으므로 빈 값으로 둔다.
            # 향후 jira_mapping.extract_relations_from_jira / DB 스키마 확장으로 보강 가능.
            self.testplan_tc_table.setItem(
                row, 2, QTableWidgetItem(rec.get("dst_priority") or "")
            )
            self.testplan_tc_table.setItem(
                row, 3, QTableWidgetItem(rec.get("dst_assignee") or "")
            )
            self.testplan_tc_table.setItem(
                row, 4, QTableWidgetItem(rec.get("dst_components") or "")
            )
            self.testplan_tc_table.setItem(
                row, 5, QTableWidgetItem(rec.get("dst_rtm_environment") or "")
            )

    def _on_add_tc_exec_clicked(self):
        """Test Case Execution 행 추가 (수동으로 한 건 더 추가)."""
        row = self.tc_exec_table.rowCount()
        self.tc_exec_table.insertRow(row)
        self.tc_exec_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

    def _on_edit_tc_exec_clicked(self):
        """
        Test Execution 화면에서 선택된 Test Case Executions 에 대해
        Assignee / Result / RTM Env / Defects 를 일괄 수정하는 팝업.
        (실제 DB 반영은 Save Local Issue 시점에 collect_testcase_executions()를 통해 이뤄진다.)
        """
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QFormLayout,
            QLineEdit,
            QDialogButtonBox,
            QLabel,
        )

        selected = self.tc_exec_table.selectedIndexes()
        if not selected:
            return
        rows = sorted({idx.row() for idx in selected})

        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Selected Test Case Executions")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(
            QLabel("Leave a field empty to keep current value. Non-empty fields overwrite all selected rows.")
        )

        form = QFormLayout()
        ed_assignee = QLineEdit()
        ed_result = QLineEdit()
        ed_env = QLineEdit()
        ed_actual_time = QLineEdit()
        ed_defects = QLineEdit()
        form.addRow("Assignee", ed_assignee)
        form.addRow("Result", ed_result)
        form.addRow("RTM Env", ed_env)
        form.addRow("Actual Time (min)", ed_actual_time)
        form.addRow("Defects", ed_defects)
        vbox.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            assignee = ed_assignee.text().strip()
            result = ed_result.text().strip()
            env = ed_env.text().strip()
            at_text = ed_actual_time.text().strip()
            defects = ed_defects.text().strip()

            if not any([assignee, result, env, at_text, defects]):
                dlg.reject()
                return

            from PySide6.QtWidgets import QTableWidgetItem

            for r in rows:
                if assignee:
                    item = self.tc_exec_table.item(r, 4) or QTableWidgetItem()
                    item.setText(assignee)
                    self.tc_exec_table.setItem(r, 4, item)
                if result:
                    item = self.tc_exec_table.item(r, 5) or QTableWidgetItem()
                    item.setText(result)
                    self.tc_exec_table.setItem(r, 5, item)
                if env:
                    item = self.tc_exec_table.item(r, 6) or QTableWidgetItem()
                    item.setText(env)
                    self.tc_exec_table.setItem(r, 6, item)
                if at_text:
                    item = self.tc_exec_table.item(r, 7) or QTableWidgetItem()
                    item.setText(at_text)
                    self.tc_exec_table.setItem(r, 7, item)
                if defects:
                    item = self.tc_exec_table.item(r, 8) or QTableWidgetItem()
                    item.setText(defects)
                    self.tc_exec_table.setItem(r, 8, item)

            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def _on_tc_exec_double_clicked(self, row: int, column: int):
        """
        Test Case Executions 테이블에서 행을 더블클릭했을 때:
        - 해당 Test Case 의 설계 Steps + 실행 상태(testcase_step_executions)를 합쳐
          Step 실행 상세 팝업을 띄운다.
        """
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QHBoxLayout,
            QTableWidget,
            QTableWidgetItem,
            QDialogButtonBox,
            QLabel,
            QComboBox,
        )

        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return

        order_item = self.tc_exec_table.item(row, 0)
        tcid_item = self.tc_exec_table.item(row, 1)
        if not order_item or not tcid_item:
            return

        tce_id = order_item.data(Qt.UserRole)
        if not tce_id:
            return
        try:
            tce_id = int(tce_id)
        except (TypeError, ValueError):
            return

        try:
            testcase_id = int(tcid_item.text().strip())
        except (TypeError, ValueError):
            return

        # 설계 단계 Steps 및 기존 Step Execution 상태 로딩
        steps = get_steps_for_issue(main_win.conn, testcase_id)
        existing_execs = get_step_executions_for_tce(main_win.conn, tce_id)
        exec_map = {
            int(rec["testcase_step_id"]): rec for rec in existing_execs if rec.get("testcase_step_id") is not None
        }

        dlg = QDialog(self)
        dlg.setWindowTitle("Execute Test Case - Steps")
        vbox = QVBoxLayout(dlg)

        tc_label = self.tc_exec_table.item(row, 3)  # Summary
        summary_text = tc_label.text() if tc_label else ""
        vbox.addWidget(QLabel(f"Test Case ID: {testcase_id}  Summary: {summary_text}"))

        # 상단: 일괄 상태 변경 콤보
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Change steps status:"))
        cmb_status = QComboBox()
        cmb_status.addItems(
            [
                "",
                "Not run",
                "In progress",
                "Pass",
                "Fail",
                "Blocked",
                "Passed with restrictions",
            ]
        )
        btn_apply_all = QPushButton("Apply to all")
        top_layout.addWidget(cmb_status)
        top_layout.addWidget(btn_apply_all)
        top_layout.addStretch()
        vbox.addLayout(top_layout)

        # Steps 테이블: Group / Order / Action / Input / Expected / Status / Actual Result / Evidence
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            ["Group", "Order", "Action", "Input", "Expected", "Status", "Actual Result", "Evidence"]
        )
        table.horizontalHeader().setStretchLastSection(True)

        for s in steps:
            step_id = s.get("id")
            row_idx = table.rowCount()
            table.insertRow(row_idx)

            item_group = QTableWidgetItem(str(s.get("group_no", 1)))
            item_group.setFlags(item_group.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_idx, 0, item_group)

            item_order = QTableWidgetItem(str(s.get("order_no", 1)))
            item_order.setFlags(item_order.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_idx, 1, item_order)

            item_action = QTableWidgetItem(s.get("action") or "")
            item_action.setFlags(item_action.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_idx, 2, item_action)

            item_input = QTableWidgetItem(s.get("input") or "")
            item_input.setFlags(item_input.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_idx, 3, item_input)

            item_expected = QTableWidgetItem(s.get("expected") or "")
            item_expected.setFlags(item_expected.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_idx, 4, item_expected)

            # 기존 실행 상태
            exec_rec = exec_map.get(int(step_id)) if step_id is not None else None
            status_val = exec_rec.get("status") if exec_rec else ""
            actual_val = exec_rec.get("actual_result") if exec_rec else ""
            evidence_val = exec_rec.get("evidence") if exec_rec else ""

            item_status = QTableWidgetItem(status_val or "")
            table.setItem(row_idx, 5, item_status)
            item_actual = QTableWidgetItem(actual_val or "")
            table.setItem(row_idx, 6, item_actual)
            item_evidence = QTableWidgetItem(evidence_val or "")
            table.setItem(row_idx, 7, item_evidence)

            # 숨은 데이터로 testcase_step_id 저장
            item_group.setData(Qt.UserRole, step_id)

        vbox.addWidget(table)

        # 일괄 상태 적용 버튼 로직
        def apply_all_status():
            val = cmb_status.currentText().strip()
            if not val:
                return
            for r in range(table.rowCount()):
                item = table.item(r, 5)
                if item is None:
                    item = QTableWidgetItem()
                    table.setItem(r, 5, item)
                item.setText(val)

        btn_apply_all.clicked.connect(apply_all_status)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            records: list[Dict[str, Any]] = []
            for r in range(table.rowCount()):
                item_group = table.item(r, 0)
                step_id = item_group.data(Qt.UserRole) if item_group else None
                if not step_id:
                    continue
                status_item = table.item(r, 5)
                actual_item = table.item(r, 6)
                evidence_item = table.item(r, 7)
                records.append(
                    {
                        "testcase_step_id": int(step_id),
                        "status": status_item.text().strip() if status_item else "",
                        "actual_result": actual_item.text().strip() if actual_item else "",
                        "evidence": evidence_item.text().strip() if evidence_item else "",
                    }
                )

            replace_step_executions_for_tce(main_win.conn, tce_id, records)
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def _on_execute_test_plan_clicked(self):
        """
        TEST_PLAN 이슈의 Executions 탭에서 'Execute Test Plan' 버튼:
        - 현재 Test Plan 을 기반으로 새로운 TEST_EXECUTION 이슈를 생성하고,
        - 해당 플랜에 연결된 모든 Test Case 에 대한 Test Case Execution 행을 초기화한다.
        """
        main_win = self.window()
        if not hasattr(main_win, "conn") or getattr(main_win, "project", None) is None:
            return
        if getattr(main_win, "current_issue_id", None) is None:
            main_win.status_bar.showMessage("No Test Plan selected.")
            return

        # 현재 이슈가 TEST_PLAN 인지 확인
        plan_issue = get_issue_by_id(main_win.conn, main_win.current_issue_id)
        if not plan_issue or (plan_issue.get("issue_type") or "").upper() != "TEST_PLAN":
            main_win.status_bar.showMessage("Current issue is not a TEST_PLAN.")
            return

        # 이 Test Plan 에 연결된 Test Case 목록
        tp_records = get_testplan_testcases(main_win.conn, int(main_win.current_issue_id))
        if not tp_records:
            main_win.status_bar.showMessage("This Test Plan has no Test Cases mapped.")
            return

        # TEST_EXECUTION 로컬 이슈 생성
        folder_id = plan_issue.get("folder_id")
        summary = f"{plan_issue.get('summary') or 'Test Plan'} (execution)"
        te_issue_id = create_local_issue(
            main_win.conn,
            project_id=main_win.project.id,
            issue_type="TEST_EXECUTION",
            folder_id=folder_id,
            summary=summary,
        )

        # Details 필드 일부를 플랜에서 복사 (환경/우선순위/라벨 등)
        fields: Dict[str, Any] = {}
        for key in ["rtm_environment", "priority", "assignee", "labels", "components"]:
            val = plan_issue.get(key)
            if val:
                fields[key] = val
        # parent_issue_id 로 플랜과의 연결을 남겨둔다.
        fields["parent_issue_id"] = int(main_win.current_issue_id)
        update_issue_fields(main_win.conn, te_issue_id, fields)

        # testexecutions 메타 행 초기화
        te_row = get_or_create_testexecution_for_issue(main_win.conn, te_issue_id)
        te_meta: Dict[str, Any] = {}
        if plan_issue.get("rtm_environment"):
            te_meta["environment"] = plan_issue.get("rtm_environment") or ""
        update_testexecution_for_issue(main_win.conn, te_issue_id, te_meta)

        # testcase_executions 행 생성 (각 Test Case 에 대해 기본 행)
        records: list[Dict[str, Any]] = []
        for idx, rec in enumerate(tp_records, start=1):
            tc_id = rec.get("testcase_id")
            if not tc_id:
                continue
            records.append(
                {
                    "testcase_id": int(tc_id),
                    "order_no": int(rec.get("order_no", idx) or idx),
                    "assignee": "",
                    "result": "",
                    "rtm_environment": plan_issue.get("rtm_environment") or "",
                    "defects": "",
                }
            )
        replace_testcase_executions(main_win.conn, te_row["id"], records)

        # 트리/상태 갱신: 새 Test Execution 은 상단 'Test Executions' 탭에서 확인 가능
        main_win.reload_local_tree()
        main_win.status_bar.showMessage(
            f"Created new Test Execution (id={te_issue_id}) for this Test Plan."
        )

    def _on_del_tc_exec_clicked(self):
        """선택된 Test Case Execution 행 삭제 및 order 재정렬."""
        selected = self.tc_exec_table.selectedIndexes()
        if not selected:
            return
        rows = sorted({idx.row() for idx in selected}, reverse=True)
        for r in rows:
            self.tc_exec_table.removeRow(r)
        # order 재정렬
        for i in range(self.tc_exec_table.rowCount()):
            item = self.tc_exec_table.item(i, 0)
            if item is None:
                item = QTableWidgetItem(str(i + 1))
                self.tc_exec_table.setItem(i, 0, item)
            else:
                item.setText(str(i + 1))

    # --------------------------- Test Execution binding helpers ------------------

    def load_testexecution(self, meta: Dict[str, Any] | None, tc_execs: List[Dict[str, Any]]):
        """Test Execution 메타 & Test Case Executions를 탭에 로드."""
        if not meta:
            self.ed_te_env.setText("")
            self.ed_te_start.setText("")
            self.ed_te_end.setText("")
            self.cmb_te_result.setCurrentIndex(0)
            self.ed_te_executed_by.setText("")
        else:
            self.ed_te_env.setText(meta.get("environment") or "")
            self.ed_te_start.setText(meta.get("start_date") or "")
            self.ed_te_end.setText(meta.get("end_date") or "")
            result_val = meta.get("result") or ""
            # 콤보박스에서 동일 텍스트를 찾고, 없으면 첫 번째 항목("")로 설정
            idx = self.cmb_te_result.findText(result_val)
            if idx < 0:
                idx = 0
            self.cmb_te_result.setCurrentIndex(idx)
            self.ed_te_executed_by.setText(meta.get("executed_by") or "")

        self.tc_exec_table.setRowCount(0)
        assignees: set[str] = set()
        results: set[str] = set()
        envs: set[str] = set()

        for rec in tc_execs:
            row = self.tc_exec_table.rowCount()
            self.tc_exec_table.insertRow(row)
            item_order = QTableWidgetItem(str(rec.get("order_no", row + 1)))
            # UserRole 에 testcase_executions.id 저장 (Step 실행 상세에 사용)
            item_order.setData(Qt.UserRole, rec.get("id"))
            self.tc_exec_table.setItem(row, 0, item_order)
            self.tc_exec_table.setItem(row, 1, QTableWidgetItem(str(rec.get("testcase_id"))))
            self.tc_exec_table.setItem(row, 2, QTableWidgetItem(rec.get("jira_key") or ""))
            self.tc_exec_table.setItem(row, 3, QTableWidgetItem(rec.get("summary") or ""))
            assignee_val = rec.get("assignee") or ""
            result_val = rec.get("result") or ""
            env_val = rec.get("rtm_environment") or ""
            self.tc_exec_table.setItem(row, 4, QTableWidgetItem(assignee_val))
            self.tc_exec_table.setItem(row, 5, QTableWidgetItem(result_val))
            self.tc_exec_table.setItem(row, 6, QTableWidgetItem(env_val))
            at = rec.get("actual_time")
            at_text = "" if at in (None, "") else str(at)
            self.tc_exec_table.setItem(row, 7, QTableWidgetItem(at_text))
            self.tc_exec_table.setItem(row, 8, QTableWidgetItem(rec.get("defects") or ""))

            if assignee_val:
                assignees.add(assignee_val)
            if result_val:
                results.add(result_val)
            if env_val:
                envs.add(env_val)

        # 대시보드: 실행된 Test Case 수/전체/퍼센트 표시
        total = len(tc_execs)
        executed = 0
        for rec in tc_execs:
            if (rec.get("result") or "").strip():
                executed += 1
        if total > 0:
            pct = executed * 100.0 / total
            self.lbl_te_executed.setText(f"TE executed: {executed}/{total} ({pct:.1f}%)")
        else:
            self.lbl_te_executed.setText("TE executed: 0/0 (0%)")

        # 필터 콤보박스 갱신 (첫 항목은 항상 'All')
        def _fill_filter_combo(combo: QComboBox, values: set[str]):
            current = combo.currentText() if combo.count() > 0 else "All"
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All")
            for v in sorted(values):
                combo.addItem(v)
            # 이전 선택이 여전히 유효하면 그대로 유지
            idx = combo.findText(current)
            if idx < 0:
                idx = 0
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)

        _fill_filter_combo(self.cmb_te_filter_assignee, assignees)
        _fill_filter_combo(self.cmb_te_filter_result, results)
        _fill_filter_combo(self.cmb_te_filter_env, envs)

        # 필터 적용
        self._apply_tc_exec_filters()

    def collect_testexecution_meta(self) -> Dict[str, Any]:
        """현재 탭의 Test Execution 메타 정보 수집."""
        return {
            "environment": self.ed_te_env.text().strip(),
            "start_date": self.ed_te_start.text().strip(),
            "end_date": self.ed_te_end.text().strip(),
            "result": self.cmb_te_result.currentText().strip(),
            "executed_by": self.ed_te_executed_by.text().strip(),
        }

    def collect_testcase_executions(self) -> List[Dict[str, Any]]:
        """현재 탭의 Test Case Execution 리스트 수집."""
        records: List[Dict[str, Any]] = []
        rows = self.tc_exec_table.rowCount()
        for r in range(rows):
            order_item = self.tc_exec_table.item(r, 0)
            tcid_item = self.tc_exec_table.item(r, 1)
            assignee_item = self.tc_exec_table.item(r, 4)
            result_item = self.tc_exec_table.item(r, 5)
            env_item = self.tc_exec_table.item(r, 6)
            at_item = self.tc_exec_table.item(r, 7)
            defects_item = self.tc_exec_table.item(r, 8)
            try:
                order_no = int(order_item.text()) if order_item and order_item.text().strip() else r + 1
            except ValueError:
                order_no = r + 1
            if not tcid_item or not tcid_item.text().strip():
                continue
            try:
                testcase_id = int(tcid_item.text().strip())
            except ValueError:
                continue
            actual_time = 0
            if at_item and at_item.text().strip():
                try:
                    actual_time = int(at_item.text().strip())
                except ValueError:
                    actual_time = 0
            records.append(
                {
                    "order_no": order_no,
                    "testcase_id": testcase_id,
                    "assignee": assignee_item.text().strip() if assignee_item else "",
                    "result": result_item.text().strip() if result_item else "",
                    "actual_time": actual_time,
                    "rtm_environment": env_item.text().strip() if env_item else "",
                    "defects": defects_item.text().strip() if defects_item else "",
                }
            )
        return records

    def _apply_tc_exec_filters(self):
        """
        상단 필터(Assignee / Result / RTM Env)에 따라 Test Case Executions 테이블을 필터링한다.
        """
        if not hasattr(self, "tc_exec_table"):
            return

        assignee = (
            self.cmb_te_filter_assignee.currentText()
            if hasattr(self, "cmb_te_filter_assignee")
            else "All"
        )
        result = (
            self.cmb_te_filter_result.currentText()
            if hasattr(self, "cmb_te_filter_result")
            else "All"
        )
        env = (
            self.cmb_te_filter_env.currentText()
            if hasattr(self, "cmb_te_filter_env")
            else "All"
        )

        assignee = assignee if assignee != "All" else ""
        result = result if result != "All" else ""
        env = env if env != "All" else ""

        rows = self.tc_exec_table.rowCount()
        for r in range(rows):
            a_item = self.tc_exec_table.item(r, 4)
            res_item = self.tc_exec_table.item(r, 5)
            env_item = self.tc_exec_table.item(r, 6)
            a_txt = a_item.text().strip() if a_item else ""
            res_txt = res_item.text().strip() if res_item else ""
            env_txt = env_item.text().strip() if env_item else ""

            visible = True
            if assignee and a_txt != assignee:
                visible = False
            if result and res_txt != result:
                visible = False
            if env and env_txt != env:
                visible = False

            self.tc_exec_table.setRowHidden(r, not visible)

    def _init_defects_tab(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Linked Defects table"))
        self.defects_tab.setLayout(layout)

    # ------------------------------------------------------------------ Binding helpers

    def _set_tab_visible(self, widget: QWidget, visible: bool) -> None:
        """
        PySide6(Qt6) 의 setTabVisible 지원 여부에 따라 탭 가시성/활성화를 제어.
        """
        idx = self.indexOf(widget)
        if idx < 0:
            return
        if hasattr(self, "setTabVisible"):
            self.setTabVisible(idx, visible)
        else:
            self.setTabEnabled(idx, visible)

    def update_tabs_for_issue_type(self, issue_type: str | None) -> None:
        """
        RTM 이슈 타입별로 필요한 탭만 보이도록 구성.

        SW 사양서 기준:
        - REQUIREMENT : Details / Test Cases / Relations
        - TEST_CASE   : Details / Steps / Requirements / Relations
        - TEST_PLAN   : Details / Test Cases / Executions / Relations
        - TEST_EXECUTION : Details / Executions / Relations
        - DEFECT      : Details / Test Cases / Relations
        - 기타/None   : 모든 탭 표시
        """
        # 1) 기본값: 모두 보이게
        all_widgets = [
            self.details_tab,
            self.steps_tab,
            self.requirements_tab,
            self.relations_tab,
            self.testcases_tab,
            self.executions_tab,
            self.defects_tab,
        ]
        for w in all_widgets:
            self._set_tab_visible(w, True)

        if not issue_type:
            return

        it = issue_type.upper()

        visible_map = {
            "REQUIREMENT": {"details", "testcases", "relations"},
            "TEST_CASE": {"details", "steps", "requirements", "relations"},
            "TEST_PLAN": {"details", "testcases", "executions", "relations"},
            "TEST_EXECUTION": {"details", "executions", "relations"},
            "DEFECT": {"details", "testcases", "relations"},
        }

        visible = visible_map.get(it)
        if visible is None:
            # 정의되지 않은 타입이면 모든 탭 유지
            return

        name_map = {
            "details": self.details_tab,
            "steps": self.steps_tab,
            "requirements": self.requirements_tab,
            "relations": self.relations_tab,
            "testcases": self.testcases_tab,
            "executions": self.executions_tab,
            "defects": self.defects_tab,
        }

        for name, widget in name_map.items():
            self._set_tab_visible(widget, name in visible)

        # 항상 Details 탭부터 보이도록 설정 (추적성/입력 흐름의 기본 진입점)
        if "details" in visible:
            self.setCurrentWidget(self.details_tab)

        # Test Cases 탭은 이슈 타입에 따라 헤더/버튼/컬럼 구성을 달리한다.
        if "testcases" in visible and hasattr(self, "configure_testcases_tab_for_issue_type"):
            self.configure_testcases_tab_for_issue_type(it)

        # Executions 탭도 TEST_PLAN / TEST_EXECUTION 에 따라 다르게 구성한다.
        if "executions" in visible and hasattr(self, "configure_executions_tab_for_issue_type"):
            self.configure_executions_tab_for_issue_type(it)

    def configure_testcases_tab_for_issue_type(self, issue_type: str) -> None:
        """
        Test Cases 탭을 이슈 타입에 맞게 구성한다.
        - REQUIREMENT / DEFECT: Linked Test Cases 뷰 (Cover by Test Case / Create New Test Case)
        - TEST_PLAN: Test Plan - Test Case 매핑 테이블
        """
        it = issue_type.upper()

        if it == "TEST_PLAN":
            # 헤더 텍스트
            self.lbl_testcases_header.setText("Test Plan - Test Cases")
            # 버튼 표시 (Add / Create / Delete / Edit order)
            self.btn_cover_by_tc.setVisible(False)
            self.btn_create_tc.setVisible(True)
            self.btn_add_tp_tc.setVisible(True)
            self.btn_del_tp_tc.setVisible(True)
            self.btn_edit_tp_order.setVisible(True)
            # 컬럼 구성은 load_testplan_testcases 에서 보장
        elif it == "TEST_CASE":
            # 순수 Test Case 이슈에서는 상단 헤더만 간단히 두고,
            # 실제 생성/관리는 좌측 패널의 'Create Test Case' 버튼을 사용하도록 한다.
            self.lbl_testcases_header.setText("Test Cases")
            self.btn_cover_by_tc.setVisible(False)
            self.btn_create_tc.setVisible(False)
            self.btn_add_tp_tc.setVisible(False)
            self.btn_del_tp_tc.setVisible(False)
            self.btn_edit_tp_order.setVisible(False)
        else:
            # REQUIREMENT / DEFECT 등: Linked Test Cases
            self.lbl_testcases_header.setText("Linked Test Cases (covered by / related test cases)")
            self.btn_cover_by_tc.setVisible(True)
            self.btn_create_tc.setVisible(True)
            self.btn_add_tp_tc.setVisible(False)
            self.btn_del_tp_tc.setVisible(False)
            self.btn_edit_tp_order.setVisible(False)
            # 컬럼 구성은 load_linked_testcases 에서 보장

    def configure_executions_tab_for_issue_type(self, issue_type: str) -> None:
        """
        Executions 탭을 이슈 타입에 맞게 구성한다.
        - TEST_PLAN      : 'Execute Test Plan' 버튼 중심의 뷰 (이 플랜에서 생성된 실행들을 관리)
        - TEST_EXECUTION : Test Case Executions 편집 뷰
        """
        it = issue_type.upper()

        if it == "TEST_PLAN":
            # 헤더/버튼 구성
            self.lbl_exec_header.setText("Executions for this Test Plan")
            # Test Plan 에서는 실제 실행(Execute Test Plan) 버튼만 보이게 하고
            # 개별 Test Case Execution 편집용 UI는 숨긴다.
            self.btn_execute_plan.setVisible(True)
            self.btn_add_tc_exec.setVisible(False)
            self.btn_del_tc_exec.setVisible(False)
            self.btn_edit_tc_exec.setVisible(False)
            self.tc_exec_table.setVisible(False)
        elif it == "TEST_EXECUTION":
            # Test Execution 상세/TC Executions 편집
            self.lbl_exec_header.setText("Test Case Executions")
            self.btn_execute_plan.setVisible(False)
            self.btn_add_tc_exec.setVisible(True)
            self.btn_del_tc_exec.setVisible(True)
            self.btn_edit_tc_exec.setVisible(True)
            self.tc_exec_table.setVisible(True)
        else:
            # 기타 타입에서는 Executions 탭을 단순 비활성화 수준으로 둔다.
            self.lbl_exec_header.setText("Executions")
            self.btn_execute_plan.setVisible(False)
            self.btn_add_tc_exec.setVisible(False)
            self.btn_del_tc_exec.setVisible(False)
            self.btn_edit_tc_exec.setVisible(False)
            self.tc_exec_table.setVisible(False)

    def set_issue(self, issue: Dict[str, Any] | None) -> None:
        """
        현재 선택된 이슈의 필드를 Details 탭에 로드하고,
        RTM 이슈 타입별 탭 구성을 적용한다.

        issues 테이블 스키마 필드 매핑:
          - summary, description, status, priority, assignee, reporter
          - labels, components, security_level, fix_versions, affects_versions
          - rtm_environment, due_date, created, updated, attachments
        """
        self._current_issue = issue

        issue_type = None
        if issue is not None:
            issue_type = issue.get("issue_type")
        self.update_tabs_for_issue_type(issue_type)

        if not issue:
            self.ed_local_id.setText("")
            self.ed_jira_key.setText("")
            self.ed_issue_type.setText("")
            self.ed_summary.setText("")
            self.ed_status.setText("")
            self.ed_priority.setText("")
            self.ed_assignee.setText("")
            self.ed_reporter.setText("")
            self.ed_labels.setText("")
            self.ed_components.setText("")
            self.ed_security_level.setText("")
            self.ed_fix_versions.setText("")
            self.ed_affects_versions.setText("")
            self.ed_epic_link.setText("")
            self.ed_sprint.setText("")
            self.ed_rtm_env.setText("")
            self.ed_due_date.setText("")
            self.ed_created.setText("")
            self.ed_updated.setText("")
            self.ed_attachments.setText("")
            self.txt_description.setPlainText("")
            # Activity 초기화
            if hasattr(self, "set_activity_text"):
                self.set_activity_text("")
            # Preconditions (TEST_CASE용) 초기화
            if hasattr(self, "set_preconditions_text"):
                self.set_preconditions_text("")
            return

        self.ed_issue_type.setText(issue_type or "")
        self.ed_summary.setText(issue.get("summary") or "")
        self.ed_status.setText(issue.get("status") or "")
        self.ed_priority.setText(issue.get("priority") or "")
        self.ed_assignee.setText(issue.get("assignee") or "")
        self.ed_reporter.setText(issue.get("reporter") or "")
        self.ed_labels.setText(issue.get("labels") or "")
        self.ed_components.setText(issue.get("components") or "")
        self.ed_security_level.setText(issue.get("security_level") or "")
        self.ed_fix_versions.setText(issue.get("fix_versions") or "")
        self.ed_affects_versions.setText(issue.get("affects_versions") or "")
        self.ed_epic_link.setText(issue.get("epic_link") or "")
        self.ed_sprint.setText(issue.get("sprint") or "")
        self.ed_rtm_env.setText(issue.get("rtm_environment") or "")
        self.ed_due_date.setText(issue.get("due_date") or "")
        self.ed_created.setText(issue.get("created") or "")
        self.ed_updated.setText(issue.get("updated") or "")
        self.ed_attachments.setText(issue.get("attachments") or "")
        # 로컬/온라인 공통: 로컬 DB에서 온 이슈는 id 필드가 있고, Online 조회 이슈는 없을 수 있다.
        local_id = issue.get("id")
        self.ed_local_id.setText(str(local_id) if local_id is not None else "")
        self.ed_jira_key.setText(issue.get("jira_key") or "")
        self.txt_description.setPlainText(issue.get("description") or "")
        # Preconditions (TEST_CASE)
        pre = issue.get("preconditions") or ""
        if hasattr(self, "set_preconditions_text"):
            self.set_preconditions_text(pre)

    def set_activity_text(self, text: str) -> None:
        """JIRA Comments/History 텍스트를 Activity 영역에 설정."""
        self.txt_activity.setPlainText(text or "")

    def get_issue_updates(self) -> Dict[str, Any]:
        """
        Details 탭에서 사용자가 수정한 필드 값을 dict로 반환.
        DB update 및 JIRA sync 시 활용.
        """
        return {
            "summary": self.ed_summary.text().strip(),
            "status": self.ed_status.text().strip(),
            "priority": self.ed_priority.text().strip(),
            "assignee": self.ed_assignee.text().strip(),
            "reporter": self.ed_reporter.text().strip(),
            "labels": self.ed_labels.text().strip(),
            "components": self.ed_components.text().strip(),
            "security_level": self.ed_security_level.text().strip(),
            "fix_versions": self.ed_fix_versions.text().strip(),
            "affects_versions": self.ed_affects_versions.text().strip(),
            "rtm_environment": self.ed_rtm_env.text().strip(),
            "due_date": self.ed_due_date.text().strip(),
            "attachments": self.ed_attachments.text().strip(),
            "description": self.txt_description.toPlainText().strip(),
        }
class PanelWidget(QWidget):
    """
    좌/우 패널 공통 레이아웃:
    - 상단 헤더(라벨 + 버튼)
    - 중간 트리뷰
    - 하단 이슈 탭
    """

    def __init__(self, title: str, is_online: bool = False, parent=None):
        super().__init__(parent)

        self.is_online = is_online

        main_layout = QVBoxLayout(self)

        # 상단 헤더
        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()

        if is_online:
            # 온라인(JIRA) 패널: 트리 갱신 / Local 로 동기화 / JIRA 엔티티 생성/삭제
            self.btn_refresh = QPushButton("Refresh")
            self.btn_sync_down = QPushButton("Sync → Local")
            self.btn_create_jira = QPushButton("Create in JIRA")
            self.btn_delete_jira = QPushButton("Delete in JIRA")
            header_layout.addWidget(self.btn_refresh)
            header_layout.addWidget(self.btn_sync_down)
            header_layout.addWidget(self.btn_create_jira)
            header_layout.addWidget(self.btn_delete_jira)
        else:
            # 로컬 패널: 폴더/이슈 생성/삭제 + 로컬 저장 + JIRA 동기화 버튼
            self.btn_add_folder = QPushButton("Add Folder")
            self.btn_delete_folder = QPushButton("Delete Folder")
            header_layout.addWidget(self.btn_add_folder)
            header_layout.addWidget(self.btn_delete_folder)

            self.btn_new_issue = QPushButton("New Issue")
            self.btn_save_issue = QPushButton("Save Local Issue")
            self.btn_delete_issue = QPushButton("Delete Issue")
            header_layout.addWidget(self.btn_new_issue)
            header_layout.addWidget(self.btn_save_issue)
            header_layout.addWidget(self.btn_delete_issue)

            # Test Case 전용 상단 액션(이미지: Create Test Case / Execute / Add to Test Plan / Link to requirement)
            # - 기본적으로는 숨겨 두고, 상단 이슈 타입 탭이 TEST_CASE 일 때만 표시/활성화한다.
            self.btn_execute_tc = QPushButton("Execute")
            self.btn_add_to_testplan = QPushButton("Add to Test Plan")
            self.btn_link_requirement = QPushButton("Link to Requirement")
            # 일단 비활성/비가시 상태로 시작; MainWindow._on_issue_type_tab_changed 에서 제어
            self.btn_execute_tc.setVisible(False)
            self.btn_add_to_testplan.setVisible(False)
            self.btn_link_requirement.setVisible(False)
            header_layout.addWidget(self.btn_execute_tc)
            header_layout.addWidget(self.btn_add_to_testplan)
            header_layout.addWidget(self.btn_link_requirement)

            self.btn_sync_up = QPushButton("Sync → JIRA")
            header_layout.addWidget(self.btn_sync_up)

        main_layout.addLayout(header_layout)

        # 모듈(최상위) 탭바: Dashboard / Requirements / Test Cases / Test Plans / Test Executions / Defects
        from PySide6.QtWidgets import QTabBar

        self.module_tab_bar = QTabBar()
        self.module_tab_bar.addTab("Dashboard")
        self.module_tab_bar.addTab("Requirements")
        self.module_tab_bar.addTab("Test Cases")
        self.module_tab_bar.addTab("Test Plans")
        self.module_tab_bar.addTab("Test Executions")
        self.module_tab_bar.addTab("Defects")
        self.module_tab_bar.setExpanding(False)
        main_layout.addWidget(self.module_tab_bar)

        # 트리 + 탭을 좌/우로 배치
        tree_and_tabs = QSplitter(Qt.Horizontal)
        tree_and_tabs.setChildrenCollapsible(False)

        # 트리 (좌측)
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        tree_and_tabs.addWidget(self.tree_view)

        # 이슈 탭 (우측)
        self.issue_tabs = IssueTabWidget()
        tree_and_tabs.addWidget(self.issue_tabs)

        tree_and_tabs.setStretchFactor(0, 3)
        tree_and_tabs.setStretchFactor(1, 5)

        main_layout.addWidget(tree_and_tabs)


class MainWindow(QMainWindow):
    def __init__(self, db_path=None, config_path: str = "jira_config.json", mode: str = "both"):
        """
        mode:
          - "local"  : 로컬 관리 전용 윈도우 (온라인 패널/툴바 요소 숨김)
          - "online" : 온라인(JIRA RTM) 전용 윈도우 (로컬 패널/툴바 요소 숨김)
          - "both"   : 기존처럼 좌/우 패널을 한 창에 모두 배치
        """
        super().__init__()
        self.logger = get_logger(__name__)
        self.mode = mode.lower()
        self.logger.info(
            "MainWindow init: db_path=%s, config_path=%s, mode=%s",
            db_path,
            config_path,
            self.mode,
        )
        title_suffix = {
            "local": " - Local",
            "online": " - Online",
            "both": "",
        }.get(self.mode, "")
        self.setWindowTitle(f"RTM Local Manager (JIRA RTM Sync Tool){title_suffix}")
        self.resize(1600, 900)

        # DB, Jira client 초기화
        self.conn = get_connection(db_path)
        init_db(self.conn)

        try:
            self.jira_config = load_config_from_file(config_path)
            self.project = get_or_create_project(
                self.conn,
                project_key=self.jira_config.project_key,
                project_id=self.jira_config.project_id,
                name=self.jira_config.project_key,
                base_url=self.jira_config.base_url,
            )
            self.jira_client = JiraRTMClient(self.jira_config)
            self.jira_available = True
        except Exception as e:
            # 설정 파일이 없거나 잘못된 경우: 오프라인 모드로 시작
            self.jira_config = None
            self.project = get_or_create_project(
                self.conn,
                project_key="LOCAL",
                project_id=0,
                name="Local Only",
                base_url=None,
            )
            self.jira_client = None
            self.jira_available = False
            self.logger.warning("Jira config not loaded: %s", e, exc_info=True)

        # currently selected issue id (local DB)
        self.current_issue_id: int | None = None
        self.current_issue_type: str | None = None
        self.current_testexecution_id: int | None = None

        # 로컬 / 온라인 트리의 이슈 타입 필터
        # - Dashboard 탭: None (필터 없음, 모든 이슈 타입 표시)
        # - 나머지 탭: REQUIREMENT / TEST_CASE / TEST_PLAN / TEST_EXECUTION / DEFECT
        self.local_issue_type_filter: str | None = None
        self.online_issue_type_filter: str | None = None

        # 메뉴바 생성 (File / Local / JIRA / Help)
        self._create_menu_bar()

        # 메인 리본/툴바 (빠른 실행 버튼)
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # --- Local 데이터 그룹 (Import / Export) ---
        self.btn_import_excel = QPushButton("Import Excel")
        self.btn_export_excel = QPushButton("Export Excel")

        toolbar.addWidget(self.btn_import_excel)
        toolbar.addWidget(self.btn_export_excel)
        toolbar.addSeparator()

        # --- Sync / JIRA 그룹 (Full Sync만 상단에 유지) ---
        self.btn_full_sync = QPushButton("Full Sync (Tree)")
        toolbar.addWidget(self.btn_full_sync)

        # 아이콘 및 툴팁 설정
        style = self.style()

        # Local
        self.btn_import_excel.setIcon(style.standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_import_excel.setToolTip("Import project data from Excel → Local SQLite (Local)")
        self.btn_export_excel.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export_excel.setToolTip("Export current project from Local SQLite → Excel file (Local)")

        # Sync / JIRA
        self.btn_full_sync.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.btn_full_sync.setToolTip("Full sync RTM tree: JIRA → Local SQLite (Tree)")

        # JIRA 필터 입력창 (리본 메뉴 우측, JQL 지원)
        toolbar.addSeparator()
        self.jira_filter_edit = QLineEdit()
        self.jira_filter_edit.setPlaceholderText("JQL or JIRA key (e.g. project = KVHSICCU)")
        self.jira_filter_edit.returnPressed.connect(self.on_jira_filter_search)
        toolbar.addWidget(self.jira_filter_edit)

        # 중앙 위젯: 좌/우(기본) 또는 상/하(옵션) 배치를 위한 스플리터
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.left_panel = PanelWidget("Local (SQLite)", is_online=False)
        self.right_panel = PanelWidget("JIRA RTM (Online)", is_online=True)

        # 중앙 세로 버튼 패널: Pull / Push 를 Local 과 JIRA 영역 사이에 세로 정렬
        self.btn_pull_jira = QPushButton("Pull from JIRA")
        self.btn_push_jira = QPushButton("Push to JIRA")
        mid_panel = QWidget()
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.addStretch()
        mid_layout.addWidget(self.btn_pull_jira)
        mid_layout.addWidget(self.btn_push_jira)
        mid_layout.addStretch()

        # 스플리터와 중앙 패널들을 속성으로 보관 (레이아웃 전환 시 재사용)
        self.main_splitter = splitter
        self.mid_panel = mid_panel

        # 기본 레이아웃 모드: 좌(로컬) / 우(온라인)
        self.layout_mode: str = "horizontal"  # "horizontal" or "vertical"

        splitter.addWidget(self.left_panel)
        splitter.addWidget(mid_panel)
        splitter.addWidget(self.right_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 3)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(splitter)

        self.setCentralWidget(container)

        # 상태바
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_bar = status

        # JIRA 연결 상태 표시 라벨 (항상 보이는 인디케이터)
        from PySide6.QtWidgets import QLabel as _QLabel  # 지역 import 로 순환 방지
        self.jira_status_label = _QLabel()
        self.status_bar.addPermanentWidget(self.jira_status_label)
        self._update_jira_status_label()

        # 좌/우 패널의 모듈 탭바를 MainWindow 핸들러에 연결
        self.left_panel.module_tab_bar.currentChanged.connect(self._on_local_issue_type_tab_changed)
        self.right_panel.module_tab_bar.currentChanged.connect(self._on_online_issue_type_tab_changed)

        # 시그널 연결
        self._connect_signals()

        # 최초 로드: 초기 필터는 Dashboard(None)로 두고 양쪽 트리 모두 로드
        self._on_local_issue_type_tab_changed(self.left_panel.module_tab_bar.currentIndex())
        self._on_online_issue_type_tab_changed(self.right_panel.module_tab_bar.currentIndex())

        # JIRA가 사용 가능한 경우에만 오른쪽 패널 활성화
        if not self.jira_available:
            self.right_panel.setEnabled(False)
            self.status_bar.showMessage("Offline mode (jira_config.json not loaded)")

    # --------------------------------------------------------------------- GUI helpers

    def _update_jira_status_label(self) -> None:
        """
        상태바 우측에 JIRA 연결 상태를 'JIRA: Online / Offline' 으로 표시.
        """
        if getattr(self, "jira_available", False):
            text = "JIRA: Online"
            color = "#007700"
        else:
            text = "JIRA: Offline"
            color = "#AA0000"
        self.jira_status_label.setText(text)
        self.jira_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    # ------------------------------------------------------------------ Top-level module tabs (Local / Online)

    def _issue_type_from_index(self, index: int) -> str | None:
        """
        모듈 탭 인덱스를 이슈 타입 문자열로 변환한다.
        - 0: Dashboard (None 반환, 필터 없음)
        - 1: REQUIREMENT
        - 2: TEST_CASE
        - 3: TEST_PLAN
        - 4: TEST_EXECUTION
        - 5: DEFECT
        """
        mapping = {
            1: "REQUIREMENT",
            2: "TEST_CASE",
            3: "TEST_PLAN",
            4: "TEST_EXECUTION",
            5: "DEFECT",
        }
        return mapping.get(index)

    def _on_local_issue_type_tab_changed(self, index: int) -> None:
        """
        좌측(로컬) 패널의 모듈 탭 변경 시 호출.
        로컬 트리 필터와 상단 로컬 전용 버튼 상태를 업데이트한다.
        """
        self.local_issue_type_filter = self._issue_type_from_index(index)

        # 로컬 패널 헤더의 버튼 텍스트/표시를 이슈 타입에 맞게 조정
        if self.left_panel and hasattr(self.left_panel, "btn_new_issue"):
            it = self.local_issue_type_filter or ""
            text_map = {
                "REQUIREMENT": "Create Requirement",
                "TEST_CASE": "Create Test Case",
                "TEST_PLAN": "Create Test Plan",
                "TEST_EXECUTION": "Create Test Execution",
                "DEFECT": "Create Defect",
            }
            self.left_panel.btn_new_issue.setText(text_map.get(it, "New Issue"))

            # Test Case 상단 액션(Execute / Add to Test Plan / Link to Requirement)은
            # TEST_CASE 탭에서만 표시
            is_tc = it == "TEST_CASE"
            self.left_panel.btn_execute_tc.setVisible(is_tc)
            self.left_panel.btn_add_to_testplan.setVisible(is_tc)
            self.left_panel.btn_link_requirement.setVisible(is_tc)

        # 로컬 트리 재로드
        self.reload_local_tree()

    def _on_online_issue_type_tab_changed(self, index: int) -> None:
        """
        우측(온라인) 패널의 모듈 탭 변경 시 호출.
        온라인 RTM 트리 필터를 업데이트한다.
        """
        self.online_issue_type_filter = self._issue_type_from_index(index)

        if self.jira_available:
            try:
                self.on_refresh_online_tree()
            except Exception:
                # 온라인 트리 로딩 실패는 치명적이지 않으므로 무시
                pass

    # ------------------------------------------------------------------ Test Cases top-level actions (MainWindow)

    def _selected_local_testcase_ids(self) -> list[int]:
        """
        좌측(Local) 트리에서 선택된 TEST_CASE 이슈들의 로컬 ID 리스트를 반환.
        상단 탭이 Test Cases 일 때 Add to Test Plan / Link to Requirement 에서 사용한다.
        """
        ids: list[int] = []
        view = self.left_panel.tree_view
        model = view.model()
        if model is None:
            return ids
        for idx in view.selectedIndexes():
            if idx.column() != 0:
                continue
            item = model.itemFromIndex(idx)
            if not item:
                continue
            node_type = item.data(Qt.UserRole)
            if node_type != "ISSUE":
                continue
            issue_id = item.data(Qt.UserRole + 1)
            issue_type = (item.data(Qt.UserRole + 3) or "").upper()
            if not issue_id or issue_type != "TEST_CASE":
                continue
            try:
                ids.append(int(issue_id))
            except (TypeError, ValueError):
                continue
        return ids

    def on_add_testcases_to_testplan_clicked(self) -> None:
        """
        상단 Test Cases 탭에서 'Add to Test Plan' 버튼:
        - 트리에서 선택된 TEST_CASE 이슈들을 하나의 Test Plan 에 추가한다.
        """
        tc_ids = self._selected_local_testcase_ids()
        if not tc_ids:
            self.status_bar.showMessage("No Test Cases selected in the tree.")
            return

        # 프로젝트 내 TEST_PLAN 목록 조회
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, jira_key, summary
              FROM issues
             WHERE project_id = ? AND is_deleted = 0 AND UPPER(issue_type) = 'TEST_PLAN'
             ORDER BY jira_key, summary
            """,
            (self.project.id,),
        )
        rows = cur.fetchall()
        plans = [dict(r) for r in rows]
        if not plans:
            self.status_bar.showMessage("No TEST_PLAN issues found; cannot add Test Cases.")
            return

        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QDialogButtonBox,
            QListWidget,
            QListWidgetItem,
            QLabel,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Add to Test Plan")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Select a Test Plan to add the selected Test Cases:"))

        lst = QListWidget()
        for p in plans:
            key = p.get("jira_key") or f"ID={p.get('id')}"
            text = key
            if p.get("summary"):
                text += f" - {p.get('summary')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p.get("id"))
            lst.addItem(item)
        vbox.addWidget(lst)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            item = lst.currentItem()
            if not item:
                self.status_bar.showMessage("No Test Plan selected.")
                return
            tp_id = item.data(Qt.UserRole)
            if not tp_id:
                return

            # 기존 매핑을 읽고 선택된 Test Case 들을 추가
            existing = get_testplan_testcases(self.conn, int(tp_id))
            existing_tc_ids = {
                int(r.get("testcase_id")) for r in existing if r.get("testcase_id")
            }
            records = [
                {"testcase_id": int(r["testcase_id"]), "order_no": int(r.get("order_no", 0) or 0)}
                for r in existing
            ]

            for tc_id in tc_ids:
                if tc_id in existing_tc_ids:
                    continue
                records.append({"testcase_id": tc_id, "order_no": 0})

            # order_no 재정렬
            for idx, rec in enumerate(records, start=1):
                rec["order_no"] = idx

            replace_testplan_testcases(self.conn, int(tp_id), records)
            self.status_bar.showMessage(
                f"Added {len(tc_ids)} Test Case(s) to Test Plan (id={tp_id})."
            )
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

    def on_link_testcases_to_requirement_clicked(self) -> None:
        """
        상단 Test Cases 탭에서 'Link to Requirement' 버튼:
        - 트리에서 선택된 TEST_CASE 이슈들을 선택한 Requirement 와 relation 으로 연결한다.
        """
        tc_ids = self._selected_local_testcase_ids()
        if not tc_ids:
            self.status_bar.showMessage("No Test Cases selected in the tree.")
            return

        # 프로젝트 내 REQUIREMENT 목록 조회
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, jira_key, summary
              FROM issues
             WHERE project_id = ? AND is_deleted = 0 AND UPPER(issue_type) = 'REQUIREMENT'
             ORDER BY jira_key, summary
            """,
            (self.project.id,),
        )
        rows = cur.fetchall()
        reqs = [dict(r) for r in rows]
        if not reqs:
            self.status_bar.showMessage("No REQUIREMENT issues found; cannot link.")
            return

        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QDialogButtonBox,
            QListWidget,
            QListWidgetItem,
            QLabel,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Link to Requirement")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("Select a Requirement to link the selected Test Cases:"))

        lst = QListWidget()
        for r in reqs:
            key = r.get("jira_key") or f"ID={r.get('id')}"
            text = key
            if r.get("summary"):
                text += f" - {r.get('summary')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, r.get("id"))
            lst.addItem(item)
        vbox.addWidget(lst)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        vbox.addWidget(btn_box)

        def on_accept():
            item = lst.currentItem()
            if not item:
                self.status_bar.showMessage("No Requirement selected.")
                return
            req_id = item.data(Qt.UserRole)
            if not req_id:
                return

            # Requirement 를 src 로 하는 relations 를 읽고, 선택된 Test Case 들을 추가
            existing_rels = get_relations_for_issue(self.conn, int(req_id))
            existing_dst_ids = {
                int(r.get("dst_issue_id")) for r in existing_rels if r.get("dst_issue_id")
            }
            new_rels = [
                {"dst_issue_id": r.get("dst_issue_id"), "relation_type": r.get("relation_type") or ""}
                for r in existing_rels
            ]
            for tc_id in tc_ids:
                if tc_id in existing_dst_ids:
                    continue
                new_rels.append({"dst_issue_id": tc_id, "relation_type": "Tests"})

            replace_relations_for_issue(self.conn, int(req_id), new_rels)

            # 현재 선택 이슈가 이 Requirement 인 경우, Relations / Requirements / Linked Test Cases 갱신
            if self.current_issue_id == int(req_id):
                rels = get_relations_for_issue(self.conn, int(req_id))
                if hasattr(self.left_panel.issue_tabs, "load_relations"):
                    self.left_panel.issue_tabs.load_relations(rels)
                if hasattr(self.left_panel.issue_tabs, "load_requirements"):
                    reqs2 = [
                        r
                        for r in rels
                        if (r.get("dst_issue_type") or "").upper() == "REQUIREMENT"
                    ]
                    self.left_panel.issue_tabs.load_requirements(reqs2)
                if hasattr(self.left_panel.issue_tabs, "load_linked_testcases"):
                    tcs2 = [
                        r
                        for r in rels
                        if (r.get("dst_issue_type") or "").upper() == "TEST_CASE"
                    ]
                    self.left_panel.issue_tabs.load_linked_testcases(tcs2)

            self.status_bar.showMessage(
                f"Linked {len(tc_ids)} Test Case(s) to Requirement (id={req_id})."
            )
            dlg.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dlg.reject)

        dlg.exec()

        # 로컬/온라인 트리를 현재 필터에 맞게 다시 로드
        self.reload_local_tree()
        if self.jira_available:
            try:
                self.on_refresh_online_tree()
            except Exception:
                # 온라인 트리 로딩 실패는 치명적이지 않으므로 무시
                pass

    def on_jira_filter_search(self) -> None:
        """
        리본 메뉴 우측 JIRA 필터 입력창에서 엔터를 치면,
        입력된 문자열을 JQL 로 간주하고 Jira 검색 REST API
        (예: GET /rest/api/2/search, [Jira REST API 9.12.0](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.0/))
        를 호출하여 Online 패널 트리에 검색 결과를 표시한다.
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("JIRA is not configured; cannot search.")
            return

        text = self.jira_filter_edit.text().strip()
        if not text:
            return

        try:
            # JQL 검색 수행
            res = self.jira_client.search_issues(text, max_results=100)
            issues = res.get("issues") or []

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["JIRA Search Results"])
            root_item = model.invisibleRootItem()

            for issue in issues:
                key = issue.get("key") or ""
                fields = issue.get("fields") or {}
                summary = fields.get("summary") or ""
                issue_type_name = ""
                issuetype = fields.get("issuetype")
                if isinstance(issuetype, dict):
                    issue_type_name = issuetype.get("name") or ""
                # RTM 타입 이름을 로컬 타입(REQUIREMENT/TEST_CASE/...) 으로 매핑
                local_type = map_rtm_type_to_local(issue_type_name) if issue_type_name else ""

                label = f"{key} - {summary}" if summary else key
                item = QStandardItem(label)
                item.setEditable(False)
                # node_type(UserRole) 에 이슈 타입, UserRole+1 에 jira_key 저장 (온라인 트리와 동일 규약)
                item.setData(local_type or issue_type_name.upper(), Qt.UserRole)
                item.setData(key, Qt.UserRole + 1)
                root_item.appendRow(item)

            self.right_panel.tree_view.setModel(model)
            self.right_panel.tree_view.expandAll()
            self.right_panel.tree_view.setSelectionMode(QTreeView.ExtendedSelection)

            # 검색 결과가 있으면 첫 번째 이슈를 자동 선택하여 상세 정보 로드
            if issues:
                first_index = model.index(0, 0)
                if first_index.isValid():
                    self.right_panel.tree_view.setCurrentIndex(first_index)
                    # selectionModel 시그널이 이미 on_online_tree_selection_changed 에 연결되어 있으므로
                    # 여기서 별도 호출은 필요 없음.

            self.status_bar.showMessage(f"JIRA search finished: {len(issues)} issue(s) found.")
        except Exception as e:
            self.status_bar.showMessage(f"Failed to search JIRA: {e}")
            print(f"[ERROR] JIRA JQL search failed for query='{text}': {e}")

    # --------------------------------------------------------------------- Tree + selection handling

    def reload_local_tree(self):
        """
        현재 project 의 folders/issues 를 SQLite 에서 읽어와
        왼쪽(Local) 패널의 QTreeView 에 바인딩한다.
        """
        if not self.project:
            return

        tree_data = fetch_folder_tree(self.conn, self.project.id)

        type_filter = self.local_issue_type_filter

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name"])

        root_item = model.invisibleRootItem()

        # 아이콘 준비: 폴더 / 이슈
        style = self.left_panel.style()
        folder_icon = style.standardIcon(QStyle.SP_DirIcon)
        issue_icon = style.standardIcon(QStyle.SP_FileIcon)

        def add_node(parent_item: QStandardItem, node: Dict[str, Any]) -> bool:
            """
            현재 이슈 타입 필터에 맞는 이슈가 하나도 없는 폴더 서브트리는 숨기고,
            각 이슈 타입 탭마다 '자신에게 해당하는' 폴더 트리만 보이도록 구성한다.

            RETURNS: 이 노드(폴더/이슈)가 실제로 트리에 추가되었는지 여부.
            """
            node_type = node.get("node_type") or "FOLDER"

            # 이슈 노드
            if node_type == "ISSUE":
                issue_type = (node.get("issue_type") or "").upper()
                if type_filter and issue_type != type_filter:
                    return False

                label = node.get("summary") or node.get("jira_key") or f"ISSUE {node.get('id')}"
                item = QStandardItem(label)
                item.setIcon(issue_icon)
                item.setEditable(False)
                item.setData("ISSUE", Qt.UserRole)
                item.setData(node.get("id"), Qt.UserRole + 1)
                item.setData(node.get("jira_key") or "", Qt.UserRole + 2)
                item.setData(node.get("issue_type") or "", Qt.UserRole + 3)
                parent_item.appendRow(item)
                return True

            # 폴더 노드
            label = node.get("name") or f"Folder {node.get('id')}"
            folder_id = str(node.get("id") or "")
            item = QStandardItem(label)
            item.setEditable(False)
            item.setData("FOLDER", Qt.UserRole)
            item.setData(folder_id, Qt.UserRole + 1)
            item.setIcon(folder_icon)

            has_visible_child = False
            for child in node.get("children", []):
                if add_node(item, child):
                    has_visible_child = True

            # 사용자가 로컬에서 생성한 폴더: LOCAL-<TYPE>-<uuid> 형태
            if folder_id.startswith("LOCAL-"):
                parts = folder_id.split("-", 2)
                local_type = parts[1].upper() if len(parts) >= 3 else ""

                # 구버전(타입 정보 없는 LOCAL-xxxx)은 어떤 탭에도 표시하지 않음
                if not local_type:
                    return False

                # 현재 탭 타입과 다른 로컬 폴더는 숨김
                if type_filter and local_type != type_filter:
                    return False

                # 자신의 타입 탭에서는, 자식이 없어도 항상 표시
                parent_item.appendRow(item)
                return True

            # RTM 에서 내려온 폴더는, 현재 타입 이슈/폴더가 하나도 없으면 숨긴다.
            if not has_visible_child:
                return False

            parent_item.appendRow(item)
            return True

        for root in tree_data.get("roots", []):
            add_node(root_item, root)

        self.left_panel.tree_view.setModel(model)
        self.left_panel.tree_view.expandAll()
        self.left_panel.tree_view.setSelectionMode(QTreeView.ExtendedSelection)

        # selectionModel 이 새로 생성되므로, selectionChanged 시그널을 다시 연결한다.
        try:
            self.left_panel.tree_view.selectionModel().selectionChanged.connect(
                self.on_local_tree_selection_changed
            )
        except Exception:
            pass

    # --------------------------------------------------------------------- Local issue create/delete

    def on_new_local_issue_clicked(self):
        """
        현재 선택된 폴더/이슈를 기준으로 새 로컬 이슈를 생성한다.
        - 좌측 모듈 탭(local_issue_type_filter)에 따라 issue_type 결정.
        - 선택이 폴더면 해당 folder_id 하위에 생성.
        - 선택이 이슈면 그 이슈의 folder_id 하위에 생성.
        - 선택이 없으면 folder_id 없이 프로젝트 루트에 생성.
        """
        if not self.project:
            self.status_bar.showMessage("No project loaded; cannot create issue.")
            return

        issue_type = (self.local_issue_type_filter or "REQUIREMENT").upper()

        folder_id: str | None = None
        model = self.left_panel.tree_view.model()
        selection_model = self.left_panel.tree_view.selectionModel()
        if model is not None and selection_model is not None:
            indexes = selection_model.selectedIndexes()
            if indexes:
                item = model.itemFromIndex(indexes[0])
                if item:
                    kind = item.data(Qt.UserRole)
                    if kind == "FOLDER":
                        folder_id = item.data(Qt.UserRole + 1)
                    elif kind == "ISSUE":
                        issue_id = item.data(Qt.UserRole + 1)
                        if issue_id:
                            issue = get_issue_by_id(self.conn, int(issue_id))
                            if issue:
                                folder_id = issue.get("folder_id")

        summary = f"New {issue_type}"
        new_id = create_local_issue(self.conn, self.project.id, issue_type=issue_type, folder_id=folder_id, summary=summary)
        self.logger.info("Created new local issue id=%s, type=%s, folder_id=%s", new_id, issue_type, folder_id)
        self.status_bar.showMessage(f"Created new local issue (type={issue_type}).")
        self.reload_local_tree()

    def on_delete_local_issue_clicked(self):
        """
        현재 선택된 로컬 이슈(복수 선택 포함)를 soft delete 한다(is_deleted=1).
        폴더는 삭제하지 않으며, 이슈가 선택되지 않은 경우 아무 것도 하지 않는다.
        """
        model = self.left_panel.tree_view.model()
        selection_model = self.left_panel.tree_view.selectionModel()
        if model is None or selection_model is None:
            self.status_bar.showMessage("No local tree to delete from.")
            return

        indexes = selection_model.selectedIndexes()
        issue_ids = []
        for idx in indexes:
            item = model.itemFromIndex(idx)
            if item and item.data(Qt.UserRole) == "ISSUE":
                issue_id = item.data(Qt.UserRole + 1)
                if issue_id is not None:
                    issue_ids.append(int(issue_id))

        if not issue_ids:
            self.status_bar.showMessage("No issue selected to delete.")
            return

        # 사용자 확인 (복수 선택 요약)
        count = len(issue_ids)
        ret = QMessageBox.question(
            self,
            "Delete Local Issue",
            f"Delete {count} local issue(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        for iid in issue_ids:
            soft_delete_issue(self.conn, iid)

        self.status_bar.showMessage(f"Deleted {count} local issue(s).")
        self.reload_local_tree()

    # --------------------------------------------------------------------- Local folder create/delete

    def on_add_local_folder_clicked(self):
        """
        현재 선택된 폴더/이슈를 기준으로 새 폴더를 생성한다.
        - 선택이 폴더면 그 하위에
        - 선택이 이슈면 해당 이슈의 folder_id 하위에
        - 선택이 없으면 루트에
        """
        if not self.project:
            self.status_bar.showMessage("No project loaded; cannot create folder.")
            return

        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        folder_parent_id: str | None = None
        model = self.left_panel.tree_view.model()
        selection_model = self.left_panel.tree_view.selectionModel()
        if model is not None and selection_model is not None:
            indexes = selection_model.selectedIndexes()
            if indexes:
                item = model.itemFromIndex(indexes[0])
                if item:
                    kind = item.data(Qt.UserRole)
                    if kind == "FOLDER":
                        folder_parent_id = item.data(Qt.UserRole + 1)
                    elif kind == "ISSUE":
                        issue_id = item.data(Qt.UserRole + 1)
                        if issue_id:
                            issue = get_issue_by_id(self.conn, int(issue_id))
                            if issue:
                                folder_parent_id = issue.get("folder_id")

        issue_type = (self.local_issue_type_filter or "REQUIREMENT").upper()
        new_folder_id = create_folder_node(
            self.conn,
            project_id=self.project.id,
            name=name,
            parent_id=folder_parent_id,
            issue_type=issue_type,
        )
        self.logger.info("Created new folder id=%s under parent=%s", new_folder_id, folder_parent_id)
        self.status_bar.showMessage(f"Created new folder '{name}'.")
        self.reload_local_tree()

    def on_delete_local_folder_clicked(self):
        """
        현재 선택된 폴더를 삭제한다.
        - 하위에 폴더/이슈가 있으면 삭제하지 않고 경고 메시지를 표시.
        """
        model = self.left_panel.tree_view.model()
        selection_model = self.left_panel.tree_view.selectionModel()
        if model is None or selection_model is None:
            self.status_bar.showMessage("No local tree to delete from.")
            return

        indexes = selection_model.selectedIndexes()
        folder_id = None
        for idx in indexes:
            item = model.itemFromIndex(idx)
            if item and item.data(Qt.UserRole) == "FOLDER":
                folder_id = item.data(Qt.UserRole + 1)
                break

        if not folder_id:
            self.status_bar.showMessage("No folder selected to delete.")
            return

        # 사용자 확인
        ret = QMessageBox.question(
            self,
            "Delete Folder",
            "Delete selected folder?\n\n(Only empty folders can be deleted.)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        ok = delete_folder_if_empty(self.conn, str(folder_id))
        if not ok:
            self.status_bar.showMessage("Folder is not empty; cannot delete. Remove child folders/issues first.")
            return

        self.status_bar.showMessage("Folder deleted.")
        self.reload_local_tree()

    def on_local_tree_selection_changed(self, selected, deselected):
        """
        왼쪽(Local) 트리에서 선택된 이슈가 변경되었을 때 Details 탭에 로드하고,
        current_issue_id / current_issue_type 을 갱신한다.
        복수 선택이더라도 Details 탭은 '첫 번째 이슈' 기준으로 표시한다.
        """
        model = self.left_panel.tree_view.model()
        if model is None:
            self.current_issue_id = None
            self.current_issue_type = None
            self.left_panel.issue_tabs.set_issue(None)
            return

        selected_indexes = self.left_panel.tree_view.selectionModel().selectedIndexes()
        issue_id = None
        issue_type = None

        for idx in selected_indexes:
            item = model.itemFromIndex(idx)
            if item and item.data(Qt.UserRole) == "ISSUE":
                issue_id = item.data(Qt.UserRole + 1)
                issue_type = item.data(Qt.UserRole + 3)
                break

        self.current_issue_id = issue_id
        self.current_issue_type = issue_type

        if issue_id is None:
            self.left_panel.issue_tabs.set_issue(None)
            return

        issue = get_issue_by_id(self.conn, issue_id)
        if not issue:
            self.left_panel.issue_tabs.set_issue(None)
            return

        tabs = self.left_panel.issue_tabs
        tabs.set_issue(issue)

        # ------------------------------------------------------------------
        # 하위 탭 데이터 로드 (로컬 DB 기준)
        issue_type = (issue.get("issue_type") or "").upper()

        # Relations (모든 이슈 공통)
        try:
            rels = get_relations_for_issue(self.conn, issue_id)
            if hasattr(tabs, "load_relations"):
                tabs.load_relations(rels)
            # Requirements 탭: relations 중 REQUIREMENT 타입만 필터링
            if hasattr(tabs, "load_requirements"):
                reqs = [r for r in rels if (r.get("dst_issue_type") or "").upper() == "REQUIREMENT"]
                tabs.load_requirements(reqs)
            # Test Cases 탭: relations 중 TEST_CASE 타입만 필터링 (REQUIREMENT / DEFECT 등에서 사용)
            if hasattr(tabs, "load_linked_testcases"):
                tcs = [r for r in rels if (r.get("dst_issue_type") or "").upper() == "TEST_CASE"]
                tabs.load_linked_testcases(tcs)
        except Exception as e_rel:
            print(f"[WARN] Failed to load local relations: {e_rel}")

        # Test Case: Steps 탭 데이터
        if issue_type == "TEST_CASE":
            try:
                steps = get_steps_for_issue(self.conn, issue_id)
                if hasattr(tabs, "load_steps"):
                    tabs.load_steps(steps)
            except Exception as e_steps:
                print(f"[WARN] Failed to load local steps: {e_steps}")

        # Test Plan: Test Cases 탭 (Plan - Test Case 매핑)
        if issue_type == "TEST_PLAN":
            try:
                tp_records = get_testplan_testcases(self.conn, issue_id)
                if hasattr(tabs, "load_testplan_testcases"):
                    tabs.load_testplan_testcases(tp_records)
            except Exception as e_tp:
                print(f"[WARN] Failed to load local test plan testcases: {e_tp}")

        # Test Execution: Executions 탭 (메타 + Test Case Executions)
        if issue_type == "TEST_EXECUTION":
            try:
                te_row = get_or_create_testexecution_for_issue(self.conn, issue_id)
                from backend.db import get_testcase_executions  # local import to avoid circular

                tc_execs = get_testcase_executions(self.conn, te_row["id"])
                if hasattr(tabs, "load_testexecution"):
                    tabs.load_testexecution(te_row, tc_execs)
            except Exception as e_te:
                print(f"[WARN] Failed to load local test execution data: {e_te}")

    # --------------------------------------------------------------------- Online tree selection (JIRA RTM)

    def on_online_tree_selection_changed(self, selected, deselected):
        """
        오른쪽(JIRA RTM Online) 트리에서 이슈를 선택했을 때,
        해당 이슈의 상세 정보를 JIRA REST/RTM API 로 조회하여 우측 이슈 탭에 표시한다.
        """
        if not self.jira_available or not self.jira_client:
            return

        model = self.right_panel.tree_view.model()
        if model is None:
            self.right_panel.issue_tabs.set_issue(None)
            return

        selection_model = self.right_panel.tree_view.selectionModel()
        if selection_model is None:
            self.right_panel.issue_tabs.set_issue(None)
            return

        selected_indexes = selection_model.selectedIndexes()
        if not selected_indexes:
            self.right_panel.issue_tabs.set_issue(None)
            return

        item = model.itemFromIndex(selected_indexes[0])
        if not item:
            self.right_panel.issue_tabs.set_issue(None)
            return

        node_type = (item.data(Qt.UserRole) or "").upper()
        jira_key = item.data(Qt.UserRole + 1) or ""

        # 폴더는 무시
        if node_type == "FOLDER" or not jira_key:
            self.right_panel.issue_tabs.set_issue(None)
            return

        issue_type = node_type  # RTM Tree 에서 오는 type 을 그대로 사용

        tabs = self.right_panel.issue_tabs

        try:
            # 1) 기본 필드: Jira 표준 REST API 로 개별 이슈 조회
            #    (fields 구조를 가진 JSON -> jira_mapping.map_jira_to_local 로 변환)
            jira_issue_json = self.jira_client.get_jira_issue(jira_key)
            updates = jira_mapping.map_jira_to_local(issue_type, jira_issue_json)
            issue_like: Dict[str, Any] = {
                "issue_type": issue_type,
                "jira_key": jira_key,
                **updates,
            }
            tabs.set_issue(issue_like)

            # 2) Relations (Jira issue links)
            try:
                rel_entries = jira_mapping.extract_relations_from_jira(jira_issue_json)
                if hasattr(tabs, "load_relations"):
                    # Online 뷰에서는 dst_issue_id 가 없으므로 None 으로 두고 표시만 한다.
                    rels_for_ui = []
                    for r in rel_entries:
                        rels_for_ui.append(
                            {
                                "relation_type": r.get("relation_type") or "",
                                "dst_issue_id": None,
                                "dst_jira_key": r.get("dst_jira_key") or "",
                                "dst_summary": r.get("dst_summary") or "",
                            }
                        )
                    tabs.load_relations(rels_for_ui)
            except Exception as e_rel:
                print(f"[WARN] Failed to load online relations: {e_rel}")

            # 3) RTM 전용 정보: 예를 들어 Test Case Steps 등은 RTM v1 REST API 사용
            if issue_type == "TEST_CASE":
                try:
                    steps_json = self.jira_client.get_testcase_steps(jira_key)
                    local_steps = jira_mapping.map_jira_testcase_steps_to_local(steps_json)
                    if hasattr(tabs, "load_steps"):
                        tabs.load_steps(local_steps)
                except Exception as e_steps:
                    print(f"[WARN] Failed to load online Test Case steps: {e_steps}")

        except Exception as e:
            self.status_bar.showMessage(f"Failed to load online issue {jira_key}: {e}")
            print(f"[ERROR] Failed to load online issue {jira_key}: {e}")

    # --------------------------------------------------------------------- Full sync / online tree

    def on_full_sync_clicked(self):
        """
        JIRA RTM Tree 전체를 내려 받아(Local DB 동기화) 왼쪽 트리를 재구성한다.
        JIRA 사용이 불가능한 경우에는 동작하지 않는다.
        """
        if not self.jira_available or not self.jira_client or not self.project:
            self.status_bar.showMessage("Cannot full sync: Jira RTM not configured.")
            return

        try:
            self.status_bar.showMessage("Syncing RTM tree from JIRA to local DB...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            sync_tree(self.project, self.jira_client, self.conn)
            self.reload_local_tree()
            # 온라인 트리도 함께 갱신
            self.on_refresh_online_tree()

            self.status_bar.showMessage("Full tree sync completed.")
        except Exception as e:
            self.status_bar.showMessage(f"Full sync failed: {e}")
            print(f"[ERROR] Full sync failed: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def on_refresh_online_tree(self):
        """
        오른쪽(JIRA RTM Online) 패널 트리를 서버에서 직접 조회하여 표시한다.
        - /rest/rtm/1.0/api/tree/{projectId} 응답 구조를 그대로 사용
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("Cannot refresh online tree: Jira RTM not configured.")
            return

        try:
            self.status_bar.showMessage("Loading online RTM tree from JIRA...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            tree = self.jira_client.get_tree()

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["JIRA RTM Tree"])

            root_item = model.invisibleRootItem()

            # 아이콘 준비: 폴더 / 이슈 (온라인 트리)
            style = self.right_panel.style()
            folder_icon = style.standardIcon(QStyle.SP_DirIcon)
            issue_icon = style.standardIcon(QStyle.SP_FileIcon)

            def add_online_node(parent_item: QStandardItem, node: Dict[str, Any]) -> bool:
                """
                RTM 온라인 트리에서도 현재 이슈 타입에 해당하는 서브트리만 보여준다.
                RETURNS: 이 노드가 실제로 추가되었는지 여부.
                """
                node_type = (node.get("type") or "").upper()
                key = node.get("jiraKey") or node.get("key") or ""
                name = node.get("name") or node.get("summary") or key or ""

                type_filter = self.online_issue_type_filter

                # 이슈 노드
                if node_type != "FOLDER":
                    if type_filter and node_type != type_filter:
                        return False
                    if key and name:
                        label = f"{key} - {name}"
                    elif key:
                        label = key
                    else:
                        label = name or "(no key)"

                    item = QStandardItem(label)
                    item.setEditable(False)
                    item.setData(node_type, Qt.UserRole)
                    item.setData(key, Qt.UserRole + 1)
                    item.setIcon(issue_icon)
                    parent_item.appendRow(item)
                    return True

                # 폴더 노드: 하위에 표시 가능한 이슈/폴더가 하나라도 있어야만 표시
                label = f"[Folder] {name}"
                item = QStandardItem(label)
                item.setEditable(False)
                item.setData(node_type, Qt.UserRole)
                item.setData(key, Qt.UserRole + 1)
                item.setIcon(folder_icon)

                has_visible_child = False
                for child in node.get("children", []):
                    if add_online_node(item, child):
                        has_visible_child = True

                if not has_visible_child:
                    return False

                parent_item.appendRow(item)
                return True

            roots: List[Dict[str, Any]] = []
            if isinstance(tree, list):
                roots = tree
            elif isinstance(tree, dict):
                roots = tree.get("roots") or tree.get("children") or []

            for r in roots:
                add_online_node(root_item, r)

            self.right_panel.tree_view.setModel(model)
            self.right_panel.tree_view.expandAll()
            self.right_panel.tree_view.setSelectionMode(QTreeView.ExtendedSelection)

            self.status_bar.showMessage("Online RTM tree refreshed.")
        except Exception as e:
            self.status_bar.showMessage(f"Failed to refresh online tree: {e}")
            print(f"[ERROR] Failed to refresh online tree: {e}")
        finally:
            QApplication.restoreOverrideCursor()



    # ------------------------------------------------------------------ 메뉴바 구성

    def _create_menu_bar(self) -> None:
        """상단 메뉴바에서 주요 기능을 카테고리별로 제공한다."""
        menubar = self.menuBar()

        # File 메뉴: 엑셀 입/출력, 종료
        file_menu = menubar.addMenu("File")
        act_import = QAction("Import from Excel...", self)
        act_import.triggered.connect(self.on_import_excel_clicked)
        act_import.setShortcut(QKeySequence("Ctrl+I"))
        file_menu.addAction(act_import)

        act_export = QAction("Export to Excel...", self)
        act_export.triggered.connect(self.on_export_excel_clicked)
        # 선택 단축키: Ctrl+E
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Local 메뉴: 로컬 이슈 저장, 트리 갱신
        local_menu = menubar.addMenu("Local")
        act_save = QAction("Save Current Issue", self)
        act_save.triggered.connect(self.on_save_issue_clicked)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        local_menu.addAction(act_save)

        act_refresh_tree = QAction("Refresh Local Tree", self)
        act_refresh_tree.triggered.connect(self.on_full_sync_clicked)
        act_refresh_tree.setShortcut(QKeySequence("F5"))
        local_menu.addAction(act_refresh_tree)

        # JIRA / RTM 메뉴: 온라인 연동 기능
        jira_menu = menubar.addMenu("JIRA / RTM")
        act_pull = QAction("Pull from JIRA (Selected)", self)
        act_pull.triggered.connect(self.on_pull_issue_clicked)
        jira_menu.addAction(act_pull)

        act_push = QAction("Push to JIRA (Selected)", self)
        act_push.triggered.connect(self.on_push_issue_clicked)
        jira_menu.addAction(act_push)

        jira_menu.addSeparator()
        act_create = QAction("Create New Issue in JIRA", self)
        act_create.triggered.connect(self.on_create_in_jira_clicked)
        jira_menu.addAction(act_create)

        act_delete = QAction("Delete Issue from JIRA", self)
        act_delete.triggered.connect(self.on_delete_in_jira_clicked)
        jira_menu.addAction(act_delete)

        # View 메뉴: 좌/우(로컬/온라인) 윈도우 표시 및 레이아웃 제어
        view_menu = menubar.addMenu("View")
        self.act_view_local = QAction("Show Local Window", self, checkable=True)
        self.act_view_local.setChecked(True)
        self.act_view_online = QAction("Show Online Window", self, checkable=True)
        self.act_view_online.setChecked(True)

        self.act_view_local.triggered.connect(self._on_toggle_local_window)
        self.act_view_online.triggered.connect(self._on_toggle_online_window)

        view_menu.addAction(self.act_view_local)
        view_menu.addAction(self.act_view_online)

        # 레이아웃(좌/우 vs 상/하) 전환
        layout_menu = view_menu.addMenu("Layout")
        self.act_layout_horizontal = QAction("Left / Right (Local | Online)", self, checkable=True)
        self.act_layout_vertical = QAction("Top / Bottom (Online / Local)", self, checkable=True)
        self.act_layout_horizontal.setChecked(True)

        self.act_layout_horizontal.triggered.connect(self._on_set_layout_horizontal)
        self.act_layout_vertical.triggered.connect(self._on_set_layout_vertical)

        layout_menu.addAction(self.act_layout_horizontal)
        layout_menu.addAction(self.act_layout_vertical)

        # Help 메뉴
        help_menu = menubar.addMenu("Help")
        act_about = QAction("About RTM Local Manager", self)
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

    def _show_about_dialog(self) -> None:
        QMessageBox.information(
            self,
            "About RTM Local Manager",
            "RTM Local Manager\n\n"
            "JIRA RTM 요구사항/테스트/결함을 로컬 SQLite DB와 동기화하여\n"
            "오프라인에서도 편리하게 관리하기 위한 도구입니다.",
        )

    # ------------------------------------------------------------------ View menu handlers

    def _on_toggle_local_window(self, checked: bool) -> None:
        """
        View > Show Local Window 체크박스에 따라 좌측(로컬) 패널 표시/숨김.
        """
        if self.left_panel is None:
            return
        self.left_panel.setVisible(checked)

    def _on_toggle_online_window(self, checked: bool) -> None:
        """
        View > Show Online Window 체크박스에 따라 우측(온라인) 패널 표시/숨김.
        """
        if self.right_panel is None:
            return
        self.right_panel.setVisible(checked)

    # ------------------------------------------------------------------ Layout mode handlers (horizontal / vertical)

    def _set_layout_mode(self, mode: str) -> None:
        """
        중앙 스플리터의 배치를 좌/우(horiz) 또는 상/하(vert, Online/Local)로 전환한다.
        - "horizontal":  Local | [Pull/Push] | Online
        - "vertical"  :  Online
                         [Pull/Push]
                         Local
        """
        mode = mode.lower()
        if mode not in ("horizontal", "vertical"):
            return
        if getattr(self, "layout_mode", None) == mode:
            return

        self.layout_mode = mode

        splitter: QSplitter = self.main_splitter

        if mode == "horizontal":
            splitter.setOrientation(Qt.Horizontal)
            # Left | [Pull/Push] | Right
            splitter.insertWidget(0, self.left_panel)
            splitter.insertWidget(1, self.mid_panel)
            splitter.insertWidget(2, self.right_panel)
        else:
            splitter.setOrientation(Qt.Vertical)
            # Top(Online) / Middle(Pull/Push) / Bottom(Local)
            splitter.insertWidget(0, self.right_panel)
            splitter.insertWidget(1, self.mid_panel)
            splitter.insertWidget(2, self.left_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 3)

    def _on_set_layout_horizontal(self, checked: bool) -> None:
        """
        View > Layout > Left / Right 선택 시 호출.
        """
        if not checked:
            # 다른 액션에 의해 해제되는 경우는 무시
            return
        self.act_layout_vertical.setChecked(False)
        self.act_layout_horizontal.setChecked(True)
        self._set_layout_mode("horizontal")

    def _on_set_layout_vertical(self, checked: bool) -> None:
        """
        View > Layout > Top / Bottom 선택 시 호출.
        """
        if not checked:
            return
        self.act_layout_horizontal.setChecked(False)
        self.act_layout_vertical.setChecked(True)
        self._set_layout_mode("vertical")

    # ------------------------------------------------------------------ Tree context menus (right-click)

    def _on_local_tree_context_menu(self, pos):
        """
        좌측(Local) 트리 우클릭 컨텍스트 메뉴.
        - 복수 선택 지원: 선택된 이슈/폴더에 대해 삭제 메뉴 제공.
        """
        from PySide6.QtWidgets import QMenu

        view = self.left_panel.tree_view
        model = view.model()
        selection_model = view.selectionModel()
        if model is None or selection_model is None:
            return

        indexes = selection_model.selectedIndexes()
        has_issue = False
        has_folder = False
        for idx in indexes:
            item = model.itemFromIndex(idx)
            if not item:
                continue
            kind = item.data(Qt.UserRole)
            if kind == "ISSUE":
                has_issue = True
            elif kind == "FOLDER":
                has_folder = True

        if not (has_issue or has_folder):
            return

        menu = QMenu(view)
        act_del_issue = act_del_folder = None
        if has_issue:
            act_del_issue = menu.addAction("Delete Selected Issue(s)")
        if has_folder:
            act_del_folder = menu.addAction("Delete Selected Folder(s)")

        action = menu.exec(view.viewport().mapToGlobal(pos))
        if action is None:
            return
        if act_del_issue is not None and action == act_del_issue:
            self.on_delete_local_issue_clicked()
        elif act_del_folder is not None and action == act_del_folder:
            self.on_delete_local_folder_clicked()

    def _on_online_tree_context_menu(self, pos):
        """
        우측(온라인 JIRA RTM) 트리 우클릭 컨텍스트 메뉴.
        - 복수 선택된 이슈들에 대해 'Delete in JIRA' 를 호출한다.
        """
        from PySide6.QtWidgets import QMenu

        if not self.jira_available:
            return

        view = self.right_panel.tree_view
        model = view.model()
        selection_model = view.selectionModel()
        if model is None or selection_model is None:
            return

        indexes = selection_model.selectedIndexes()
        has_issue = False
        for idx in indexes:
            item = model.itemFromIndex(idx)
            if item and item.data(Qt.UserRole) == "ISSUE":
                has_issue = True
                break

        if not has_issue:
            return

        menu = QMenu(view)
        act_del = menu.addAction("Delete Selected Issue(s) in JIRA")
        action = menu.exec(view.viewport().mapToGlobal(pos))
        if action is None or action != act_del:
            return

        self._delete_online_issues_in_jira()

    def _connect_signals(self):
        # Full sync 버튼: JIRA 트리 → Local DB → Local Tree reload
        self.btn_full_sync.clicked.connect(self.on_full_sync_clicked)

        # JIRA pull/push (중앙 세로 버튼)
        self.btn_pull_jira.clicked.connect(self.on_pull_issue_clicked)
        self.btn_push_jira.clicked.connect(self.on_push_issue_clicked)

        # Excel Import/Export
        self.btn_import_excel.clicked.connect(self.on_import_excel_clicked)
        self.btn_export_excel.clicked.connect(self.on_export_excel_clicked)

        # Right panel buttons (온라인 관련)
        if self.jira_available:
            self.right_panel.btn_refresh.clicked.connect(self.on_refresh_online_tree)
            self.right_panel.btn_sync_down.clicked.connect(self.on_full_sync_clicked)
            # JIRA create/delete (온라인 패널 헤더에 위치)
            self.right_panel.btn_create_jira.clicked.connect(self.on_create_in_jira_clicked)
            self.right_panel.btn_delete_jira.clicked.connect(self.on_delete_in_jira_clicked)
            # 온라인 패널 트리 selection
            r_selection = self.right_panel.tree_view.selectionModel()
            if r_selection is not None:
                r_selection.selectionChanged.connect(self.on_online_tree_selection_changed)

        # Local panel 트리 selection
        selection_model = self.left_panel.tree_view.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(self.on_local_tree_selection_changed)
        else:
            self.logger.debug("Local tree_view selectionModel is None at _connect_signals; will be connected after model set.")

        # Local panel 폴더/이슈 생성/삭제/저장 버튼
        self.left_panel.btn_add_folder.clicked.connect(self.on_add_local_folder_clicked)
        self.left_panel.btn_delete_folder.clicked.connect(self.on_delete_local_folder_clicked)
        self.left_panel.btn_new_issue.clicked.connect(self.on_new_local_issue_clicked)
        self.left_panel.btn_delete_issue.clicked.connect(self.on_delete_local_issue_clicked)
        self.left_panel.btn_save_issue.clicked.connect(self.on_save_issue_clicked)
        # Test Case 상단 액션들
        self.left_panel.btn_add_to_testplan.clicked.connect(self.on_add_testcases_to_testplan_clicked)
        self.left_panel.btn_link_requirement.clicked.connect(self.on_link_testcases_to_requirement_clicked)
        # Execute 버튼은 향후 Test Execution 흐름과 연계 (현재는 비활성화하거나 후속 구현 예정)
        # self.left_panel.btn_execute_tc.clicked.connect(self.on_execute_testcases_clicked)

        # Local / Online 트리 컨텍스트 메뉴 (우클릭)
        self.left_panel.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.left_panel.tree_view.customContextMenuRequested.connect(self._on_local_tree_context_menu)
        if self.jira_available:
            self.right_panel.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
            self.right_panel.tree_view.customContextMenuRequested.connect(self._on_online_tree_context_menu)

        # 전역 단축키 (추가 보강용, 메뉴 단축키와 중복 가능)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.on_save_issue_clicked)
        QShortcut(QKeySequence("F5"), self, activated=self.on_full_sync_clicked)
        QShortcut(QKeySequence("Ctrl+I"), self, activated=self.on_import_excel_clicked)

        # Details 탭 Activity 새로고침 버튼
        try:
            self.left_panel.issue_tabs.btn_refresh_activity.clicked.connect(
                self.on_refresh_activity_clicked
            )
        except Exception:
            # 방어적: 위젯 초기화 순서 문제가 있을 경우를 대비
            pass


        # --------------------------------------------------------------------- Excel import/export

    def on_export_excel_clicked(self):
        """
        현재 Project 전체를 Excel 파일(.xlsx)로 내보낸다.
        - Issues, TestcaseSteps, Relations, TestPlanTestcases, TestExecutions, TestcaseExecutions 시트 생성
        """
        if not self.project:
            self.status_bar.showMessage("No project loaded; cannot export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Excel",
            "",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if not file_path:
            return

        try:
            excel_io.export_project_to_excel(self.conn, self.project.id, file_path)
            self.status_bar.showMessage(f"Exported project to Excel: {file_path}")
        except Exception as e:
            self.status_bar.showMessage(f"Excel export failed: {e}")
            print(f"[ERROR] Excel export failed: {e}")

    def on_import_excel_clicked(self):
        """
        Excel 파일(.xlsx)에서 데이터를 읽어와 로컬 DB에 병합(import)한다.
        - Issues / TestcaseSteps / Relations 시트를 1차 대상으로 처리
        - Import 후 로컬 트리를 새로고침한다.
        """
        if not self.project:
            self.status_bar.showMessage("No project loaded; cannot import.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import from Excel",
            "",
            "Excel Files (*.xlsx);;All Files (*)",
        )
        if not file_path:
            return

        try:
            excel_io.import_project_from_excel(self.conn, self.project.id, file_path)
            self.reload_local_tree()
            self.status_bar.showMessage(f"Imported data from Excel: {file_path}")
        except Exception as e:
            self.status_bar.showMessage(f"Excel import failed: {e}")
            print(f"[ERROR] Excel import failed: {e}")

    def on_refresh_activity_clicked(self):
        """
        현재 선택된 이슈의 JIRA Comments / History 를 조회하여 Details 탭 Activity 영역에 표시.
        - jira_key 가 없는 로컬 전용 이슈이거나, JIRA 클라이언트가 없으면 메시지 표시만 수행.
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("JIRA is offline; cannot load activity.")
            return

        if self.current_issue_id is None:
            self.status_bar.showMessage("No issue selected; cannot load activity.")
            return

        issue = get_issue_by_id(self.conn, self.current_issue_id)
        if not issue:
            self.status_bar.showMessage("Issue not found in local DB; cannot load activity.")
            return

        jira_key = issue.get("jira_key")
        if not jira_key:
            self.status_bar.showMessage("Selected issue has no JIRA Key; no remote activity.")
            return

        try:
            self.status_bar.showMessage(f"Loading activity from JIRA for {jira_key}...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            data = self.jira_client.get_jira_issue(jira_key, expand="comments,changelog")

            # Comments
            activity_lines: list[str] = []
            fields = data.get("fields", {})
            comments = None
            comment_container = fields.get("comment")
            if isinstance(comment_container, dict):
                comments = comment_container.get("comments")
            if isinstance(comments, list):
                activity_lines.append("=== Comments ===")
                for c in comments:
                    author = (
                        c.get("author", {}).get("displayName")
                        if isinstance(c.get("author"), dict)
                        else ""
                    )
                    created = c.get("created", "")
                    body = c.get("body", "")
                    activity_lines.append(f"- [{created}] {author}:")
                    activity_lines.append(str(body))
                    activity_lines.append("")

            # Changelog (History)
            changelog = data.get("changelog", {})
            histories = changelog.get("histories") if isinstance(changelog, dict) else None
            if isinstance(histories, list) and histories:
                activity_lines.append("=== History ===")
                for h in histories:
                    author = (
                        h.get("author", {}).get("displayName")
                        if isinstance(h.get("author"), dict)
                        else ""
                    )
                    created = h.get("created", "")
                    items = h.get("items") or []
                    activity_lines.append(f"- [{created}] {author}")
                    for it in items:
                        field = it.get("field", "")
                        from_val = it.get("fromString", "")
                        to_val = it.get("toString", "")
                        activity_lines.append(f"    {field}: '{from_val}' → '{to_val}'")
                    activity_lines.append("")

            if not activity_lines:
                activity_text = "No comments or history found for this issue."
            else:
                activity_text = "\n".join(activity_lines)

            self.left_panel.issue_tabs.set_activity_text(activity_text)
            self.status_bar.showMessage(f"Loaded activity from JIRA for {jira_key}")
        except Exception as e:
            self.status_bar.showMessage(f"Failed to load activity: {e}")
            print(f"[ERROR] Failed to load activity for {jira_key}: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    # --------------------------------------------------------------------- JIRA create/delete

    

    # --------------------------------------------------------------------- Local save (Details / Steps / Relations / Plans / Executions)

    def on_save_issue_clicked(self):
        """
        현재 좌측(Local) 패널에서 선택된 이슈에 대해
        - Details 탭 필드
        - Steps (TEST_CASE)
        - Relations (모든 이슈)
        - Test Plan - Test Case 매핑 (TEST_PLAN)
        - Test Execution 메타/케이스 (TEST_EXECUTION)
        를 로컬 SQLite DB에 저장한다.
        """
        if self.current_issue_id is None:
            self.status_bar.showMessage("No issue selected to save.")
            return

        issue = get_issue_by_id(self.conn, self.current_issue_id)
        if not issue:
            self.status_bar.showMessage(f"Issue id={self.current_issue_id} not found in DB.")
            return

        issue_type = issue.get("issue_type")
        tabs = self.left_panel.issue_tabs

        # 1) Details 탭 → issues 테이블 필드 업데이트
        fields: Dict[str, Any] = {
            "summary": tabs.ed_summary.text().strip(),
            "status": tabs.ed_status.text().strip(),
            "priority": tabs.ed_priority.text().strip(),
            "assignee": tabs.ed_assignee.text().strip(),
            "reporter": tabs.ed_reporter.text().strip(),
            "labels": tabs.ed_labels.text().strip(),
            "components": tabs.ed_components.text().strip(),
            "security_level": tabs.ed_security_level.text().strip(),
            "fix_versions": tabs.ed_fix_versions.text().strip(),
            "affects_versions": tabs.ed_affects_versions.text().strip(),
            "epic_link": tabs.ed_epic_link.text().strip(),
            "sprint": tabs.ed_sprint.text().strip(),
            "rtm_environment": tabs.ed_rtm_env.text().strip(),
            "due_date": tabs.ed_due_date.text().strip(),
            "description": tabs.txt_description.toPlainText().strip(),
            "attachments": tabs.ed_attachments.text().strip(),
        }
        if issue_type == "TEST_CASE" and hasattr(tabs, "get_preconditions_text"):
            fields["preconditions"] = tabs.get_preconditions_text()
        # 빈 문자열만 있는 키는 그대로 둬도 무방하지만, 필요시 None 제거도 가능
        update_issue_fields(self.conn, self.current_issue_id, fields)

        # 2) Steps 저장 (TEST_CASE일 때만)
        if issue_type == "TEST_CASE":
            try:
                steps = tabs.collect_steps()
                replace_steps_for_issue(self.conn, self.current_issue_id, steps)
            except Exception as e_steps:
                print(f"[WARN] save steps failed: {e_steps}")

        # 3) Relations 저장 (모든 이슈 공통)
        try:
            rels = tabs.collect_relations()
            replace_relations_for_issue(self.conn, self.current_issue_id, rels)
        except Exception as e_rels:
            print(f"[WARN] save relations failed: {e_rels}")

        # 4) Test Plan - Test Case 매핑 저장
        if issue_type == "TEST_PLAN":
            try:
                tp_records = tabs.collect_testplan_testcases()
                replace_testplan_testcases(self.conn, self.current_issue_id, tp_records)
            except Exception as e_tp:
                print(f"[WARN] save testplan mappings failed: {e_tp}")

        # 5) Test Execution 메타/케이스 저장
        if issue_type == "TEST_EXECUTION":
            try:
                te_fields = tabs.collect_testexecution_meta()
                update_testexecution_for_issue(self.conn, self.current_issue_id, te_fields)

                tce_records = tabs.collect_testcase_executions()
                if tce_records:
                    te_row = get_or_create_testexecution_for_issue(self.conn, self.current_issue_id)
                    replace_testcase_executions(self.conn, te_row["id"], tce_records)
            except Exception as e_te:
                print(f"[WARN] save testexecution data failed: {e_te}")

        self.status_bar.showMessage("Local issue saved.")

        # 트리 레이블(특히 Summary)이 갱신되도록 트리를 다시 로드
        self.reload_local_tree()

    def on_create_in_jira_clicked(self):
        """
        현재 선택된 로컬 이슈를 기준으로 JIRA RTM에 새 엔티티를 생성한다.

        전제:
          - 현재 이슈에 jira_key 가 비어 있어야 한다. (이미 연동된 경우는 update 사용)
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("Cannot create: Jira RTM not configured.")
            return
        if self.current_issue_id is None:
            self.status_bar.showMessage("No issue selected to create in JIRA.")
            return

        issue = get_issue_by_id(self.conn, self.current_issue_id)
        if not issue:
            self.status_bar.showMessage(f"Issue id={self.current_issue_id} not found in DB.")
            return

        issue_type = issue.get("issue_type")
        jira_key = issue.get("jira_key")
        if jira_key:
            self.status_bar.showMessage(f"Issue already has JIRA key ({jira_key}); use Push instead.")
            return

        # 생성 전 로컬 저장 (Details/Steps 등)
        self.on_save_issue_clicked()
        issue = get_issue_by_id(self.conn, self.current_issue_id)

        try:
            self.status_bar.showMessage(f"Creating new {issue_type} in JIRA...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            payload = jira_mapping.build_jira_create_payload(issue_type, issue)
            resp = self.jira_client.create_entity(issue_type, payload)

            new_key = None
            if isinstance(resp, dict):
                # 일반 Jira create 응답: {"id": "...", "key": "KVHSICCU-123", ...}
                new_key = resp.get("key") or resp.get("jiraKey") or resp.get("issueKey")

            if not new_key:
                # RTM 환경에 따라 응답 구조가 다를 수 있으므로, 필요 시 로깅 후 사용자에게 알림
                self.status_bar.showMessage("Created entity in JIRA, but could not determine new issue key.")
                print("[WARN] create_entity response without 'key':", resp)
            else:
                from backend.db import update_issue_fields
                update_issue_fields(self.conn, self.current_issue_id, {"jira_key": new_key})
                self.status_bar.showMessage(f"Created in JIRA as {new_key}.")
                # 트리 갱신
                self.reload_local_tree()

        except Exception as e:
            self.status_bar.showMessage(f"Create in JIRA failed: {e}")
            print(f"[ERROR] Create in JIRA failed: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def on_delete_in_jira_clicked(self):
        """
        현재 선택된 로컬 이슈에 연결된 JIRA 엔티티를 삭제한다.

        - 실제로는 RTM / Jira 서버에서 이슈 삭제(또는 RTM 엔티티 삭제)를 시도한다.
        - 로컬 DB의 이슈는 삭제하지 않고, jira_key 만 비워서 "오프라인 전용"으로 남긴다.
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("Cannot delete: Jira RTM not configured.")
            return
        # 현재 단일 선택 기준 삭제는 멀티 삭제 helper를 재사용한다.
        self._delete_online_issues_in_jira()

    # --------------------------------------------------------------------- JIRA issue sync (Details only, skeleton)

    def _delete_online_issues_in_jira(self):
        """
        우측 온라인 트리에서 선택된 이슈들(jira_key 기반)을 JIRA 에서 삭제하고,
        로컬 DB 에서도 해당 jira_key 를 비운다.
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("Cannot delete: Jira RTM not configured.")
            return
        if not self.project:
            self.status_bar.showMessage("No project loaded; cannot delete in JIRA.")
            return

        view = self.right_panel.tree_view
        model = view.model()
        selection_model = view.selectionModel()
        if model is None or selection_model is None:
            self.status_bar.showMessage("No online tree to delete from.")
            return

        from backend.db import update_issue_fields

        indexes = selection_model.selectedIndexes()
        targets = []  # (issue_type, jira_key)
        for idx in indexes:
            item = model.itemFromIndex(idx)
            if not item or item.data(Qt.UserRole) != "ISSUE":
                continue
            jira_key = item.data(Qt.UserRole + 1) or ""
            issue_type = item.data(Qt.UserRole + 2) or ""
            if jira_key:
                targets.append((str(issue_type), str(jira_key)))

        if not targets:
            self.status_bar.showMessage("No online issue selected to delete.")
            return

        count = len(targets)
        ret = QMessageBox.question(
            self,
            "Delete in JIRA",
            f"Delete {count} issue(s) in JIRA?\n\n이 작업은 JIRA 서버에서 실제 이슈 삭제를 시도합니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        try:
            self.status_bar.showMessage(f"Deleting {count} issue(s) in JIRA...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # JIRA 삭제 + 로컬 jira_key 비우기
            for issue_type, jira_key in targets:
                try:
                    self.jira_client.delete_entity(issue_type, jira_key)
                except Exception as e_del:
                    print(f"[ERROR] Failed to delete {jira_key} in JIRA: {e_del}")
                    continue

                # 로컬 DB 에서 jira_key 일치하는 이슈들의 jira_key 를 비운다.
                cur = self.conn.cursor()
                cur.execute(
                    "SELECT id FROM issues WHERE project_id = ? AND jira_key = ? AND is_deleted = 0",
                    (self.project.id, jira_key),
                )
                rows = cur.fetchall()
                for r in rows:
                    update_issue_fields(self.conn, int(r["id"]), {"jira_key": ""})

            self.status_bar.showMessage(f"Deleted {count} issue(s) in JIRA (local issues kept).")
            self.reload_local_tree()
        finally:
            QApplication.restoreOverrideCursor()

# --------------------------------------------------------------------- JIRA issue sync (Details only, skeleton)

    def on_pull_issue_clicked(self):
        """
        선택된 로컬 이슈에 대해 JIRA RTM에서 필드를 가져와 로컬 DB에 반영한다.
        - summary / description / status / priority / assignee / reporter
        - labels / components / security_level / fix_versions / affects_versions
        - rtm_environment / due_date / created / updated / attachments
        - (TEST_CASE일 경우) Steps 정보까지 testcase_steps 테이블에 동기화
        - (TEST_PLAN일 경우) Test Plan - Test Case 매핑 동기화
        - (TEST_EXECUTION일 경우) Test Execution 메타 + Test Case Execution 목록 동기화
        - Relations (Jira issue links) 를 relations 테이블로 동기화
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("Cannot pull: Jira RTM not configured.")
            return
        if self.current_issue_id is None:
            self.status_bar.showMessage("No issue selected to pull from JIRA.")
            return

        # 로컬 이슈 정보 조회
        issue = get_issue_by_id(self.conn, self.current_issue_id)
        if not issue:
            self.status_bar.showMessage(f"Issue id={self.current_issue_id} not found in DB.")
            return

        issue_type = issue.get("issue_type")
        jira_key = issue.get("jira_key")
        if not jira_key:
            self.status_bar.showMessage("Selected issue has no JIRA key; cannot pull.")
            return

        try:
            self.status_bar.showMessage(f"Pulling from JIRA: {jira_key} ({issue_type})...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # 1) JIRA RTM 엔티티 조회
            data = self.jira_client.get_entity(issue_type, jira_key)

            # 2) mapping layer 사용하여 로컬 필드 업데이트 dict 생성
            updates = jira_mapping.map_jira_to_local(issue_type, data)

            if updates:
                update_issue_fields(self.conn, self.current_issue_id, updates)

            # 3) Test Case인 경우: Steps도 별도 endpoint를 통해 동기화
            if issue_type == "TEST_CASE":
                try:
                    steps_json = self.jira_client.get_testcase_steps(jira_key)
                    local_steps = jira_mapping.map_jira_testcase_steps_to_local(steps_json)
                    from backend.db import replace_steps_for_issue  # local import to avoid circular issues
                    replace_steps_for_issue(self.conn, self.current_issue_id, local_steps)
                    # UI 갱신
                    if hasattr(self.left_panel.issue_tabs, "load_steps"):
                        self.left_panel.issue_tabs.load_steps(local_steps)
                except Exception as e_steps:
                    # Steps 동기화 실패는 치명적 에러로 간주하지 않고 로그만 남김
                    print(f"[WARN] Failed to sync Test Case steps from JIRA: {e_steps}")

            # 4) Test Plan인 경우: Test Case 매핑 동기화
            if issue_type == "TEST_PLAN":
                try:
                    tp_json = self.jira_client.get_testplan_testcases(jira_key)
                    tp_items = jira_mapping.map_jira_testplan_testcases_to_local(tp_json)
                    from backend.db import replace_testplan_testcases, get_testplan_testcases
                    # testcase_key -> local testcase_id 로 변환
                    from backend.db import get_issue_by_jira_key
                    records = []
                    for item in tp_items:
                        tc_key = item.get("testcase_key")
                        if not tc_key:
                            continue
                        tc_issue = get_issue_by_jira_key(self.conn, self.project.id, tc_key)
                        if not tc_issue:
                            # 로컬에 없는 TC는 스킵
                            continue
                        records.append(
                            {
                                "order_no": item.get("order_no") or 0,
                                "testcase_id": tc_issue["id"],
                            }
                        )
                    if records:
                        replace_testplan_testcases(self.conn, self.current_issue_id, records)
                        tp_rels = get_testplan_testcases(self.conn, self.current_issue_id)
                        if hasattr(self.left_panel.issue_tabs, "load_testplan_testcases"):
                            self.left_panel.issue_tabs.load_testplan_testcases(tp_rels)
                except Exception as e_tp:
                    print(f"[WARN] Failed to sync Test Plan testcases from JIRA: {e_tp}")

            # 5) Test Execution인 경우: 메타 + Test Case Execution 동기화
            if issue_type == "TEST_EXECUTION":
                try:
                    te_json = self.jira_client.get_testexecution_details(jira_key)
                    from backend.db import get_or_create_testexecution_for_issue, update_testexecution_for_issue, get_testcase_executions, replace_testcase_executions
                    te_meta = jira_mapping.map_jira_testexecution_meta_to_local(te_json)
                    if te_meta:
                        # get_or_create 를 이용해 id 확보 후 메타 업데이트
                        te_row = get_or_create_testexecution_for_issue(self.conn, self.current_issue_id)
                        update_testexecution_for_issue(self.conn, self.current_issue_id, te_meta)
                    # Test Case Execution 목록
                    tce_json = self.jira_client.get_testexecution_testcases(jira_key)
                    tce_items = jira_mapping.map_jira_testexecution_testcases_to_local(tce_json)
                    if tce_items:
                        # testcase_key -> local testcase_id 매핑 필요
                        from backend.db import get_issue_by_jira_key
                        tce_records = []
                        for item in tce_items:
                            tc_key = item.get("testcase_key")
                            if not tc_key:
                                continue
                            tc_issue = get_issue_by_jira_key(self.conn, self.project.id, tc_key)
                            if not tc_issue:
                                continue
                            tce_records.append(
                                {
                                    "order_no": item.get("order_no") or 0,
                                    "testcase_id": tc_issue["id"],
                                    "assignee": item.get("assignee") or "",
                                    "result": item.get("result") or "",
                                    "rtm_environment": item.get("rtm_environment") or "",
                                    "defects": item.get("defects") or "",
                                }
                            )
                        if tce_records:
                            # 다시 get_or_create로 testexecution id 확보 후 replace
                            te_row = get_or_create_testexecution_for_issue(self.conn, self.current_issue_id)
                            replace_testcase_executions(self.conn, te_row["id"], tce_records)
                            # UI 갱신: Executions 탭
                            execs = get_testcase_executions(self.conn, te_row["id"])
                            if hasattr(self.left_panel.issue_tabs, "load_testcase_executions"):
                                self.left_panel.issue_tabs.load_testcase_executions(execs)
                except Exception as e_te:
                    print(f"[WARN] Failed to sync Test Execution from JIRA: {e_te}")

            # 6) Jira issue links -> local relations 동기화
            try:
                rel_entries = jira_mapping.extract_relations_from_jira(data)
                if rel_entries:
                    from backend.db import replace_relations_for_issue, get_relations_for_issue, get_issue_by_jira_key
                    # dst_jira_key 를 로컬 issue_id 로 변환
                    rel_records = []
                    for rel in rel_entries:
                        dst_key = rel.get("dst_jira_key")
                        rel_type = rel.get("relation_type") or ""
                        if not dst_key:
                            continue
                        dst_issue = get_issue_by_jira_key(self.conn, self.project.id, dst_key)
                        if not dst_issue:
                            # 아직 트리에 존재하지 않는 이슈는 스킵
                            continue
                        rel_records.append(
                            {
                                "dst_issue_id": dst_issue["id"],
                                "relation_type": rel_type,
                            }
                        )
                    if rel_records:
                        replace_relations_for_issue(self.conn, self.current_issue_id, rel_records)
                        # UI 갱신: Relations / Requirements 탭
                        rels = get_relations_for_issue(self.conn, self.current_issue_id)
                        if hasattr(self.left_panel.issue_tabs, "load_relations"):
                            self.left_panel.issue_tabs.load_relations(rels)
                        if hasattr(self.left_panel.issue_tabs, "load_requirements"):
                            reqs = [r for r in rels if r.get("dst_issue_type") == "REQUIREMENT"]
                            self.left_panel.issue_tabs.load_requirements(reqs)
                        if hasattr(self.left_panel.issue_tabs, "load_linked_testcases"):
                            tcs = [
                                r
                                for r in rels
                                if (r.get("dst_issue_type") or "").upper() == "TEST_CASE"
                            ]
                            self.left_panel.issue_tabs.load_linked_testcases(tcs)
            except Exception as e_rel:
                print(f"[WARN] Failed to sync relations from JIRA: {e_rel}")

            if updates:
                self.status_bar.showMessage(f"Pulled from JIRA and updated local issue {jira_key}.")
                self.reload_local_tree()
            else:
                self.status_bar.showMessage("No mappable fields from JIRA response.")

        except Exception as e:
            self.status_bar.showMessage(f"Pull from JIRA failed: {e}")
            print(f"[ERROR] Pull from JIRA failed: {e}")
        finally:
            QApplication.restoreOverrideCursor()
    def on_push_issue_clicked(self):
        """
        선택된 로컬 이슈의 필드(Details 탭 기준 중 안전한 범위)를 JIRA RTM에 업데이트한다.
        - summary / description / labels / components / duedate / environment
        - (TEST_CASE일 경우) testcase_steps 내용을 RTM Test Case Steps로 함께 업데이트
        - (TEST_PLAN일 경우) Test Plan - Test Case 매핑을 RTM으로 업데이트
        - (TEST_EXECUTION일 경우) Test Execution 메타 + Test Case Execution 목록을 RTM으로 업데이트
        - 로컬 relations 를 기준으로 Jira issueLink 를 생성 (단순 skeleton, 중복 링크 체크는 미구현)
        (status / priority / assignee / reporter 등은 기본 매핑에서 제외)
        """
        if not self.jira_available or not self.jira_client:
            self.status_bar.showMessage("Cannot push: Jira RTM not configured.")
            return
        if self.current_issue_id is None:
            self.status_bar.showMessage("No issue selected to push to JIRA.")
            return

        # 먼저 로컬 DB에 저장(Details/Steps/Relations 등)
        self.on_save_issue_clicked()

        issue = get_issue_by_id(self.conn, self.current_issue_id)
        if not issue:
            self.status_bar.showMessage(f"Issue id={self.current_issue_id} not found in DB.")
            return

        issue_type = issue.get("issue_type")
        jira_key = issue.get("jira_key")
        if not jira_key:
            self.status_bar.showMessage("Selected issue has no JIRA key; cannot push.")
            return

        # 로컬 필드를 JIRA payload로 변환 (mapping layer 사용)
        payload = jira_mapping.build_jira_update_payload(issue_type, issue)

        try:
            self.status_bar.showMessage(f"Pushing to JIRA: {jira_key} ({issue_type})...")
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # 1) 기본 필드 업데이트
            self.jira_client.update_entity(issue_type, jira_key, payload)

            # 2) Test Case인 경우 Steps도 별도 endpoint로 업데이트
            if issue_type == "TEST_CASE":
                from backend.db import get_steps_for_issue  # local import
                local_steps = get_steps_for_issue(self.conn, self.current_issue_id)
                steps_payload = jira_mapping.build_jira_testcase_steps_payload(local_steps)
                try:
                    self.jira_client.update_testcase_steps(jira_key, steps_payload)
                except Exception as e_steps:
                    print(f"[WARN] Failed to push Test Case steps to JIRA: {e_steps}")

            # 3) Test Plan인 경우: Test Case 매핑을 RTM에 업데이트
            if issue_type == "TEST_PLAN":
                try:
                    from backend.db import get_testplan_testcases
                    tp_rels = get_testplan_testcases(self.conn, self.current_issue_id)
                    # tp_rels 는 join 결과로 testcase_jira_key 또는 jira_key 포함하도록 설계되어 있음
                    tp_payload = jira_mapping.build_jira_testplan_testcases_payload(tp_rels)
                    self.jira_client.update_testplan_testcases(jira_key, tp_payload)
                except Exception as e_tp:
                    print(f"[WARN] Failed to push Test Plan testcases to JIRA: {e_tp}")

            # 4) Test Execution인 경우: 메타 + Test Case Execution 목록을 RTM에 업데이트
            if issue_type == "TEST_EXECUTION":
                try:
                    from backend.db import get_or_create_testexecution_for_issue, get_testcase_executions
                    te_row = get_or_create_testexecution_for_issue(self.conn, self.current_issue_id)
                    # te_row 에는 이미 최신 메타가 저장되어 있다고 가정
                    te_meta = {
                        "environment": te_row.get("environment"),
                        "start_date": te_row.get("start_date"),
                        "end_date": te_row.get("end_date"),
                        "result": te_row.get("result"),
                        "executed_by": te_row.get("executed_by"),
                    }
                    te_payload = jira_mapping.build_jira_testexecution_payload(te_meta)
                    self.jira_client.update_testexecution(jira_key, te_payload)

                    # Test Case Executions
                    tce_records = get_testcase_executions(self.conn, te_row["id"])
                    tce_payload = jira_mapping.build_jira_testexecution_testcases_payload(tce_records)
                    self.jira_client.update_testexecution_testcases(jira_key, tce_payload)
                except Exception as e_te:
                    print(f"[WARN] Failed to push Test Execution to JIRA: {e_te}")

            # 5) Relations -> Jira issueLink 생성 (skeleton)
            try:
                from backend.db import get_relations_for_issue
                rels = get_relations_for_issue(self.conn, self.current_issue_id)
                for rel in rels:
                    dst_issue_id = rel.get("dst_issue_id")
                    if not dst_issue_id:
                        continue
                    dst_issue = get_issue_by_id(self.conn, dst_issue_id)
                    if not dst_issue:
                        continue
                    dst_key = dst_issue.get("jira_key")
                    if not dst_key:
                        continue

                    rel_type = rel.get("relation_type") or ""
                    # relation_type 예: "Relates (out)", "Relates (in)"
                    base_type = rel_type
                    direction = "out"
                    if "(" in rel_type and rel_type.endswith(")"):
                        base_type, paren = rel_type.rsplit("(", 1)
                        base_type = base_type.strip()
                        direction = paren[:-1].strip()
                    if not base_type:
                        base_type = "Relates"

                    # 방향에 따라 inward/outward 설정
                    if direction == "in":
                        inward_key = dst_key
                        outward_key = jira_key
                    else:
                        inward_key = jira_key
                        outward_key = dst_key

                    try:
                        self.jira_client.create_issue_link(base_type, inward_key, outward_key)
                    except Exception as e_link:
                        print(f"[WARN] Failed to create issue link {base_type} between {jira_key} and {dst_key}: {e_link}")
            except Exception as e_rel:
                print(f"[WARN] Failed to push relations to JIRA: {e_rel}")

            self.status_bar.showMessage(f"Pushed local changes to JIRA for {jira_key}.")

        except Exception as e:
            self.status_bar.showMessage(f"Push to JIRA failed: {e}")
            print(f"[ERROR] Push to JIRA failed: {e}")
        finally:
            QApplication.restoreOverrideCursor()


def run(db_path: str = "rtm_local.db", config_path: str = "jira_config.json") -> None:
    """
    애플리케이션 엔트리 포인트.

    예:
        from gui.main_window import run
        run()

    또는 main.py 에서 실행:
        python main.py
    """
    app = QApplication(sys.argv)
    win = MainWindow(db_path=db_path, config_path=config_path, mode="both")
    win.show()
    sys.exit(app.exec())