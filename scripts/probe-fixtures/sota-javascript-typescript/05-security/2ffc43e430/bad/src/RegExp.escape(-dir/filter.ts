export const byPrefix = (prefix: string, names: string[]) => {
  const re = new RegExp(`^${prefix}`);
  return names.filter((n) => re.test(n));
};
