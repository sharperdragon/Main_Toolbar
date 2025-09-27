# * GUI editor to manage toolbar tools defined in assets/actions.json (add, delete, reorder, save)
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
from typing import Dict, Any

# Paths and config: ASSETS points to ./assets; CONFIG loads assets/config.json
ASSETS = os.path.join(os.path.dirname(__file__), "assets")
with open(os.path.join(ASSETS, "config.json"), encoding="utf-8") as f:
    CONFIG = json.load(f)

from aqt.utils import qconnect
from aqt.qt import QFile, QTextStream

# Apply external stylesheet/QSS based on Anki theme.
# Chooses dark or light file if present; otherwise uses default styling.
def apply_stylesheet(widget):
    # Determine which stylesheet to use based on whether Anki is in night mode or not
    from aqt.theme import theme_manager
    style_name = "Style_toolbar_editor_dark.css" if theme_manager.night_mode else "Style_toolbar_editor_light.css"
    css_path = os.path.join(ASSETS, style_name)
    # Load and apply the CSS file if it exists to style the widget accordingly
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            widget.setStyleSheet(f.read())

# Table columns: name, module, function, submenu, icon, enabled (checkbox)
TOOL_FIELDS = ["name", "module", "function", "submenu", "icon", "enabled"]

class ToolbarManager(QDialog):
    """
    * Modal dialog to view/edit toolbar tools stored in assets/actions.json.
    ^ Loads existing tools, supports drag-drop reordering, writes JSON (with backup), refreshes menus.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toolbarEditorDialog")
        self.setWindowTitle(CONFIG["toolbar_title"])
        self.path = os.path.join(ASSETS, "actions.json")
        self.resize(975, 300)

        self.tools = []

        self.layout = QVBoxLayout(self)

        # Create and configure the table widget to display tool entries
        self.table = QTableWidget(0, len(TOOL_FIELDS))
        self.table.setObjectName("toolbarTable")
        # Set the header labels to correspond to the tool fields
        self.table.setHorizontalHeaderLabels(TOOL_FIELDS)

        # Enable row-wise selection and internal drag-drop to reorder rows (no external drops).
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

        # Column sizing:
        # - enabled: Fixed
        # - module/function/submenu: Stretch with minimum width
        # - others: Interactive with per-column minimums
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
        self.btn_save = QPushButton("Save")     # Button to save changes to actions.json
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

    def load_tools(self):
        # Load actions.json if present; otherwise start empty.
        # Skip showing separators and the "Toolbar Settings" row in the editor.
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
            # Show traceback for easier debugging (non-fatal load failures).
            showText(traceback.format_exc(), title="Load Error")

    def add_row(self, tool=None):
        # Insert a row; fill missing fields with CONFIG defaults (submenu, icon, enabled=True).
        # Divider rows render as read-only "↕ Divider" and are not editable.
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
            # 'enabled' renders as a user-checkable checkbox (checked if "true"/"1").
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

    def delete_row(self):
        # * Single-row selection; delete in reverse order to avoid index shifts (future-proof if multi-select re-enabled).
        indexes = self.table.selectionModel().selectedRows()
        for index in sorted(indexes, reverse=True):
            self.table.removeRow(index.row())

    def save_tools(self):
        # ^ 1) Read table → list[dict]
        # ^ 2) Normalize dividers (type="separator")
        # ^ 3) Validate imports (module/function) and report any errors
        # ^ 4) Ensure "Toolbar Settings" exists (append if missing)
        # ^ 5) Backup existing actions.json → write new JSON
        # ^ 6) Refresh menus and optionally notify
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
                # * Map visual "↕ Divider" to canonical separator name and type.
                if entry.get("name", "").strip() == "↕ Divider":
                    entry["name"] = "———"
                    entry["type"] = "separator"
                    entry["module"] = ""
                    entry["function"] = ""
                tools.append(entry)

            # * Mark any canonical divider names as type="separator"
            for entry in tools:
                name = entry.get("name", "").strip()
                if name in ("---", "—", "——", "———", "————", "—————"):
                    entry["type"] = "separator"
                else:
                    entry.pop("type", None)

            # * Import check: import module and assert function exists; report per-entry errors via showInfo.
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

            # * Guarantee presence of a “Toolbar Settings” action so users can re-open the editor easily.
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

            # * Defensive write: rename current file to .bak before writing pretty-printed JSON.
            backup_path = self.path + ".bak"
            if os.path.exists(self.path):
                os.rename(self.path, backup_path)

            # Write the updated tools list to actions.json with pretty formatting
            with open(self.path, "w") as f:
                json.dump(tools, f, indent=2)
            # Refresh the Anki menu to reflect changes immediately
            _refresh_menu()
            # ! Key 'sucess_notification' appears misspelled in some configs; code treats "true"/"1" as enabled if present.
            # ? Consider standardizing to 'success_notification' in config (code change not included here).
            # Optionally show a success notification if configured in any tool entry
            for entry in tools:
                if str(entry.get("sucess_notification", "true")).lower() in ("true", "1"):
                    msg = entry.get("success_message", "Saved successfully. Restart Anki or reopen the Tools menu.")
                    showInfo(msg)
                    break
        except Exception:
            # * On any failure, show full traceback to aid debugging.
            showText(traceback.format_exc(), title="Save Error")

    def add_divider(self):
        # Insert a non-interactive divider entry; stored as a separator when saved.
        self.add_row({
            "name": "———",
            "module": "",
            "function": "",
            "submenu": "",
            "icon": "",
            "enabled": False
        })

def _load_toolbar_config(config_path: str) -> Dict[str, Any]:
    """
    Load toolbar config JSON (emojis, nicknames, etc.).
    """
    import json, os
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f) or {}

def _get_emoji_for(addon_name: str, cfg: Dict[str, Any]) -> str:
    """
    Return configured value or '' if none is set.
    """
    emojis = (cfg.get("addon_emojis") or {})
    return emojis.get(addon_name, "") or ""

def _get_nickname_for(addon_name: str, cfg: Dict[str, Any]) -> str:
    """
    Return configured value or '' if none is set.
    """
    nicknames = (cfg.get("addon_nicknames") or {})
    return nicknames.get(addon_name, "") or ""

def format_toolbar_label(addon_name: str, cfg: Dict[str, Any]) -> str:
    """
    Build the display label for the toolbar/menu: [emoji␠] + [nickname or addon_name].
    Prefers nickname if present; otherwise uses addon_name. Prefixes emoji if available.
    """
    emoji = _get_emoji_for(addon_name, cfg)
    nick  = _get_nickname_for(addon_name, cfg)

    # Prefer nickname if present; otherwise use the original addon_name.
    base_label = nick if nick else addon_name

    # If we have an emoji, prefix it with a space after; otherwise no prefix.
    return f" {base_label} {emoji}" if emoji else base_label



 # Launch as a modal dialog attached to the Anki main window.
def open_toolbar_editor():
    from aqt import mw
    dlg = ToolbarManager(mw)
    dlg.exec_()

edit_toolbar_json = open_toolbar_editor