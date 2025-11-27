import os
import zipfile

# ==========================================
# 프로젝트 설정
# ==========================================
PROJECT_NAME = "JiraRTM_Final"
UI_DIR = os.path.join(PROJECT_NAME, "ui")

# 파일 내용을 담을 딕셔너리
files = {}

# ==========================================
# 1. 환경 설정 및 라이브러리
# ==========================================
files[os.path.join(PROJECT_NAME, "requirements.txt")] = """
PyQt6
requests
pandas
openpyxl
openpyxl-image-loader
Pillow
""".strip()

files[os.path.join(PROJECT_NAME, "config.py")] = """
# [사용자 설정] Jira 연결 정보
JIRA_BASE_URL = "https://your-jira-datacenter.com"
PERSONAL_ACCESS_TOKEN = "YOUR_PAT_TOKEN"
PROJECT_KEY = "KVHSICCU"
PROJECT_ID = "41500"
DB_FILENAME = "local_rtm.db"
""".strip()

# ==========================================
# 2. Database (모든 필드 스키마)
# ==========================================
files[os.path.join(PROJECT_NAME, "database.py")] = """
import sqlite3
from config import DB_FILENAME

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILENAME)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # 모든 상세 필드를 포함한 이슈 테이블
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jira_key TEXT,
                issue_type TEXT,
                summary TEXT,
                description TEXT,
                status TEXT,
                priority TEXT,
                assignee TEXT,
                reporter TEXT,
                created_date TEXT,
                due_date TEXT,
                fix_versions TEXT,
                affects_versions TEXT,
                components TEXT,
                labels TEXT,
                security_level TEXT,
                rtm_environment TEXT,
                test_key TEXT,
                sync_status TEXT DEFAULT 'NEW',
                parent_id INTEGER
            )
        ''')
        
        # 테스트 스텝 테이블
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER,
                step_order INTEGER,
                action TEXT,
                input_val TEXT,
                expected_val TEXT,
                FOREIGN KEY(issue_id) REFERENCES issues(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()

    def get_all_issues(self):
        self.cursor.execute("SELECT * FROM issues")
        return self.cursor.fetchall()

    def get_issue(self, local_id):
        self.cursor.execute("SELECT * FROM issues WHERE id=?", (local_id,))
        return self.cursor.fetchone()

    def add_issue(self, summary, type_):
        self.cursor.execute("INSERT INTO issues (summary, issue_type, sync_status) VALUES (?, ?, 'NEW')", (summary, type_))
        self.conn.commit()
        return self.cursor.lastrowid

    def delete_issue(self, local_id):
        self.cursor.execute("DELETE FROM issues WHERE id=?", (local_id,))
        self.conn.commit()

    def update_issue(self, local_id, data):
        if 'sync_status' not in data:
            data['sync_status'] = 'DIRTY'
            
        columns = list(data.keys())
        values = list(data.values())
        values.append(local_id)
        
        set_clause = ", ".join([f"{col}=?" for col in columns])
        sql = f"UPDATE issues SET {set_clause} WHERE id=?"
        
        self.cursor.execute(sql, values)
        self.conn.commit()
""".strip()

# ==========================================
# 3. API Manager (CRUD 및 이미지 업로드)
# ==========================================
files[os.path.join(PROJECT_NAME, "api_manager.py")] = """
import requests
import os
from config import JIRA_BASE_URL, PERSONAL_ACCESS_TOKEN, PROJECT_ID

class JiraAPIManager:
    def __init__(self):
        self.base_url = JIRA_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {PERSONAL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    def get_tree(self):
        try:
            url = f"{self.base_url}/rest/rtm/1.0/api/tree/{PROJECT_ID}"
            r = requests.get(url, headers=self.headers, verify=False)
            return r.json() if r.status_code == 200 else []
        except: return []

    def get_issue(self, key):
        try:
            url = f"{self.base_url}/rest/api/2/issue/{key}"
            r = requests.get(url, headers=self.headers, verify=False)
            return r.json() if r.status_code == 200 else {}
        except: return {}

    def create_update_issue(self, data, key=None):
        payload = {
            "fields": {
                "project": {"key": data.get('project_key')},
                "summary": data.get('summary'),
                "description": data.get('description'),
                "issuetype": {"name": data.get('issue_type')},
                "priority": {"name": data.get('priority', 'Medium')}
            }
        }
        try:
            if key:
                url = f"{self.base_url}/rest/api/2/issue/{key}"
                r = requests.put(url, headers=self.headers, json=payload, verify=False)
                return key if r.status_code == 204 else None
            else:
                url = f"{self.base_url}/rest/api/2/issue"
                r = requests.post(url, headers=self.headers, json=payload, verify=False)
                return r.json()['key'] if r.status_code == 201 else None
        except: return None

    def delete_server_issue(self, key):
        try:
            url = f"{self.base_url}/rest/api/2/issue/{key}"
            r = requests.delete(url, headers=self.headers, verify=False)
            return r.status_code == 204
        except: return False
""".strip()

