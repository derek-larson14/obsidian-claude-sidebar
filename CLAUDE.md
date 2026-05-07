# Claude Sidebar - Agent Guide

Congrats, your user wants you to help them contribute to the Obsidian Claude Sidebar plugin. Your job is to help them produce a good contribution: a clean bug report, or a focused PR that fits what this plugin is, and is easy for the maintainer. 

Repo: https://github.com/derek-larson14/obsidian-claude-sidebar

## What this plugin does

Make agents feel native in Obsidian. The plugin runs the terminal that hosts the agent and routes Obsidian actions to it. It does not own anything else. The agent CLI (Claude Code, Codex, OpenCode, Gemini, Kimi Code, GitHub Copilot, Pi) handles auth, models, billing, and its own UI.

## Two things you can help the user do

1. **File a bug report.** You hit something but don't have a fix. Diagnose (Step 1), then open an issue with the diagnostic block.
2. **Open a PR.** (preferred) You have a fix or a small feature you want to propose. Diagnose, fix, test, then PR.

## Step 1: Diagnose

Run through this list. The maintainer will ask for everything in it on every issue, so paste the block into your report. If you're opening a PR, use the same info as context for figuring out the fix.

**Required (issues):**
- Plugin version (Settings → Community plugins → Claude Sidebar - or read `manifest.json`)
- Install method (BRAT / manual / Obsidian community store)
- CLI backend and version (`claude --version` or equivalent for your backend)
- Obsidian version + installer version (Settings → About - both numbers)
- OS and how Obsidian was installed
  - Linux: snap, AppImage, deb, Flatpak
  - Windows: installer or Microsoft Store
  - Mac: dmg or Homebrew
- Other plugins active that touch hotkeys, layout, or terminals (BRAT, iconize, Vimrc). Load-order interactions cause real bugs.

**Required for crashes or freezes:**
- Developer console output. Open with `Cmd-Option-I` on Mac, `Ctrl-Shift-I` on Windows/Linux. Copy any errors from the Console tab.

**Already tried (check what applies):**
- Restarted Obsidian
- Disabled other plugins
- Updated to latest plugin version
- Tested in a fresh empty vault

**Windows-specific:**
- Read the actual Python error from the terminal output first - `terminal_win.py` prints `sys.executable` and a pip command on import failure
- If no obvious error: output of `where python` and `where py`, and whether you're using pyenv, conda, or a virtualenv

If your agent has shell access, it can collect most of this for you.

## Step 2a: File a bug report

If you don't have a fix, open an issue at https://github.com/derek-larson14/obsidian-claude-sidebar/issues with the diagnostic block above plus:
- What happened
- What you expected
- Steps to reproduce (numbered, exact)

## Step 2b: Open a PR

The fast loop: edit `main.js` in your vault, reload Obsidian (`Cmd-R` on Mac, `Ctrl-R` on Windows/Linux), confirm the fix, copy to a fork, open a PR against `main` (the agent can help with much of this).

If you installed via BRAT, disable auto-update for this plugin while you iterate - BRAT will overwrite your edits.

If you're going to iterate often, symlink your fork into a vault to skip the copy step:

```bash
ln -s /path/to/your/fork /path/to/vault/.obsidian/plugins/claude-sidebar
```

Test in both the sidebar pane and a main-area tab - different layout code paths.

### Python fixes (PTY backend)

If your bug looks like one of these, it's likely Python:

- Orphaned processes after closing a tab, idle CPU spin, kill signals not propagating
- CJK or multi-byte character corruption in terminal output
- Terminal won't resize at all (vs. resizing but rendering wrong)
- Windows: pywinpty errors, ConPTY-specific issues
- Terminal capability queries (DA1/DA2/DSR) breaking cmd.exe or the shell

The two files:

- `terminal_pty.py` - Mac and Linux. Forks a child shell via `pty.fork()` (the shell is whatever the user has configured - not always bash), relays stdin/stdout, parses RESIZE escape sequences, sends SIGTERM-then-SIGKILL to the process group on cleanup.
- `terminal_win.py` - Windows. Spawns via pywinpty, handles UTF-8 multi-byte sequences across read boundaries, filters terminal protocol responses (DA1/DA2/DSR) so cmd.exe doesn't break.

These files aren't installed in your vault. They're embedded as base64 in `main.js`. To fix Python you need a clone:

1. Fork and clone the repo.
2. Edit the relevant file.
3. Run `bash build.sh` to re-embed as base64 into `main.js`.
4. Copy the rebuilt `main.js` into your vault, reload Obsidian, and test.
5. Commit, push, open a PR.

### Rules for any PR

