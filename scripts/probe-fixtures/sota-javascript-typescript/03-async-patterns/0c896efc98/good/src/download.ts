import { createReadStream, createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { createGzip } from 'node:zlib';
export async function compress(src: string, dst: string) {
  await pipeline(createReadStream(src), createGzip(), createWriteStream(dst));
}
