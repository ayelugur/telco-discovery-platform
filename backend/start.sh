#!/bin/bash
# Start the Telco Discovery Platform backend
set -e

cd "$(dirname "$0")"

# Check for .env
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example to .env and add your ANTHROPIC_API_KEY."
  exit 1
fi

# Load env
export $(grep -v '^#' .env | xargs)

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_api_key_here" ]; then
  echo "ERROR: ANTHROPIC_API_KEY not set in .env"
  exit 1
fi

echo "Starting Telco Discovery Platform backend..."
echo "  API: http://localhost:${PORT:-8000}"
echo "  Docs: http://localhost:${PORT:-8000}/docs"
echo ""

uvicorn main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --reload
