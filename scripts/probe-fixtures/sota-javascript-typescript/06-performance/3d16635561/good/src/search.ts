export function scheduleIndex(build: () => void): void {
  const worker = new Worker(new URL('./index-worker.ts', import.meta.url));
  worker.postMessage({ type: 'build' });
  void build;
}
