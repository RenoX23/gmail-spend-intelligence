"""Polarisk Gmail Spend Intelligence - Root Streamlit Entrypoint."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Execute main Streamlit dashboard
import runpy

if __name__ == "__main__":
    runpy.run_path(str(PROJECT_ROOT / "src" / "ui" / "app.py"), run_name="__main__")
else:
    # When executed via `streamlit run app.py`
    runpy.run_path(str(PROJECT_ROOT / "src" / "ui" / "app.py"), run_name="__main__")
