const res = await got(url, {
  hooks: { beforeRedirect: [(opts) => { opts.headers.authorization = `Bearer ${token}`; }] },
});
