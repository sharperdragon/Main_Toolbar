from __future__ import annotations

from aqt import mw
from aqt.utils import showInfo, askUser
import json
from pathlib import Path
from typing import Dict, Any

# Path to the central Change_notes config.json
CONFIG_PATH = Path("/Users/claytongoddard/Library/Application Support/Anki2/addons21/Change_notes/config.json")

def _default_cfg() -> Dict[str, Any]:
    return {
        "protected_notes": [],
        "confirm": True,
    }

def _load_delete_cfg() -> Dict[str, Any]:
    defaults = _default_cfg()
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            sect = data.get("delete_empty_notes_config", {})
            return {
                "protected_notes": list(sect.get("protected_notes", defaults["protected_notes"])),
                "confirm": bool(sect.get("confirm", defaults["confirm"]))
            }
    except Exception:
        pass
    return defaults

def delete_empty_note_types() -> None:
    """Delete all note types (models) that currently have zero cards.

    Respects settings in Change_notes/config.json → "delete_empty_notes_config":
      - protected_notes: list of model names that must never be deleted
      - confirm: if True, prompt for confirmation before deletion
    """
    col = mw.col
    cfg = _load_delete_cfg()
    protected = set(cfg.get("protected_notes", []))

    models = col.models.all()
    to_delete_names = []

    for model in models:
        model_name = model.get("name", "")
        if model_name in protected:
            continue
        count = col.db.scalar(
            "SELECT COUNT() FROM cards WHERE nid IN (SELECT id FROM notes WHERE mid=?)",
            model["id"],
        )
        if count == 0:
            to_delete_names.append(model_name)

    if not to_delete_names:
        showInfo("No note types have zero cards.")
        return

    summary = "Note types with zero cards:\n- " + "\n- ".join(to_delete_names)

    if cfg.get("confirm", True):
        if not askUser(summary + "\n\nDelete these note types now?"):
            showInfo("Deletion cancelled.")
            return

    by_name = {m.get("name", ""): m for m in col.models.all()}
    deleted = 0
    for name in to_delete_names:
        m = by_name.get(name)
        if m:
            col.models.rem(m)
            deleted += 1

    mw.reset()
    showInfo(f"Deleted {deleted} note types with zero cards.")