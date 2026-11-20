export const page = (state: State, html: string) =>
  `<div id="root">${html}</div><script>window.__STATE__ = ${JSON.stringify(state).replace(/</g, '\\u003c')}</script>`;
