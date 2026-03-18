#!/bin/bash
# Test script to verify the startup experience is working

echo "=================================================="
echo "Testing xCode Elegant Startup Experience"
echo "=================================================="
echo ""
echo "This will:"
echo "1. Clear Python cache"
echo "2. Run xCode in interactive mode"
echo "3. Show the elegant welcome screen with progress"
echo ""
echo "Press Ctrl+D to exit after you see it working"
echo ""
read -p "Press Enter to continue..."

# Clear cache
find /Users/elijahgjacob/xcode -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /Users/elijahgjacob/xcode -name "*.pyc" -delete 2>/dev/null

# Run xcode
cd /Users/elijahgjacob/xcode
python -m xcode.cli -i --path /Users/elijahgjacob/xcode
