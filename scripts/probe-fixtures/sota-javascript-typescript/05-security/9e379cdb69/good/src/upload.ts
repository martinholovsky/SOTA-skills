import { randomUUID } from 'node:crypto';
const storage = multer.diskStorage({
  destination: 'uploads/',
  filename: (_req, _f, cb) => cb(null, randomUUID()),
});
