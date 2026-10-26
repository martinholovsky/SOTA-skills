const params = new URLSearchParams(window.location.search);
const next = toRelativePath(params.get("next")); // "/"-rooted, no scheme or "//"
window.location.assign(next || "/");
