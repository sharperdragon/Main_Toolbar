# AC_IMG_DUPES.py — Native API version for internal Anki execution

from aqt import mw
from aqt.utils import showInfo
from anki.notes import Note

from typing import List
import re

def run_img_dupes_script():
    print("🚀 Starting AC_IMG_DUPES inside Anki...")

    # Step 1: Find all notes with the target tag
    query = "tag:#Temp::Dupe_img"
    note_ids = mw.col.find_notes(query)
    print(f"📌 Found {len(note_ids)} notes matching query: {query}")
    
    if not note_ids:
        showInfo("No notes found with tag: #Temp::Dupe_img")
        return

    removed_nids: List[int] = []
    for nid in note_ids:
        note: Note = mw.col.get_note(nid)
        changed = False

        for field in ['Text', 'Extra', 'Extra2', 'Extra3', 'Extra4', 'Extra5']:
            if field not in note:
                continue
            original = note[field]

            # Extract all <img> tags
            imgs = re.findall(r'<img [^>]*src="([^"]+)"[^>]*>', original, flags=re.IGNORECASE)
            if not imgs or len(set(imgs)) == len(imgs):
                continue  # No dupes

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
                        changed = True  # This is a duplicate <img>, skip it
                else:
                    updated_html += chunk

            if updated_html != original:
                print(f"🧹 Removed dupes in field '{field}' of note {nid}")
                note[field] = updated_html
                changed = True

        if changed:
            note.flush()
            removed_nids.append(nid)

    msg = f"✅ Done. Cleaned {len(removed_nids)} notes."
    print(msg)
    showInfo(msg)

    if len(removed_nids) > 45:
        backup_path = "/Users/claytongoddard/ANki/Missing Media/backups/dupe_img_nids.txt"
        with open(backup_path, "w") as f:
            f.write("\n".join(str(nid) for nid in removed_nids))
        print(f"📝 Wrote backup of {len(removed_nids)} NIDs to: {backup_path}")
