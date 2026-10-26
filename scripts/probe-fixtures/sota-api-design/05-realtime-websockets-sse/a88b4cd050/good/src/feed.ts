import { config } from './config';

const es = new EventSource(config.eventsUrl, { withCredentials: true });
es.onmessage = (e) => render(JSON.parse(e.data));
