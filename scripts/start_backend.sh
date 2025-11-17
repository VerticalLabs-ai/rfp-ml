#!/bin/bash
# Start FastAPI backend server

set -e

echo "🚀 Starting RFP Dashboard Backend..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Navigate to project root (script is in scripts/)
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment with uv..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies with uv..."
uv pip install -r requirements_api.txt

# Navigate to API directory
cd api

# Initialize database
echo "🗄️ Initializing database..."
python -c "from app.core.database import init_db; init_db()"

# Start server
echo "✅ Starting FastAPI server on http://localhost:8000..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
