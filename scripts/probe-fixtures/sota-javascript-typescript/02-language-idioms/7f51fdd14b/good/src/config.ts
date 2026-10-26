export function configValue(key: string): string | undefined {
  return process.env[key.toUpperCase()];
}
