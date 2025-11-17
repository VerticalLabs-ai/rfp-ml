#!/bin/bash
# Start React frontend development server

set -e

echo "🚀 Starting RFP Dashboard Frontend..."

# Navigate to frontend directory
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start development server
echo "✅ Starting Vite dev server on http://localhost:3000..."
npm run dev
