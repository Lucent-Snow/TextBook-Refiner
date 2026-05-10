"""TextBook Refiner — ModelScope Studio entry point.

Starts FastAPI (port 8000) and Next.js (port 7860).
Next.js serves the frontend and proxies /api/* to FastAPI.
Port 7860 is exposed for ModelScope Studio.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    print("=== TextBook Refiner ===")
    print(f"Working directory: {ROOT}")

    # Start FastAPI on port 8000
    print("[1/2] Starting FastAPI backend on port 8000...")
    backend = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
        ],
        cwd=str(ROOT),
        env={**os.environ, "LOG_LEVEL": "INFO"},
    )

    # Give FastAPI a moment to start
    time.sleep(3)
    if backend.poll() is not None:
        print("ERROR: FastAPI failed to start!")
        sys.exit(1)
    print("[1/2] FastAPI running.")

    # Start Next.js on port 7860 (ModelScope external port)
    print("[2/2] Starting Next.js frontend on port 7860...")
    frontend_dir = ROOT / "frontend"
    node_bin = os.environ.get("NODE_BIN", "node")

    frontend = subprocess.Popen(
        [node_bin, "server.js"],
        cwd=str(frontend_dir),
        env={
            **os.environ,
            "PORT": "7860",
            "HOSTNAME": "0.0.0.0",
        },
    )

    print("[2/2] Frontend running.")
    print("=== Ready: http://localhost:7860 ===")

    # Wait for either process to exit
    try:
        backend.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for proc in [frontend, backend]:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    main()
