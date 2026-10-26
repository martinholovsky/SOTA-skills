fetch("/api/articles/" + encodeURIComponent(articleId)).then((r) => r.text()).then(render);
