import json
import os
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    QSplitter, Qt, QWidget, QTextEdit
)
from aqt import mw
import markdown
from aqt.utils import showInfo

class ConfigDialog(QDialog):
    def __init__(self, addon_name: str, config_manager_cls, parent=None):
        super().__init__(parent or mw)
        # Initialize dialog window with title and modality
        self.setWindowTitle(f"{addon_name} Add-on Configuration")
        self.setWindowFlags(Qt.Window)
        self.setWindowModality(Qt.ApplicationModal)
        self.setGeometry(200, 200, 850, 1000)

        self.addon_name = addon_name
        self.config_manager = config_manager_cls(self.addon_name)

        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Configuration Settings"))

        # JSON editor for the config
        self.config_editor = QTextEdit()
        self.config_editor.setPlainText(json.dumps(self.config_manager.config, indent=4))
        self.config_editor.setMinimumSize(180, 180)
        self.config_editor.setMaximumWidth(350)
        left_panel.addWidget(self.config_editor, stretch=6)

        # Buttons for restore/save
        button_layout = QHBoxLayout()
        restore_button = QPushButton("Restore Defaults")
        restore_button.clicked.connect(self.restore_defaults)
        button_layout.addWidget(restore_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_config)
        button_layout.addWidget(save_button)

        left_panel.addLayout(button_layout)

        # Load and style help text (Markdown guide)
        self.help_text = QTextBrowser()
        self.help_text.setOpenExternalLinks(True)
        self.help_text.setHtml(self.load_guide())
        self.help_text.setMinimumSize(200, 200)
        self.help_text.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
                padding: 2px; 
                margin: 2px; 
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
                margin: 0px 1px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 100, 100, 0.4);
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(100, 100, 100, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        # Set up horizontal splitter between config and guide
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.help_text)

        # Initial width allocation
        initial_config_width = min(400, int(self.width() * 0.6))
        initial_guide_width = self.width() - initial_config_width
        splitter.setSizes([initial_config_width, initial_guide_width])

        # Dynamically adjust splitter ratio on resize
        def adjust_splitter():
            total_width = self.width()
            extra_width = max(0, total_width - 800)
            guide_extra = extra_width * (2.5 / 3.5)
            config_extra = extra_width * (1 / 3.5)
            splitter.setSizes([
                int(min(400, initial_config_width + config_extra)),
                int(max(200, initial_guide_width + guide_extra)),
            ])
        self.resizeEvent = lambda event: adjust_splitter()

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        self.raise_()
        self.activateWindow()

    def load_guide(self):
        # Try to load 'config.md' for help panel from the add-on folder
        guide_path = os.path.join(mw.addonManager.addonsFolder(), self.addon_name, "config.md")
        try:
            with open(guide_path, "r", encoding="utf-8") as file:
                return markdown.markdown(file.read())
        except FileNotFoundError:
            return "<b>Configuration Guide Not Found.</b>"

    def save_config(self):
        # Save user-edited config after validating JSON
        try:
            new_config = json.loads(self.config_editor.toPlainText())
            self.config_manager.save_config(new_config)
            self.config_editor.setPlainText(json.dumps(new_config, indent=4))
            showInfo("Configuration Saved!")
        except json.JSONDecodeError:
            showInfo("Error: Invalid JSON format. Please check your input.")

    def restore_defaults(self):
        # Load config.json from assets/ first, fallback to root
        addon_path = os.path.join(mw.addonManager.addonsFolder(), self.addon_name)
        assets_path = os.path.join(addon_path, "assets", "config.json")
        default_path = os.path.join(addon_path, "config.json")
        config_path = assets_path if os.path.exists(assets_path) else default_path
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                default_config = json.load(file)
            self.config_manager.save_config(default_config)
            self.config_editor.setPlainText(json.dumps(default_config, indent=4))
            showInfo("Defaults Restored.")
        except FileNotFoundError:
            showInfo("Error: config.json file not found.")
        except json.JSONDecodeError:
            showInfo("Error: config.json is not a valid JSON.")