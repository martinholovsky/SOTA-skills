export function loadConfig(path: string) {
  return new Promise(async (resolve) => {
    const text = await readFile(path, 'utf8');
    resolve(JSON.parse(text));
  });
}
