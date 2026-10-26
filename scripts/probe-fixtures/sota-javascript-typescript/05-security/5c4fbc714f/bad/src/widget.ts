export function bind(btn: HTMLElement, action: string) {
  btn.setAttribute('onclick', action);
}
