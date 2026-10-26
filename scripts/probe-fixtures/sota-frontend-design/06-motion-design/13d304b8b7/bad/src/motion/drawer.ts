import { animate } from 'motion';

export const openDrawer = (el: Element) =>
  animate(el, { x: 0 }, { duration: 0.3, easing: 'ease-out' });
