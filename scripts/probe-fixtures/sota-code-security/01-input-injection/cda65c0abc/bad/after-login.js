const params = new URLSearchParams(window.location.search);
window.location.href = params.get("next") || "/";
