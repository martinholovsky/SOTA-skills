const params = new URLSearchParams(location.search);
const target = new URL(params.get('callback') ?? '/', location.origin);
if (target.origin === location.origin) fetch(target, { credentials: 'include' }).then(render);
export {};
