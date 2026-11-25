"""Local, persistent TextureLab run archive (private to this computer)."""
from pathlib import Path
from datetime import datetime
import json
import uuid

RUNS = Path(__file__).resolve().parents[1] / "saved_runs"
RUNS.mkdir(parents=True, exist_ok=True)

def save_run(blob, preview, filename, parameters):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    folder = RUNS / run_id
    folder.mkdir()
    (folder / "results.zip").write_bytes(blob)
    (folder / "preview.png").write_bytes(preview)
    info = {"id": run_id, "created": datetime.now().isoformat(timespec="seconds"),
            "filename": filename, "parameters": parameters}
    (folder / "run.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return run_id

def list_runs():
    runs = []
    for path in RUNS.glob("*/run.json"):
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
            if (path.parent / "results.zip").is_file():
                runs.append(info)
        except (OSError, ValueError):
            continue
    return sorted(runs, key=lambda x: x["id"], reverse=True)

def load_run(run_id):
    if not run_id or not all(c.isalnum() or c == "_" for c in run_id):
        raise ValueError("Invalid run ID")
    folder = RUNS / run_id
    info = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    preview = folder / "preview.png"
    return info, (folder / "results.zip").read_bytes(), preview.read_bytes() if preview.exists() else None
