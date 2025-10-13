#!/bin/bash

# Carbon DNA Ledger Startup Script with Climate TRACE Integration
echo "🌱 Starting Carbon DNA Ledger with Climate TRACE Integration..."

# Set environment variables
export COMPLIANCE_CT_ENABLED=true
export CT_SYNC_INTERVAL_HOURS=24
export CT_LOOKBACK_MONTHS=12

echo "✅ Environment variables set:"
echo "   COMPLIANCE_CT_ENABLED=$COMPLIANCE_CT_ENABLED"
echo "   CT_SYNC_INTERVAL_HOURS=$CT_SYNC_INTERVAL_HOURS"
echo "   CT_LOOKBACK_MONTHS=$CT_LOOKBACK_MONTHS"

# Kill any existing servers
echo "🔄 Stopping existing servers..."
pkill -f uvicorn 2>/dev/null || true
pkill -f streamlit 2>/dev/null || true
sleep 2

# Start FastAPI server
echo "🚀 Starting FastAPI server on port 8000..."
python3 -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1 &
FASTAPI_PID=$!

# Wait for FastAPI to start
sleep 5

# Test FastAPI
echo "🔍 Testing FastAPI server..."
if curl -s http://127.0.0.1:8000/ > /dev/null; then
    echo "✅ FastAPI server is running"
else
    echo "❌ FastAPI server failed to start"
    exit 1
fi

# Start Streamlit server
echo "🚀 Starting Streamlit server on port 8501..."
streamlit run ui/app.py --server.port 8501 --server.headless true &
STREAMLIT_PID=$!

# Wait for Streamlit to start
sleep 5

# Test Streamlit
echo "🔍 Testing Streamlit server..."
if curl -s http://127.0.0.1:8501/ > /dev/null; then
    echo "✅ Streamlit server is running"
else
    echo "❌ Streamlit server failed to start"
    exit 1
fi

echo ""
echo "🎉 Carbon DNA Ledger is now running!"
echo ""
echo "📊 Streamlit UI: http://127.0.0.1:8501"
echo "🔌 FastAPI Backend: http://127.0.0.1:8000"
echo "🌍 Climate TRACE Integration: ENABLED"
echo ""
echo "💡 To access Climate TRACE features:"
echo "   1. Go to http://127.0.0.1:8501"
echo "   2. Navigate to '🌍 Climate TRACE' tab"
echo "   3. Run cross-check analysis"
echo ""
echo "🛑 To stop servers: Ctrl+C or run 'pkill -f uvicorn && pkill -f streamlit'"
echo ""

# Keep script running
wait
