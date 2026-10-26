export function startWorker() {
  return new Worker(new URL('./resize.worker.ts', import.meta.url), { type: 'module' });
}
