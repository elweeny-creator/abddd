"""Launch the Streamlit app."""

import subprocess
import sys
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "src" / "pt_insights_os" / "app" / "Home.py"

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(APP_PATH)], check=True)
