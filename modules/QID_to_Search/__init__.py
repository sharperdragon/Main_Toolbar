from aqt import mw
from aqt.utils import getText
from aqt.browser import Browser
from aqt.utils import getText, showInfo
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from .utils import QIDSearchDialog

def prompt_and_search_qids_in_browser():
    # Instantiate the dialog with the main application window as parent
    dlg = QIDSearchDialog(mw.app.activeWindow())
    # Show dialog modally and proceed if user accepts (Close + Search)
    if dlg.exec():
        query = dlg.get_preview()
        if query:
            # Open Anki browser and set the search field to the constructed query
            browser = Browser(mw)
            browser.form.searchEdit.lineEdit().setText(query)
            browser.onSearch()
        else:
            # Inform user if no valid QIDs were entered
            showInfo("No valid QIDs entered.")

from aqt.qt import QAction
from aqt import mw
from anki.hooks import gui_hooks  # for Anki <2.1.66 use hook-based API

def on_qid_tool_triggered():
    prompt_and_search_qids_in_browser()

def add_qid_search_to_menu():
    action = QAction("🔍 Search UWorld QIDs", mw)
    action.triggered.connect(on_qid_tool_triggered)
    mw.form.menuTools.addAction(action)

gui_hooks.main_window_did_init.append(add_qid_search_to_menu)