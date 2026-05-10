"""TextBook Refiner — ModelScope Studio entry point.

This file is called by the Docker CMD (start.sh) which runs
both FastAPI (port 8000) and Next.js (port 7860) inside the container.
Next.js serves the frontend on port 7860 (ModelScope's exposed port)
and proxies /api/* calls to FastAPI internally.
"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(["./start.sh"], check=True)
