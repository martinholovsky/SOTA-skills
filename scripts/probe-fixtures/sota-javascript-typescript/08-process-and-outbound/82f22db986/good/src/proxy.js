const res = await got(url, {
  headers: { authorization: `Bearer ${token}` },
  followRedirect: false,
});
