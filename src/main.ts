import { Plugin, Notice } from 'obsidian';
import { ClaudeSettings, DEFAULT_SETTINGS } from './settings';
import { ClaudeSettingsTab } from './settingsPane';
import { autoDetectLocalServer, testUrl, sendToServer } from './connector';

export default class ClaudePlugin extends Plugin {
  settings: ClaudeSettings;

  async onload() {
    await this.loadSettings();
    this.addSettingTab(new ClaudeSettingsTab(this.app, this));

    if ((this.settings.serverType === 'private' || this.settings.serverType === 'custom') && this.settings.autoDetect) {
      const found = await autoDetectLocalServer(this.settings.healthPath);
      if (found) {
        this.settings.privateServerUrl = found;
        await this.saveSettings();
        new Notice(`Detected local Claude server at ${found}`);
      }
    }

    // Example command to test sending a payload — plugin won't run by default
    this.addCommand({
      id: 'claude-test-send',
      name: 'Test send to configured Claude server',
      callback: async () => {
        try {
          const payload = { input: 'hello' };
          const resp = await sendToServer(this.settings.privateServerUrl, payload, '/v1/claude');
          console.log('server response', resp);
          new Notice('Sent test payload — see console for response');
        } catch (e) {
          console.error(e);
          new Notice('Failed to send to server');
        }
      }
    });
  }

  onunload() {

  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  async testServerConnection(): Promise<boolean> {
    return await testUrl(this.settings.privateServerUrl, this.settings.healthPath, 2000);
  }
}
