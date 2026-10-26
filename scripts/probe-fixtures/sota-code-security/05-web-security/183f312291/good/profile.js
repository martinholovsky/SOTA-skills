const cache = new Map();
export function cacheProfile(user) {
  cache.set("profile", user); // in memory, gone with the tab
}
