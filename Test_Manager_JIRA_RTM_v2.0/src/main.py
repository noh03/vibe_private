import sys
import os
from PyQt6.QtWidgets import QApplication

# v2.0용 src 디렉터리를 import 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from database.db_manager import db_manager


def main():
    # Database 초기화
    db_manager.init_db()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


