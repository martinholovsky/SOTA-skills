export const backoff = (fn: () => void) => setTimeout(fn, 500);
