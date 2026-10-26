export function isRetryable(err: Error) {
  return err.message.includes('ECONNRESET');
}
