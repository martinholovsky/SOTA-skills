const params = new URLSearchParams(window.location.search);
const es = new EventSource(params.get('stream') ?? '/events');
es.onmessage = (e) => render(JSON.parse(e.data));
