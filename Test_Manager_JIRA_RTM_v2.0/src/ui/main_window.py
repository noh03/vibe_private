import random

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QWidget,
    QVBoxLayout,
    QToolBar,
    QFileDialog,
    QMessageBox,
    QToolButton,
    QHBoxLayout,
    QPushButton,
    QMenu,
    QTableWidgetItem,
)

from .tree_view import IssueTreeView
from .detail_view import IssueDetailView
from .settings_dialog import JiraSettingsDialog
from .link_dialog import LinkIssueDialog
from database.repository import issue_repository
from utils.excel_manager import excel_manager
from api.jira_client import JiraClient, JiraSettings
from services.sync_service import SyncService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JIRA RTM Manager v2.0")
        self.resize(1400, 900)

        self.jira_client: JiraClient | None = None
        self.sync_service: SyncService | None = None
        self.init_menubar()
        self.init_toolbar()
        self.init_ui()
        self.statusBar().showMessage("준비됨")

    # 메뉴바 설정
    def init_menubar(self):
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일(&F)")

        new_req_action = QAction("새 Requirement(&R)", self)
        new_req_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        new_req_action.triggered.connect(lambda: self.add_local_issue_btn("Requirement"))
        file_menu.addAction(new_req_action)

        new_tc_action = QAction("새 Test Case(&C)", self)
        new_tc_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        new_tc_action.triggered.connect(lambda: self.add_local_issue_btn("Test Case"))
        file_menu.addAction(new_tc_action)

        file_menu.addSeparator()

        import_action = QAction("엑셀 가져오기(&I)", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self.import_excel)
        file_menu.addAction(import_action)

        export_action = QAction("엑셀 내보내기(&E)", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_excel)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # JIRA 메뉴
        jira_menu = menubar.addMenu("JIRA(&J)")

        sync_action = QAction("JIRA 동기화(&S)", self)
        sync_action.setShortcut(QKeySequence("F5"))
        sync_action.triggered.connect(self.sync_with_jira)
        jira_menu.addAction(sync_action)

        push_action = QAction("로컬 변경 JIRA로 보내기(&P)", self)
        push_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        push_action.triggered.connect(self.push_local_changes)
        jira_menu.addAction(push_action)

        # 편집 메뉴
        edit_menu = menubar.addMenu("편집(&E)")

        save_action = QAction("현재 이슈 저장(&S)", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_local_issue)
        edit_menu.addAction(save_action)

        delete_action = QAction("현재 이슈 삭제(&D)", self)
        delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        delete_action.triggered.connect(self.delete_local_issue_btn)
        edit_menu.addAction(delete_action)

        # 도움말 메뉴 (간단 About)
        help_menu = menubar.addMenu("도움말(&H)")

        about_action = QAction("About", self)
        about_action.triggered.connect(
            lambda: QMessageBox.information(
                self,
                "About",
                "JIRA RTM Manager v2.0\n로컬 RTM 데이터와 JIRA RTM을 동기화하는 도구입니다.",
            )
        )
        help_menu.addAction(about_action)

    def init_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        sync_action = QAction("JIRA 동기화", self)
        sync_action.triggered.connect(self.sync_with_jira)
        sync_action.setToolTip("JIRA RTM과 연결하고 트리를 동기화합니다.")
        toolbar.addAction(sync_action)

        # 로컬 dirty 이슈를 JIRA로 푸시
        push_action = QAction("로컬 변경 JIRA로 보내기", self)
        push_action.triggered.connect(self.push_local_changes)
        push_action.setToolTip("로컬에서 수정된 이슈들을 JIRA 이슈로 반영합니다.")
        toolbar.addAction(push_action)

        toolbar.addSeparator()

        import_action = QAction("엑셀 가져오기", self)
        import_action.triggered.connect(self.import_excel)
        import_action.setToolTip("엑셀 파일에서 이슈/스텝 데이터를 가져옵니다.")
        toolbar.addAction(import_action)

        export_action = QAction("엑셀 내보내기", self)
        export_action.triggered.connect(self.export_excel)
        export_action.setToolTip("현재 로컬 이슈/스텝 데이터를 엑셀로 저장합니다.")
        toolbar.addAction(export_action)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # Local Panel
        self.local_container = QSplitter(Qt.Orientation.Vertical)

        local_top_widget = QWidget()
        local_top_layout = QVBoxLayout(local_top_widget)
        local_top_layout.setContentsMargins(0, 0, 0, 0)

        btn_layout = QHBoxLayout()

        self.add_btn = QToolButton()
        self.add_btn.setText("➕ 이슈 추가")
        self.add_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.add_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        self.add_btn.setToolTip("새 Requirement / Test Case / Test Plan 등을 추가합니다.")

        add_menu = QMenu(self.add_btn)
        for type_name in [
            "Requirement",
            "Test Case",
            "Test Plan",
            "Test Execution",
            "Defect",
            "Folder",
        ]:
            action = add_menu.addAction(type_name)
            action.triggered.connect(
                lambda checked, t=type_name: self.add_local_issue_btn(t)
            )
        self.add_btn.setMenu(add_menu)

        self.del_btn = QPushButton("🗑️ 이슈 삭제")
        self.del_btn.setStyleSheet("padding: 5px;")
        self.del_btn.clicked.connect(self.delete_local_issue_btn)
        self.del_btn.setToolTip("선택한 이슈를 로컬 DB에서 삭제합니다.")

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()

        local_top_layout.addLayout(btn_layout)

        self.local_tree = IssueTreeView("로컬 데이터 (v2.0)")
        local_top_layout.addWidget(self.local_tree)

        self.local_detail = IssueDetailView()

        self.local_container.addWidget(local_top_widget)
        self.local_container.addWidget(self.local_detail)
        self.main_splitter.addWidget(self.local_container)

        # Remote Panel
        self.remote_container = QSplitter(Qt.Orientation.Vertical)
        self.remote_tree = IssueTreeView("JIRA 온라인 데이터")
        self.remote_detail = IssueDetailView()
        self.remote_container.addWidget(self.remote_tree)
        self.remote_container.addWidget(self.remote_detail)
        self.main_splitter.addWidget(self.remote_container)

        self.main_splitter.setSizes([700, 700])

        # Signals
        self.local_tree.tree.itemClicked.connect(self.on_local_tree_clicked)
        self.local_tree.add_issue_requested.connect(self.add_local_issue)
        self.local_tree.delete_issue_requested.connect(self.delete_local_issue)

        self.local_detail.save_btn.clicked.connect(self.save_local_issue)
        self.local_detail.add_link_requested.connect(self.open_link_dialog)

        self.refresh_local_tree()

    def sync_with_jira(self):
        dialog = JiraSettingsDialog(self)
        if dialog.exec():
            url, token = dialog.get_settings()
            if not url or not token:
                QMessageBox.warning(
                    self, "경고", "JIRA URL과 토큰을 모두 입력해 주세요."
                )
                return

            try:
                self.jira_client = JiraClient(JiraSettings(url=url, token=token))
                self.sync_service = SyncService(self.jira_client)
                QMessageBox.information(
                    self, "정보", "JIRA에 연결되었습니다. RTM 트리를 가져오는 중..."
                )

                # 1) 로컬 DB 동기화
                self.sync_service.sync_tree(41500)
                self.refresh_local_tree()

                # 2) 원본 트리를 UI에 그대로 표시 (온라인 뷰)
                tree_data = self.jira_client.get_tree(41500)
                self.remote_tree.tree.clear()
                self.populate_remote_tree(tree_data)

                QMessageBox.information(self, "성공", "JIRA 트리가 로컬/온라인 모두 동기화되었습니다.")

            except Exception as e:
                QMessageBox.critical(self, "오류", f"동기화 실패: {e}")

    def push_local_changes(self):
        if not self.sync_service:
            QMessageBox.warning(
                self,
                "경고",
                "먼저 'JIRA 동기화'를 통해 JIRA에 연결해 주세요.",
            )
            return

        try:
            pushed = self.sync_service.push_dirty_issues(41500)
            if pushed > 0:
                QMessageBox.information(
                    self,
                    "성공",
                    f"로컬 변경 {pushed}건을 JIRA에 반영했습니다.",
                )
                self.refresh_local_tree()
            else:
                QMessageBox.information(
                    self,
                    "정보",
                    "JIRA로 보낼 로컬 변경이 없습니다.",
                )
        except Exception as e:
            QMessageBox.critical(self, "오류", f"변경 반영 실패: {e}")

    def populate_remote_tree(self, data):
        if isinstance(data, list):
            for item in data:
                self.add_remote_item(None, item)
        elif isinstance(data, dict):
            if "roots" in data:
                for item in data["roots"]:
                    self.add_remote_item(None, item)
            else:
                self.add_remote_item(None, data)

    def add_remote_item(self, parent, item_data):
        name = item_data.get("name") or item_data.get("summary") or "No Name"
        key = item_data.get("issueKey") or item_data.get("key") or str(
            item_data.get("id", "")
        )
        status = item_data.get("status", "")

        ui_data = {"summary": name, "key": key, "status": status}
        tree_item = self.remote_tree.add_item(parent, ui_data)

        if "children" in item_data and isinstance(item_data["children"], list):
            for child in item_data["children"]:
                self.add_remote_item(tree_item, child)

    def refresh_local_tree(self, select_issue_key=None):
        self.local_tree.tree.clear()
        issues = issue_repository.get_all_issues()
        issues.sort(key=lambda x: x.get("id", 0))

        # 타입별 그룹 노드 생성
        type_roots: dict[str, object] = {}

        for data in issues:
            if "issue_key" in data:
                data["key"] = data["issue_key"]
            issue_type = data.get("issue_type", "Requirement")

            if issue_type not in type_roots:
                root_data = {
                    "summary": issue_type,
                    "issue_type": "Group",
                }
                root_item = self.local_tree.add_item(None, root_data)
                root_item.setExpanded(True)
                type_roots[issue_type] = root_item

            parent = type_roots[issue_type]
            item = self.local_tree.add_item(parent, data)

            if select_issue_key and data.get("issue_key") == select_issue_key:
                self.local_tree.tree.setCurrentItem(item)

        # 상태바에 로컬/dirty 개수 표시
        self._update_status_bar()

    def add_local_issue(self, parent_item, issue_type):
        self._create_issue_logic(issue_type)

    def add_local_issue_btn(self, issue_type):
        self._create_issue_logic(issue_type)

    def _create_issue_logic(self, issue_type):
        new_key = f"NEW-{random.randint(1000, 9999)}"
        data = {
            "issue_key": new_key,
            "summary": f"New {issue_type}",
            "issue_type": issue_type,
            "status": "Open",
        }
        try:
            created = issue_repository.create_issue(data)
            self.refresh_local_tree(select_issue_key=created.get("issue_key"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create issue: {e}")

    def delete_local_issue(self, item):
        self._delete_issue_logic(item)

    def delete_local_issue_btn(self):
        item = self.local_tree.tree.currentItem()
        if item:
            self._delete_issue_logic(item)
        else:
            QMessageBox.warning(self, "경고", "삭제할 이슈를 먼저 선택해 주세요.")

    def _delete_issue_logic(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and "id" in data:
            confirm = QMessageBox.question(
                self, "확인", f"{data.get('key')} 이슈를 삭제하시겠습니까?"
            )
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    issue_repository.delete_issue(data["id"], data["issue_type"])
                    self.refresh_local_tree()
                except Exception as e:
                    QMessageBox.critical(self, "오류", f"이슈 삭제 실패: {e}")

    def save_local_issue(self):
        issue_id = self.local_detail.current_issue_id
        if not issue_id:
            QMessageBox.warning(self, "경고", "저장할 이슈가 선택되어 있지 않습니다.")
            return

        data = self.local_detail.get_data()
        issue_type = self.local_detail.current_issue_type

        try:
            issue_repository.update_issue(issue_id, issue_type, data)
            # JIRA와 동기화 (연결되어 있을 때만)
            if self.jira_client:
                self._sync_issue_to_jira(issue_id, issue_type)

            QMessageBox.information(self, "성공", "이슈가 저장되었습니다.")
            self.refresh_local_tree()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"이슈 저장 실패: {e}")

    def _sync_issue_to_jira(self, issue_id: int, issue_type: str) -> None:
        """단일 이슈를 JIRA에 반영 (새 이슈는 생성, 기존 이슈는 업데이트)."""
        issue = issue_repository.get_issue(issue_id, issue_type)
        if not issue or not self.jira_client:
            return

        key = issue.get("issue_key")

        # 공통 필드를 JIRA fields 구조로 매핑
        summary = issue.get("summary") or ""
        description = issue.get("description") or ""
        priority = issue.get("priority") or None
        due_date = issue.get("due_date")
        labels = issue.get("labels") or ""
        components = issue.get("components") or ""
        fix_version = issue.get("fix_version") or ""
        affects_version = issue.get("affects_version") or ""

        fields: dict = {
            "summary": summary,
            "description": description,
        }

        if priority:
            fields["priority"] = {"name": priority}

        if due_date:
            try:
                # SQLAlchemy DateTime -> 문자열
                fields["duedate"] = due_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        if labels:
            fields["labels"] = [l.strip() for l in labels.split(",") if l.strip()]

        if components:
            fields["components"] = [{"name": c.strip()} for c in components.split(",") if c.strip()]

        if fix_version:
            fields["fixVersions"] = [{"name": v.strip()} for v in fix_version.split(",") if v.strip()]

        if affects_version:
            fields["versions"] = [{"name": v.strip()} for v in affects_version.split(",") if v.strip()]

        try:
            # 새 이슈 (로컬 키가 NEW-로 시작) -> JIRA에 생성
            if key and key.startswith("NEW-"):
                # TODO: 프로젝트 ID/이슈타입 매핑은 설정화 가능
                result = self.jira_client.create_issue(
                    project_id="41500",
                    issue_type_name=issue_type,
                    summary=summary,
                    description=description,
                    extra_fields=fields,
                )
                jira_key = result.get("key") or result.get("issueKey")
                if jira_key:
                    issue_repository.update_issue_key_and_mark_clean(issue_id, issue_type, jira_key)
            else:
                # 기존 이슈 -> 요약/설명만 간단히 업데이트
                if key:
                    self.jira_client.update_issue(key, fields)
                    issue_repository.mark_issue_synced(issue_id, issue_type)
        except Exception as e:
            # 동기화 실패는 치명적 에러로 보지 않고, 로그/메시지 정도로 처리 가능
            QMessageBox.warning(self, "경고", f"JIRA 동기화 실패: {e}")

    def on_local_tree_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.local_detail.load_issue_data(data)
            key = data.get("key") or data.get("issue_key")
            self.refresh_links(key)

    def open_link_dialog(self):
        # 링크 주체 이슈가 실제로 선택/생성되어 있는지 확인
        issue_id = self.local_detail.current_issue_id
        if not issue_id:
            QMessageBox.warning(
                self, "경고", "링크를 추가할 이슈를 먼저 선택하거나 생성해 주세요."
            )
            return

        # NEW- 키이든 JIRA 키이든, 로컬 이슈 키만 있으면 링크는 생성 가능
        current_data = self.local_detail.current_issue_data or {}
        current_key = current_data.get("issue_key") or self.local_detail.key_label.text()
        if not current_key:
            QMessageBox.warning(
                self, "경고", "현재 이슈의 키를 확인할 수 없습니다."
            )
            return

        all_issues = issue_repository.get_all_issues()
        filtered = [
            i
            for i in all_issues
            if i.get("issue_key") != current_key and i.get("key") != current_key
        ]

        dialog = LinkIssueDialog(filtered, self)
        if dialog.exec():
            target_issue, link_type = dialog.get_data()
            if target_issue:
                target_key = target_issue.get("issue_key", target_issue.get("key"))
                try:
                    issue_repository.add_link(current_key, target_key, link_type)
                    QMessageBox.information(self, "성공", "링크가 생성되었습니다.")
                    self.refresh_links(current_key)
                except Exception as e:
                    QMessageBox.critical(self, "오류", f"링크 생성 실패: {e}")

    def refresh_links(self, key):
        if not key:
            return
        links = issue_repository.get_links(key)

        self.local_detail.relations_list.setRowCount(0)
        for link in links:
            row = self.local_detail.relations_list.rowCount()
            self.local_detail.relations_list.insertRow(row)
            self.local_detail.relations_list.setItem(
                row, 0, QTableWidgetItem(link["link_type"])
            )
            self.local_detail.relations_list.setItem(
                row, 1, QTableWidgetItem(link["other_key"])
            )
            self.local_detail.relations_list.setItem(
                row, 2, QTableWidgetItem(link["direction"])
            )

    def export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "", "Excel Files (*.xlsx)"
        )
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
                QMessageBox.information(
                    self, "성공", "엑셀 내보내기가 완료되었습니다."
                )
            except Exception as e:
                QMessageBox.critical(self, "오류", f"엑셀 내보내기 실패: {str(e)}")

    def import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Excel", "", "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                data = excel_manager.import_data(file_path)
                count = 0
                for issue_data in data.get("issues", []):
                    if "key" in issue_data and "issue_key" not in issue_data:
                        issue_data["issue_key"] = issue_data["key"]

                    if issue_data.get("issue_type") == "Test Case":
                        related_steps = [
                            s
                            for s in data.get("steps", [])
                            if s.get("key") == issue_data.get("key")
                        ]
                        issue_data["steps"] = related_steps

                    issue_repository.create_issue(issue_data)
                    count += 1

                QMessageBox.information(
                    self, "성공", f"{count}개의 이슈를 가져왔습니다."
                )
                self.refresh_local_tree()
            except Exception as e:
                QMessageBox.critical(self, "오류", f"엑셀 가져오기 실패: {str(e)}")

    def _update_status_bar(self):
        """상태바에 로컬 이슈 수 및 dirty 개수 표시"""
        all_issues = issue_repository.get_all_issues()
        total = len(all_issues)
        dirty = len([i for i in all_issues if i.get("sync_status") == "dirty"])
        self.statusBar().showMessage(f"로컬 이슈: {total}개 (미동기화: {dirty}개)")


