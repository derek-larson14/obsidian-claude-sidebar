#!/bin/bash
# Embeds terminal_pty.py into main.js as base64
# Run this after modifying terminal_pty.py

set -e

PYTHON_FILE="terminal_pty.py"
JS_FILE="main.js"

if [ ! -f "$PYTHON_FILE" ]; then
    echo "Error: $PYTHON_FILE not found"
    exit 1
fi

# Base64 encode (single line)
B64=$(base64 -i "$PYTHON_FILE" | tr -d '\n')

# Replace the PTY_SCRIPT_B64 value in main.js
sed -i '' "s|PTY_SCRIPT_B64 = \"[^\"]*\"|PTY_SCRIPT_B64 = \"$B64\"|" "$JS_FILE"

echo "✓ Embedded $PYTHON_FILE into $JS_FILE"
