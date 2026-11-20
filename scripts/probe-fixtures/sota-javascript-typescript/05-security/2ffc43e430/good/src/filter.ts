export const byPrefix = (prefix: string, names: string[]) => {
  const re = new RegExp(`^${RegExp.escape(prefix)}`);
  return names.filter((n) => re.test(n));
};
