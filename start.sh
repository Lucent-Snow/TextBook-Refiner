#!/bin/bash
set -e

echo "=== TextBook Refiner ==="
echo "Starting FastAPI backend on port 8000..."

cd /home/user/app
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
sleep 2

echo "Starting Next.js frontend on port 7860..."
cd /home/user/app/frontend
PORT=7860 HOSTNAME=0.0.0.0 node server.js
