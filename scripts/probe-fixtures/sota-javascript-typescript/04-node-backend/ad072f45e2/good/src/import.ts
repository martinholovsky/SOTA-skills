export async function importCsv(path: string) {
  const rows = await parse(path);
  if (rows.length === 0) throw new ImportError(`empty file: ${path}`);
  await repo.bulkInsert(rows);
}
