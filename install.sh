#!/bin/bash
# Copy the built plugin into a vault. Pass a vault path, or symlink instead
# (see README "Development") for a live loop that needs no re-run.
set -e

VAULT="${1:-}"
if [ -z "$VAULT" ]; then
    echo "Usage: ./install.sh /path/to/vault"
    exit 1
fi
if [ ! -d "$VAULT/.obsidian" ]; then
    echo "Not an Obsidian vault (no .obsidian): $VAULT"
    exit 1
fi

DEST="$VAULT/.obsidian/plugins/claude-sidebar"
mkdir -p "$DEST"
cp main.js manifest.json styles.css "$DEST/"
echo "✓ Installed $(node -p "require('./manifest.json').version") to $DEST"
echo "  Reload the plugin in Obsidian: Settings → Community plugins → toggle off/on"
