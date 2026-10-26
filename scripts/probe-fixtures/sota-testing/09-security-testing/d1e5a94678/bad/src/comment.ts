import DOMPurify from 'dompurify';

export function renderComment(el: HTMLElement, html: string) {
  el.innerHTML = DOMPurify.sanitize(html);
}
