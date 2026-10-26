export function isRetryable(err: unknown) {
  return err instanceof NetworkError && err.code === 'ECONNRESET';
}
