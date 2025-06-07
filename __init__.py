# pyright: reportMissingImports=false
from .utils import CONFIG, register_addon_tool
from .Run_add_ons import load_tools_from_config, load_other_configs

# Load all tools and config dialogs
from aqt.gui_hooks import main_window_did_init
main_window_did_init.append(load_tools_from_config)
main_window_did_init.append(load_other_configs)
