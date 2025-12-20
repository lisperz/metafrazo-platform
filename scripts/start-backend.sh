#!/bin/bash
# Start backend development server

set -e

echo "🚀 Starting Backend Development Server..."

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Source uv environment
export PATH="$HOME/.local/bin:$PATH"

# Create/activate virtual environment using uv
echo "🐍 Setting up Python environment with uv..."
if [ ! -d ".venv" ]; then
    uv venv .venv
fi

# Activate virtual environment and install dependencies
source .venv/bin/activate
echo "📦 Installing backend dependencies..."
uv pip install -r backend/requirements.txt

# Set up logging directory
mkdir -p logs

# Check if database is accessible
echo "🗄️ Checking database connection..."
if ! uv run python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='video_text_inpainting',
        user='vti_user',
        password='vti_password_123'
    )
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    print('Please start database with: docker-compose up -d db')
    exit(1)
"; then
    echo "⚠️ Database not available. Starting database container..."
    docker-compose up -d db
    sleep 5
fi

# Set database URL for the application
export DATABASE_URL="postgresql://vti_user:vti_password_123@localhost:5432/video_text_inpainting"

# Start the backend server
echo "🔥 Starting FastAPI server..."
.venv/bin/python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000