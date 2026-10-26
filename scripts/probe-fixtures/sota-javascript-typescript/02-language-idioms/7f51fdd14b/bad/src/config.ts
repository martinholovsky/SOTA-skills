export const config = new Proxy({} as Record<string, string>, {
  get: (_t, key: string) => process.env[key.toUpperCase()],
});
