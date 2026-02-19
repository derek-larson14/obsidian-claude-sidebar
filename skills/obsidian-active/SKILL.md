---
name: obsidian-active
description: |
  Fetch the active Obsidian note with full content, outline, and properties.
  Use when:
  - User says "this note", "the current note", "what I'm looking at"
  - Hook injected an active note path and user asks about it
  - User wants to edit, summarize, or analyze their active note
  - User says "read my note", "summarize this", "what am I working on"
---

# Obsidian Active Note

Retrieve and interact with the currently active note in a running Obsidian instance
using the Obsidian CLI (v1.12+).

## Tools

Use `Bash` with `obsidian` CLI commands to interact with the active note.

## Workflow

1. Get note metadata: `obsidian file`
2. Read full content: `obsidian read active`
3. If needed, get structure: `obsidian outline active`
4. If needed, get frontmatter: `obsidian properties active format=json`

## Related commands

- `obsidian tabs` — list all open tabs
- `obsidian backlinks active` — see what links to this note
- `obsidian links active` — see outgoing links
- `obsidian search query="term"` — search the vault
- `obsidian search:context query="term"` — search with surrounding context
- `obsidian daily:read` — read today's daily note

## Notes

- Obsidian must be running for CLI commands to work (v1.12+)
- Commands default to the active file when `active` flag is used
- Use `vault="Vault Name"` as the first parameter to target a specific vault
