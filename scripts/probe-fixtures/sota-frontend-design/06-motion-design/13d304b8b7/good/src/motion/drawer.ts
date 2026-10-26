import { animate } from 'motion';
import { motion } from '../tokens/motion';

export const openDrawer = (el: Element) =>
  animate(el, { x: 0 }, { duration: motion.duration.base, easing: motion.easing.out });
