#!/bin/bash

# Start a simple Python HTTP server to serve the static site locally
# Usage: ./start_server.sh [port]
# Default port: 8000

PORT=${1:-8000}

echo "Starting Python HTTP server on port $PORT..."
python3 -m http.server $PORT