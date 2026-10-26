export function Clock() {
  return <time>{new Date().toLocaleTimeString()}</time>
}
