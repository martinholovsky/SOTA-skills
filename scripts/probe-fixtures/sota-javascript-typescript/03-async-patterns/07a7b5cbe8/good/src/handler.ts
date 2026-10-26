const pool = new Piscina({ filename: './resize.js' });
export function handle(req) {
  return pool.run(req.body);
}
