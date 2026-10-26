export function bind(btn: HTMLElement, action: () => void) {
  btn.addEventListener('click', action);
}
