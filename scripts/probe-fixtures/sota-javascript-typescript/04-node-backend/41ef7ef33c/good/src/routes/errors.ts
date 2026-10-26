import { config } from '../config';
export function errorBody(err: Error) {
  if (config.exposeStack) return { message: err.message, stack: err.stack };
  return { message: 'Internal error' };
}
