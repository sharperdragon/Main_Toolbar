# AC_IMG_DUPES.py — Native API version for internal Anki execution

from aqt import mw
from aqt.utils import showInfo, showWarning
from anki.notes import Note
from aqt.qt import QInputDialog
from aqt.operations import Progress, QueryOp

from typing import List
import re

def normalize_tag_input(raw: str) -> str:
    tag = raw.strip().replace("\\_", "_")
    if not tag.startswith("tag:"):
        tag = f"tag:{tag}"
    return tag

def run_img_dupes_script():
    print("🚀 Starting AC_IMG_DUPES inside Anki...")

    # Step 1: Prompt user for the tag query
    dlg = QInputDialog(mw)
    dlg.setWindowTitle("Enter Tag")
    dlg.setLabelText("Enter a search query like in the Anki browser:")
    dlg.setModal(False)  # Allow interaction outside the dialog
    from PyQt6.QtCore import Qt
    dlg.setWindowModality(Qt.WindowModality.NonModal)
    dlg.setFixedSize(400, 100)
    if dlg.exec() != dlg.Accepted:
        return
    query = dlg.textValue()
    query = normalize_tag_input(query)
    if not query.strip():
        return

    note_ids = mw.col.find_notes(query)
    print(f"📌 Found {len(note_ids)} notes matching query: {query}")

    if not note_ids:
        showInfo("No notes found with tag: #Temp::Dupe_img")
        return

    def process_notes(col):
        removed_nids = []
        for nid in note_ids:
            note: Note = col.get_note(nid)
            changed = False

            for field in ['Text', 'Extra', 'Extra2', 'Extra3', 'Extra4', 'Extra5', 'Button', 'Display']:
                if field not in note:
                    continue
                original = note[field]

                imgs = re.findall(r'<img [^>]*src="([^"]+)"[^>]*>', original, flags=re.IGNORECASE)
                if not imgs or len(set(imgs)) == len(imgs):
                    continue

                seen = set()
                updated_html = ""
                split = re.split(r'(<img [^>]*src="[^"]+"[^>]*>)', original)

                for chunk in split:
                    match = re.search(r'<img [^>]*src="([^"]+)"[^>]*>', chunk)
                    if match:
                        src = match.group(1)
                        if src not in seen:
                            updated_html += chunk
                            seen.add(src)
                        else:
                            changed = True
                    else:
                        updated_html += chunk

                if updated_html != original:
                    print(f"🧹 Removed dupes in field '{field}' of note {nid}")
                    note[field] = updated_html
                    changed = True

            if changed:
                try:
                    note.flush()
                    removed_nids.append(nid)
                except Exception as e:
                    msg = f"❌ Error flushing note {nid}: {e}"
                    print(msg)
                    showWarning(msg)
        return removed_nids

    def on_success(removed_nids):
        msg = f"✅ Done. Cleaned {len(removed_nids)} notes."
        print(msg)
        showInfo(msg)
        if len(removed_nids) > 45:
            backup_path = "/Users/claytongoddard/ANki/Missing Media/backups/dupe_img_nids.txt"
            with open(backup_path, "w") as f:
                f.write("\n".join(str(nid) for nid in removed_nids))
            print(f"📝 Wrote backup of {len(removed_nids)} NIDs to: {backup_path}")

    QueryOp(
        parent=mw,
        op=process_notes,
        success=on_success,
    ).with_progress("Removing duplicate images...").run_in_background()
