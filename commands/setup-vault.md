---
description: Set up project-level Obsidian context hooks in the current vault
allowed-tools: Bash, Write, Read
---

# Setup Vault-Level Obsidian Context

Create project-level Claude Code configuration in the current directory so the active note
hook only fires when Claude is running from this vault directory.

## Steps

1. Verify current directory is an Obsidian vault (check for `.obsidian/` directory)
2. Create `.claude/hooks/` directory
3. Write the hook script to `.claude/hooks/obsidian-active-note.sh` and make it executable.
   Use the same content as the plugin's `hooks/obsidian-active-note.sh`:

```bash
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

To interact with this note, use the Obsidian CLI:
- obsidian read active          # Read full content
- obsidian outline active       # Show headings
- obsidian properties active    # Show frontmatter
- obsidian backlinks active     # Show backlinks
- obsidian search query="..."   # Search vault
EOF
```

4. Write `.claude/settings.local.json`:

```json
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
```

5. Write `.claude/CLAUDE.md`:

```markdown
# Obsidian Vault

This is an Obsidian vault. A hook injects the active note path on every message.

## Quick Reference
- `obsidian read active` — read the open note
- `obsidian search query="..."` — search the vault
- `obsidian outline active` — note structure
- `obsidian tabs` — open tabs
- `obsidian daily:read` — today's daily note
```

6. If `.gitignore` exists, add `.claude/` to it (if not already present)

Inform the user that setup is complete and they should restart Claude Code for hooks to take effect.
