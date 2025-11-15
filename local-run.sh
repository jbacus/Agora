#!/bin/bash

# Function to start the FastAPI server
start_server() {
  echo "Starting FastAPI server..."
  # Start the frontend server in the background
(cd src/ui && echo "Starting frontend server..." && python3 -m http.server 3000) &

# Start the backend server in the background
(echo "Starting FastAPI server..." && poetry run uvicorn src.api.main:app --reload --port 8000) &

# Wait for both background processes to start before exiting
sleep 2

echo "Local environment started."
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "Use './local-run.sh stop' to stop the servers."
  echo "FastAPI server started on http://localhost:8000"
}

# Function to stop the FastAPI server
stop_server() {
  echo "Stopping FastAPI server..."
  # Stop the frontend server
echo "Stopping frontend server..."
pkill -f "python3 -m http.server 3000"

# Stop the backend server
echo "Stopping FastAPI server..."
pkill -f uvicorn
  echo "FastAPI server stopped"
}

case "$1" in
  run)
    start_server
    ;;

  stop)
    stop_server
    ;;

  restart)
    stop_server
    start_server
    ;;

  *)
    echo "Usage: $0 {run|stop|restart}"
    exit 1
esac