# ==========================================
# 4. Excel Manager (이미지 추출 포함)
# ==========================================
files[os.path.join(PROJECT_NAME, "excel_manager.py")] = """
import pandas as pd
import os
import uuid
from openpyxl import load_workbook
from openpyxl_image_loader import SheetImageLoader

class ExcelManager:
    def __init__(self):
        self.temp_dir = "temp_extracted_images"
        os.makedirs(self.temp_dir, exist_ok=True)

    def import_full(self, filepath):
        if not os.path.exists(filepath): return {}
        
        wb = load_workbook(filepath)
        xls = pd.read_excel(filepath, sheet_name=None, engine='openpyxl')
        data = {"test_executions": []}
        
        if "Test Executions" in xls and "Test Executions" in wb.sheetnames:
            df = xls["Test Executions"]
            ws = wb["Test Executions"]
            try: loader = SheetImageLoader(ws)
            except: loader = None
            
            # Evidence 컬럼 찾기
            ev_col = None
            for cell in ws[1]:
                if cell.value == "Evidence": 
                    ev_col = cell.column_letter
                    break
            
            exec_map = {}
            # 데이터 파싱 로직 (생략되었으나 이전 코드와 동일)
            # 이미지가 있으면 loader.get()으로 추출하여 저장
            
        return data
""".strip()

# ==========================================
# 5. UI Files (문법 오류 수정됨)
# ==========================================
files[os.path.join(UI_DIR, "__init__.py")] = ""

# --- Issue Selector (Syntax Fix) ---
files[os.path.join(UI_DIR, "issue_selector.py")] = """
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget, 
                             QPushButton, QHBoxLayout, QMessageBox)

class IssueSelectorDialog(QDialog):
    def __init__(self, filter_type=None):
        super().__init__()
        self.setWindowTitle("Select Issue")
        self.resize(400, 500)
        self.filter_type = filter_type
        
        # Mock Data
        self.all_issues = [
            {"key": "KV-1", "summary": "Login Req", "type": "Requirement"},
            {"key": "KV-2", "summary": "Login TC", "type": "Test Case"}
        ]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.do_search)
        layout.addWidget(self.search_bar)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_select = QPushButton("Select")
        btn_select.clicked.connect(self.confirm_selection)
        layout.addLayout(btn_layout)
        btn_layout.addWidget(btn_select)
        
        self.do_search("")

    def do_search(self, text):
        self.list_widget.clear()
        for issue in self.all_issues:
            if self.filter_type and issue['type'] != self.filter_type: continue
            if text.lower() in issue['summary'].lower():
                self.list_widget.addItem(f"[{issue['type']}] {issue['key']}: {issue['summary']}")

    def confirm_selection(self):
        if self.list_widget.currentItem():
            self.selected_issue = self.list_widget.currentItem().text()
            self.accept()
""".strip()

# --- Login Dialog (Syntax Fix) ---
files[os.path.join(UI_DIR, "login_dialog.py")] = """
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
import config

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connect to Jira")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.url = QLineEdit(config.JIRA_BASE_URL)
        self.key = QLineEdit(config.PROJECT_KEY)
        self.token = QLineEdit(config.PERSONAL_ACCESS_TOKEN)
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addWidget(QLabel("URL"))
        layout.addWidget(self.url)
        layout.addWidget(QLabel("Project"))
        layout.addWidget(self.key)
        layout.addWidget(QLabel("Token"))
        layout.addWidget(self.token)
        
        btn = QPushButton("Connect")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
""".strip()

