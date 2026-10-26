export function handle(req) {
  const w = new Worker('./resize.js');
  w.postMessage(req.body);
}
