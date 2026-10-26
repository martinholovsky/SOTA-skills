export function shell(state: unknown, html: string) {
  return `<div id="root">${html}</div><script>window.__DATA__ = ${JSON.stringify(state)}</script>`
}
