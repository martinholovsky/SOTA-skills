export default defineEventHandler(async (event) => {
  const { email } = await readBody(event)
  const link = `https://${getRequestHost(event)}/reset?token=${await issueToken(email)}`
  await sendMail(email, link)
  return { ok: true }
})
