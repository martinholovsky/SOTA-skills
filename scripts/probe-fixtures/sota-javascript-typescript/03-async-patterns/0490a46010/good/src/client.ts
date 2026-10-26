import pRetry, { AbortError } from 'p-retry';
export async function getJson(url: string, signal?: AbortSignal) {
  return pRetry(async () => {
    const res = await fetch(url, { signal });
    if (res.status >= 400 && res.status < 500) throw new AbortError(`HTTP ${res.status}`);
    return res.json();
  }, { retries: 3, signal });
}
