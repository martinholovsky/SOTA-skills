export async function shutdown(code: number) {
  await server.close();
  process.exit(code);
}
