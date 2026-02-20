#!/bin/bash
# Obsidian Active Note Context Hook
# Injects the currently active Obsidian note into Claude's context.
# Exits silently when Obsidian is not running — zero overhead for non-Obsidian sessions.

# Resolve obsidian CLI path
OBSIDIAN_CLI="/Applications/Obsidian.app/Contents/MacOS/obsidian"
if command -v obsidian &>/dev/null; then
  OBSIDIAN_CLI="obsidian"
elif [ ! -x "$OBSIDIAN_CLI" ]; then
  exit 0
fi

# Get active file info (fast IPC to running Obsidian, ~50ms)
# This also serves as the "is Obsidian running?" check — exits silently if not.
FILE_INFO=$("$OBSIDIAN_CLI" file 2>/dev/null)
if [ -z "$FILE_INFO" ]; then
  exit 0
fi

cat << EOF
Obsidian Active Note:
$FILE_INFO

To interact with this note, use the Obsidian CLI:
- obsidian read active          # Read full content
- obsidian outline active       # Show headings
- obsidian properties active    # Show frontmatter
- obsidian backlinks active     # Show backlinks
- obsidian search query="..."   # Search vault
EOF
