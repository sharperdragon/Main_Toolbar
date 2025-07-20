# Utility functions and shared state for managing custom toolbar tools in Anki add-ons.

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
import os
import json
from aqt import mw
from aqt.qt import QAction, QMenu, QIcon

from aqt.utils import showText

# Optional tool name remapping for menu display
TOOL_NAME_MAP = {
    "Resolve IMG Dupes": "🧬 Resolve IMG Dupes",
    "Delete stray note types": "📝 Delete stray note types",
    "Get Unused": "🗑️ Get Unused",
    "Export Missing Media": "🧩 Export Missing Media",
    "Toolbar Settings": "⚙️ Toolbar Settings"
}

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
        emoji = config.get("addon_emojis", {}).get(addon)
        display = addon.replace("_", " ").replace("-", " ").title()
        tools.append(dict(
            name=f"{display} {emoji}" if emoji else display,
            callback=make_open_fn(addon),
            submenu_name="Add-ons Configurations",
            icon=config.get("default_icon"),
            enabled=True
        ))
    return tools