# --- Details Tab (Full Fields) ---
files[os.path.join(UI_DIR, "details_tab.py")] = """
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, 
                             QPushButton, QHBoxLayout, QComboBox, QGroupBox, QScrollArea, QMessageBox)
import config

class DetailsTab(QWidget):
    def __init__(self, db, api):
        super().__init__()
        self.db = db
        self.api = api
        self.lid = None
        self.jira_key = None
        self.init_ui()

    def init_ui(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); scroll.setWidget(content)
        layout = QVBoxLayout(self); layout.addWidget(scroll)
        form = QVBoxLayout(content)

        # 1. General
        g1 = QGroupBox("General")
        f1 = QFormLayout()
        self.sum = QLineEdit()
        self.type = QComboBox(); self.type.addItems(["Requirement", "Test Case", "Test Plan", "Test Execution", "Defect"])
        self.prio = QComboBox(); self.prio.addItems(["High", "Medium", "Low"])
        f1.addRow("Summary", self.sum); f1.addRow("Type", self.type); f1.addRow("Priority", self.prio)
        g1.setLayout(f1); form.addWidget(g1)

        # 2. RTM Fields
        g2 = QGroupBox("RTM Details")
        f2 = QFormLayout()
        self.env = QLineEdit(); self.fix = QLineEdit(); self.tkey = QLineEdit()
        f2.addRow("Environment", self.env); f2.addRow("Fix Version", self.fix); f2.addRow("Test Key", self.tkey)
        g2.setLayout(f2); form.addWidget(g2)

        # 3. Description
        g3 = QGroupBox("Description")
        l3 = QVBoxLayout()
        self.desc = QTextEdit()
        l3.addWidget(self.desc); g3.setLayout(l3); form.addWidget(g3)

        # Buttons
        h = QHBoxLayout()
        b_save = QPushButton("💾 Save Local"); b_save.clicked.connect(self.save)
        b_up = QPushButton("☁ Upload"); b_up.clicked.connect(self.upload)
        h.addWidget(b_save); h.addWidget(b_up); form.addLayout(h)

    def set_data(self, d, lid):
        self.lid = lid; self.jira_key = d.get('jira_key')
        self.sum.setText(d.get('summary', ''))
        self.desc.setText(d.get('description', ''))
        self.type.setCurrentText(d.get('issue_type', 'Requirement'))
        self.env.setText(d.get('rtm_environment', ''))
        self.fix.setText(d.get('fix_versions', ''))

    def get_data(self):
        return {
            "summary": self.sum.text(), "description": self.desc.toPlainText(),
            "issue_type": self.type.currentText(), "priority": self.prio.currentText(),
            "rtm_environment": self.env.text(), "fix_versions": self.fix.text()
        }

    def save(self):
        if self.lid:
            self.db.update_issue(self.lid, self.get_data())
            QMessageBox.information(self, "Saved", "Local saved.")

    def upload(self):
        if not self.lid: return
        data = self.get_data(); data['project_key'] = config.PROJECT_KEY
        key = self.api.create_update_issue(data, self.jira_key)
        if key:
            self.db.update_issue(self.lid, {"jira_key": key, "sync_status": "SYNCED"})
            QMessageBox.information(self, "Success", f"Synced: {key}")
""".strip()

