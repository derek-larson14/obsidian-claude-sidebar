import { App, PluginSettingTab, Setting, Notice } from 'obsidian';
import type ClaudePlugin from './main';
import { DEFAULT_SETTINGS } from './settings';

export class ClaudeSettingsTab extends PluginSettingTab {
  plugin: ClaudePlugin;

  constructor(app: App, plugin: ClaudePlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName('Server type')
      .setDesc('Choose Anthropic cloud, a private local server, or a custom URL')
      .addDropdown(drop => drop
        .addOption('anthropic', 'Anthropic (cloud)')
        .addOption('private', 'Private local (claude-code-local)')
        .addOption('custom', 'Custom URL')
        .setValue(this.plugin.settings.serverType)
        .onChange(async (value) => {
          this.plugin.settings.serverType = value as any;
          await this.plugin.saveSettings();
          this.display();
        }));

    if (this.plugin.settings.serverType !== 'anthropic') {
      new Setting(containerEl)
        .setName('Server URL')
        .setDesc('URL for your private Claude server (example: http://localhost:3000)')
        .addText(text => text
          .setPlaceholder('http://localhost:3000')
          .setValue(this.plugin.settings.privateServerUrl)
          .onChange(async (v) => {
            this.plugin.settings.privateServerUrl = v.trim();
            await this.plugin.saveSettings();
          }));

      new Setting(containerEl)
        .setName('Health path')
        .setDesc('Path to check server health (default /health). Use / if unknown.')
        .addText(text => text
          .setValue(this.plugin.settings.healthPath)
          .onChange(async (v) => {
            this.plugin.settings.healthPath = v.trim() || '/';
            await this.plugin.saveSettings();
          }));

      new Setting(containerEl)
        .setName('Auto-detect server')
        .setDesc('Scan common localhost ports for a running server')
        .addToggle(tg => tg
          .setValue(this.plugin.settings.autoDetect)
          .onChange(async (v) => {
            this.plugin.settings.autoDetect = v;
            await this.plugin.saveSettings();
          }));

      new Setting(containerEl)
        .setName('Quick start / Install')
        .setDesc('Open the claude-code-local quick-start docs to install/run a private server')
        .addButton(btn => btn
          .setButtonText('Open Quick Start')
          .onClick(() => {
            window.open(this.plugin.settings.quickStartUrl, '_blank');
          }));

      new Setting(containerEl)
        .setName('Copy install command')
        .setDesc('Copy the one-command install to your clipboard (review it before running)')
        .addButton(btn => btn
          .setButtonText('Copy Command')
          .onClick(async () => {
            const cmd = 'curl -fsSL https://raw.githubusercontent.com/nicedreamzapp/claude-code-local/main/setup.sh | bash';
            await navigator.clipboard.writeText(cmd);
            new Notice('Install command copied to clipboard — paste in a terminal to run.');
          }));

      new Setting(containerEl)
        .setName('Test connection')
        .setDesc('Try connecting to the configured server now')
        .addButton(btn => btn
          .setButtonText('Test')
          .onClick(async () => {
            const ok = await this.plugin.testServerConnection();
            new Notice(ok ? 'Server reachable' : 'Server not reachable');
          }));
    }
  }
}
