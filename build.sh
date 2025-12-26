#!/bin/bash
# Embeds terminal_pty.py and terminal_win.py into main.js as base64
# Run this after modifying the PTY scripts

set -e

JS_FILE="main.js"

# Unix PTY script
if [ -f "terminal_pty.py" ]; then
    B64=$(base64 -i "terminal_pty.py" | tr -d '\n')
    sed -i '' "s|PTY_SCRIPT_B64 = \"[^\"]*\"|PTY_SCRIPT_B64 = \"$B64\"|" "$JS_FILE"
    echo "✓ Embedded terminal_pty.py into $JS_FILE"
else
    echo "Warning: terminal_pty.py not found"
fi

# Windows PTY script
if [ -f "terminal_win.py" ]; then
    WIN_B64=$(base64 -i "terminal_win.py" | tr -d '\n')
    sed -i '' "s|WIN_PTY_SCRIPT_B64 = \"[^\"]*\"|WIN_PTY_SCRIPT_B64 = \"$WIN_B64\"|" "$JS_FILE"
    echo "✓ Embedded terminal_win.py into $JS_FILE"
else
    echo "Warning: terminal_win.py not found (Windows support disabled)"
fi
