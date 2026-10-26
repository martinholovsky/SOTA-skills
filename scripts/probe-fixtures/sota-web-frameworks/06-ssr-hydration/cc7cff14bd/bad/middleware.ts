export function middleware() {
  const csp = "default-src 'self'; script-src 'self' 'unsafe-inline'";
  return csp;
}
