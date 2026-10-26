export function readUpload(req: Req) {
  const buf = Buffer.alloc(Number(req.headers['content-length']));
  return fillFrom(req, buf);
}
