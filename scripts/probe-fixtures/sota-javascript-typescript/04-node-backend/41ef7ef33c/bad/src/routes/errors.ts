export function errorBody(err: Error) {
  if (process.env.NODE_ENV !== 'production') return { message: err.message, stack: err.stack };
  return { message: 'Internal error' };
}
