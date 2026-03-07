#!/bin/bash
# Start Celery Beat Scheduler for periodic tasks

set -e

echo "⏰ Starting Celery Beat Scheduler..."

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Source uv environment
export PATH="$HOME/.local/bin:$PATH"

# Activate virtual environment
source .venv/bin/activate

# Set up logging directory
mkdir -p logs

# Check if Redis is accessible
echo "🔴 Checking Redis connection..."
if ! python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, password='redis_password_123')
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
    print('Please start Redis with: docker-compose up -d redis')
    exit(1)
"; then
    echo "⚠️ Redis not available. Starting Redis container..."
    docker-compose up -d redis
    sleep 5
fi

# Start Celery beat
echo "⏰ Starting Celery beat scheduler..."
echo "📋 This will check for embedded job completion every 30 seconds"
cd backend
celery -A workers.celery_app beat --loglevel=info --logfile=../logs/beat.log
