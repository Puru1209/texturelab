import os
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
frontend_app = here / "frontend" / "app.py"

if not frontend_app.exists():
    frontend_app = here / "SIP_GLCM_Project" / "texturelab_project" / "frontend" / "app.py"

sys.path.insert(0, str(frontend_app.parents[1]))
sys.path.insert(0, str(frontend_app.parent))
os.chdir(str(frontend_app.parents[1]))

import runpy
runpy.run_path(str(frontend_app), run_name="__main__")
