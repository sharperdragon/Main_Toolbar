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


def format_config_label(addon: str, config: dict) -> str:
    """
    Build the display label for the Add-ons Configurations submenu using:
      [emoji␠][nickname OR prettified addon name]
    where nickname is sourced from config["addon_nicknames"].
    """
    emojis = (config.get("addon_emojis") or {})
    nicknames = (config.get("addon_nicknames") or {})

    emoji = emojis.get(addon, "") or ""
    # Prefer nickname if provided; fall back to prettified addon key
    display = nicknames.get(addon) or addon.replace("_", " ").replace("-", " ").title()

    return f"{emoji} {display}" if emoji else display


# Rebuild the "Custom Tools" top menu in Anki, supporting nested submenus via '::'
def _refresh_menu():
    """Rebuilds all top-level menus based on registered addon tools and submenu structure."""
    # Remove any previously added menus matching registered top-level names
    existing_titles = {submenu.split("::")[0] if submenu else CONFIG.get("toolbar_title", "Custom Tools") 
                       for submenu in addon_actions}
    for action in mw.form.menubar.actions():
        if action.menu() and action.menu().title() in existing_titles:
            mw.form.menubar.removeAction(action)

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
            sub = next((a.menu() for a in menu.actions() if a.menu() and a.menu().title() == head), None)
            if not sub:
                sub = QMenu(head, mw)
                menu.addMenu(sub)
            add_nested_action(sub, tail, name, callback, icon, enabled)

    # Build top-level menus by grouping tools
    menu_groups = {}
    for submenu_path, actions in addon_actions.items():
        top = submenu_path.split("::")[0] if submenu_path else CONFIG.get("toolbar_title", "Custom Tools")
        menu_groups.setdefault(top, []).append((submenu_path, actions))

    for top_title, grouped in menu_groups.items():
        top_menu = QMenu(top_title, mw)
        for submenu_path, actions in grouped:
            path = submenu_path.split("::")[1:] if submenu_path else []
            for (name, callback, icon, enabled) in actions:
                add_nested_action(top_menu, path, name, callback, icon, enabled)
        mw.form.menubar.addMenu(top_menu)


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
        label = format_config_label(addon, config)
        tools.append(dict(
            name=label,  # includes emoji + nickname fallback
            callback=make_open_fn(addon),
            submenu_name="Add-ons Configurations",
            icon=config.get("default_icon"),
            enabled=True
        ))
    return tools