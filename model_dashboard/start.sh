#!/bin/bash
# Start the Model Dashboard

echo "Starting Zone Code Extraction Model Dashboard..."
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: Please run this script from the model_dashboard directory"
    echo "  cd model_dashboard"
    echo "  ./start.sh"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import flask" 2>/dev/null || {
    echo "Error: Flask is not installed"
    echo "Please install dependencies first:"
    echo "  uv sync"
    echo "  or: pip install flask transformers torch seqeval"
    exit 1
}

# Check if models exist
if [ ! -d "../model/zoning_codes_extract/artifacts/models/extractor" ]; then
    echo "Warning: Extractor model not found at:"
    echo "  model/zoning_codes_extract/artifacts/models/extractor/"
    echo ""
    echo "You may need to train the model first or update the paths in app.py"
    echo ""
fi

# Start the server
echo "Starting Flask server..."
echo "Dashboard will be available at: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
