export async function loadConfig(path: string) {
  const text = await readFile(path, 'utf8');
  return JSON.parse(text);
}
