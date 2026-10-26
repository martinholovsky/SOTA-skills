export function cacheProfile(user) {
  localStorage.setItem("profile", JSON.stringify(user));
}
