# This script provides a GUI for editing the toolbar tools in Anki via a table interface.
# It allows users to add, remove, reorder, and save tools defined in tools.json using drag-and-drop.
# GUI editor for managing custom toolbar tools in Anki add-ons.
# Provides a table interface to edit tools.json with support for drag-and-drop reordering.
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QHeaderView, Qt
)
from .utils import _refresh_menu
from aqt.utils import showInfo, showText
import json, os, traceback
import importlib

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
CONFIG = json.load(open(os.path.join(ASSETS, "config.json")))

from aqt.utils import qconnect
from aqt.qt import QFile, QTextStream

# Apply external CSS styling based on Anki theme
def apply_stylesheet(widget):
    # Determine which stylesheet to use based on whether Anki is in night mode or not
    from aqt.theme import theme_manager
    style_name = "Style_toolbar_editor_dark.css" if theme_manager.night_mode else "Style_toolbar_editor_light.css"
    css_path = os.path.join(ASSETS, style_name)
    # Load and apply the CSS file if it exists to style the widget accordingly
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            widget.setStyleSheet(f.read())

# Define the fields used for each tool entry in the table
TOOL_FIELDS = ["name", "module", "function", "submenu", "icon", "enabled"]

# Main dialog for editing the toolbar tools table
class ToolbarManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbarEditorDialog")
        self.setWindowTitle(CONFIG["toolbar_title"])
        self.path = os.path.join(ASSETS, "tools.json")
        self.resize(975, 300)

        self.tools = []

        self.layout = QVBoxLayout(self)

        # Create and configure the table widget to display tool entries
        self.table = QTableWidget(0, len(TOOL_FIELDS))
        self.table.setObjectName("toolbarTable")
        # Set the header labels to correspond to the tool fields
        self.table.setHorizontalHeaderLabels(TOOL_FIELDS)

        # Enable dragging rows from the table
        self.table.setDragEnabled(True)
        # Allow the table widget to accept drops (needed for drag-and-drop reordering)
        self.table.setAcceptDrops(True)
        # Also accept drops on the viewport area of the table for full coverage
        self.table.viewport().setAcceptDrops(True)
        # Show a visual drop indicator when dragging rows to indicate the drop location
        self.table.setDropIndicatorShown(True)
        # Enable internal drag-and-drop for reordering rows within the table
        self.table.setDragDropMode(QAbstractItemView.InternalMove)
        # Prevent drag-and-drop from overwriting existing rows, instead insert at drop position
        self.table.setDragDropOverwriteMode(False)

        # Enable selection of entire rows for easier manipulation
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Restrict selection to a single row at a time to simplify delete and edit operations
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Only allow editing when a cell is double-clicked to prevent accidental edits
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)

        # === Responsive column sizing with individual minimums ===
        field_widths = {
            "name": 125,
            "module": 200,
            "function": 180,
            "submenu": 140,
            "icon": 100,
            "enabled": 70,
        }

        # Restore individual widths and set priorities per column
        for i, field in enumerate(TOOL_FIELDS):
            width = field_widths.get(field, 100)
            self.table.setColumnWidth(i, width)

            if field == "enabled":
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            elif field in ("module", "function", "submenu"):
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
                self.table.horizontalHeader().setMinimumSectionSize(width)
            else:
                self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Interactive)
                self.table.horizontalHeader().setMinimumSectionSize(width)

        # Hide vertical row indices for a cleaner look
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table)

        # Create a horizontal layout for control buttons
        btns = QHBoxLayout()
        self.btn_add = QPushButton("Add")       # Button to add new tool entries
        self.btn_add.setObjectName("btnAddTool")
        self.btn_delete = QPushButton("Delete") # Button to delete selected tool entries
        self.btn_delete.setObjectName("btnDeleteTool")
        self.btn_save = QPushButton("Save")     # Button to save changes to tools.json
        self.btn_save.setObjectName("btnSaveTools")
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_delete)
        btns.addWidget(self.btn_save)
        self.btn_add_divider = QPushButton("Add Divider")
        self.btn_add_divider.setObjectName("btnAddDivider")
        btns.addWidget(self.btn_add_divider)
        self.btn_add_divider.clicked.connect(self.add_divider)
        self.layout.addLayout(btns)

        # Connect button clicks to their respective handler methods
        self.btn_add.clicked.connect(self.add_row)
        self.btn_delete.clicked.connect(self.delete_row)
        self.btn_save.clicked.connect(self.save_tools)

        # Load existing tools from file and populate the table
        self.load_tools()
        # Apply theme-based styling to the dialog
        apply_stylesheet(self)

    # Load tools from tools.json and populate the table
    def load_tools(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self.tools = json.load(f)
            else:
                self.tools = []

            # Clear any existing rows before populating the table
            self.table.setRowCount(0)
            for tool in self.tools:
                name = tool.get("name", "").strip()
                if (
                    tool.get("type") == "separator"
                    or name in ("---", "—", "——", "———", "————", "—————")
                    or name.lower() == "toolbar settings"
                ):
                    continue  # Skip displaying separators and toolbar settings in the editor
                self.add_row(tool)
        except Exception:
            # Show traceback in a text dialog if loading fails
            showText(traceback.format_exc(), title="Load Error")

    # Add a new row to the table, either blank or populated from an existing tool entry
    def add_row(self, tool=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Set a uniform height for all rows in the table for visual consistency.
        self.table.setRowHeight(row, 32)
        tool = tool or {}
        # Provide default values for any missing keys to ensure consistent table display
        tool.setdefault("name", "")
        tool.setdefault("module", "")
        tool.setdefault("function", "")
        tool.setdefault("submenu", CONFIG.get("default_submenu", "None"))
        tool.setdefault("icon", CONFIG.get("default_icon", "icons/bent_menu-burger.svg"))
        tool.setdefault("enabled", True)

        is_divider = tool.get("name", "").strip() in ("---", "—", "——", "———", "————", "—————")

        for col, key in enumerate(TOOL_FIELDS):
            val = str(tool.get(key, "true" if key == "enabled" else ""))
            if is_divider:
                item = QTableWidgetItem("↕ Divider")
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(Qt.gray)
                self.table.setItem(row, col, item)
                continue
            # For the 'enabled' column, render a checkbox to reflect boolean state
            if key == "enabled":
                checkbox = QTableWidgetItem()
                # Make the checkbox user-checkable
                checkbox.setFlags(checkbox.flags() | Qt.ItemIsUserCheckable)
                # Set the checkbox state based on the value (treat "true" or "1" as checked)
                checkbox.setCheckState(Qt.Checked if val.lower() in ("true", "1") else Qt.Unchecked)
                self.table.setItem(row, col, checkbox)
            else:
                # For other fields, display the value as editable text
                self.table.setItem(row, col, QTableWidgetItem(val))

    # Delete selected row(s) from the table
    def delete_row(self):
        # Get all selected rows (should be only one due to selection mode)
        indexes = self.table.selectionModel().selectedRows()
        # Remove rows in reverse order to avoid shifting indices during deletion
        for index in sorted(indexes, reverse=True):
            self.table.removeRow(index.row())

    # Save current table entries to tools.json, making a backup and refreshing the menu
    def save_tools(self):
        try:
            # Convert each table row back into a dictionary matching the tool fields
            tools = []
            for row in range(self.table.rowCount()):
                entry = {}
                for col, key in enumerate(TOOL_FIELDS):
                    item = self.table.item(row, col)
                    if key == "enabled":
                        # For the 'enabled' checkbox, store True if checked, False otherwise
                        entry[key] = item.checkState() == Qt.Checked if item else False
                    else:
                        # For other fields, strip whitespace from the text or default to empty string
                        entry[key] = item.text().strip() if item else ""
                # Normalize divider name if present
                if entry.get("name", "").strip() == "↕ Divider":
                    entry["name"] = "———"
                    entry["type"] = "separator"
                    entry["module"] = ""
                    entry["function"] = ""
                tools.append(entry)

            # Mark dividers with type "separator"
            for entry in tools:
                name = entry.get("name", "").strip()
                if name in ("---", "—", "——", "———", "————", "—————"):
                    entry["type"] = "separator"
                else:
                    entry.pop("type", None)

            # Validate imports for each tool that has module and function defined
            for entry in tools:
                if entry.get("type") == "separator":
                    continue
                module_name = entry.get("module", "").strip()
                func_name = entry.get("function", "").strip()
                if module_name and func_name:
                    try:
                        mod = importlib.import_module(module_name)
                        if not hasattr(mod, func_name):
                            raise ImportError(f"Module '{module_name}' has no function '{func_name}'")
                    except Exception as e:
                        showInfo(f"Import error in tool '{entry.get('name', '')}': {e}")

            # Append Toolbar Settings if missing
            toolbar_settings_exists = any(
                entry.get("name", "").strip().lower() == "toolbar settings" for entry in tools
            )
            if not toolbar_settings_exists:
                tools.append({
                    "name": "Toolbar Settings",
                    "module": "Main_Toolbar.toolbar_editor",
                    "function": "edit_toolbar_json",
                    "submenu": "",
                    "icon": CONFIG.get("default_icon", "icons/bent_menu-burger.svg"),
                    "enabled": True
                })

            # Before overwriting tools.json, create a backup of the existing file if it exists
            backup_path = self.path + ".bak"
            if os.path.exists(self.path):
                os.rename(self.path, backup_path)

            # Write the updated tools list to tools.json with pretty formatting
            with open(self.path, "w") as f:
                json.dump(tools, f, indent=2)
            # Refresh the Anki menu to reflect changes immediately
            _refresh_menu()
            # Optionally show a success notification if configured in any tool entry
            for entry in tools:
                if str(entry.get("sucess_notification", "true")).lower() in ("true", "1"):
                    msg = entry.get("success_message", "Saved successfully. Restart Anki or reopen the Tools menu.")
                    showInfo(msg)
                    break
        except Exception:
            # Show traceback in a text dialog if saving fails
            showText(traceback.format_exc(), title="Save Error")

    def add_divider(self):
        self.add_row({
            "name": "———",
            "module": "",
            "function": "",
            "submenu": "",
            "icon": "",
            "enabled": False
        })

# Launch the ToolbarManager dialog
def open_toolbar_editor():
    # Import Anki main window and create the toolbar editor dialog as a modal window
    from aqt import mw
    dlg = ToolbarManager(mw)
    dlg.exec_()

edit_toolbar_json = open_toolbar_editor