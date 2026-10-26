fetch(location.hash.slice(1)).then((r) => r.text()).then(render);
