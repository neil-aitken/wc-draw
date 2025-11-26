#!/bin/bash

# Make sure we're in the screenshots directory
cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    npx playwright install chromium
fi

# Make sure the web server is running
echo "Starting web server..."
cd ..
python3 -m http.server 8080 &
SERVER_PID=$!
sleep 3

# Capture screenshots
cd screenshots
echo ""
echo "Capturing city views..."
npm run capture:cities

echo ""
echo "Capturing team views..."
npm run capture:teams

# Kill the web server
kill $SERVER_PID

echo ""
echo "✓ All screenshots captured!"
echo "  City views: screenshots/city_views/"
echo "  Team views: screenshots/team_views/"
