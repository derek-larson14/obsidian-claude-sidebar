export async function testUrl(url: string, healthPath = '/health', timeoutMs = 2000): Promise<boolean> {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    const r = await fetch(new URL(healthPath, url).toString(), { method: 'GET', signal: controller.signal });
    clearTimeout(id);
    return r.ok;
  } catch (e) {
    return false;
  }
}

export async function autoDetectLocalServer(healthPath = '/health') : Promise<string | null> {
  const ports = [3000, 8080, 7860, 8000];
  for (const p of ports) {
    const url = `http://localhost:${p}`;
    if (await testUrl(url, healthPath, 1000)) return url;
  }
  return null;
}

export async function sendToServer(serverUrl: string, payload: any, path = '/v1/claude', timeoutMs = 20000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(new URL(path, serverUrl).toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(id);
    if (!resp.ok) throw new Error(`Server responded ${resp.status}`);
    return resp.json();
  } finally {
    clearTimeout(id);
  }
}
