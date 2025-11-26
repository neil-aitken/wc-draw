#!/bin/bash

echo "============================================================"
echo "World Cup Draw Screenshot Capture"
echo "============================================================"
echo ""

# Install playwright if not already installed
echo "Installing dependencies..."
pip install playwright --quiet
playwright install chromium

echo ""
echo "Starting web server on port 8080..."
# Start server from parent directory (where HTML files are)
cd "$(dirname "$0")/.."
python3 -m http.server 8080 &
SERVER_PID=$!
sleep 3

echo ""
echo "Running screenshot capture..."
cd screenshots
python3 capture_screenshots.py

# Kill the web server
echo ""
echo "Stopping web server..."
kill $SERVER_PID

echo ""
echo "============================================================"
echo "✓ Complete!"
echo "============================================================"
echo "  City views: screenshots/city_views/"
echo "  Team views: screenshots/team_views/"
