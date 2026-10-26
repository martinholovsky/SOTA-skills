const MAX_UPLOAD_BYTES = 1_048_576;
export function readUpload(req: Req) {
  const buf = Buffer.alloc(MAX_UPLOAD_BYTES);
  return fillFrom(req, buf);
}
