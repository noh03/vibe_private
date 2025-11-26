import sys
import os
from PyQt6.QtWidgets import QApplication

# Add src directory to python path to handle imports correctly if running from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from database.db_manager import db_manager

def main():
    # Initialize Database
    db_manager.init_db()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()