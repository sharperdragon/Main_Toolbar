from aqt import gui_hooks
from aqt.editor import Editor
from aqt.qt import QShortcut, QKeySequence
from anki.utils import json
import os
from datetime import datetime

# 📂 Log file path
LOG_FOLDER = "/Users/claytongoddard/Library/Application Support/Anki2/addons21/keyed_html_wrap"
LOG_FILE = os.path.join(
    LOG_FOLDER, f"debug_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
)

# 🗄️ Global config
CONFIG = {}

# Track editors for which shortcuts have been registered
EDITOR_SHORTCUTS_REGISTERED = set()

# 🔄 Reload config
CONFIG_PATH = os.path.join(__file__.rsplit("/", 1)[0], "config.json")
def reload_config():
    global CONFIG
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            CONFIG = json.load(f)
        log(f"🔄 Reloaded config from {CONFIG_PATH}")
    except Exception as e:
        CONFIG = {"shortcuts": {}}
        log(f"❌ Failed to reload config: {e}")

# Shortcut registration helper
def register_shortcut(editor: Editor, keybind: str, template: str):
    try:
        shortcut = QShortcut(QKeySequence(keybind), editor.web)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(lambda t=template: wrap_selected_text(editor, t))
        log(f"🔗 Registered shortcut {keybind} -> {template}")
    except Exception as e:
        log(f"❌ Failed to register shortcut {keybind}: {e}")

# 🪵 Simple logger
def log(msg: str):
    try:
        os.makedirs(LOG_FOLDER, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception as e:
        print(f"[wrap_shortcuts] Logging failed: {e}")

# 🔧 Load Config
reload_config()

def wrap_selected_text(editor: Editor, template: str):
    if '{}' not in template:
        log(f"⚠️ Skipping shortcut — template missing '{{}}': {template}")
        return
    try:
        js_template_path = os.path.join(__file__.rsplit("/", 1)[0], "javascript_utils.js")
        with open(js_template_path, encoding="utf-8") as f:
            js_template = f.read()
        js_code = js_template.replace("TEMPLATE_PLACEHOLDER", json.dumps(template))
        log(f"📄 JS Template loaded: {js_template_path}")
        log(f"🧪 Final JS to inject:\n{js_code}")
        if not js_code.strip().startswith("(function"):
            log("🛑 JS code malformed — skipping injection")
            return
        log(f"🚀 Executing fixed JS wrap with template: {template}")
        wrapped_js = f"wrapField(function() {{ {js_code} }});"
        log(f"🧪 Wrapped JS to run:\n{wrapped_js}")
        editor.web.eval("focusField();")  # Ensure field is focused before injection
        editor.web.eval(wrapped_js)
    except Exception as e:
        log(f"❌ Failed to inject JS: {e}")
        import traceback
        log(traceback.format_exc())

def on_editor_did_init(editor: Editor):
    if editor in EDITOR_SHORTCUTS_REGISTERED:
        log(f"🛑 Editor already initialized: {editor}")
        return
    log(f"🧵 Initializing editor: {editor}")
    log(f"🗂 Shortcut definitions: {CONFIG.get('shortcuts', {})}")
    for keybind, template in CONFIG.get("shortcuts", {}).items():
        register_shortcut(editor, keybind, template)
    reload_shortcut = QShortcut(QKeySequence("Cmd+Alt+R"), editor.web)
    reload_shortcut.setAutoRepeat(False)
    reload_shortcut.activated.connect(reload_config)
    log("🧪 Registered config reload shortcut: Cmd+Alt+R")
    EDITOR_SHORTCUTS_REGISTERED.add(editor)

def on_editor_did_load_note(editor: Editor):
    if hasattr(editor, "web"):
        log(f"🧷 Loading editor for browser note: {editor}")
        on_editor_did_init(editor)

# 🔗 Hook into editor startup
gui_hooks.editor_did_init.append(on_editor_did_init)
log("🔁 Editor hook installed")

gui_hooks.editor_did_load_note.append(on_editor_did_load_note)
log("📎 Browser editor hook installed")