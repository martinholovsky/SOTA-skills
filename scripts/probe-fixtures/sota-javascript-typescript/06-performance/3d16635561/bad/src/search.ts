export function scheduleIndex(build: () => void): void {
  requestIdleCallback(() => build());
}
