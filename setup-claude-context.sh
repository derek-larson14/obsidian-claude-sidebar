#!/bin/bash
# Setup Claude Code active note integration for an Obsidian vault.
# Run from the vault root, or pass the vault path as argument.
#
# Usage:
#   cd /path/to/vault && /path/to/setup-claude-context.sh
#   /path/to/setup-claude-context.sh /path/to/vault

set -e

VAULT_DIR="${1:-.}"
VAULT_DIR="$(cd "$VAULT_DIR" && pwd)"

if [ ! -d "$VAULT_DIR/.obsidian" ]; then
  echo "Error: $VAULT_DIR is not an Obsidian vault (.obsidian/ not found)"
  exit 1
fi

echo "Setting up Claude Code integration in: $VAULT_DIR"

mkdir -p "$VAULT_DIR/.claude/hooks"

# Write hook script
cat > "$VAULT_DIR/.claude/hooks/obsidian-active-note.sh" << 'HOOKSCRIPT'
#!/bin/bash
if ! pgrep -xq "Obsidian"; then exit 0; fi
OBSIDIAN_CLI="/Applications/Obsidian.app/Contents/MacOS/obsidian"
if command -v obsidian &>/dev/null; then OBSIDIAN_CLI="obsidian"
elif [ ! -x "$OBSIDIAN_CLI" ]; then exit 0; fi
FILE_INFO=$("$OBSIDIAN_CLI" file 2>/dev/null)
if [ -z "$FILE_INFO" ]; then exit 0; fi
cat << EOF
Obsidian Active Note:
$FILE_INFO

Use the Obsidian CLI to interact: obsidian read active, obsidian search query="...", etc.
EOF
HOOKSCRIPT
chmod +x "$VAULT_DIR/.claude/hooks/obsidian-active-note.sh"

# Write project-level settings
cat > "$VAULT_DIR/.claude/settings.local.json" << 'SETTINGS'
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/obsidian-active-note.sh"
          }
        ]
      }
    ]
  }
}
SETTINGS

# Write vault CLAUDE.md
cat > "$VAULT_DIR/.claude/CLAUDE.md" << 'CLAUDEMD'
# Obsidian Vault

A hook injects the active note path on every message.

- `obsidian read active` — read the open note
- `obsidian search query="..."` — search the vault
- `obsidian outline active` — note structure
- `obsidian tabs` — open tabs
CLAUDEMD

# Add .claude/ to .gitignore if applicable
if [ -f "$VAULT_DIR/.gitignore" ]; then
  grep -qx '\.claude/' "$VAULT_DIR/.gitignore" || echo '.claude/' >> "$VAULT_DIR/.gitignore"
fi

echo "Done! Restart Claude Code for hooks to take effect."
