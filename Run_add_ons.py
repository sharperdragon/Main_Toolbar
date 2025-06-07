# This script dynamically builds and inserts custom toolbars and submenu entries into the Anki Tools menu.
# It registers both internal utility scripts and external add-on config dialogs based on JSON config files.
# This module dynamically loads and registers tools and configuration dialogs 
# into a custom toolbar for Anki add-ons based on JSON configs and settings.
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
# Run_add_ons.py
import os
import traceback
import importlib
from PyQt6.QtWidgets import QMenu
from PyQt6 import QtGui, QtSvg
from aqt import mw
from aqt.utils import showText
from aqt.qt import QIcon

from .utils import CONFIG, register_addon_tool, load_json_file, build_config_tools, resolve_icon_path
from .assets.config_ui import ConfigDialog
from .assets.config_manager import ConfigManager

# Lookup dictionary to keep track of created submenus for reuse.
submenu_lookup = {}

# Loads and registers separate configuration dialogs for other add-ons into a submenu.
def load_other_configs():
    """
    Load and register configuration dialogs for other add-ons into a dedicated submenu.
    This function checks the global configuration to determine if toolbar settings
    should be enabled, then dynamically creates menu entries for each add-on listed
    in the 'OTher_addon_names' configuration key.
    """
    # Skip if toolbar settings are disabled in the config.
    # Exit early if toolbar settings are disabled in the config
    # This flag controls whether the 'Other Add-ons Configurations' submenu is shown
    if not CONFIG.get("enable_toolbar_settings", False):
        return


    # Generates a function to open the config dialog for a given add-on name.
    # Returns a function that opens the config dialog for a specific add-on
    # This closure allows each menu item to open the correct add-on's config dialog
    def make_open_fn(addon_name):
        def _open():
            dlg = ConfigDialog(addon_name, ConfigManager)
            dlg.exec_()
        return _open

    try:
        # Prepare the list of config tools to register
        config_tools = build_config_tools(CONFIG, make_open_fn)


        # Locate the custom toolbar menu already present in the Anki Tools menu.
        custom_tools_menu = None
        for action in mw.form.menuTools.actions():
            if action.menu() and action.menu().title() == CONFIG.get("toolbar_title", "Custom Tools"):
                custom_tools_menu = action.menu()
                break

        if not custom_tools_menu:
            return

        # Setup submenu for "Other Add-ons Configurations" if not already created.
        submenu_title = "Add-ons Configurations"
        submenu = submenu_lookup.get(submenu_title)
        if not submenu:
            submenu = QMenu(submenu_title, mw)
            submenu_lookup[""].insertMenu(
                submenu_lookup[""].actions()[0] if submenu_lookup[""].actions() else None,
                submenu
            )
            # Insert a separator immediately after the last action in "Add-ons Configurations"
            submenu_lookup[""].insertSeparator(submenu.menuAction())
            submenu_lookup[submenu_title] = submenu

        # Add each external config tool to the submenu with proper icon and callback registration.
        for tool in config_tools:
            action = submenu.addAction(tool["name"])
            if tool["icon"]:
                icon_path = resolve_icon_path(tool["icon"])
                icon_obj = QIcon(icon_path)
                print(f"📦 Icon: {tool['name']} | Path: {icon_path} | Sizes: {icon_obj.availableSizes()}")
                action.setIcon(icon_obj)
            action.setEnabled(tool["enabled"])
            action.triggered.connect(tool["callback"])

    except Exception:
        err = traceback.format_exc()
        showText(
            f"[Custom Tools] Failed to load Other Add-ons Configurations menu:\n\n{err}",
            title=CONFIG.get("toolbar_title", "Custom Tools") + " Error"
        )

# Main function to dynamically load functional tools defined in tools.json and add to the toolbar.
# Dynamically loads and registers tools from tools.json file.
def load_tools_from_config():
    """
    Load and register tools defined in the external tools.json configuration file.
    This function differentiates between separators, labels, and functional tools,
    dynamically imports tool callback functions, and registers them into the toolbar.
    """

    global submenu_lookup
    submenu_lookup.clear()

    # Create the main custom tools menu and append it to Anki's Tools menu.
    custom_menu = QMenu(CONFIG.get("toolbar_title", "Custom Tools"), mw)
    mw.form.menuTools.addSeparator()
    mw.form.menuTools.addMenu(custom_menu)
    submenu_lookup[""] = custom_menu

    # Utility to fetch existing submenu or create a new one if it doesn't exist.
    def get_or_create_submenu(name):
        if name not in submenu_lookup:
            submenu = QMenu(name, mw)
            submenu_lookup[name] = submenu
            submenu_lookup[""].addMenu(submenu)
        return submenu_lookup[name]

    # Define and check path to the tools.json configuration file.
    tools_path = os.path.join(os.path.dirname(__file__), "assets", "tools.json")
   
    # Skip loading if the config file is missing
    if not os.path.exists(tools_path):
        return

    # Load and parse the JSON file containing tool definitions
    tools = load_json_file(tools_path)
    # Iterate over each tool defined in tools.json to determine how it should be registered.
    for entry in tools:
        entry_type = entry.get("type", "").strip()
        name = entry.get("name", "").strip()
        submenu_name = entry.get("submenu", "").strip()
        icon = entry.get("icon")
        enabled = entry.get("enabled", True)

        # Get or create the correct submenu
        submenu = get_or_create_submenu(submenu_name)

        # Add a visual separator to the submenu.
        if entry_type == "separator":
            submenu.addSeparator()
            continue

        # Add a non-clickable label to the submenu.
        elif entry_type == "label":
            action = submenu.addAction(name or "---")
            action.setEnabled(False)
            continue

        # For functional tools, extract required fields
        func_name = entry.get("function")
        module_path = entry.get("module")
        # Skip malformed tool entries that are missing key data.
        if not name or not func_name or not module_path:
            continue

        # Dynamically import the specified module and extract the callback function.
        try:
            module = importlib.import_module(module_path)
            callback = getattr(module, func_name)
        except Exception:
            err = traceback.format_exc()
            showText(
                f"[Custom Tools] Failed to import '{name}' from {module_path}.{func_name}:\n\n{err}",
                title=CONFIG.get("toolbar_title", "Custom Tools") + " Error"
            )
            continue

        # Register the tool as a clickable action in the appropriate submenu.
        try:
            action = submenu.addAction(name)
            if icon:
                icon_path = resolve_icon_path(icon)
                icon_obj = QIcon(icon_path)
                print(f"📦 Icon: {name} | Path: {icon_path} | Sizes: {icon_obj.availableSizes()}")
                action.setIcon(icon_obj)
                if not icon_obj.availableSizes():
                        print(f"⚠️ Icon failed to load or is empty: {icon_path}")
            action.setEnabled(enabled)
            action.triggered.connect(callback)
        except Exception:
            err = traceback.format_exc()
            showText(
                f"[Custom Tools] Failed to register '{name}':\n\n{err}",
                title=CONFIG.get("toolbar_title", "Custom Tools") + " Error"
            )
