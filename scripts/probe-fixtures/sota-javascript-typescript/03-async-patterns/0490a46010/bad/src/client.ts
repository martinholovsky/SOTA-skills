export async function getJson(url: string) {
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      return await (await fetch(url)).json();
    } catch {
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
  throw new Error('unreachable');
}
