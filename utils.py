# Utility functions and shared state for managing custom toolbar tools in Anki add-ons.

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
import os
import json
from aqt import mw
from aqt.qt import QAction, QMenu, QIcon
from aqt.utils import showText

# Dictionary storing registered toolbar actions categorized by submenu path
# Shared state for registered toolbar actions
addon_actions = {}

# Load and return JSON data from a file path
def load_json_file(path):
    """Load and return JSON data from the given file path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Load configuration settings from the config.json file
# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "assets", "config.json")
CONFIG = load_json_file(CONFIG_PATH)

def resolve_icon_path(path):
    """
    Resolve icon path based on relative logic:
    - Absolute → return as-is
    - Qt resource (starts with ":assets/") → map to real assets folder path
    - Qt resource (starts with ":") → return as-is
    - Starts with "assets/" or "icons/" → join with addon_dir
    - Otherwise → assume it's in 'icons/'
    """
    if not path:
        return ""

    if os.path.isabs(path):
        return path

    addon_dir = os.path.dirname(__file__)

    if path.startswith(":assets/"):
        return os.path.join(addon_dir, "assets", path.replace(":assets/", ""))

    if path.startswith(":"):
        return path

    if path.startswith("assets/") or path.startswith("icons/"):
        return os.path.join(addon_dir, path)

    return os.path.join(addon_dir, "icons", path)


# Rebuild the "Custom Tools" top menu in Anki, supporting nested submenus via '::'
def _refresh_menu():
    """Rebuild the Custom Tools menu with support for nested submenus using '::'."""

    # Remove any previously added "Custom Tools" menu to avoid duplicates
    # Remove existing custom menu
    for action in mw.form.menuTools.actions():
        if action.menu() and action.menu().title() == CONFIG.get("toolbar_title", "Custom Tools"):
            mw.form.menuTools.removeAction(action)

    # Create a new top-level QMenu with the configured toolbar title
    top_menu = QMenu(CONFIG.get("toolbar_title", "Custom Tools"), mw)

    # Recursively build nested actions based on '::' submenu structure
    def add_nested_action(menu: QMenu, path: list[str], name, callback, icon=None, enabled=True):
        if not path:
            action = QAction(name, mw)
            action.triggered.connect(callback)
            action.setEnabled(enabled)
            if icon:
                action.setIcon(QIcon(resolve_icon_path(icon)))
            menu.addAction(action)
        else:
            head, *tail = path
            # Find or create submenu
            sub = next((a.menu() for a in menu.actions() if a.menu() and a.menu().title() == head), None)
            if not sub:
                sub = QMenu(head, mw)
                menu.addMenu(sub)
            add_nested_action(sub, tail, name, callback, icon, enabled)

    # Iterate over all registered tools and insert them into the nested menu
    for submenu_path, actions in addon_actions.items():
        path = submenu_path.split("::") if submenu_path else []
        for (name, callback, icon, enabled) in actions:
            add_nested_action(top_menu, path, name, callback, icon, enabled)

    mw.form.menuTools.addMenu(top_menu)


# Register a tool into the custom toolbar and refresh the menu
def register_addon_tool(name, callback, submenu_name="", icon=None, enabled=True):
    """
    Register a new tool under a submenu. submenu_name can use '::' for nesting.
    """
    items = addon_actions.setdefault(submenu_name or "", [])
    items.append((name, callback, icon, enabled))
    _refresh_menu()

def build_config_tools(config, make_open_fn):
    """
    Build a list of config tool definitions for add-ons based on config settings.

    Args:
        config (dict): Global config dictionary.
        make_open_fn (Callable): Function that returns a callback to open the config dialog.

    Returns:
        List[dict]: List of tool definitions with name, callback, icon, and other display settings.
    """
    tools = []
    for addon in config.get("Other_addon_names", []):
        display = addon.replace("_", " ").replace("-", " ").title()
        tools.append(dict(
            name=f"{display} Config",
            callback=make_open_fn(addon),
            submenu_name="Add-ons Configurations",
            icon=config.get("default_icon"),
            enabled=True
        ))
    return tools