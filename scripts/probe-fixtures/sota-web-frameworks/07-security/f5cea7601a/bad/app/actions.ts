'use server'

export async function archive(id: string) {
  await db.doc.update({ where: { id }, data: { archived: true } })
}
