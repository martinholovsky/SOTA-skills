export async function importCsv(path: string) {
  const rows = await parse(path);
  if (rows.length === 0) process.exit(1);
  await repo.bulkInsert(rows);
}
