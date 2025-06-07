from datetime import datetime
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import QFileDialog
from pathlib import Path
import os
import re

from aqt.utils import showText

def export_missing_media_to_txt(output_path: str = None) -> None:
    """
    Finds all media files referenced in notes but missing from the collection.media folder,
and writes them to a text file on the Desktop (or user-specified path).
    """
    timestamp = datetime.now().strftime("%b-%d-%y_%I-%M-%p")
    filename = f"missing_anki_media_{timestamp}.txt"
    output_path = Path.home() / "Desktop" / filename

    output_path = Path(output_path)

    media_dir = Path(mw.col.media.dir())
    all_files = set(os.listdir(media_dir))

    used_files = set()
    for nid in mw.col.find_notes(""):
        note = mw.col.get_note(nid)
        for field in note.fields:
            used_files.update(re.findall(r'\[sound:([^\]]+)\]', field))
            used_files.update(re.findall(r'<img src="([^"]+)"', field))

    missing_media = sorted(used_files - all_files)
    grouped = [", ".join(missing_media[i:i+30]) for i in range(0, len(missing_media), 30)]
    formatted_output = ",\n\n\n".join(grouped)
    output_path.write_text(formatted_output, encoding="utf-8")

    showInfo(f"📦 {len(missing_media)} missing media files written to Desktop as:\n{output_path.name}")
