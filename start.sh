#!/bin/bash
# Carbon DNA Ledger Startup Script
# Starts both FastAPI backend and Streamlit UI

echo "🌱 Starting Carbon DNA Ledger..."

# Check if required environment variables are set
if [ -z "$DB_URL" ]; then
    echo "❌ ERROR: DB_URL environment variable not set"
    echo "Please set your Supabase database URL:"
    echo "export DB_URL='postgresql+psycopg2://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres'"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start the FastAPI backend
start_backend() {
    echo "🚀 Starting FastAPI backend on port 8000..."
    
    if check_port 8000; then
        echo "⚠️  Port 8000 is already in use. Skipping backend startup."
        echo "   If this is not the Carbon DNA Ledger API, please stop it and restart."
    else
        cd /app || cd .
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
        BACKEND_PID=$!
        echo "✅ FastAPI backend started (PID: $BACKEND_PID)"
    fi
}

# Function to start the Streamlit UI
start_frontend() {
    echo "🖥️  Starting Streamlit UI on port 5000..."
    
    if check_port 5000; then
        echo "⚠️  Port 5000 is already in use. Skipping frontend startup."
        echo "   If this is not the Carbon DNA Ledger UI, please stop it and restart."
    else
        cd /app || cd .
        streamlit run ui/app.py --server.port 5000 --server.address 0.0.0.0 &
        FRONTEND_PID=$!
        echo "✅ Streamlit UI started (PID: $FRONTEND_PID)"
    fi
}

# Function to wait for services to be ready
wait_for_services() {
    echo "⏳ Waiting for services to start..."
    
    # Wait for backend
    for i in {1..30}; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo "✅ Backend is ready"
            break
        fi
        echo "   Waiting for backend... ($i/30)"
        sleep 1
    done
    
    # Wait for frontend
    for i in {1..30}; do
        if curl -s http://localhost:5000/ > /dev/null 2>&1; then
            echo "✅ Frontend is ready"
            break
        fi
        echo "   Waiting for frontend... ($i/30)"
        sleep 1
    done
}

# Function to run database seeding
seed_database() {
    echo "🌱 Checking if database needs seeding..."
    
    # Try to seed the database (will skip if already seeded)
    cd /app || cd .
    if python -m app.seed; then
        echo "✅ Database seeding completed"
    else
        echo "⚠️  Database seeding had issues - check logs above"
        echo "   The application may still work if data already exists"
    fi
}

# Function to show startup information
show_info() {
    echo ""
    echo "🎉 Carbon DNA Ledger is starting up!"
    echo ""
    echo "📡 API Backend:  http://localhost:8000"
    echo "🖥️  Web UI:      http://localhost:5000"
    echo ""
    echo "🔗 Quick Links:"
    echo "   • Upload Data:     http://localhost:5000 → Upload Data"
    echo "   • Event Explorer:  http://localhost:5000 → Event Explorer" 
    echo "   • Analytics:       http://localhost:5000 → Analytics"
    echo "   • API Docs:        http://localhost:8000/docs"
    echo ""
    echo "🛑 To stop: Press Ctrl+C or kill the processes"
    echo ""
}

# Function to handle shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down Carbon DNA Ledger..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend stopped"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ Frontend stopped"
    fi
    
    echo "👋 Goodbye!"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Main execution
show_info

# Start services
start_backend
start_frontend

# Wait for services to be ready
wait_for_services

# Seed database if needed
seed_database

echo ""
echo "🎉 Carbon DNA Ledger is ready!"
echo ""
echo "🌐 Open your browser to: http://localhost:5000"
echo ""
echo "📚 Quick Start Guide:"
echo "1. Upload demo data using the Upload page"
echo "2. Explore events in the Event Explorer"
echo "3. View detailed DNA receipts in Event Details"
echo "4. Run what-if scenarios to test different parameters"
echo "5. Analyze trends in the Analytics dashboard"
echo ""
echo "⏳ Services will keep running. Press Ctrl+C to stop."

# Keep script running and wait for cleanup signal
wait
