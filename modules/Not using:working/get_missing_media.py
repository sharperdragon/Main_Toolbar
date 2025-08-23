import os 
import json 
import datetime

# Update this path to your Anki profile's media directory
# Specify the name of your Anki profile here. This should match the folder name in Anki's data directory.
profile = "Random"

collection_path = os.path.expanduser(f"~/Library/Application Support/Anki2/{profile}")
media_folder = os.path.join(collection_path, "collection.media")
media_check_output = os.path.expanduser(f"/Users/claytongoddard/ANki/Missing Media/txt/missing_media_{profile}.txt")

# === Logging wrapper for Anki console output ===
def log(msg):
    print(f"[📦 Missing Media] {msg}")

def get_used_media():
    db_path = os.path.join(collection_path, "collection.anki2")
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT flds FROM notes")
        extensions = set(os.getenv("MEDIA_EXTENSIONS", ".png,.jpg,.gif,.svg").split(","))
        used = set()
        while True:
            rows = cursor.fetchmany(1000)  # Fetch 1000 rows at a time
            if not rows:
                break
            for row in rows:
                for field in row[0].split('\x1f'):
                    for ref in field.split('"'):
                        if any(ext in ref for ext in extensions):
                            name = os.path.basename(ref)
                            used.add(name)
        return used
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

def get_existing_media():
    if not os.path.exists(media_folder):
        log(f"Media folder '{media_folder}' does not exist. Please check if the profile name '{profile}' is correct or if the folder path is valid.")
        return set()
    return set(os.listdir(media_folder))

def export_missing_media():
    used = get_used_media()
    existing = get_existing_media()
    missing = used - existing
    try:
        with open(media_check_output, "w", encoding="utf-8") as f:
            for name in missing:
                f.write(f"{name}\n")
        log(f"Saved list to {media_check_output}")
    except IOError as e:
        log(f"Error: Unable to write to {media_check_output}. Details: {e}")
    log(f"Found {len(missing)} missing media files.")

# === Entry point function for Anki add-on use ===
def run():
    export_missing_media()

# === Optional: integrate with a button or menu in Anki ===
def on_run_media_check():
    from aqt.utils import showInfo
    run()
    showInfo("✅ Missing media check complete. Check the output file for details.")