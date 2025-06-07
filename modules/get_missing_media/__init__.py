import os
import re
import sqlite3
from aqt import mw
from aqt.utils import showInfo



def write_missing_file():
    def normalize_refs(text, extensions):
        refs = set()
        for ext in extensions:
            refs.update(re.findall(rf'[\w\/\.-]+{re.escape(ext)}', text))
        return {os.path.basename(r) for r in refs}

    def get_used_media():
        # Direct SQLite query for media refs
        db = mw.col.db
        rows = db.all("SELECT flds FROM notes")
        extensions = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".mp3", ".mp4"}
        used = set()
        for (flds,) in rows:
            for field in flds.split("\x1f"):
                used |= normalize_refs(field, extensions)
        return used

    def get_existing_media():
        return set(os.listdir(mw.col.media.dir()))

    def export_missing_media():
        used = get_used_media()
        existing = get_existing_media()
        missing = used - existing

        output_dir = os.path.expanduser("~/Desktop/Missing Media files")
        os.makedirs(output_dir, exist_ok=True)

        profile_name = mw.pm.name
        output_file = os.path.join(output_dir, f"missing_media_{profile_name}.txt")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for name in sorted(missing):
                    f.write(name + "\n")
        except Exception as e:
            print(f"❌ Failed to write missing media file: {e}")

        backup_dir = os.path.expanduser("~/ANki/Missing Media/backup")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"missing_media_{profile_name}.txt")

        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                for name in sorted(missing):
                    f.write(name + "\n")
        except Exception as e:
            print(f"❌ Failed to write backup missing media file: {e}")

        return output_file, len(missing)

    def run_missing_media_check():
        path, count = export_missing_media()
        showInfo(f"✅ Missing media check complete.\n\n📦 {count} missing files saved to:\n{path}")

    run_missing_media_check()

if __name__ == "__main__":
    write_missing_file()  # which defines and runs everything inside