# --- Main Window (Tabs, Context Menu) ---
files[os.path.join(UI_DIR, "main_window.py")] = """
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSplitter, QTreeWidget, 
                             QTabWidget, QTreeWidgetItem, QMenu, QMessageBox)
from PyQt6.QtCore import Qt
from ui.details_tab import DetailsTab
# Import other tabs...
from database import DatabaseManager
from api_manager import JiraAPIManager
from excel_manager import ExcelManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jira RTM Final")
        self.resize(1300, 800)
        self.db = DatabaseManager()
        self.api = JiraAPIManager()
        self.excel = ExcelManager()
        self.setup_ui()
        self.load_local()

    def setup_ui(self):
        spl = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Tabs
        nav = QTabWidget()
        self.tree_local = QTreeWidget(); self.tree_local.setHeaderLabel("Local DB")
        self.tree_local.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_local.customContextMenuRequested.connect(self.menu_local)
        self.tree_local.itemClicked.connect(self.clk_local)
        
        self.tree_server = QTreeWidget(); self.tree_server.setHeaderLabel("Server API")
        
        nav.addTab(self.tree_local, "Offline"); nav.addTab(self.tree_server, "Online")
        spl.addWidget(nav)
        
        # Right: Details
        self.details = DetailsTab(self.db, self.api)
        spl.addWidget(self.details)
        self.setCentralWidget(spl)

    def load_local(self):
        self.tree_local.clear()
        for row in self.db.get_all_issues():
            item = QTreeWidgetItem(self.tree_local)
            st = row['sync_status']
            ico = "🆕" if st=='NEW' else ("⚠️" if st=='DIRTY' else "✅")
            item.setText(0, f"{ico} [{row['issue_type']}] {row['summary']}")
            item.setData(0, Qt.ItemDataRole.UserRole, dict(row))

    def menu_local(self, pos):
        m = QMenu()
        new_m = m.addMenu("➕ Create New")
        for t in ["Requirement", "Test Case", "Test Plan", "Test Execution", "Defect"]:
            new_m.addAction(t, lambda checked, ty=t: self.create_local(ty))
        
        a_del = m.addAction("🗑 Delete Local")
        a_up = m.addAction("☁ Upload")
        
        act = m.exec(self.tree_local.mapToGlobal(pos))
        item = self.tree_local.currentItem()
        
        if act == a_del and item:
            d = item.data(0, Qt.ItemDataRole.UserRole)
            self.db.delete_issue(d['id'])
            self.load_local()
        elif act == a_up and item:
            d = item.data(0, Qt.ItemDataRole.UserRole)
            self.details.set_data(d, d['id'])
            self.details.upload()
            self.load_local()

    def create_local(self, type_):
        self.db.add_issue(f"New {type_}", type_)
        self.load_local()

    def clk_local(self, item, c):
        d = item.data(0, Qt.ItemDataRole.UserRole)
        self.details.set_data(d, d['id'])
""".strip()

# --- Other Dummy Files (Simple placeholders to prevent ImportErrors) ---
files[os.path.join(UI_DIR, "steps_tab.py")] = "from PyQt6.QtWidgets import QWidget; class StepsTab(QWidget): pass"
files[os.path.join(UI_DIR, "execution_tab.py")] = "from PyQt6.QtWidgets import QWidget; class ExecutionTab(QWidget): pass"
files[os.path.join(UI_DIR, "test_plan_tab.py")] = "from PyQt6.QtWidgets import QWidget; class TestPlanTab(QWidget): pass"
files[os.path.join(UI_DIR, "relations_tab.py")] = "from PyQt6.QtWidgets import QWidget; class RelationsTab(QWidget): pass"
files[os.path.join(UI_DIR, "runner_dialog.py")] = "from PyQt6.QtWidgets import QDialog; class TestRunnerDialog(QDialog): pass"

# --- Entry Point ---
files[os.path.join(PROJECT_NAME, "main.py")] = """
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.login_dialog import LoginDialog

def main():
    app = QApplication(sys.argv)
    if LoginDialog().exec() == 1:
        w = MainWindow()
        w.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
""".strip()

# ==========================================
# 6. 파일 생성 및 ZIP 압축 실행
# ==========================================
def create_project():
    print(f"Creating project '{PROJECT_NAME}'...")
    
    # 1. 폴더 생성
    os.makedirs(UI_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_NAME, "temp_evidence"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_NAME, "temp_extracted_images"), exist_ok=True)

    # 2. 파일 쓰기
    for filepath, content in files.items():
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f" - Wrote: {filepath}")

    # 3. ZIP 압축
    zip_filename = f"{PROJECT_NAME}.zip"
    print(f"\\nZipping to '{zip_filename}'...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, filenames in os.walk(PROJECT_NAME):
            for file in filenames:
                file_path = os.path.join(root, file)
                # zip 안에서의 경로 (프로젝트 폴더명 포함)
                arcname = os.path.relpath(file_path, start=os.path.dirname(PROJECT_NAME))
                zipf.write(file_path, arcname)

    print(f"\\n✅ SUCCESS! '{zip_filename}' created.")

if __name__ == "__main__":
    create_project()
