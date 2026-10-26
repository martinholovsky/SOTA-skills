export function renderComment(el: HTMLElement, c: Comment) {
  const p = document.createElement('p');
  p.textContent = c.body;
  el.replaceChildren(p);
}
