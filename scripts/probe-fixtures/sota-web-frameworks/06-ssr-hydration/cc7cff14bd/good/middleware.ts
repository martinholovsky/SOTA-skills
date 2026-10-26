export function middleware(nonce: string) {
  const csp = `default-src 'self'; script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`;
  return csp;
}
