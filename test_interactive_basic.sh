#!/bin/bash
# Quick test of interactive mode

echo "Testing xCode Interactive Mode"
echo "================================"
echo ""

# Test 1: Show help
echo "Test 1: Check if xcode command is available"
if command -v xcode &> /dev/null; then
    echo "✓ xcode command found"
else
    echo "✗ xcode command not found"
    exit 1
fi

# Test 2: Show version
echo ""
echo "Test 2: Check version"
xcode --version

# Test 3: Show help
echo ""
echo "Test 3: Show help"
xcode --help | head -20

echo ""
echo "================================"
echo "Basic tests passed!"
echo ""
echo "To test interactive mode manually:"
echo "  xcode --no-build-graph -i"
echo ""
echo "Then try these commands:"
echo "  /help"
echo "  /model"
echo "  /verbose"
echo "  /history"
echo "  /exit"
