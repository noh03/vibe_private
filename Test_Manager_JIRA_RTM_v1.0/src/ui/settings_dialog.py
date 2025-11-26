from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox
import json
import os

SETTINGS_FILE = "settings.json"

class JiraSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JIRA Settings")
        self.resize(400, 150)
        
        self.layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.url_edit = QLineEdit()
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("JIRA URL:", self.url_edit)
        form_layout.addRow("Personal Access Token:", self.token_edit)
        self.layout.addLayout(form_layout)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.save_settings_and_accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        
        self.load_settings()
        
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.url_edit.setText(data.get("url", ""))
                    self.token_edit.setText(data.get("token", ""))
            except:
                pass
                
    def save_settings_and_accept(self):
        self.save_settings()
        self.accept()

    def save_settings(self):
        data = {
            "url": self.url_edit.text(),
            "token": self.token_edit.text()
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
            
    def get_settings(self):
        return self.url_edit.text(), self.token_edit.text()

