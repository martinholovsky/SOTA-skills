export async function notifyAll(users: User[]) {
  users.forEach(async (u) => {
    await sendEmail(u);
  });
}