- **Make ONE change at a time.**
- **Don't bump `manifest.json`.**
- **Test the surface you touched, plus one nearby.**
- **In the PR description, include:**
  - What was wrong
  - What you changed
  - What you tested it on (which OS, which CLI backend)

## Things we like to see:

1. **Routing an Obsidian-native action into the terminal** - file paths, selections, clipboard images, folder context menus, ribbon actions.
2. **Bug fixes / regressions** that break the existing experience.

## Things we do not like to see:

The plugin does one thing: route Obsidian actions into a terminal that runs a vanilla agent CLI. Stuff outside that usually gets pushed back.

- **Auth, API keys, model names, billing.** Those belong to the agent CLI, not the plugin.
- **New settings, unless there's no other way.** Every setting is something to maintain, document, and migrate. If existing settings can handle it (e.g. with per-backend flags) or the CLI itself already exposes the option the answer is probably no.
- **Bundling or modifying the agent's distribution files.** Don't install or modify Claude Code's skills, hooks, output styles, `.claude-plugin/` files, etc. Those have their own marketplaces.
- **Big changes for small gains.** New complexity tends to be a pain to debug and maintain, it should add up to something that meaningfully improves the experience, not polish for a niche case.

If a proposal feels close to one of these, raise the potential concern with the user before writing code, and see if there is a better way. If there's friction, suggest opening an issue to discuss with the maintainer first.

## Tread carefully

These areas have absorbed fixes-on-fixes. If your change touches one, expect more scrutiny, and do more testing.

1. **Scroll position management.** Many fixes-on-fixes, including ones that reverted prior fixes. If your fix needs a tunable grace period, you probably haven't found the race condition.
2. **Hotkey scope.** Three sequential versions to fix Ctrl-O. Global handler registration breaks Obsidian's command palette and Quick Switcher. Use dynamic scope on `focusin` / `focusout`. Never global.
3. **Windows PTY lifecycle.** Many versions, many PRs. Test with BRAT and iconize loaded - they trigger startup race conditions other plugins don't.
4. **Workspace state restore.** `TerminalView.unload` errors on layout restore are a recurring bug class.
5. **Process cleanup on tab close.** POSIX process group semantics differ across Linux and macOS. Log pgid and parent pid when debugging.
6. **macOS Option-key with international layouts.** Use `term.paste(char)` rather than feeding the keystroke into xterm input - Electron's IME consumes the underlying keydown event.
7. **PATH / shell-rc detection on Unix.** There's a 5s timeout because heavy `.zshrc` files were timing out - keep that in mind before adding sync work to that path.

## Architecture (TL;DR)

```
Obsidian View → xterm.js → Python PTY wrapper → shell → CLI binary
```

The plugin owns the xterm.js terminal and the wrapper script. The wrapper spawns the user's shell (bash/zsh/fish on Unix, cmd or wsl on Windows) which runs the CLI. JS sends keystrokes and resize escape sequences down stdin. Python relays output back up stdout.

The only custom thing in the protocol is the resize sequence: `\x1b]RESIZE;cols;rows\x07`. Everything else is raw terminal I/O.

## Repo layout

- `main.js` - the entire plugin, single file, edited directly (no build step for JS). The top of the file is vendored xterm.js + addons - don't touch anything above the plugin code. Plugin code lives near the end of the file (search for `extends Plugin` or `class` definitions to find the entry point).
- `terminal_pty.py` - Unix and Mac PTY wrapper. Embedded as base64 in `main.js`.
- `terminal_win.py` - Windows ConPTY wrapper. Embedded as base64 in `main.js`.
- `build.sh` - re-embeds the .py files into `main.js`. Run after editing the .py files.
- `manifest.json` - plugin metadata. Don't bump the version.
- `styles.css` - plugin styles.
- `README.md` - user-facing.
- `AGENTS.md` - one-line pointer to this file, for agents that look there first.

## Platform support

Mac is the primary test machine of the core maintainer. Windows and Linux are tested by contributors, and most platform-specific fixes ship from contributor PRs. Two implications:

- If you're on Windows or Linux, the bar for testing is higher. The maintainer can't easily verify your bug / change, so do the work to be sure it fixes the thing and does not create new bugs.
- The bar is also higher for changes that *add* complexity to Windows or Linux code paths. Future bugs there will be hard to debug without you, so the upside has to be worth the ongoing cost.

Mobile is a separate plugin: https://github.com/derek-larson14/claude-anywhere.

## After you submit

Once a PR is in, the maintainer will take a look, leave comments, and merge or push back. Iteration is normal - if a fix lands but doesn't fully resolve the bug, just say so and keep going. After merge, the maintainer tags a release; BRAT users update once the tag is up.
