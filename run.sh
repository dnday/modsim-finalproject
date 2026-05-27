#!/bin/bash
# Install required backend dependencies
pip install fastapi uvicorn pydantic

# Run the FastAPI server in the background
# It mounts the dashboard directory to "/"
echo "Starting SPKLU Real-Time Interactive Dashboard..."
echo "Open your browser to: http://127.0.0.1:8080"
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
