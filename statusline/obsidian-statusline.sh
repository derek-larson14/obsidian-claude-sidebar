#!/bin/bash
# Obsidian Status Line for Claude Code
# Shows the active note name, context %, and cost in the status bar.
# Falls back to a standard display when Obsidian is not running.

input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
COST_FMT=$(printf '$%.2f' "$COST")

# Color thresholds for context usage
GREEN='\033[32m'; YELLOW='\033[33m'; RED='\033[31m'; DIM='\033[2m'; RESET='\033[0m'
if [ "$PCT" -ge 90 ]; then CTX_COLOR="$RED"
elif [ "$PCT" -ge 70 ]; then CTX_COLOR="$YELLOW"
else CTX_COLOR="$GREEN"; fi

# Try to get active note from Obsidian (cached for 2s to stay fast)
CACHE_FILE="/tmp/obsidian-statusline-cache"
NOTE=""

if pgrep -xq "Obsidian"; then
  OBSIDIAN_CLI="/Applications/Obsidian.app/Contents/MacOS/obsidian"
  command -v obsidian &>/dev/null && OBSIDIAN_CLI="obsidian"

  # Cache to avoid calling obsidian file on every update
  if [ ! -f "$CACHE_FILE" ] || [ $(($(date +%s) - $(stat -f %m "$CACHE_FILE" 2>/dev/null || echo 0))) -gt 2 ]; then
    NOTE_NAME=$("$OBSIDIAN_CLI" file 2>/dev/null | head -1 | sed 's/.*name[[:space:]]*//' | sed 's/[[:space:]]*$//')
    echo "$NOTE_NAME" > "$CACHE_FILE"
  fi
  NOTE=$(cat "$CACHE_FILE")
fi

if [ -n "$NOTE" ]; then
  printf '%b' "${DIM}[$MODEL]${RESET} ${NOTE} | ${CTX_COLOR}${PCT}%%${RESET} | ${DIM}${COST_FMT}${RESET}\n"
else
  printf '%b' "${DIM}[$MODEL]${RESET} ${CTX_COLOR}${PCT}%%${RESET} | ${DIM}${COST_FMT}${RESET}\n"
fi
