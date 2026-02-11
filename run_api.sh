#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set up CUDA library paths (for GPU acceleration)
export LD_LIBRARY_PATH=$(find $(pwd)/venv/lib/python3.10/site-packages/nvidia -name "lib" -type d 2>/dev/null | paste -sd ":" -)

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Get host and port from environment or use defaults
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8000}

echo "Starting ZipClip API server..."
echo "API will be available at http://${API_HOST}:${API_PORT}"
echo "API documentation at http://${API_HOST}:${API_PORT}/docs"
echo ""

# Run the API server with uvicorn
uvicorn api:app --host $API_HOST --port $API_PORT --reload
