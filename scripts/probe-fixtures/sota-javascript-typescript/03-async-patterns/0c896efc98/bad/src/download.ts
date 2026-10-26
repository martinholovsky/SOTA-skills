import { createReadStream, createWriteStream } from 'node:fs';
import { createGzip } from 'node:zlib';
export function compress(src: string, dst: string) {
  createReadStream(src).pipe(createGzip()).pipe(createWriteStream(dst));
}
