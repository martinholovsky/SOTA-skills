export function startWorker(scriptUrl: string) {
  return new Worker(scriptUrl, { type: 'module' });
}
