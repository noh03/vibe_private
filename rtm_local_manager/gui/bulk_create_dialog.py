"""
bulk_create_dialog.py - 대량 이슈 생성 다이얼로그

로컬 DB의 이슈들을 JIRA RTM에 대량으로 생성하는 진행 상황을 표시합니다.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QDialogButtonBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QWidget,
    QHeaderView,
)
from PySide6.QtCore import Qt


class BulkCreateDialog(QDialog):
    """
    대량 이슈 생성 진행 상황 다이얼로그
    
    Attributes:
        total_issues: 생성할 총 이슈 개수
        progress_bar: 진행률 표시
        log_text: 진행 상황 로그
        results_table: 결과 표시 테이블
    """
    
    def __init__(self, total_issues: int, parent=None):
        super().__init__(parent)
        self.total_issues = total_issues
        self.setWindowTitle("대량 이슈 생성")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self._init_ui()
    
    def _init_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 상태 라벨
        self.status_label = QLabel(f"대량 생성 준비 중: {self.total_issues}개 이슈")
        layout.addWidget(self.status_label)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.total_issues)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 탭 위젯 (로그 / 결과)
        tabs = QTabWidget()
        
        # 로그 탭
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Consolas")
        log_layout.addWidget(self.log_text)
        tabs.addTab(log_tab, "진행 로그")
        
        # 성공 결과 탭
        success_tab = QWidget()
        success_layout = QVBoxLayout(success_tab)
        self.success_table = QTableWidget()
        self.success_table.setColumnCount(4)
        self.success_table.setHorizontalHeaderLabels(["ID", "JIRA Key", "Type", "Summary"])
        self.success_table.horizontalHeader().setStretchLastSection(True)
        success_layout.addWidget(self.success_table)
        tabs.addTab(success_tab, "성공")
        
        # 실패 결과 탭
        failure_tab = QWidget()
        failure_layout = QVBoxLayout(failure_tab)
        self.failure_table = QTableWidget()
        self.failure_table.setColumnCount(4)
        self.failure_table.setHorizontalHeaderLabels(["ID", "Type", "Summary", "Error"])
        self.failure_table.horizontalHeader().setStretchLastSection(True)
        failure_layout.addWidget(self.failure_table)
        tabs.addTab(failure_tab, "실패")
        
        layout.addWidget(tabs)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.btn_close = button_box.button(QDialogButtonBox.Close)
        self.btn_close.setEnabled(False)  # 초기에는 비활성화
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def update_progress(self, message: str, current: int, total: int):
        """진행 상황 업데이트"""
        self.status_label.setText(message)
        self.progress_bar.setValue(current)
        self.log_text.append(f"[{current}/{total}] {message}")
        # 자동 스크롤
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def set_results(self, results: Dict[str, Any]):
        """생성 결과 설정"""
        successes = results.get("successes", [])
        failures = results.get("failures", [])
        
        # 성공 결과 테이블
        self.success_table.setRowCount(len(successes))
        for row, item in enumerate(successes):
            self.success_table.setItem(row, 0, QTableWidgetItem(str(item.get("issue_id", ""))))
            self.success_table.setItem(row, 1, QTableWidgetItem(item.get("jira_key", "")))
            self.success_table.setItem(row, 2, QTableWidgetItem(item.get("issue_type", "")))
            self.success_table.setItem(row, 3, QTableWidgetItem(item.get("summary", "")))
        
        # 실패 결과 테이블
        self.failure_table.setRowCount(len(failures))
        for row, item in enumerate(failures):
            self.failure_table.setItem(row, 0, QTableWidgetItem(str(item.get("issue_id", ""))))
            self.failure_table.setItem(row, 1, QTableWidgetItem(item.get("issue_type", "")))
            self.failure_table.setItem(row, 2, QTableWidgetItem(item.get("summary", "")))
            self.failure_table.setItem(row, 3, QTableWidgetItem(item.get("error", "")))
        
        # 완료 메시지
        success_count = results.get("success_count", 0)
        failure_count = results.get("failure_count", 0)
        self.status_label.setText(
            f"완료: 성공 {success_count}개, 실패 {failure_count}개"
        )
        self.log_text.append(f"\n=== 생성 완료 ===")
        self.log_text.append(f"성공: {success_count}개")
        self.log_text.append(f"실패: {failure_count}개")
        
        # 닫기 버튼 활성화
        self.btn_close.setEnabled(True)

