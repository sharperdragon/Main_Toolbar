# pyright: reportMissingImports=false

from .utils import CONFIG, register_addon_tool
from .Run_add_ons import load_tools_from_config, load_other_configs

# Load all tools and config dialogs
from aqt.gui_hooks import main_window_did_init
main_window_did_init.append(load_tools_from_config)
main_window_did_init.append(load_other_configs)

# Add custom Mac top menu
from aqt import mw
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo


def on_click_myaddon():
    showInfo("✅ You clicked the custom menu!")

def add_mac_top_menu():
    # Only add once to avoid duplicates
    if mw.form.menubar.findChild(QMenu, "MyAddonMenu"):
        return

    from .Run_add_ons import TOOL_REGISTRY
    from .utils import TOOL_NAME_MAP

    menu = QMenu(CONFIG.get("toolbar_title", "MyAddon"), mw)
    menu.setObjectName("MyAddonMenu")

    # Create submenu tree
    submenu_map = {"": menu}
    for entry in TOOL_REGISTRY:
        if not entry.get("enabled", True):
            continue
        submenu_name = entry.get("submenu", "").strip()
        parent_menu = submenu_map.get(submenu_name)
        if submenu_name and not parent_menu:
            parent_menu = QMenu(submenu_name, mw)
            submenu_map[submenu_name] = parent_menu
            menu.addMenu(parent_menu)

        target_menu = submenu_map.get(submenu_name, menu)

        action = QAction(TOOL_NAME_MAP.get(entry["name"], entry["name"]), mw)
        if entry.get("icon"):
            try:
                action.setIcon(QIcon(entry["icon"]))
            except Exception:
                pass
        action.setEnabled(entry.get("enabled", True))
        action.triggered.connect(entry["callback"])
        target_menu.addAction(action)

    mw.form.menubar.addMenu(menu)

main_window_did_init.append(add_mac_top_menu)
