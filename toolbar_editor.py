# Toolbar Editor (WebView rewrite) (WebView rewrite)
# - Loads HTML UI from assets/tool_template.html
# - Uses AnkiWebView + bridge for save/refresh
# - Right-click → Inspect opens DevTools focused at cursor

from __future__ import annotations

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
import os, json, traceback
from typing import Any, Dict

from aqt.qt import (
    QDialog, QVBoxLayout, Qt, QCursor, QMenu, QAction, QWebEngineView
)
from aqt.webview import AnkiWebView
from aqt.utils import showInfo, showText
from aqt import gui_hooks

from .utils import _refresh_menu

# --- Paths & constants ---
ADDON_DIR = os.path.dirname(__file__)
ASSETS = os.path.join(ADDON_DIR, "assets")
CONFIG_PATH = os.path.join(ASSETS, "config.json")
ACTIONS_PATH = os.path.join(ASSETS, "actions.json")
HTML_PATH = os.path.join(ASSETS, "tool_template.html")  # external file (lowercase name expected)
DEVTOOLS_WINDOW_TITLE = "Toolbar DevTools"

# Load config (labels, defaults)
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
except Exception:
    CONFIG = {"toolbar_title": "Toolbar Editor"}

# Keep handles to the editor view and the DevTools window so we can attach DevTools
_toolbar_view: AnkiWebView | None = None
_toolbar_devtools: QWebEngineView | None = None


class ToolbarEditorDialog(QDialog):
    """Modal dialog hosting an AnkiWebView UI for toolbar editing."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbarEditorDialog")
        self.setWindowTitle(CONFIG.get("toolbar_title", "Toolbar Editor"))
        self.resize(1100, 700)

        # Layout + WebView
        lay = QVBoxLayout(self)
        self.view = AnkiWebView(title="Toolbar Editor")
        lay.addWidget(self.view)

        # Expose global reference for the context-menu hook
        global _toolbar_view
        _toolbar_view = self.view

        # Bridge for save/refresh
        self.view.set_bridge_command(self._on_bridge, "toolbar_editor")

        # Load external HTML from assets/tool_template.html
        html = self._read_html()
        # Inject <base href> so relative paths (icons, css, js) resolve to ./assets/
        html = self._with_base_href(html)
        self.view.stdHtml(html, context=None)

        # Hydrate the UI with current actions.json
        self._inject_model(self._load_actions())

    # --- I/O helpers ---
    def _read_html(self) -> str:
        try:
            # Accept either tool_template.html or Tool_template.html
            path = HTML_PATH
            if not os.path.exists(path):
                alt = os.path.join(ASSETS, "Tool_template.html")
                path = alt if os.path.exists(alt) else HTML_PATH
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            showText(traceback.format_exc(), title="Load HTML Error")
            return "<html><body><p>Failed to load tool_template.html</p></body></html>"

    def _with_base_href(self, html: str) -> str:
        """Ensure the HTML has a <base href="file://.../assets/"> so relative paths resolve."""
        try:
            base = f"file://{ASSETS}/"
            lower = html.lower()
            if "<head" in lower and "<base" not in lower:
                # Insert <base> immediately after <head>
                return html.replace("<head>", f"<head>\n<base href=\"{base}\">", 1)
            return html
        except Exception:
            return html

    def _load_actions(self) -> list[Dict[str, Any]]:
        try:
            if os.path.exists(ACTIONS_PATH):
                with open(ACTIONS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            showText(traceback.format_exc(), title="Load Actions Error")
        return []

    def _inject_model(self, data: list[Dict[str, Any]]) -> None:
        # Pass JSON string to JS hydrate(jsonStr)
        payload = json.dumps(data)
        # Double-encode so quotes are preserved inside JS call
        js = f"hydrate({json.dumps(payload)});"
        self.view.eval(js)

    # --- Bridge ---
    def _on_bridge(self, cmd: str) -> None:
        # toolbar_editor:save:<json>
        # toolbar_editor:refresh
        if not cmd.startswith("toolbar_editor:"):
            return
        try:
            _, action, rest = cmd.split(":", 2)
        except ValueError:
            return

        if action == "refresh":
            _refresh_menu()
            return

        if action == "save":
            try:
                tools = json.loads(rest)
                # Normalize separators
                for e in tools:
                    name = (e.get("name") or "").strip()
                    if name in ("---", "—", "——", "———", "————", "—————"):
                        e["type"] = "separator"
                    else:
                        e.pop("type", None)
                # Guarantee Toolbar Settings row
                if not any((e.get("name", "").strip().lower() == "toolbar settings") for e in tools):
                    tools.append({
                        "name": "Toolbar Settings",
                        "module": "Main_Toolbar.toolbar_editor",
                        "function": "edit_toolbar_json",
                        "submenu": "",
                        "icon": "icons/bent_menu-burger.svg",
                        "enabled": True,
                    })
                # Backup + write
                if os.path.exists(ACTIONS_PATH):
                    os.replace(ACTIONS_PATH, ACTIONS_PATH + ".bak")
                with open(ACTIONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(tools, f, indent=2)
                _refresh_menu()
                showInfo("Saved. Reopen the Tools menu to see changes.")
                self._inject_model(tools)
            except Exception:
                showText(traceback.format_exc(), title="Save Error")


# --- DevTools context menu hook (right-click → Inspect) ---

def _toolbar_context_menu_hook(webview: AnkiWebView, menu: QMenu) -> None:
    """Add an Inspect action to the context menu of our toolbar editor webview only."""
    global _toolbar_view
    if webview is not _toolbar_view:
        return
    act = menu.addAction("Inspect")
    act.triggered.connect(lambda: _inspect_toolbar_at_cursor(webview))


def _inspect_toolbar_at_cursor(for_view: AnkiWebView) -> None:
    """Open DevTools and inspect the element at the cursor position."""
    global _toolbar_devtools
    if _toolbar_devtools is None:
        _toolbar_devtools = QWebEngineView()
        _toolbar_devtools.setWindowTitle(DEVTOOLS_WINDOW_TITLE)
        _toolbar_devtools.resize(1100, 800)
    page = for_view.page()
    page.setDevToolsPage(_toolbar_devtools.page())
    _toolbar_devtools.show()
    _toolbar_devtools.raise_()
    try:
        gp = QCursor.pos()
        lp = for_view.mapFromGlobal(gp)
        page.inspectElementAt(lp.x(), lp.y())
    except Exception:
        # DevTools still opens even if precise inspect isn't available
        pass


# Register the hook once (hooks aren’t iterable; track via module flag)
try:
    _TOOLBAR_HOOK_REGISTERED
except NameError:
    _TOOLBAR_HOOK_REGISTERED = False

if not _TOOLBAR_HOOK_REGISTERED:
    try:
        gui_hooks.webview_will_show_context_menu.append(_toolbar_context_menu_hook)
    except Exception:
        # Older/newer hook APIs: best effort, ignore if unavailable
        pass
    _TOOLBAR_HOOK_REGISTERED = True


# --- Entry points ---

def open_toolbar_editor() -> None:
    from aqt import mw
    dlg = ToolbarEditorDialog(mw)
    dlg.exec_()

# Back-compat name used in actions.json
edit_toolbar_json = open_toolbar_editor
