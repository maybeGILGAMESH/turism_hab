from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    os.environ.setdefault("API_BASE_URL", "http://localhost:8100")
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"],
            cwd=ROOT,
        ),
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.port", "8601"],
            cwd=ROOT,
        ),
    ]
    print("Открой Хабаровский край: API http://localhost:8100, Streamlit http://localhost:8601")
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()


if __name__ == "__main__":
    main()
