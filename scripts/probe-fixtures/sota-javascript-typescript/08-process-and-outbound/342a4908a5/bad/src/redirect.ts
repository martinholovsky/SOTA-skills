const params = new URLSearchParams(location.search);
fetch(params.get('callback') ?? '/', { credentials: 'include' }).then(render);
export {};
