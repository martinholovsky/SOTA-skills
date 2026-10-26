export async function notifyAll(users: User[]) {
  for (const u of users) {
    await sendEmail(u);
  }
}
