export async function loadDashboard(id: string) {
  const [user, feed, ads] = await Promise.all([getUser(id), getFeed(id), getAds(id)]);
  return { user, feed, ads };
}
