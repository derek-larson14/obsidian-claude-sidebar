export interface ClaudeSettings {
  serverType: 'anthropic' | 'private' | 'custom';
  privateServerUrl: string;
  autoDetect: boolean;
  healthPath: string;
  quickStartUrl: string;
}

export const DEFAULT_SETTINGS: ClaudeSettings = {
  serverType: 'anthropic',
  privateServerUrl: 'http://localhost:3000',
  autoDetect: true,
  healthPath: '/health',
  quickStartUrl: 'https://github.com/nicedreamzapp/claude-code-local#-quick-start-one-command',
};
