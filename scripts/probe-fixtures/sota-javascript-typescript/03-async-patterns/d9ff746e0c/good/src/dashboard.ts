export async function loadDashboard(id: string) {
  const [user, feed, ads] = await Promise.allSettled([getUser(id), getFeed(id), getAds(id)]);
  return { user, feed, ads };
}
