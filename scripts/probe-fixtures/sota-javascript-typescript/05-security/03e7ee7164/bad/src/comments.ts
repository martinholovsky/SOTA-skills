export function renderComment(el: HTMLElement, c: Comment) {
  el.innerHTML = `<p>${c.body}</p>`;
}
