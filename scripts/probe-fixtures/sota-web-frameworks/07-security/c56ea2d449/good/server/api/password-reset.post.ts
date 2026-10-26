export default defineEventHandler(async (event) => {
  const { email } = await readBody(event)
  const link = `${useRuntimeConfig().public.siteUrl}/reset?token=${await issueToken(email)}`
  await sendMail(email, link)
  return { ok: true }
})
