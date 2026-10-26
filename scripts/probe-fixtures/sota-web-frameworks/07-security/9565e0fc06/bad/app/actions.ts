'use server'

export async function updateProfile(form: FormData) {
  await db.user.update({ where: { id: String(form.get('id')) }, data: { name: String(form.get('name')) } })
}
