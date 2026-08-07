# Claude Sidebar - Private Claude Server

This branch adds support for pointing the plugin at a local/private Claude server launched via the native (non-Docker) installer from nicedreamzapp/claude-code-local.

Quick start command the plugin offers to copy (no Docker required):

```bash
curl -fsSL https://raw.githubusercontent.com/nicedreamzapp/claude-code-local/main/setup.sh | bash
```

Example with a different model:

```bash
MODEL=gemma4-31b bash setup.sh
```

What this change includes

- New settings UI for selecting server type, server URL, health path, and auto-detect
- Buttons to open the claude-code-local quick-start README and copy the one-command installer to clipboard
- Auto-detection of common localhost ports and a Test Connection button
- Connector helpers for detection and sending requests to the configured server

Security note

The installer runs locally and should be reviewed before running. The plugin never executes the install command itself — it only copies it to your clipboard and provides documentation.
